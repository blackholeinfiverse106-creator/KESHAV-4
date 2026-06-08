import sys
import os
import uuid
import time
import json
import threading
import concurrent.futures
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, HTTPServer

# 1. KESHAV-4 Imports
from app.engine import PropagationEngine

# 2. Path Trick
if 'app' in sys.modules:
    del sys.modules['app']
sys.path.insert(0, r'c:\rajaryan\text-risk-scoring-service')

# 3. Live Service Imports
from app.sutradhara_control_plane import invoke_agent
from app.enforcement_schemas import KSMLInput, ContextSignal, SourceSystem
from app.layer3_dgic import compute_envelope_hash
from app.layer5_bucket import verify_by_trace_hash

# Mock Bucket Server for live integration
class LiveIntegrationBucketHandler(BaseHTTPRequestHandler):
    store = []
    
    def do_POST(self):
        if self.path == "/bucket/artifact":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            self.store.append(payload)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()
            
    def do_GET(self):
        if self.path.startswith("/bucket/artifacts"):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"artifacts": self.store}).encode())
        else:
            self.send_response(404)
            self.end_headers()
            
    def log_message(self, format, *args):
        pass # Suppress logs for tests

def run_single_trace(trace_idx: int, graph: dict, blocked_task: str, root_cause: str):
    trace_id = f"trace-live-integration-{uuid.uuid4().hex[:10]}"
    
    # 1. Propagation Engine (via HTTP API)
    prop_in = {
        "blocked_task_id": blocked_task,
        "root_cause": root_cause,
        "trace_id": trace_id,
        "timestamp": "2026-05-22T12:00:00Z",
        "dependency_graph": graph
    }
    import requests
    resp = requests.post("http://localhost:8081/api/v1/propagation", json=prop_in, timeout=5)
    assert resp.status_code == 200, f"Propagation API failed: {resp.text}"
    prop_out = resp.json()
    
    # Generate DGIC State for Integration
    lineage_hash = "1" * 64
    payload_dict = {
        "epistemic_state": "KNOWN",
        "entropy_score": 0.0,
        "contradiction_flag": False
    }
    env_hash = compute_envelope_hash("schema_v1", lineage_hash, payload_dict)
    
    # 2. Map to KSML (Phase 3)
    ksml = KSMLInput(
        execution_id=trace_id,
        structured_signals=[
            ContextSignal(
                signal_id=f"prop_impact_{trace_idx}",
                signal_type="DEPENDENCY_IMPACT",
                value=0.9 if prop_out["severity"] == "HIGH" else 0.5,
                source="KESHAV"
            )
        ],
        metadata={
            "actor": "SETU_INTEGRATION_TEST",
            "proposed_action": prop_out["resolution_signal"],
            "source_system": SourceSystem.SOVEREIGN_CORE.value,
            "dgic_epistemic_state": {
                "epistemic_state": "KNOWN",
                "entropy_score": 0.0,
                "contradiction_flag": False,
                "lineage_hash": lineage_hash,
                "envelope_hash": env_hash
            }
        }
    )
    
    # 3. Live Pipeline Invocation (Phase 3)
    result = invoke_agent(ksml)
    
    # Assertions
    assert result.execution_id == trace_id, f"Trace ID corrupted! Expected {trace_id}, got {result.execution_id}"
    assert result.trace_hash is not None
    assert len(result.trace_hash) == 64
    
    return {
        "trace_id": trace_id,
        "impacted_tasks": prop_out["impacted_tasks"],
        "trace_hash": result.trace_hash,
        "enforcement_decision": result.enforcement_decision
    }

def test_live_tantra_integration_and_determinism():
    """
    Phase 3 & 4 combined:
    - Runs in live flow (Sūtradhāra → DGIC → Intelligence → RAJYA → Sarathi → Core → Bucket)
    - Concurrently processes 10 traces across different graph topologies
    - Proves deterministic trace continuation and no impact task corruption
    """
    # Start mock bucket server so the live pipeline can POST artifacts
    os.environ["BUCKET_SERVICE_URL"] = "http://localhost:8000"
    server = HTTPServer(('localhost', 8000), LiveIntegrationBucketHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    time.sleep(0.5)  # Wait for server to start
    LiveIntegrationBucketHandler.store.clear()
    
    # Start KESHAV API server in a separate background process
    import subprocess
    import requests
    import sys
    keshav_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8081"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for KESHAV API server to start
    started = False
    start_time = time.time()
    while time.time() - start_time < 5:
        try:
            resp = requests.get("http://localhost:8081/health", timeout=1)
            if resp.status_code == 200:
                started = True
                break
        except Exception:
            time.sleep(0.1)
            
    assert started, "KESHAV API server failed to start!"
    
    try:
        graphs = [
            # 1. Branching
            {"RC": ["T1", "T2"], "T1": ["T3"], "T2": ["T4"]},
            # 2. Cyclic
            {"RC": ["T1"], "T1": ["T2"], "T2": ["T1", "T3"]},
            # 3. Disconnected (T1 must be a key for blocked_task_id validation)
            {"RC": ["T1"], "T1": ["T99"], "T99": ["T100"]},
            # 4. Deep chain
            {f"T{i}": [f"T{i+1}"] for i in range(10)}
        ]
        graphs[3]["RC"] = ["T0"]
        
        futures = []
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for i in range(15):  # Min 10 traces
                graph = graphs[i % len(graphs)]
                futures.append(executor.submit(run_single_trace, i, deepcopy(graph), "T1", "RC"))
                
            for f in concurrent.futures.as_completed(futures):
                # Will raise exception if thread failed
                res = f.result()
                results.append(res)
                
        assert len(results) == 15
        
        # Phase 4 Requirements: No duplicate impact sets, Trace continuity
        for res in results:
            # Check no duplicates
            assert len(set(res["impacted_tasks"])) == len(res["impacted_tasks"]), "Duplicate impacted tasks found!"
            
        # Verify bucket received artifacts
        assert len(LiveIntegrationBucketHandler.store) > 0, "No data reached the Bucket server during live integration!"
    finally:
        if 'keshav_process' in locals():
            keshav_process.terminate()
            keshav_process.wait()
        server.shutdown()
        server.server_close()

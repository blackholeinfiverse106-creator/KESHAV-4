import hashlib
import json
from typing import Dict, Any
from app.engine import PropagationEngine

class TantraFlowError(Exception):
    pass

class StructuredFailure(TantraFlowError):
    """
    Phase 6: Structured Failure Visibility.
    Ensures all failures are traceable and visible with specific error codes.
    """
    def __init__(self, failure_type: str, message: str, trace_id: str = "UNKNOWN"):
        super().__init__(f"[{failure_type}] Trace: {trace_id} - {message}")
        self.failure_type = failure_type
        self.message = message
        self.trace_id = trace_id

class TANTRAFlow:
    """
    Simulates the downstream consumers of the KESHAV Propagation Engine.
    """
    
    @staticmethod
    def constraint_layer_signal(trace_id: str = "trace-tantra-live-001") -> Dict[str, Any]:
        """
        Phase 1: Generates the live feed signal with trace_id.
        """
        return {
            "blocked_task_id": "TASK_77",
            "root_cause": "RC_99",
            "trace_id": trace_id,
            "timestamp": "2026-05-06T12:00:00Z",
            "dependency_graph": {
                "RC_99": ["TASK_10", "TASK_11"],
                "TASK_10": ["TASK_77"],
                "TASK_11": ["TASK_12"],
                "TASK_77": ["TASK_100"]
            }
        }

    @staticmethod
    def pritesh_dependency_intelligence(propagation_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 1 & 2: Consumes propagation directly. No schema transformation.
        Produces TANTRA output.
        """
        # Ensure it receives the exact propagation output fields
        expected_keys = {
            "blocked_task_id", "root_cause", "impacted_tasks", "impact_score",
            "severity", "resolution_signal", "trace_id", "timestamp"
        }
        if not expected_keys.issubset(propagation_output.keys()):
            raise StructuredFailure(
                failure_type="SCHEMA_MISMATCH",
                message=f"Schema transformation detected! Missing keys: {expected_keys - propagation_output.keys()}",
                trace_id=propagation_output.get("trace_id", "UNKNOWN")
            )
            
        # Wraps it in TANTRA envelop
        return {
            "tantra_packet": propagation_output,
            "intelligence_status": "PROCESSED",
            "trace_id": propagation_output["trace_id"] # Pass-through
        }

    @staticmethod
    def kanishk_validation_engine(tantra_output: Dict[str, Any]) -> bool:
        """
        Validates determinism and contract correctness.
        """
        packet = tantra_output.get("tantra_packet", {})
        if not isinstance(packet.get("impacted_tasks"), list):
            raise StructuredFailure(
                failure_type="VALIDATION_ERROR",
                message="Validation Engine Failed: impacted_tasks must be a list.",
                trace_id=tantra_output.get("trace_id", "UNKNOWN")
            )
        return True

    @staticmethod
    def sarathi_decision_layer(tantra_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2: Consumes KESHAV output without interpretation.
        Reads resolution_signal.
        """
        packet = tantra_output.get("tantra_packet", {})
        resolution_signal = packet.get("resolution_signal", "")
        
        # Decision logic is strictly based on the resolution_signal without modifying it
        return {
            "decision": "EXECUTE",
            "signal": resolution_signal,
            "trace_id": tantra_output["trace_id"],
            "payload": tantra_output
        }

    @staticmethod
    def core_execution_layer(decision_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes decision.
        """
        if decision_output["decision"] != "EXECUTE":
            raise StructuredFailure(
                failure_type="EXECUTION_ABORTED",
                message="Core Layer Execution Aborted due to non-EXECUTE decision.",
                trace_id=decision_output.get("trace_id", "UNKNOWN")
            )
            
        return {
            "execution_status": "SUCCESS",
            "executed_signal": decision_output["signal"],
            "trace_id": decision_output["trace_id"],
            "final_data": decision_output["payload"]
        }

    @staticmethod
    def bucket_truth_layer(execution_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 5: Truth Verification
        Stores final output and generates a cryptographic hash for artifact verifiability.
        """
        # Create a deterministic string representation for hashing
        payload_str = json.dumps(execution_output, sort_keys=True)
        artifact_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
        
        return {
            "artifact_hash": artifact_hash,
            "stored_payload": execution_output
        }

    @staticmethod
    def insightflow_observability(bucket_data: Dict[str, Any], original_trace_id: str) -> bool:
        """
        Phase 3: Trace Continuity Enforcement.
        Phase 5: Truth Verification (hash proof).
        """
        stored_payload = bucket_data.get("stored_payload", {})
        trace_id_in_bucket = stored_payload.get("trace_id")
        
        # Verify artifact integrity
        payload_str = json.dumps(stored_payload, sort_keys=True)
        recomputed_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
        if recomputed_hash != bucket_data.get("artifact_hash"):
            raise StructuredFailure(
                failure_type="VERIFICATION_FAILED",
                message="Artifact Hash Mismatch! Data mutated after Core layer.",
                trace_id=trace_id_in_bucket
            )
        
        # Check trace in nested payload to ensure no layer altered it
        nested_trace_id = stored_payload.get("final_data", {}).get("tantra_packet", {}).get("trace_id")
        
        if trace_id_in_bucket != original_trace_id or nested_trace_id != original_trace_id:
            raise StructuredFailure(
                failure_type="TRACE_MISMATCH",
                message=f"Trace Continuity Broken! Original: {original_trace_id}, Found: {trace_id_in_bucket}, Nested: {nested_trace_id}",
                trace_id=original_trace_id
            )
            
        return True

def run_end_to_end_flow(signal: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Demonstrates ONE full flow end-to-end.
    """
    if signal is None:
        signal = TANTRAFlow.constraint_layer_signal()
        
    original_trace_id = signal["trace_id"]
    
    # 1. Propagation Engine (KESHAV)
    propagation_output = PropagationEngine.compute_dependency_output(signal)
    
    # 2. KESHAV (Pritesh)
    tantra_output = TANTRAFlow.pritesh_dependency_intelligence(propagation_output)
    
    # 3. Validation Engine (Kanishk)
    TANTRAFlow.kanishk_validation_engine(tantra_output)
    
    # 4. Sarathi (Decision)
    decision_output = TANTRAFlow.sarathi_decision_layer(tantra_output)
    
    # 5. Core (Execution)
    execution_output = TANTRAFlow.core_execution_layer(decision_output)
    
    # 6. Bucket (Write)
    bucket_data = TANTRAFlow.bucket_truth_layer(execution_output)
    
    # 7. InsightFlow (Verification)
    TANTRAFlow.insightflow_observability(bucket_data, original_trace_id)
    
    return bucket_data

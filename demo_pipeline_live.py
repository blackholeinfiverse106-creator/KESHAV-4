import json
import logging
import time

from analyzer.analyze_blockage import analyze_and_recommend
from tantra import bucket, core, insightflow, rajya, sarathi

# Configure logging to suppress noisy external libraries, but keep our errors visible
logging.basicConfig(level=logging.WARNING)

def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"[*] PHASE: {title}")
    print(f"{'='*60}")

def print_payload(name: str, payload: dict):
    print(f"\n>>> {name} PAYLOAD:")
    print(json.dumps(payload, indent=2))
    time.sleep(1) # Add a small delay for dramatic visual effect during the demo

def run_live_demo():
    print("\n" + "*"*60)
    print("      LIVE TANTRA PIPELINE END-TO-END DEMO      ")
    print("*"*60 + "\n")
    
    # 1. Incoming Data (from SANSKAR/SETU)
    print_header("SANSKAR / SETU (Input Generation)")
    input_data = {
        "execution_id": "demo-exec-555",
        "trace_id": "demo-live-trace-999",
        "tasks": [
            {"task_id": "T1", "depends_on": []},
            {"task_id": "T2", "depends_on": ["T1"]}
        ],
        "constraint_results": [
            {"task_id": "T2", "is_valid": False, "unsatisfied_dependencies": ["T1"]}
        ],
        "propagation_results": [
            {"task_id": "T2", "affected_tasks": ["T3", "T4"], "impact_score": 8}
        ]
    }
    print_payload("INCOMING SANSKAR ALERT", input_data)


    # 2. KESHAV (Analysis)
    print_header("KESHAV (Local Analyzer Layer)")
    keshav_output = analyze_and_recommend(input_data)
    print_payload("KESHAV ANALYSIS RESULT", keshav_output)
    
    if keshav_output.get("status") == "FAIL":
        print("\n[!] Pipeline stopped: KESHAV failed to analyze.")
        return

    # 3. InsightFlow (Background Observability)
    print_header("InsightFlow (Live Observability Stream)")
    print(f"[>] Asynchronously streaming event to: https://bhiv-6.onrender.com/api/v1/flow/events")
    insightflow.emit(keshav_output)
    print("[+] Emit triggered in background daemon thread. Pipeline continuing immediately!")


    # 4. RAJYA (Validation)
    print_header("RAJYA (Live External Validation Checkpoint)")
    print(f"[>] Hitting External API: text-risk-scoring-service.onrender.com...")
    try:
        rajya_output = rajya.consume(keshav_output, input_data["trace_id"])
        print_payload("RAJYA APPROVED (Unmutated Passthrough)", rajya_output)
    except Exception as e:
        print(f"\n[!] Pipeline stopped: RAJYA validation failed: {e}")
        return


    # 5. Sarathi (Enforcement)
    print_header("Sarathi (Live External Enforcement)")
    print(f"[>] Hitting External API: https://sarathi-9n5g.onrender.com/v1/keshav/enforce...")
    try:
        sarathi_output = sarathi.enforce(rajya_output)
        print_payload("SARATHI ENFORCEMENT RECORD", sarathi_output)
    except Exception as e:
        print(f"\n[!] Pipeline stopped: Sarathi enforcement failed: {e}")
        return


    # 6. Core (Execution)
    print_header("Core (Live External Execution)")
    print(f"[>] Hitting External API: http://163.128.209.18:8004/execute_task...")
    try:
        core_output = core.execute(sarathi_output)
        print_payload("CORE EXECUTION RESULT", core_output)
    except Exception as e:
        print(f"\n[!] Pipeline stopped: Core execution failed: {e}")
        return


    # 7. Bucket (Storage Log)
    print_header("Bucket (Live External Storage & Hash Chaining)")
    print(f"[>] Hitting External API: https://bhiv-bucket-i1l6.onrender.com/bucket/artifact...")
    try:
        bucket.write(core_output, keshav_output)
        print("\n[+] Execution Artifact securely stored in the Bucket!")
        print(f"[~] Current Bucket Hash Chain Head: {bucket._CURRENT_PARENT_HASH}")
    except Exception as e:
        print(f"\n[!] Pipeline stopped: Bucket write failed: {e}")
        return

    print("\n" + "*"*60)
    print(" [*] DEMO COMPLETE: 100% DISTRIBUTED EXECUTION SUCCESSFUL! [*]")
    print("*"*60 + "\n")


if __name__ == "__main__":
    run_live_demo()

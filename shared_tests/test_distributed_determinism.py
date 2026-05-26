import multiprocessing
import time
import random
import pytest
from app.engine import PropagationEngine

def run_propagation_task(worker_id: int, input_data: dict, result_queue: multiprocessing.Queue):
    """
    Worker function to run propagation in an isolated process with adversarial timing.
    """
    # Adversarial timing variance: random sleep between 10ms and 100ms
    time.sleep(random.uniform(0.01, 0.1))
    
    try:
        output = PropagationEngine.compute_dependency_output(input_data)
        result_queue.put({"worker_id": worker_id, "output": output, "status": "success"})
    except Exception as e:
        result_queue.put({"worker_id": worker_id, "error": str(e), "status": "error"})


def test_distributed_determinism():
    """
    Phase 6 / Gap 2: Distributed Determinism Proof
    Validates cross-process replay equivalence and adversarial timing variance.
    """
    # Complex graph to ensure sorting and traversal paths are challenged
    prop_in = {
        "blocked_task_id": "T1",
        "root_cause": "RC",
        "trace_id": "trace-dist-001",
        "timestamp": "2026-05-22T12:00:00Z",
        "dependency_graph": {
            "RC": ["T1", "T2", "T3"],
            "T1": ["T4", "T5"],
            "T2": ["T4", "T6"],
            "T3": ["T7"],
            "T4": ["T8"],
            "T5": ["T8"],
            "T6": ["T9"],
            "T7": ["T9"],
            "T8": ["T10"],
            "T9": ["T10"]
        }
    }
    
    num_processes = 10
    result_queue = multiprocessing.Queue()
    processes = []
    
    # 1. Launch multiple isolated processes
    for i in range(num_processes):
        p = multiprocessing.Process(target=run_propagation_task, args=(i, prop_in, result_queue))
        processes.append(p)
        p.start()
        
    # 2. Wait for all processes to complete
    for p in processes:
        p.join(timeout=5)
        
    # 3. Collect and verify results
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())
        
    assert len(results) == num_processes, "Not all processes completed successfully"
    
    # 4. Assert absolute equivalence across all isolated runs
    first_output = None
    for res in results:
        assert res["status"] == "success", f"Worker {res['worker_id']} failed: {res.get('error')}"
        if first_output is None:
            first_output = res["output"]
        else:
            # Prove absolute determinism
            assert res["output"] == first_output, f"Mismatch found in worker {res['worker_id']}"
            
    print("Distributed Determinism Proven: 10 isolated processes produced identical paths despite adversarial timing.")

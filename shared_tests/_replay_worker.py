"""
Multiprocessing worker for cross-process replay tests.
Kept in a separate file to avoid Windows multiprocessing spawn issues
with module-level imports that depend on sys.path state.
"""
import sys
import os
import json
import time
import hashlib


def cross_process_worker(worker_id, input_data, adversarial_delay, project_root, result_queue):
    """Worker that runs in a completely isolated process with adversarial delay."""
    sys.path.insert(0, project_root)
    time.sleep(adversarial_delay)
    
    from app.engine import PropagationEngine
    output = PropagationEngine.compute_dependency_output(input_data)
    canonical = json.dumps(output, sort_keys=True, separators=(',', ':'))
    output_hash = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    result_queue.put({
        "worker_id": worker_id,
        "output": output,
        "hash": output_hash,
        "delay": adversarial_delay,
        "pid": os.getpid()
    })

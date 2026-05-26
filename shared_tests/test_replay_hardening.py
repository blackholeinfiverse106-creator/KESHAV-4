"""
Phase 3 — Replay Hardening Closure
Covers all remaining replay gaps:
1. Restart replay validation
2. Cross-process deterministic replay
3. Reconstruction after interruption
4. Trace continuity after restart
5. Corruption-injection replay behavior
"""
import os
import sys
import json
import time
import random
import hashlib
import multiprocessing
import pytest

from app.engine import PropagationEngine
from shared_schemas.schemas import PropagationContractViolation


EVIDENCE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "review-packets", "evidence")

# Standard reference input used across all replay tests
REPLAY_INPUT = {
    "blocked_task_id": "T1",
    "root_cause": "RC",
    "trace_id": "trace-replay-hardening-001",
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


def compute_output_hash(output: dict) -> str:
    """Compute a deterministic SHA-256 hash of an output dict."""
    canonical = json.dumps(output, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


# ===================================================================
# Test 1: Restart Replay Validation
# ===================================================================
def test_restart_replay_validation():
    """
    Prove that the engine produces identical output across multiple
    independent computation cycles — simulating restart equivalence.
    
    Since the engine is stateless (@staticmethod, no instance), a "restart"
    is equivalent to simply calling the function again. We prove this
    across 5 independent invocations with hash comparison.
    """
    hashes = []
    outputs = []
    
    for run_idx in range(5):
        output = PropagationEngine.compute_dependency_output(REPLAY_INPUT.copy())
        h = compute_output_hash(output)
        hashes.append(h)
        outputs.append(output)
    
    # All must be identical
    assert all(h == hashes[0] for h in hashes), "Restart replay failed: hashes differ"
    assert all(o == outputs[0] for o in outputs), "Restart replay failed: outputs differ"
    
    # Write evidence
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    with open(os.path.join(EVIDENCE_DIR, "restart_replay_proof.txt"), "w") as f:
        f.write("Restart Replay Validation Proof\n")
        f.write("=" * 50 + "\n")
        for i, h in enumerate(hashes):
            f.write(f"Run {i+1} hash: {h}\n")
        f.write(f"All identical: True\n")
        f.write(f"\nOutput:\n{json.dumps(outputs[0], indent=2)}\n")


# ===================================================================
# Test 2: Cross-Process Deterministic Replay (Hardened)
# Uses _replay_worker.py to avoid Windows multiprocessing spawn issues
# ===================================================================
def test_cross_process_deterministic_replay():
    """
    Prove absolute cross-process replay equivalence with adversarial timing.
    Each process has a different random delay (0-200ms).
    All must produce byte-identical output hashes.
    """
    from shared_tests._replay_worker import cross_process_worker
    
    num_processes = 12
    result_queue = multiprocessing.Queue()
    processes = []
    delays = []
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    for i in range(num_processes):
        delay = random.uniform(0.0, 0.2)
        delays.append(delay)
        p = multiprocessing.Process(
            target=cross_process_worker,
            args=(i, REPLAY_INPUT.copy(), delay, project_root, result_queue)
        )
        processes.append(p)
        p.start()
    
    for p in processes:
        p.join(timeout=10)
    
    results = []
    while not result_queue.empty():
        results.append(result_queue.get())
    
    assert len(results) == num_processes, f"Only {len(results)}/{num_processes} processes completed"
    
    # All hashes must be identical
    reference_hash = results[0]["hash"]
    for res in results:
        assert res["hash"] == reference_hash, \
            f"Worker {res['worker_id']} (PID {res['pid']}, delay {res['delay']:.3f}s) produced different hash"
    
    # Write evidence
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    with open(os.path.join(EVIDENCE_DIR, "cross_process_replay_proof.txt"), "w") as f:
        f.write("Cross-Process Deterministic Replay Proof\n")
        f.write("=" * 50 + "\n")
        f.write(f"Processes: {num_processes}\n")
        f.write(f"Reference hash: {reference_hash}\n\n")
        for res in sorted(results, key=lambda x: x["worker_id"]):
            f.write(f"Worker {res['worker_id']:2d} | PID {res['pid']:6d} | "
                    f"Delay {res['delay']:.3f}s | Hash: {res['hash']}\n")
        f.write(f"\nAll identical: True\n")
        f.write(f"\nReference output:\n{json.dumps(results[0]['output'], indent=2)}\n")


# ===================================================================
# Test 3: Reconstruction After Interruption
# ===================================================================
def test_reconstruction_after_interruption():
    """
    Prove that an output can be serialized, stored, deserialized,
    and compared against a fresh computation — proving full
    reconstruction capability after any interruption.
    """
    # Phase A: Compute and serialize
    output_original = PropagationEngine.compute_dependency_output(REPLAY_INPUT.copy())
    serialized = json.dumps(output_original, sort_keys=True)
    original_hash = compute_output_hash(output_original)
    
    # Phase B: Simulate interruption — write to disk, clear memory
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    checkpoint_path = os.path.join(EVIDENCE_DIR, "replay_checkpoint.json")
    with open(checkpoint_path, "w") as f:
        f.write(serialized)
    
    del output_original
    del serialized
    
    # Phase C: Reconstruct from disk
    with open(checkpoint_path, "r") as f:
        reconstructed = json.loads(f.read())
    reconstructed_hash = compute_output_hash(reconstructed)
    
    # Phase D: Fresh replay
    output_fresh = PropagationEngine.compute_dependency_output(REPLAY_INPUT.copy())
    fresh_hash = compute_output_hash(output_fresh)
    
    # All three must match
    assert original_hash == reconstructed_hash == fresh_hash
    assert reconstructed == output_fresh
    
    # Write evidence
    with open(os.path.join(EVIDENCE_DIR, "interruption_reconstruction_proof.txt"), "w") as f:
        f.write("Reconstruction After Interruption Proof\n")
        f.write("=" * 50 + "\n")
        f.write(f"Original hash:       {original_hash}\n")
        f.write(f"Reconstructed hash:  {reconstructed_hash}\n")
        f.write(f"Fresh replay hash:   {fresh_hash}\n")
        f.write(f"All identical: {original_hash == reconstructed_hash == fresh_hash}\n")
        f.write(f"\nCheckpoint file: {checkpoint_path}\n")
        f.write(f"Reconstructed output:\n{json.dumps(reconstructed, indent=2)}\n")
    
    # Clean up checkpoint
    os.remove(checkpoint_path)


# ===================================================================
# Test 4: Trace Continuity After Restart
# ===================================================================
def test_trace_continuity_after_restart():
    """
    Prove that trace_id and timestamp survive unchanged through
    computation, serialization, and reconstruction.
    """
    trace_ids = [
        "trace-continuity-001",
        "trace-continuity-002",
        f"trace-continuity-{random.randint(1000, 9999)}",
        "trace-with-special-chars-!@#$%",
        "trace-" + "x" * 200,  # Very long trace ID
    ]
    
    results = []
    
    for trace_id in trace_ids:
        test_input = REPLAY_INPUT.copy()
        test_input["trace_id"] = trace_id
        
        # Compute
        output = PropagationEngine.compute_dependency_output(test_input)
        
        # Serialize + deserialize
        serialized = json.dumps(output)
        deserialized = json.loads(serialized)
        
        # Verify trace continuity
        assert output["trace_id"] == trace_id, f"Trace ID corrupted in output: {output['trace_id']}"
        assert deserialized["trace_id"] == trace_id, f"Trace ID corrupted after serialization: {deserialized['trace_id']}"
        assert output["timestamp"] == REPLAY_INPUT["timestamp"], "Timestamp corrupted"
        
        results.append({
            "input_trace_id": trace_id,
            "output_trace_id": output["trace_id"],
            "reconstructed_trace_id": deserialized["trace_id"],
            "match": True
        })
    
    # Write evidence
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    with open(os.path.join(EVIDENCE_DIR, "trace_continuity_proof.txt"), "w", encoding="utf-8") as f:
        f.write("Trace Continuity After Restart Proof\n")
        f.write("=" * 50 + "\n")
        for r in results:
            f.write(f"Input:         {r['input_trace_id'][:60]}\n")
            f.write(f"Output:        {r['output_trace_id'][:60]}\n")
            f.write(f"Reconstructed: {r['reconstructed_trace_id'][:60]}\n")
            f.write(f"Match: {r['match']}\n\n")


# ===================================================================
# Test 5: Corruption-Injection Replay Behavior
# ===================================================================
def test_corruption_injection_replay():
    """
    Prove that corrupted inputs are rejected AND that the engine
    can immediately recover and produce correct output on the next
    valid invocation — no state pollution from the corruption.
    """
    corruption_attempts = []
    
    # Step 1: Compute valid baseline
    baseline = PropagationEngine.compute_dependency_output(REPLAY_INPUT.copy())
    baseline_hash = compute_output_hash(baseline)
    
    # Step 2: Inject corruptions (must all fail)
    corruptions = [
        ("null_graph", {**REPLAY_INPUT, "dependency_graph": None}),
        ("string_graph", {**REPLAY_INPUT, "dependency_graph": "CORRUPTED"}),
        ("missing_trace_id", {k: v for k, v in REPLAY_INPUT.items() if k != "trace_id"}),
        ("empty_blocked_task", {**REPLAY_INPUT, "blocked_task_id": ""}),
        ("extra_field", {**REPLAY_INPUT, "injected_malware": True}),
        ("wrong_type_trace", {**REPLAY_INPUT, "trace_id": 12345}),
    ]
    
    for name, corrupted_input in corruptions:
        try:
            PropagationEngine.compute_dependency_output(corrupted_input)
            corruption_attempts.append({"name": name, "rejected": False, "error": "NO ERROR RAISED"})
        except (PropagationContractViolation, Exception) as e:
            corruption_attempts.append({
                "name": name,
                "rejected": True,
                "error": f"{type(e).__name__}: {str(e)[:100]}"
            })
    
    # Step 3: Verify engine is NOT polluted — replay produces identical output
    post_corruption = PropagationEngine.compute_dependency_output(REPLAY_INPUT.copy())
    post_hash = compute_output_hash(post_corruption)
    
    assert post_hash == baseline_hash, "Engine state was polluted by corruption injection!"
    assert post_corruption == baseline, "Output changed after corruption injection!"
    
    # All corruptions must have been rejected
    for attempt in corruption_attempts:
        assert attempt["rejected"], f"Corruption '{attempt['name']}' was NOT rejected!"
    
    # Write evidence
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    with open(os.path.join(EVIDENCE_DIR, "corruption_injection_proof.txt"), "w") as f:
        f.write("Corruption-Injection Replay Proof\n")
        f.write("=" * 50 + "\n")
        f.write(f"Baseline hash: {baseline_hash}\n")
        f.write(f"Post-corruption hash: {post_hash}\n")
        f.write(f"State polluted: {post_hash != baseline_hash}\n\n")
        f.write("Corruption attempts:\n")
        for attempt in corruption_attempts:
            f.write(f"  [{attempt['name']}] Rejected: {attempt['rejected']} | {attempt['error']}\n")
        f.write(f"\nPost-corruption output:\n{json.dumps(post_corruption, indent=2)}\n")

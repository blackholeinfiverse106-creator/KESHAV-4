import logging
from tantra import core

logging.basicConfig(level=logging.INFO)

print("Starting live Core Execution test...")

sarathi_output = {
    "trace_id": "test-core-sync-01",
    "enforced": True,
    "action": "ENFORCE:UNBLOCK_DEPENDENCY:T1"
}

print("\n--- Triggering Synchronous Execution ---")
try:
    result = core.execute(sarathi_output)
    print("\nSuccess! KESHAV downstream result:")
    print(result)
except Exception as e:
    print(f"\nExecution failed: {e}")

import logging
import time
from tantra import insightflow

logging.basicConfig(level=logging.INFO)

print("Starting live InsightFlow test...")

keshav_output = {
    "trace_id": "test-insight-async-01",
    "root_cause": "T1",
    "impact_score": 5,
    "severity": "MEDIUM",
    "resolution_signal": "UNBLOCK_DEPENDENCY:T1"
}

print("\n--- Triggering Emit ---")
insightflow.emit(keshav_output)

# Wait a few seconds for the daemon thread to finish the HTTP request
time.sleep(3)
print("\nSuccess! Check logs above for the 'External InsightFlow Emit OK' message.")

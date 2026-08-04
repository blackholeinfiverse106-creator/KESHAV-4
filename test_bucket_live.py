import logging
from tantra import bucket

logging.basicConfig(level=logging.INFO)

print("Starting live bucket test...")

# 1. First Write: Should initialize by fetching latest hash, then post, then capture new hash
core_output = {"trace_id": "live-bucket-test-01"}
keshav_output = {"test_data": "init_test"}

print("\n--- Triggering Write 1 ---")
bucket.write(core_output, keshav_output)

# 2. Second Write: Should use the hash generated from the first write
core_output2 = {"trace_id": "live-bucket-test-02"}
keshav_output2 = {"test_data": "second_test"}

print("\n--- Triggering Write 2 ---")
bucket.write(core_output2, keshav_output2)

print("\nSuccess! Both writes completed. Check logs above for hash chaining behavior.")

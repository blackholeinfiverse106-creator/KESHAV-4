# SETU Integration Guide for TANTRA Pipeline

## Overview
This document outlines the requirements and steps for integrating the **SETU** real-time signal source into the TANTRA pipeline (via the KESHAV entry point / Sutradhara Control Plane). By completing these steps, SETU signals will flow into the pipeline for intelligence analysis, enforcement, and observability.

## API Endpoint Integration
The TANTRA pipeline exposes a RESTful API endpoint that SETU must call to forward real-time signals.

* **Base URL**: `https://keshav-cia7.onrender.com` *(or `http://127.0.0.1:5000` for local dev)*
* **Endpoint**: `POST /analyze`
* **Content-Type Header**: `application/json`

## Payload Contract (Request)
SETU must map its incoming signals into a JSON payload adhering to the strict input contract expected by KESHAV.

### Required Fields
- `trace_id` (string): A unique identifier for the trace. **Critical**: This ID must be preserved and will be used across the entire pipeline for observability (InsightFlow).
- `execution_id` (string): An identifier for this specific execution run.
- `tasks` (list of objects): Represents the tasks in the signal. Each object should have a `task_id` and `depends_on`.
- `constraint_results` (list of objects): Validation results of the constraints. Each object contains `task_id`, `is_valid` (boolean), and `unsatisfied_dependencies`.
- `propagation_results` (list of objects): Impact analysis of the signal. Each object contains `task_id`, `affected_tasks`, and `impact_score`.

### Example Request Payload
```json
{
    "trace_id": "setu-trace-12345",
    "execution_id": "exec-setu-9876",
    "tasks": [
        {"task_id": "T1", "depends_on": []}
    ],
    "constraint_results": [
        {"task_id": "T1", "is_valid": false, "unsatisfied_dependencies": []}
    ],
    "propagation_results": [
        {"task_id": "T1", "affected_tasks": [], "impact_score": 10}
    ]
}
```

## Response Contract
Upon successful ingestion and processing, the TANTRA pipeline will return an HTTP 200 OK response with the analyzed output contract from KESHAV.

### Example Response Payload
```json
{
    "trace_id": "setu-trace-12345",
    "execution_id": "exec-setu-9876",
    "root_cause": "T1",
    "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
    "impact_score": 10,
    "severity": "HIGH",
    "timestamp": "2026-07-18T10:46:09Z"
}
```

## Error Handling
The API returns specific HTTP status codes and JSON error messages if something goes wrong.

* **400 Bad Request**: Indicates `INVALID_JSON` or a failure within the pipeline logic itself (e.g., missing `trace_id` breaking trace continuity).
* **413 Payload Too Large**: Request body exceeds the maximum allowed size (default limit is 1MB).
* **415 Unsupported Media Type**: The `Content-Type` header was not set to `application/json`.
* **500 Internal Error**: Unhandled exception in the pipeline.

All error responses follow this format:
```json
{
    "status": "FAIL",
    "reason": "INVALID_JSON",
    "trace_id": "" 
}
```

## Action Items for SETU Owner
To successfully connect SETU to the TANTRA pipeline, you must complete the following in the SETU project:

1. **Implement Signal Mapping**: Translate the raw real-time SETU signals into the JSON structure specified in the Payload Contract.
2. **Enforce Trace Continuity**: Generate and pass a unique `trace_id` for every request. **Do not omit this field**, as the pipeline enforce a fail-closed policy (it will reject the request if the `trace_id` is missing or mutated).
3. **Handle HTTP Client Configuration**: 
   - Set the `Content-Type: application/json` header.
   - Ensure the request body does not exceed 1MB. If you are sending bulk signals, chunk them appropriately.
4. **Implement Retry Logic**: Add retry mechanisms for network timeouts or 500-level errors. **Do not retry 400-level errors** without modifying the payload, as they indicate a contract violation.
5. **Network Connectivity**: Ensure the SETU runtime environment has network access to the TANTRA pipeline API host and port.

## Working Demo Example

Below is a complete, runnable Python script using the `requests` library to demonstrate how to submit a payload to the TANTRA pipeline and receive the response.

### Python `requests` Example
Save this as `demo.py` and run it:

```python
import requests
import json

# TANTRA Pipeline URL (Adjust port/host as necessary)
API_URL = "https://keshav-cia7.onrender.com/analyze"

# Construct the payload according to the KESHAV input contract
payload = {
    "trace_id": "setu-trace-12345",
    "execution_id": "exec-setu-9876",
    "tasks": [
        {"task_id": "T1", "depends_on": []}
    ],
    "constraint_results": [
        {"task_id": "T1", "is_valid": False, "unsatisfied_dependencies": []}
    ],
    "propagation_results": [
        {"task_id": "T1", "affected_tasks": [], "impact_score": 10}
    ]
}

print(f"Sending payload to {API_URL}...")

try:
    response = requests.post(
        API_URL, 
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    # Check for success
    if response.status_code == 200:
        print("Success! Received output payload:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Failed with status code {response.status_code}:")
        print(json.dumps(response.json(), indent=2))
        
except requests.exceptions.RequestException as e:
    print(f"Network error connecting to TANTRA pipeline: {e}")
```

### cURL Equivalent
If you prefer testing directly from the command line:

```bash
curl -X POST https://keshav-cia7.onrender.com/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "setu-trace-12345",
    "execution_id": "exec-setu-9876",
    "tasks": [{"task_id": "T1", "depends_on": []}],
    "constraint_results": [{"task_id": "T1", "is_valid": false, "unsatisfied_dependencies": []}],
    "propagation_results": [{"task_id": "T1", "affected_tasks": [], "impact_score": 10}]
  }'
```

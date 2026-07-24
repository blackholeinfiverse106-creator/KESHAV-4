# KESHAV API Integration Details

Here are the complete details for integrating and verifying the deployed KESHAV project based on the system architecture and API endpoints:

## 1. Current live base URL
`https://keshav-cia7.onrender.com/`

## 2. Exact API endpoint/path to call
`/analyze`
*(Note: There is also a `/health` endpoint for liveness/readiness checks and `/metrics` for Prometheus metrics).*

## 3. HTTP method
`POST`

## 4. Required request JSON/body and headers
- **Headers:** `Content-Type: application/json`
- **Body:** Requires a standard KESHAV input contract containing `trace_id`, `execution_id`, `tasks`, `constraint_results`, and `propagation_results`.

## 5. Expected response JSON
A structured JSON object representing the `keshav_output` contract. It typically includes:
- `trace_id` (matching the input)
- `execution_id`
- `root_cause`
- `resolution_signal`
- `impact_score`
- `severity`
- `timestamp`

## 6. How KESHAV output should be passed to RAJYA in the deployed version
The output from KESHAV (`keshav_output`) is passed directly to RAJYA along with the `trace_id`. The exact execution path signature is:
`rajya.consume(keshav_output, trace_id)`
RAJYA enforces strict trace continuity and performs zero transformations on the data itself.

## 7. Interaction between RAJYA, TANTRA, and Sarathi
**TANTRA handles the orchestration.** The deployed RAJYA does *not* call Sarathi itself. The entire execution path is strictly orchestrated centrally by `tantra/pipeline.py` via `run_tantra_pipeline()`. TANTRA takes the `rajya_output` and directly passes it to Sarathi using the method: `sarathi.enforce(rajya_output)`.

## 8. Sample valid request payload for live E2E validation
You can use the exact payload found in `sample_input.json` to perform a complete test:

```json
{
  "trace_id": "rajya-trace-001",
  "execution_id": "exec-demo",
  "tasks": [
    { "task_id": "T1", "depends_on": [] },
    { "task_id": "T2", "depends_on": ["T1"] },
    { "task_id": "T3", "depends_on": ["T2"] }
  ],
  "constraint_results": [
    { "task_id": "T1", "is_valid": false, "unsatisfied_dependencies": [] },
    { "task_id": "T2", "is_valid": false, "unsatisfied_dependencies": ["T1"] },
    { "task_id": "T3", "is_valid": true,  "unsatisfied_dependencies": [] }
  ],
  "propagation_results": [
    { "task_id": "T1", "affected_tasks": ["T2", "T3"], "impact_score": 10 },
    { "task_id": "T2", "affected_tasks": ["T3"],       "impact_score": 4  }
  ]
}
```

You can test this endpoint live via cURL:
```bash
curl -X POST https://keshav-cia7.onrender.com/analyze \
  -H "Content-Type: application/json" \
  -d '{
        "trace_id": "rajya-trace-001",
        "execution_id": "exec-demo",
        "tasks": [{"task_id": "T1", "depends_on": []}],
        "constraint_results": [{"task_id": "T1", "is_valid": false, "unsatisfied_dependencies": []}],
        "propagation_results": [{"task_id": "T1", "affected_tasks": [], "impact_score": 10}]
      }'
```

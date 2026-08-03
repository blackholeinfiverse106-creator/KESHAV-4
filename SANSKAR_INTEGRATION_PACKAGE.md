# SANSKAR Integration Package for KESHAV & RAJYA

Welcome to the TANTRA ecosystem! This document provides all the necessary details to successfully integrate the SANSKAR service with the live **KESHAV (Analyzer)** and **RAJYA (Decision Layer)** endpoints.

---

### 1. API Documentation
* **Service Name**: KESHAV & RAJYA (TANTRA Orchestration)
* **Description**: KESHAV acts as the Dependency Intelligence Layer, calculating downstream impact scores and resolving blocked dependency graphs. RAJYA acts as the Decision Gateway, taking KESHAV's output, bridging it with the external Sarathi authorization tags, and forwarding the verified trace to enforcement.
* **Core Endpoints**: 
  - `POST /analyze` (Full Pipeline)
  - `POST /api/v1/rajya/validate` (Dedicated RAJYA gateway)
  - `GET /health` (Readiness check)

### 2. OpenAPI / Swagger Documentation
FastAPI automatically generates live, interactive API documentation.
* **Swagger UI**: [https://keshav-cia7.onrender.com/docs](https://keshav-cia7.onrender.com/docs)
* **ReDoc**: [https://keshav-cia7.onrender.com/redoc](https://keshav-cia7.onrender.com/redoc)
* **Raw OpenAPI JSON**: [https://keshav-cia7.onrender.com/openapi.json](https://keshav-cia7.onrender.com/openapi.json)

### 3. Authentication Mechanism
Currently, the services operate inside an internal trust network.
* **Auth Requirement**: No specific API keys or Bearer tokens are required for these endpoints at this phase.
* **Headers**: All requests must strictly contain `Content-Type: application/json`.

### 4. Base URLs
* **Live Production Server**: `https://keshav-cia7.onrender.com`

### 5. Sample Requests & Responses

#### Endpoint 1: KESHAV Analyzer (`POST /analyze`)
This endpoint accepts raw SETU data, diagnoses the root cause, and orchestrates the full pipeline.
* **cURL Example**:
```bash
curl -X POST https://keshav-cia7.onrender.com/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "sanskar-trace-001",
    "execution_id": "exec-demo",
    "tasks": [
      { "task_id": "T1", "depends_on": [] },
      { "task_id": "T2", "depends_on": ["T1"] }
    ],
    "constraint_results": [
      { "task_id": "T1", "is_valid": false, "unsatisfied_dependencies": [] },
      { "task_id": "T2", "is_valid": false, "unsatisfied_dependencies": ["T1"] }
    ],
    "propagation_results": [
      { "task_id": "T1", "affected_tasks": ["T2"], "impact_score": 10 }
    ]
  }'
```
* **Expected Response (200 OK)**:
```json
{
  "trace_id": "sanskar-trace-001",
  "execution_id": "exec-demo",
  "root_cause": "T1",
  "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
  "impact_score": 10,
  "severity": "HIGH",
  "timestamp": "2026-07-29T10:00:00Z"
}
```

#### Endpoint 2: RAJYA Validation Gateway (`POST /api/v1/rajya/validate`)
This endpoint takes the structured KESHAV output, validates it through the RAJYA thin adapter, and passes it directly to Sarathi.
* **cURL Example**:
```bash
curl -X POST https://keshav-cia7.onrender.com/api/v1/rajya/validate \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "sanskar-trace-002",
    "execution_id": "exec-demo",
    "root_cause": "T1",
    "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
    "impact_score": 10,
    "severity": "HIGH",
    "timestamp": "2026-07-29T10:00:00Z"
  }'
```
* **Expected Response (200 OK)**:
```json
{
  "status": "EXECUTION_APPROVED",
  "trace_id": "sanskar-trace-002",
  "rajya_output": { ... },
  "sarathi_output": {
    "trace_id": "sanskar-trace-002",
    "enforced": true,
    "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
    "action": "ENFORCE:UNBLOCK_DEPENDENCY:T1"
  },
  "message": "KESHAV output successfully consumed by RAJYA and passed to Sarathi."
}
```

### 6. Required Environment Variables
If you are spinning up these services locally alongside SANSKAR, no strict environment variables are required to start, but the following are used to route to external dependencies:
* `RAJYA_EXTERNAL_URL`: (Defaults to the live text-risk-scoring service)
* `SARATHI_EXTERNAL_URL`: (Defaults to `https://sarathi-9n5g.onrender.com/v1/keshav/enforce`)
* `SARATHI_LIVE_ENFORCEMENT`: Set to `"true"` to enable live enforcement bridging.

### 7. SDK / Client Libraries
There is no dedicated pip package/SDK yet. Standard HTTP libraries (`requests` in Python, `axios` in JS, or `HttpClient` in Java) are fully supported. Use the OpenAPI spec (`/openapi.json`) if you wish to auto-generate a client using Swagger Codegen.

### 8. Event / Message Schemas
We enforce a strict **Trace Continuity Contract**:
* Every payload crossing between SANSKAR and KESHAV/RAJYA **MUST** contain a `"trace_id"` (string). 
* The system is designed to "fail-closed"—if `"trace_id"` is missing or mismatched between layers, the request will immediately return a `400 Bad Request`.

### 9. Test Environment Details
* The Render URL (`https://keshav-cia7.onrender.com`) is currently serving as a joint staging/production environment.
* **Note on Cold Starts**: Render spins down free-tier instances after 15 minutes of inactivity. If the first request times out or takes ~30 seconds, please retry.

### 10. Integration Guide (Quick Start)
1. Determine your entry point. If SANSKAR produces raw constraint graphs, POST them to `/analyze`. If SANSKAR has already analyzed the graphs and just needs to pass the decision gate, POST the structured output to `/api/v1/rajya/validate`.
2. Inspect the HTTP Response.
3. Pass the resulting `resolution_signal` (or `sarathi_output.action`) down to the execution layer.
4. If you have any trace continuity issues, ensure your payload injects `"trace_id"`.

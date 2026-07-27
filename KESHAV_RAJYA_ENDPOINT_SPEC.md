# KESHAV $\rightarrow$ RAJYA $\rightarrow$ Sarathi Live Endpoint Specification

This document details the live dedicated RAJYA integration endpoint deployed on the KESHAV service. It takes the diagnosed output from KESHAV, passes it through RAJYA validation (via a thin compatibility adapter), and transfers it to Sarathi for operational enforcement.

---

## 1. Live RAJYA Endpoint
* **Primary URL:** `https://keshav-cia7.onrender.com/api/v1/rajya/validate`
* **Alias URL:** `https://keshav-cia7.onrender.com/rajya/consume` *(both routes execute identical logic)*

---

## 2. HTTP Method & Headers
* **HTTP Method:** `POST`
* **Headers Required:** `Content-Type: application/json`

---

## 3. Exact Request Contract (Accepts KESHAV Output)
The request body must be a valid JSON object matching the exact output dictionary produced by KESHAV.

### Request Properties Schema
| Field | Type | Required | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `"trace_id"` | String | Yes | Unique trace identifier for audit chain continuity. | `"rajya-trace-001"` |
| `"execution_id"` | String | Yes | Identifier for the execution run. | `"exec-demo-2026"` |
| `"root_cause"` | String / null| No | The task ID identified as the bottleneck source. | `"T1"` |
| `"resolution_signal"` | String | No | Recommended action signal from diagnostic graph. | `"UNBLOCK_DEPENDENCY:T1"` |
| `"impact_score"` | Number | No | Total downstream propagation impact calculation. | `10` |
| `"severity"` | String | No | Categorized severity level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).| `"HIGH"` |
| `"timestamp"` | String | No | ISO 8601 UTC execution timestamp. | `"2026-07-25T10:00:00Z"` |

### Request Sample JSON
```json
{
  "trace_id": "rajya-trace-live-test-01",
  "execution_id": "exec-demo-2026",
  "root_cause": "T1",
  "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
  "impact_score": 10,
  "severity": "HIGH",
  "timestamp": "2026-07-25T10:00:00Z"
}
```

---

## 4. Expected Response Contract (For Sarathi Enforcement)
When the request is authorized (`200 OK`), the endpoint returns a structured response containing both the validated RAJYA contract and the actionable Sarathi enforcement command.

### Response Structure Schema
```json
{
  "status": "EXECUTION_APPROVED",
  "trace_id": "string",
  "rajya_output": {
    "trace_id": "string",
    "execution_id": "string",
    "root_cause": "string",
    "resolution_signal": "string",
    "impact_score": "number",
    "severity": "string",
    "timestamp": "string"
  },
  "sarathi_output": {
    "trace_id": "string",
    "enforced": true,
    "resolution_signal": "string",
    "action": "string (formatted operational action, e.g., ENFORCE:UNBLOCK_DEPENDENCY:T1)"
  },
  "message": "KESHAV output successfully consumed by RAJYA and passed to Sarathi."
}
```
> [!TIP]
> **Sarathi Integration Note:** Downstream execution layer components can consume the `"sarathi_output"` dictionary directly to execute physical remediation actions on the targeted systems.

---

## 5. One Working Sample Request (E2E Verification)
You can verify live connectivity immediately from your terminal by copy-pasting and executing the command below:

### Terminal cURL Command
```bash
curl -X POST https://keshav-cia7.onrender.com/api/v1/rajya/validate \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "rajya-trace-live-test-01",
    "execution_id": "exec-demo-2026",
    "root_cause": "T1",
    "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
    "impact_score": 10,
    "severity": "HIGH",
    "timestamp": "2026-07-25T10:00:00Z"
  }'
```

### Expected Live Server Response (200 OK)
```json
{
  "status": "EXECUTION_APPROVED",
  "trace_id": "rajya-trace-live-test-01",
  "rajya_output": {
    "trace_id": "rajya-trace-live-test-01",
    "execution_id": "exec-demo-2026",
    "root_cause": "T1",
    "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
    "impact_score": 10,
    "severity": "HIGH",
    "timestamp": "2026-07-25T10:00:00Z"
  },
  "sarathi_output": {
    "trace_id": "rajya-trace-live-test-01",
    "enforced": true,
    "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
    "action": "ENFORCE:UNBLOCK_DEPENDENCY:T1"
  },
  "message": "KESHAV output successfully consumed by RAJYA and passed to Sarathi."
}
```

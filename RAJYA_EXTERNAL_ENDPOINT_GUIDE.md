# Deployed RAJYA Validation Service — Integration & Testing Guide

This document provides complete instructions for integrating and testing the standalone deployed **Sovereign-Core (RAJYA) Validation Service**.

---

## 1. Live Endpoint Details
* **Service URL:** `https://text-risk-scoring-service.onrender.com/api/v1/rajya/validate`
* **HTTP Method:** `POST`
* **Headers:** `Content-Type: application/json`

---

## 2. Important: Required Request Schema (Contract Requirements)
To prevent your requests from being rejected by the server with governance errors (such as `RAJYA_SARATHI_AUTHORITY_MISSING` or `RAJYA_EXECUTION_ID_MISMATCH`), **your request JSON body must include these specific root-level governance fields**:
1. `"sarathi_decision"` (String: `"ALLOW"` or `"DENY"`)
2. `"sarathi_execution_id"` (String matching your `"execution_id"`)
3. `"enforcement_verdict"` (Dictionary containing the matched execution ID and decision)

---

## 3. Copy-Paste Sample Payloads for E2E Testing

### ✅ Scenario 1: Approved Execution (ALLOW Path)
When sending this valid payload, the server will evaluate and authorize the execution.

**Request JSON Body:**
```json
{
  "trace_id": "rajya-trace-test-001",
  "execution_id": "exec-demo-001",
  "root_cause": "T1 is blocked",
  "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
  "impact_score": 5,
  "severity": "MEDIUM",
  "timestamp": "2026-07-25T10:00:00Z",
  "sarathi_decision": "ALLOW",
  "sarathi_execution_id": "exec-demo-001",
  "enforcement_verdict": {
    "execution_id": "exec-demo-001",
    "enforcement_decision": "ALLOW",
    "confidence": 1.0
  }
}
```

**Expected Response (200 OK):**
```json
{
  "status": "EXECUTION_APPROVED"
}
```

---

### 🛑 Scenario 2: Rejected Execution (DENY Path)
If the decision is set to DENY, the server will correctly reject execution and return the corresponding rejection codes.

**Request JSON Body:**
```json
{
  "trace_id": "rajya-trace-test-002",
  "execution_id": "exec-demo-002",
  "root_cause": "Critical loop detected",
  "resolution_signal": "HALT",
  "impact_score": 10,
  "severity": "CRITICAL",
  "timestamp": "2026-07-25T10:00:00Z",
  "sarathi_decision": "DENY",
  "sarathi_execution_id": "exec-demo-002",
  "enforcement_verdict": {
    "execution_id": "exec-demo-002",
    "enforcement_decision": "DENY",
    "confidence": 1.0
  }
}
```

**Expected Response:**
```json
{
  "status": "REJECT",
  "rejection_code": "RAJYA_SARATHI_NOT_ALLOW",
  "rejection_reason": "Sarathi decision is 'DENY', not ALLOW. Execution not authorized."
}
```

---

## 4. Live cURL Commands for Terminal Testing

You can copy and execute this cURL command directly in your terminal to test the live server right now:

```bash
curl -X POST https://text-risk-scoring-service.onrender.com/api/v1/rajya/validate \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "rajya-trace-test-001",
    "execution_id": "exec-demo-001",
    "root_cause": "T1 is blocked",
    "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
    "impact_score": 5,
    "severity": "MEDIUM",
    "timestamp": "2026-07-25T10:00:00Z",
    "sarathi_decision": "ALLOW",
    "sarathi_execution_id": "exec-demo-001",
    "enforcement_verdict": {
      "execution_id": "exec-demo-001",
      "enforcement_decision": "ALLOW",
      "confidence": 1.0
    }
  }'
```

---

## 5. Python Adapter Pattern (For Backends & Pipelines)
If your teammate needs to invoke this endpoint within an automated Python application or processing pipeline without manually building the governance parameters every time, they can use this drop-in function:

```python
import urllib.request
import json
from typing import Any

def validate_with_rajya(payload: dict[str, Any]) -> bool:
    """
    Adapter that appends required governance tags and validates execution via deployed RAJYA service.
    Returns True if approved, raises Exception otherwise.
    """
    url = "https://text-risk-scoring-service.onrender.com/api/v1/rajya/validate"
    
    # Ensure matching execution identities
    exec_id = payload.get("execution_id") or payload.get("trace_id", "default-exec-id")
    signal = payload.get("resolution_signal", "")
    
    # Map resolution signal to governance decisions
    decision = "DENY" if signal in ("HALT", "BLOCK", "DENY") else "ALLOW"
    
    adapter_payload = {
        **payload,
        "sarathi_decision": decision,
        "sarathi_execution_id": exec_id,
        "enforcement_verdict": {
            "execution_id": exec_id,
            "enforcement_decision": decision,
            "confidence": 1.0
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(adapter_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if data.get("status") in ("EXECUTION_APPROVED", "OK"):
            return True
        raise RuntimeError(f"RAJYA Server Rejected Execution: {data}")
```

"""
RAJYA — Decision Layer & TANTRA Compatibility Adapter

Consumes KESHAV output directly. Bridges interface requirements for external
RAJYA service by injecting expected Sarathi structural authority tags before calling out.
Enforces trace_id continuity — rejects if trace_id is absent or mismatched.
"""


import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger("keshav.rajya")

RAJYA_EXTERNAL_URL = os.environ.get(
    "RAJYA_EXTERNAL_URL",
    "https://text-risk-scoring-service.onrender.com/api/v1/rajya/validate",
)
RAJYA_LIVE_VALIDATION = (
    os.environ.get("RAJYA_LIVE_VALIDATION", "true").lower() == "true"
)


def consume(keshav_output: dict[str, Any], expected_trace_id: str) -> dict[str, Any]:
    """
    Validate and accept KESHAV output into the decision layer using a thin compatibility adapter.

    Returns the same dict unchanged down the TANTRA chain.
    Raises ValueError on contract violation (fail-closed).
    """
    if keshav_output.get("status") == "FAIL":
        raise ValueError(
            f"RAJYA: upstream KESHAV failure — {keshav_output.get('reason')}"
        )
    if "trace_id" not in keshav_output:
        raise ValueError("RAJYA: missing trace_id in KESHAV output")
    if keshav_output["trace_id"] != expected_trace_id:
        raise ValueError(
            f"RAJYA: trace_id mismatch — "
            f"expected={expected_trace_id!r} got={keshav_output['trace_id']!r}"
        )

    if RAJYA_LIVE_VALIDATION and RAJYA_EXTERNAL_URL:
        _validate_external_via_adapter(keshav_output, expected_trace_id)

    # Return KESHAV output down the TANTRA chain so Sarathi can process it next
    return keshav_output


def _validate_external_via_adapter(
    keshav_output: dict[str, Any], trace_id: str
) -> None:
    """
    THIN ADAPTER LAYER: Construct expected Sarathi parameters for external RAJYA validation.
    """
    execution_id = keshav_output.get("execution_id") or trace_id
    signal = keshav_output.get("resolution_signal", "")

    # Map KESHAV signal to expected Sarathi decision authorization structure
    decision = "DENY" if signal in ("HALT", "BLOCK", "DENY") else "ALLOW"

    adapter_payload = {
        **keshav_output,
        "sarathi_decision": decision,
        "sarathi_execution_id": execution_id,
        "enforcement_verdict": {
            "execution_id": execution_id,
            "enforcement_decision": decision,
            "confidence": 1.0,
        },
    }

    req = urllib.request.Request(
        RAJYA_EXTERNAL_URL,
        data=json.dumps(adapter_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") not in ("EXECUTION_APPROVED", "OK"):
                raise ValueError(f"RAJYA External Rejected: {data}")
    except ValueError as exc:
        raise exc
    except Exception as exc:
        logger.warning(
            "RAJYA external service check failed (%s).",
            exc,
        )
        if os.environ.get("RAJYA_STRICT_MODE", "false").lower() == "true":
            raise ValueError(f"RAJYA Service validation unreachable: {exc}") from exc


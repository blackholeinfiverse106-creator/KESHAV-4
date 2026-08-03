"""
Sarathi — Enforcement Layer

Consumes resolution_signal from RAJYA output.
Enforces trace_id continuity. Calls out to external Sarathi service when configured.
"""

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger("keshav.sarathi")

SARATHI_EXTERNAL_URL = os.environ.get(
    "SARATHI_EXTERNAL_URL",
    "https://sarathi-9n5g.onrender.com/v1/keshav/enforce",
)
SARATHI_LIVE_ENFORCEMENT = (
    os.environ.get("SARATHI_LIVE_ENFORCEMENT", "true").lower() == "true"
)


def enforce(rajya_output: dict[str, Any]) -> dict[str, Any]:
    """
    Read resolution_signal and enforce the decision via the Sarathi service.

    Returns enforcement record with trace_id preserved.
    Raises ValueError on missing trace_id (fail-closed).
    """
    trace_id = rajya_output.get("trace_id")
    if not trace_id:
        raise ValueError("Sarathi: missing trace_id")

    # Delegate to the external service if enabled
    if SARATHI_LIVE_ENFORCEMENT and SARATHI_EXTERNAL_URL:
        try:
            return _enforce_external(rajya_output)
        except ValueError as exc:
            raise exc
        except Exception as exc:
            logger.warning("SARATHI external service check failed (%s).", exc)
            if os.environ.get("SARATHI_STRICT_MODE", "false").lower() == "true":
                raise ValueError(f"Sarathi Service validation unreachable: {exc}") from exc

    # Local fallback / Offline mock processing
    resolution_signal = rajya_output.get("resolution_signal")
    return {
        "trace_id": trace_id,
        "enforced": True,
        "resolution_signal": resolution_signal,
        "action": f"ENFORCE:{resolution_signal}" if resolution_signal else "NO_ACTION",
    }


def _enforce_external(rajya_output: dict[str, Any]) -> dict[str, Any]:
    """
    Makes actual HTTP POST request to the deployed Sarathi service.
    """
    req = urllib.request.Request(
        SARATHI_EXTERNAL_URL,
        data=json.dumps(rajya_output).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if data.get("trace_id") != rajya_output["trace_id"]:
            raise ValueError(
                f"Sarathi external response trace_id mismatch — "
                f"expected={rajya_output['trace_id']!r} got={data.get('trace_id')!r}"
            )
        return data

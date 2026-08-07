"""
Core — Execution Layer

Receives Sarathi enforcement record. Executes the action.
Preserves trace_id. No transformation of upstream data.

Integrates with an external physical execution service (bhiv-core) when configured.
"""

import json
import logging
import os
import urllib.request
from typing import Any

logger = logging.getLogger("keshav.core")

CORE_EXTERNAL_URL = os.environ.get(
    "CORE_EXTERNAL_URL", "http://163.128.209.18:8004/execute_task"
)
CORE_LIVE_INTEGRATION = (
    os.environ.get("CORE_LIVE_INTEGRATION", "true").lower() == "true"
)
CORE_STRICT_MODE = (
    os.environ.get("CORE_STRICT_MODE", "false").lower() == "true"
)


def _execute_external(sarathi_output: dict[str, Any]) -> dict[str, Any]:
    """
    Perform a synchronous, blocking network call to the physical Core Execution layer.
    """
    trace_id = sarathi_output.get("trace_id")
    action = sarathi_output.get("action")
    
    # Map to the external TaskPayload schema
    payload = {
        "input": action if action else "NO_ACTION",
        "trace_id": trace_id,
        "input_type": "text"
    }

    req = urllib.request.Request(
        CORE_EXTERNAL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        logger.info("External Core execution OK: trace_id=%s, task_id=%s", trace_id, data.get("task_id"))
        
        # Return exactly what KESHAV expects downstream, preserving trace_id
        return {
            "trace_id": trace_id,
            "executed": True,
            "action": action,
            "core_response": data  # Inject the raw task response for bucket storage
        }


def execute(sarathi_output: dict[str, Any]) -> dict[str, Any]:
    """
    Execute the enforced action.

    Returns execution record with trace_id preserved.
    Raises ValueError on missing trace_id (fail-closed).
    """
    trace_id = sarathi_output.get("trace_id")
    if not trace_id:
        raise ValueError("Core: missing trace_id")

    if CORE_LIVE_INTEGRATION and CORE_EXTERNAL_URL:
        try:
            return _execute_external(sarathi_output)
        except Exception as exc:
            logger.warning("Core external execution failed (%s)", exc)
            if CORE_STRICT_MODE:
                raise ValueError(f"Core External Execution Failed: {exc}") from exc

    # Local fallback / Offline mock processing
    return {
        "trace_id": trace_id,
        "executed": True,
        "action": sarathi_output.get("action"),
    }

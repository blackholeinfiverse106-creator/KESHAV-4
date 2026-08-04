"""
InsightFlow — Observability Layer

Read-only. Emits structured events from KESHAV output.
Never mutates core output. Exposes traces, failures, and execution visibility.
Thread-safe: event list mutations are protected by a lock.
Bounded: retains at most MAX_EVENTS entries (oldest evicted first).

Streams live telemetry securely via an external API utilizing W3C Trace Context headers.
"""

import hashlib
import json
import logging
import os
import threading
import urllib.request
from typing import Any

logger = logging.getLogger("insightflow")

MAX_EVENTS = 10_000

INSIGHTFLOW_API_KEY = os.environ.get(
    "INSIGHTFLOW_API_KEY", "vijay_insightflow_10c5cbe7831071d120a52db97695fdb6"
)
INSIGHTFLOW_REGISTRY_ID = os.environ.get(
    "INSIGHTFLOW_REGISTRY_ID", "BHIV-DS-GOVERNANCE-CONTRADICTION-AUDITS-001"
)
INSIGHTFLOW_EXTERNAL_URL = os.environ.get(
    "INSIGHTFLOW_EXTERNAL_URL", "https://bhiv-6.onrender.com/api/v1/flow/events"
)
INSIGHTFLOW_LIVE_INTEGRATION = (
    os.environ.get("INSIGHTFLOW_LIVE_INTEGRATION", "true").lower() == "true"
)

_events: list[dict[str, Any]] = []
_lock = threading.Lock()


def _generate_w3c_traceparent(raw_trace_id: str) -> tuple[str, str]:
    """
    Hashes the raw_trace_id into a W3C compliant 32-character hex string.
    Returns a tuple of (compliant_hex_trace_id, traceparent_header_string).
    """
    hashed_trace = hashlib.md5(raw_trace_id.encode("utf-8")).hexdigest()
    # W3C Format: version(00) - trace_id(32 hex) - span_id(16 hex) - flags(01)
    # Using a dummy span_id for now as InsightFlow primary matching focuses on trace_id
    traceparent = f"00-{hashed_trace}-0000000000000001-01"
    return hashed_trace, traceparent


def _stream_to_insightflow_async(event: dict[str, Any]) -> None:
    """
    Fire-and-forget background worker to push observability event over HTTP.
    """
    raw_trace_id = event.get("trace_id", "")
    if not raw_trace_id:
        return
        
    hashed_trace, traceparent = _generate_w3c_traceparent(raw_trace_id)
    
    # Mutate a copy for the network payload to fulfill strict external contracts
    payload = event.copy()
    payload["original_trace_id"] = raw_trace_id
    payload["trace_id"] = hashed_trace
    payload["registry_id"] = INSIGHTFLOW_REGISTRY_ID

    req = urllib.request.Request(
        INSIGHTFLOW_EXTERNAL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": INSIGHTFLOW_API_KEY,
            "traceparent": traceparent,
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read().decode("utf-8")
            logger.info("External InsightFlow Emit OK: %s", data)
    except Exception as exc:
        # We silently swallow network failures on observability to avoid blocking execution!
        logger.debug("Background observability stream failed: %s", exc)


def emit(keshav_output: dict[str, Any]) -> None:
    """
    Emit a structured observability event from KESHAV output.
    Read-only: does not modify keshav_output.
    """
    if keshav_output.get("status") == "FAIL":
        event = {
            "type": "FAILURE",
            "trace_id": keshav_output.get("trace_id", ""),
            "reason": keshav_output.get("reason"),
        }
        logger.warning("insightflow | %s", event)
    else:
        event = {
            "type": "EXECUTION",
            "trace_id": keshav_output.get("trace_id"),
            "root_cause": keshav_output.get("root_cause"),
            "impact_score": keshav_output.get("impact_score"),
            "severity": keshav_output.get("severity"),
            "resolution_signal": keshav_output.get("resolution_signal"),
        }
        logger.info("insightflow | %s", event)

    with _lock:
        if len(_events) >= MAX_EVENTS:
            _events.pop(0)
        _events.append(event)
        
    if INSIGHTFLOW_LIVE_INTEGRATION and INSIGHTFLOW_EXTERNAL_URL:
        # Fire-and-Forget asynchronously so we never block KESHAV
        threading.Thread(
            target=_stream_to_insightflow_async, 
            args=(event,), 
            daemon=True
        ).start()


def get_events() -> list[dict]:
    """Return all emitted events (read-only copy)."""
    with _lock:
        return list(_events)


def get_failures() -> list[dict]:
    """Return only failure events."""
    with _lock:
        return [e for e in _events if e["type"] == "FAILURE"]


def clear() -> None:
    """Reset event log — for test isolation only."""
    with _lock:
        _events.clear()

"""
Bucket — Truth Layer

Stores verifiable execution output. Write only on successful runs.
Fail-closed: rejects writes if trace_id is missing.
Read-only retrieval for verification.
Thread-safe: all mutations are protected by a lock.
Bounded: retains at most MAX_ENTRIES entries (oldest evicted first).

Integrates with an external append-only Bucket service using cryptographic hash chaining.
"""

import datetime
import json
import logging
import os
import threading
import urllib.error
import urllib.request
import uuid

logger = logging.getLogger("bucket")

MAX_ENTRIES = 50_000

BUCKET_API_BASE = os.environ.get(
    "BUCKET_EXTERNAL_URL", "https://bhiv-bucket-i1l6.onrender.com/bucket"
)
BUCKET_LIVE_INTEGRATION = (
    os.environ.get("BUCKET_LIVE_INTEGRATION", "true").lower() == "true"
)

_store: dict[str, dict] = {}
_insertion_order: list[str] = []
_lock = threading.Lock()

_CURRENT_PARENT_HASH: str | None = None
_IS_HASH_INITIALIZED: bool = False


def _fetch_latest_hash() -> str | None:
    req = urllib.request.Request(
        f"{BUCKET_API_BASE}/latest-hash",
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("last_hash")


def _write_external(trace_id: str, core_output: dict, keshav_output: dict) -> None:
    global _CURRENT_PARENT_HASH, _IS_HASH_INITIALIZED

    if not _IS_HASH_INITIALIZED:
        try:
            _CURRENT_PARENT_HASH = _fetch_latest_hash()
            _IS_HASH_INITIALIZED = True
            logger.info("Bucket initialized parent_hash: %s", _CURRENT_PARENT_HASH)
        except Exception as exc:
            logger.warning("Failed to fetch latest hash during init: %s", exc)
            if os.environ.get("BUCKET_STRICT_MODE", "false").lower() == "true":
                raise ValueError(f"Bucket Init Failed: {exc}") from exc
            return

    payload = {
        "artifact_id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "schema_version": "1.0.0",
        "source_module_id": "keshav_pipeline",
        "artifact_type": "execution_record",
        "parent_hash": _CURRENT_PARENT_HASH,
        "payload": {
            "keshav_output": keshav_output,
            "core_output": core_output,
        },
    }

    req = urllib.request.Request(
        f"{BUCKET_API_BASE}/artifact",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                _CURRENT_PARENT_HASH = data.get("hash")
                logger.info(
                    "External bucket write OK trace_id=%s new_hash=%s",
                    trace_id,
                    _CURRENT_PARENT_HASH,
                )
            else:
                raise ValueError(f"Bucket rejected write: {data}")
    except urllib.error.HTTPError as e:
        error_resp = e.read().decode("utf-8")
        logger.warning("Bucket HTTPError: %s, %s", e.code, error_resp)
        if e.code in (400, 422) and "parent_hash" in error_resp:
            logger.info("Concurrency mismatch detected. Resyncing and retrying...")
            try:
                _CURRENT_PARENT_HASH = _fetch_latest_hash()
                payload["parent_hash"] = _CURRENT_PARENT_HASH
                retry_req = urllib.request.Request(
                    f"{BUCKET_API_BASE}/artifact",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(retry_req, timeout=10) as retry_resp:
                    retry_data = json.loads(retry_resp.read().decode("utf-8"))
                    if retry_data.get("success"):
                        _CURRENT_PARENT_HASH = retry_data.get("hash")
                        logger.info(
                            "External bucket retry OK trace_id=%s new_hash=%s",
                            trace_id,
                            _CURRENT_PARENT_HASH,
                        )
                    else:
                        raise ValueError(f"Bucket retry rejected: {retry_data}")
            except Exception as retry_exc:
                logger.warning("Bucket retry failed: %s", retry_exc)
                if os.environ.get("BUCKET_STRICT_MODE", "false").lower() == "true":
                    raise ValueError(f"Bucket Sync/Write Failed: {retry_exc}") from retry_exc
        else:
            if os.environ.get("BUCKET_STRICT_MODE", "false").lower() == "true":
                raise ValueError(f"Bucket Write HTTPError: {error_resp}") from e
    except Exception as exc:
        logger.warning("External bucket write failed (%s).", exc)
        if os.environ.get("BUCKET_STRICT_MODE", "false").lower() == "true":
            raise ValueError(f"Bucket Write Failed: {exc}") from exc


def write(core_output: dict, keshav_output: dict) -> None:
    """
    Persist execution truth. Raises ValueError on missing trace_id (fail-closed).
    No write on failure — caller must not invoke this on failed runs.
    """
    trace_id = core_output.get("trace_id")
    if not trace_id:
        raise ValueError("Bucket: missing trace_id — write rejected")

    with _lock:
        if BUCKET_LIVE_INTEGRATION and BUCKET_API_BASE:
            _write_external(trace_id, core_output, keshav_output)

        if trace_id not in _store:
            if len(_store) >= MAX_ENTRIES:
                oldest = _insertion_order.pop(0)
                _store.pop(oldest, None)
            _insertion_order.append(trace_id)
        _store[trace_id] = {
            "trace_id": trace_id,
            "keshav_output": keshav_output,
            "core_output": core_output,
        }
    logger.info("bucket | write trace_id=%s", trace_id)


def read(trace_id: str) -> dict | None:
    """Retrieve stored truth by trace_id. Returns None if not found."""
    with _lock:
        return _store.get(trace_id)


def clear() -> None:
    """Reset store — for test isolation only."""
    global _IS_HASH_INITIALIZED, _CURRENT_PARENT_HASH
    with _lock:
        _store.clear()
        _insertion_order.clear()
        # Do not clear the external hash tracking if we want tests to act consecutively, 
        # but to keep isolation true, we can reset the init flag so it fetches again next time.
        _IS_HASH_INITIALIZED = False
        _CURRENT_PARENT_HASH = None


def all_trace_ids() -> list[str]:
    """Return all stored trace_ids."""
    with _lock:
        return list(_store.keys())

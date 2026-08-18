"""
KESHAV API — FastAPI wrapper for the full TANTRA pipeline

Endpoints:
    POST /analyze   — run full TANTRA chain, returns KESHAV output contract
    GET  /health    — liveness + readiness check

Run (development):
    uvicorn api:app --reload

Run (production):
    uvicorn api:app --workers 4 --host 0.0.0.0 --port 5000

Environment variables:
    PORT            — listening port (default: 5000)
    HOST            — bind address  (default: 127.0.0.1)
    DEBUG           — enable debug logging (default: false)
    MAX_CONTENT_MB  — max request body size in MB (default: 1)
"""

import logging
import os
import json
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

import metrics
from tantra import bucket, core, rajya, sarathi
from tantra.pipeline import run_tantra_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("keshav.api")

_max_mb = int(os.environ.get("MAX_CONTENT_MB", 1))
MAX_CONTENT_LENGTH = _max_mb * 1024 * 1024

app = FastAPI(title="KESHAV API", description="FastAPI wrapper for the full TANTRA pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://niyantrankendra.blackholeinfiverse.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > MAX_CONTENT_LENGTH:
                return JSONResponse(
                    {"status": "FAIL", "reason": "REQUEST_TOO_LARGE", "trace_id": ""},
                    status_code=413
                )
            
            # Starlette reads bodies incrementally, but we can also just rely on content-length
            # Since test client might not send content length sometimes, we'll also catch errors later.
        response = await call_next(request)
        return response

app.add_middleware(ContentSizeLimitMiddleware)


# ── error handlers ────────────────────────────────────────────────────────────

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse({"status": "FAIL", "reason": "NOT_FOUND", "trace_id": ""}, status_code=404)
    if exc.status_code == 405:
        return JSONResponse({"status": "FAIL", "reason": "METHOD_NOT_ALLOWED", "trace_id": ""}, status_code=405)
    return JSONResponse({"status": "FAIL", "reason": str(exc.detail), "trace_id": ""}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"status": "FAIL", "reason": "INVALID_JSON", "trace_id": ""}, status_code=400)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled internal error")
    return JSONResponse({"status": "FAIL", "reason": "INTERNAL_ERROR", "trace_id": ""}, status_code=500)


# ── routes ────────────────────────────────────────────────────────────────────

def check_content_type(request: Request):
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        raise HTTPException(status_code=415, detail="UNSUPPORTED_MEDIA_TYPE")

@app.post("/analyze", tags=["TANTRA"], dependencies=[Depends(check_content_type)])
async def analyze(request: Request, payload: Any = Body(
    ...,
    example={
        "trace_id": "rajya-trace-001",
        "execution_id": "exec-demo",
        "tasks": [{"task_id": "T1", "depends_on": []}],
        "constraint_results": [{"task_id": "T1", "is_valid": False, "unsatisfied_dependencies": []}],
        "propagation_results": [{"task_id": "T1", "affected_tasks": [], "impact_score": 10}]
    }
)):
    """
    POST /analyze
    Content-Type: application/json
    Body: KESHAV input contract (trace_id + execution_id required)
    """
    start_time = metrics.record_request_start()
    
    # Since FastAPI parses the JSON body into `payload` via the `Body` parameter,
    # and throws RequestValidationError (handled above) for invalid JSON, we can just use payload directly.
    try:
        # Check size explicitly for test client which might omit Content-Length
        raw_body = await request.body()
        if len(raw_body) > MAX_CONTENT_LENGTH:
            metrics.record_request_error(start_time)
            return JSONResponse({"status": "FAIL", "reason": "REQUEST_TOO_LARGE", "trace_id": ""}, status_code=413)

        input_data = payload
    except Exception:
        metrics.record_request_error(start_time)
        return JSONResponse({"status": "FAIL", "reason": "INVALID_JSON", "trace_id": ""}, status_code=400)

    if input_data is None:
        metrics.record_request_error(start_time)
        return JSONResponse({"status": "FAIL", "reason": "INVALID_JSON", "trace_id": ""}, status_code=400)

    trace_id = input_data.get("trace_id", "") if isinstance(input_data, dict) else ""
    logger.info("POST /analyze trace_id=%s", trace_id)

    # Execute the blocking pipeline in the threadpool to avoid freezing the event loop
    result = await run_in_threadpool(run_tantra_pipeline, input_data)

    if result["status"] == "FAIL":
        logger.warning("pipeline FAIL trace_id=%s error=%s", trace_id, result.get("error"))
        metrics.record_request_error(start_time)
        return JSONResponse(result["keshav_output"], status_code=400)

    logger.info("pipeline OK trace_id=%s", trace_id)
    severity = result["keshav_output"].get("severity", "UNKNOWN")
    metrics.record_request_success(start_time, severity, trace_id)
    return JSONResponse(result["keshav_output"], status_code=200)


@app.post("/api/v1/rajya/validate", tags=["TANTRA", "RAJYA"], dependencies=[Depends(check_content_type)])
@app.post("/rajya/consume", tags=["TANTRA", "RAJYA"], dependencies=[Depends(check_content_type)])
async def rajya_validate_endpoint(
    request: Request,
    payload: Any = Body(
        ...,
        example={
            "trace_id": "rajya-trace-001",
            "execution_id": "exec-demo",
            "root_cause": "T1 is blocked",
            "resolution_signal": "UNBLOCK_DEPENDENCY:T1",
            "impact_score": 10,
            "severity": "HIGH",
            "timestamp": "2026-07-25T10:00:00Z",
        },
    ),
):
    """
    POST /api/v1/rajya/validate (also accessible at POST /rajya/consume)
    Content-Type: application/json
    Body: KESHAV output contract

    Takes the output of KESHAV as input, consumes it through RAJYA, and passes it to Sarathi.
    """
    start_time = metrics.record_request_start()
    try:
        raw_body = await request.body()
        if len(raw_body) > MAX_CONTENT_LENGTH:
            metrics.record_request_error(start_time)
            return JSONResponse(
                {"status": "FAIL", "reason": "REQUEST_TOO_LARGE", "trace_id": ""},
                status_code=413,
            )
        input_data = payload
    except Exception:
        metrics.record_request_error(start_time)
        return JSONResponse(
            {"status": "FAIL", "reason": "INVALID_JSON", "trace_id": ""},
            status_code=400,
        )

    if not isinstance(input_data, dict) or not input_data.get("trace_id"):
        metrics.record_request_error(start_time)
        return JSONResponse(
            {
                "status": "FAIL",
                "reason": "MISSING_TRACE_ID_OR_INVALID_PAYLOAD",
                "trace_id": "",
            },
            status_code=400,
        )

    trace_id = str(input_data["trace_id"])
    logger.info("POST /api/v1/rajya/validate trace_id=%s", trace_id)

    def _blocking_execution():
        # 1. RAJYA directly consumes KESHAV output
        rajya_out = rajya.consume(input_data, trace_id)
        # 2. RAJYA's output is passed directly to Sarathi for enforcement
        sarathi_out = sarathi.enforce(rajya_out)
        # 3. Finalize execution layer in Core & Bucket
        core_out = core.execute(sarathi_out)
        bucket.write(core_out, input_data)
        return rajya_out, sarathi_out

    try:
        # Offload the blocking external network calls to the threadpool
        rajya_output, sarathi_output = await run_in_threadpool(_blocking_execution)

        logger.info("RAJYA -> Sarathi OK trace_id=%s", trace_id)
        severity = input_data.get("severity", "UNKNOWN")
        metrics.record_request_success(start_time, severity, trace_id)

        return JSONResponse(
            {
                "status": "EXECUTION_APPROVED",
                "trace_id": trace_id,
                "rajya_output": rajya_output,
                "sarathi_output": sarathi_output,
                "message": "KESHAV output successfully consumed by RAJYA and passed to Sarathi.",
            },
            status_code=200,
        )
    except ValueError as exc:
        logger.warning("RAJYA/Sarathi contract violation trace_id=%s: %s", trace_id, exc)
        metrics.record_request_error(start_time)
        return JSONResponse(
            {"status": "REJECT", "reason": str(exc), "trace_id": trace_id},
            status_code=400,
        )
    except Exception as exc:
        logger.exception("Unexpected error during RAJYA/Sarathi processing trace_id=%s", trace_id)
        metrics.record_request_error(start_time)
        return JSONResponse(
            {"status": "FAIL", "reason": f"INTERNAL_ERROR: {exc}", "trace_id": trace_id},
            status_code=500,
        )


@app.get("/health", tags=["System"])
async def health():
    """GET /health — liveness + readiness check."""
    return JSONResponse({"status": "OK", "service": "KESHAV"}, status_code=200)


@app.get("/metrics")
async def metrics_endpoint():
    """GET /metrics — Prometheus-compatible metrics."""
    return Response(content=metrics.get_prometheus_metrics(), status_code=200, media_type="text/plain; charset=utf-8")


@app.get("/metrics/json")
async def metrics_json():
    """GET /metrics/json — JSON metrics for debugging."""
    return JSONResponse(metrics.get_metrics(), status_code=200)


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    uvicorn.run("api:app", host=host, port=port, reload=debug)

"""
KESHAV API — Flask wrapper for the full TANTRA pipeline

Endpoints:
    POST /analyze   — run full TANTRA chain, returns KESHAV output contract
    GET  /health    — liveness + readiness check

Run (development):
    python api.py

Run (production):
    gunicorn "api:app" --workers 4 --bind 0.0.0.0:5000

Environment variables:
    PORT            — listening port (default: 5000)
    HOST            — bind address  (default: 127.0.0.1)
    DEBUG           — enable Flask debug mode (default: false)
    MAX_CONTENT_MB  — max request body size in MB (default: 1)
"""

import logging
import os

from flask import Flask, jsonify, request
from flasgger import Swagger

import metrics
from tantra.pipeline import run_tantra_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("keshav.api")

app = Flask(__name__)
swagger = Swagger(app)

_max_mb = int(os.environ.get("MAX_CONTENT_MB", 1))
app.config["MAX_CONTENT_LENGTH"] = _max_mb * 1024 * 1024


# ── error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(413)
def request_too_large(_e):
    return jsonify({"status": "FAIL", "reason": "REQUEST_TOO_LARGE", "trace_id": ""}), 413


@app.errorhandler(405)
def method_not_allowed(_e):
    return jsonify({"status": "FAIL", "reason": "METHOD_NOT_ALLOWED", "trace_id": ""}), 405


@app.errorhandler(404)
def not_found(_e):
    return jsonify({"status": "FAIL", "reason": "NOT_FOUND", "trace_id": ""}), 404


@app.errorhandler(500)
def internal_error(_e):
    logger.exception("Unhandled internal error")
    return jsonify({"status": "FAIL", "reason": "INTERNAL_ERROR", "trace_id": ""}), 500


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/analyze", methods=["POST"])
def analyze():
    """
    POST /analyze
    Content-Type: application/json
    Body: KESHAV input contract (trace_id + execution_id required)

    Returns 200 with TANTRA output on success.
    Returns 400 with FAIL response on invalid input.
    Returns 415 if Content-Type is not application/json.
    ---
    tags:
      - TANTRA
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - trace_id
            - execution_id
          properties:
            trace_id:
              type: string
              example: "upstream-trace-001"
            execution_id:
              type: string
              example: "exec-001"
            tasks:
              type: array
              items:
                type: object
    responses:
      200:
        description: TANTRA output on success
      400:
        description: Invalid input contract or pipeline failure
      415:
        description: Unsupported Media Type (not application/json)
    """
    start_time = metrics.record_request_start()
    
    if not request.is_json:
        metrics.record_request_error(start_time)
        return jsonify({"status": "FAIL", "reason": "UNSUPPORTED_MEDIA_TYPE", "trace_id": ""}), 415

    input_data = request.get_json(silent=True)
    if input_data is None:
        metrics.record_request_error(start_time)
        return jsonify({"status": "FAIL", "reason": "INVALID_JSON", "trace_id": ""}), 400

    trace_id = input_data.get("trace_id", "") if isinstance(input_data, dict) else ""
    logger.info("POST /analyze trace_id=%s", trace_id)

    result = run_tantra_pipeline(input_data)

    if result["status"] == "FAIL":
        logger.warning("pipeline FAIL trace_id=%s error=%s", trace_id, result.get("error"))
        metrics.record_request_error(start_time)
        return jsonify(result["keshav_output"]), 400

    logger.info("pipeline OK trace_id=%s", trace_id)
    severity = result["keshav_output"].get("severity", "UNKNOWN")
    metrics.record_request_success(start_time, severity, trace_id)
    return jsonify(result["keshav_output"]), 200


@app.route("/health", methods=["GET"])
def health():
    """GET /health — liveness + readiness check.
    ---
    tags:
      - System
    responses:
      200:
        description: OK
    """
    return jsonify({"status": "OK", "service": "KESHAV"}), 200


@app.route("/metrics", methods=["GET"])
def metrics_endpoint():
    """GET /metrics — Prometheus-compatible metrics."""
    return metrics.get_prometheus_metrics(), 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/metrics/json", methods=["GET"])
def metrics_json():
    """GET /metrics/json — JSON metrics for debugging."""
    return jsonify(metrics.get_metrics()), 200


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)

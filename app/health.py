"""
KESHAV-4 Health Check Module
Gap 4 — Deployment Readiness: Health endpoint for operational observability.

Provides a standard health-check function that can be invoked by load balancers,
container orchestrators, or monitoring systems to verify service readiness.
"""
import time
from shared_schemas.schemas import PropagationInput, PropagationOutput


class HealthStatus:
    """Encapsulates a health check result."""
    def __init__(self, status: str, checks: dict, elapsed_ms: float):
        self.status = status
        self.checks = checks
        self.elapsed_ms = elapsed_ms
    
    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "service": "KESHAV-4-PropagationEngine",
            "checks": self.checks,
            "elapsed_ms": round(self.elapsed_ms, 3)
        }


def check_health() -> HealthStatus:
    """
    Performs a non-destructive health check on the PropagationEngine.
    
    Checks:
    1. Schema import integrity — Can PropagationInput/Output be instantiated?
    2. Engine computation — Can compute_downstream_path run a trivial graph?
    3. Bounded latency — Does the check complete within 500ms?
    
    Returns:
        HealthStatus with status "healthy" or "unhealthy".
    """
    from app.engine import PropagationEngine
    
    checks = {}
    start = time.perf_counter()
    overall_healthy = True
    
    # Check 1: Schema import integrity
    try:
        _ = PropagationInput(
            blocked_task_id="healthcheck",
            root_cause="healthcheck",
            trace_id="healthcheck",
            timestamp="healthcheck",
            dependency_graph={"healthcheck": []}
        )
        checks["schema_import"] = "ok"
    except Exception as e:
        checks["schema_import"] = f"FAIL: {str(e)}"
        overall_healthy = False
    
    # Check 2: Engine computation
    try:
        path = PropagationEngine.compute_downstream_path(
            "A", {"A": ["B"], "B": ["C"]}
        )
        if path == ["B", "C"]:
            checks["engine_computation"] = "ok"
        else:
            checks["engine_computation"] = f"FAIL: unexpected path {path}"
            overall_healthy = False
    except Exception as e:
        checks["engine_computation"] = f"FAIL: {str(e)}"
        overall_healthy = False
    
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    # Check 3: Bounded latency
    if elapsed_ms < 500:
        checks["latency_bound"] = "ok"
    else:
        checks["latency_bound"] = f"FAIL: {elapsed_ms:.1f}ms exceeds 500ms"
        overall_healthy = False
    
    status = "healthy" if overall_healthy else "unhealthy"
    return HealthStatus(status=status, checks=checks, elapsed_ms=elapsed_ms)


if __name__ == "__main__":
    import json
    result = check_health()
    print(json.dumps(result.to_dict(), indent=2))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

VALID_INPUT = {
    "blocked_task_id": "T1",
    "root_cause": "RC",
    "trace_id": "trace-api-test-001",
    "timestamp": "2026-05-22T12:00:00Z",
    "dependency_graph": {"RC": ["T1", "T2"], "T1": ["T3"], "T2": ["T3"]}
}

def test_api_propagation_success():
    response = client.post("/api/v1/propagation", json=VALID_INPUT)
    assert response.status_code == 200
    data = response.json()
    assert data["blocked_task_id"] == "T1"
    assert data["root_cause"] == "RC"
    assert data["impacted_tasks"] == ["T3"]
    assert data["impact_score"] == 1
    assert data["severity"] == "LOW"
    assert data["resolution_signal"] == "UNBLOCK_DEPENDENCY:RC"
    assert data["trace_id"] == "trace-api-test-001"
    assert data["timestamp"] == "2026-05-22T12:00:00Z"

def test_api_propagation_invalid_graph_structure():
    payload = VALID_INPUT.copy()
    payload["dependency_graph"] = "NOT_A_DICT"
    
    response = client.post("/api/v1/propagation", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "SCHEMA_MISMATCH"
    assert "validation" in data["message"].lower() or "input" in data["message"].lower()

def test_api_propagation_missing_required_fields():
    payload = VALID_INPUT.copy()
    payload.pop("blocked_task_id")
    
    response = client.post("/api/v1/propagation", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "SCHEMA_MISMATCH"
    assert "validation" in data["message"].lower() or "input" in data["message"].lower()

def test_api_propagation_extra_fields_forbidden():
    payload = VALID_INPUT.copy()
    payload["unknown_extra_field"] = "some_value"
    
    response = client.post("/api/v1/propagation", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "SCHEMA_MISMATCH"
    assert "extra" in data["message"].lower() or "unknown_extra_field" in data["message"].lower() or "validation" in data["message"].lower()

def test_api_propagation_broken_root_cause():
    payload = VALID_INPUT.copy()
    payload["root_cause"] = "NON_EXISTENT_RC"
    
    response = client.post("/api/v1/propagation", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "BROKEN_ROOT_CAUSE"

def test_api_propagation_invalid_graph_nodes():
    payload = VALID_INPUT.copy()
    payload["blocked_task_id"] = "NON_EXISTENT_BLOCKED"
    
    response = client.post("/api/v1/propagation", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_GRAPH"

def test_api_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "KESHAV-4-PropagationEngine"
    assert "schema_import" in data["checks"]
    assert "engine_computation" in data["checks"]
    assert "latency_bound" in data["checks"]

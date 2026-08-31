# KESHAV Production Deployment Guide

**Status:** Production Ready  
**Service:** Deterministic Dependency Intelligence Layer (FastAPI / Gunicorn)  
**Host Port:** `5003` (Container Internal Port: `5000`)

---

## 1. Blackhole Production VM Deployment & CI/CD

KESHAV is deployed onto the Blackhole production VM via automated GitHub Actions CI/CD (`.github/workflows/cicd.yml`).

### Architecture Overview
- **Service Name**: `keshav-backend`
- **Port Mapping**: `5003:5000` (FastAPI / Gunicorn with Uvicorn workers)
- **Deployment Directory on VM**: `~/KESHAV`
- **Docker Compose Template**: `docker-compose.production.template.yml`
- **Container Name**: `bhiv_keshav_backend`
- **Health Check**: `GET http://localhost:5003/health` $\to$ `{"status": "OK", "service": "KESHAV"}`

### GitHub Secrets Required
| Secret Name | Description |
|---|---|
| `DOCKER_USERNAME` | Docker Hub username (`bhiv`) |
| `DOCKER_PASSWORD` | Docker Hub access token |
| `VM_IP` | Remote VM IP address |
| `VM_PORT` | SSH Port (e.g., `22`) |
| `VM_USERNAME` | SSH username |
| `VM_PASSWORD` | SSH password |
| `KESHAV_ENV_FILE` (or `ENV_FILE`) | Full production `.env` file contents |

### CI/CD Pipeline Stages
1. **Validate**: Generates `docker-compose.production.yml` with Git commit SHA and validates compose configuration.
2. **Build**: Builds multi-stage Docker image and pushes `bhiv/keshav-backend:<short_sha>` and `:latest` to Docker Hub.
3. **Deploy**: Securely transfers deployment package to `~/KESHAV` on VM via SSH, starts container stack, verifies health check loop on port `5003`, and updates `RELEASE_HISTORY.md`.
4. **Rollback**: Automatically triggers upon deployment failure, restoring the last recorded healthy Git SHA from persistent release history.

---

## 2. Quick Start

### Local Development
```bash
pip install -e ".[dev]"
python api.py
```

### Production (Docker)
```bash
docker build -t bhiv/keshav-backend:latest .
docker run -d --name keshav_backend -p 5003:5000 --env-file .env bhiv/keshav-backend:latest
```

### Production (Docker Compose)
```bash
docker compose up -d
```

---

## 3. Health Check & Verification Endpoints

- **Liveness & Readiness Probe**:
  ```bash
  curl http://localhost:5003/health
  # Response: {"status": "OK", "service": "KESHAV"}
  ```

- **Prometheus Metrics**:
  ```bash
  curl http://localhost:5003/metrics
  ```

- **JSON Metrics (Debugging)**:
  ```bash
  curl http://localhost:5003/metrics/json
  ```

- **Analyze Endpoint**:
  ```bash
  curl -X POST http://localhost:5003/analyze \
    -H "Content-Type: application/json" \
    -d @sample_input.json
  ```

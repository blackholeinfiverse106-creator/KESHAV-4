import os
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from shared_schemas.schemas import (
    PropagationInput,
    PropagationOutput,
    PropagationContractViolation,
)
from app.engine import PropagationEngine
from app.health import check_health

app = FastAPI(
    title="KESHAV Propagation Service",
    description="FastAPI service for KESHAV-4 dependency propagation engine",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(PropagationContractViolation)
async def contract_violation_handler(request: Request, exc: PropagationContractViolation):
    """
    Handles internal business rule violations, e.g. BROKEN_ROOT_CAUSE or INVALID_GRAPH.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_code": exc.code,
            "message": exc.message
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Maps FastAPI / Pydantic validation errors (extra fields, bad types, missing fields)
    to match the contract violation SCHEMA_MISMATCH format.
    """
    errors_str = str(exc.errors())
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_code": "SCHEMA_MISMATCH",
            "message": f"Input validation failed: {errors_str}"
        }
    )

@app.post("/api/v1/propagation", response_model=PropagationOutput)
def compute_propagation(payload: PropagationInput):
    """
    Computes downstream propagation and blast radius.
    """
    input_dict = payload.model_dump()
    output_dict = PropagationEngine.compute_dependency_output(input_dict)
    return output_dict

@app.get("/health")
def health_check():
    """
    Operational observability health check.
    """
    result = check_health()
    status_code = status.HTTP_200_OK if result.status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content=result.to_dict()
    )

if __name__ == "__main__":
    port = int(os.getenv("KESHAV_PORT", "8081"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

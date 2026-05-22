from typing import List, Literal, Dict
from pydantic import BaseModel, ConfigDict, Field

class PropagationContractViolation(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")

class PropagationInput(BaseModel):
    blocked_task_id: str = Field(..., min_length=1)
    root_cause: str = Field(..., min_length=1)
    trace_id: str = Field(..., min_length=1)
    timestamp: str = Field(..., min_length=1)
    dependency_graph: Dict[str, List[str]]

    model_config = ConfigDict(extra="forbid")
class PropagationOutput(BaseModel):
    blocked_task_id: str
    root_cause: str
    impacted_tasks: List[str]
    impact_score: int
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    resolution_signal: str
    trace_id: str
    timestamp: str

    model_config = ConfigDict(extra="forbid")

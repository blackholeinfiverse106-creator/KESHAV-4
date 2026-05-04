from typing import List, Literal
from pydantic import BaseModel, ConfigDict

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

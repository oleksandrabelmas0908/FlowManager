from enum import Enum
from uuid import uuid4
from datetime import datetime

from pydantic import BaseModel, Field

from schemas.task import TaskDefinition, TaskResult
from schemas.condition import Condition


class ExecutionStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FlowDefinition(BaseModel):
    id: str
    name: str
    start_task: str
    tasks: list[TaskDefinition]
    conditions: list[Condition]


class FlowEnvelope(BaseModel):
    flow: FlowDefinition


class FlowExecution(BaseModel):
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    flow_id: str
    status: ExecutionStatus = ExecutionStatus.RUNNING
    current_task: str | None = None
    task_results: list[TaskResult] = []
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = None
    error: str | None = None

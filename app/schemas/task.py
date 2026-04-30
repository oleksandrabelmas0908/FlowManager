from enum import Enum
from datetime import datetime

from pydantic import BaseModel


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"


class TaskDefinition(BaseModel):
    name: str
    description: str


class TaskResult(BaseModel):
    task_name: str
    status: TaskStatus
    output: dict | None = None
    error: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
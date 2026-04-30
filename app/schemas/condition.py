from pydantic import BaseModel


class Condition(BaseModel):
    name: str
    description: str
    source_task: str
    outcome: str
    target_task_success: str
    target_task_failure: str
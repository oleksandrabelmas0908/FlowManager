import asyncio
from datetime import datetime

import tasks  # noqa: F401 — ensures Celery task decorators run before engine is called
from utils.celery_app import celery_app
from schemas import ExecutionStatus, FlowDefinition, FlowExecution, TaskResult, TaskStatus


async def execute_flow(flow: FlowDefinition, execution: FlowExecution) -> FlowExecution:
    condition_index = {condition.source_task: condition for condition in flow.conditions}
    current_task_name = flow.start_task

    while current_task_name and current_task_name != "end":
        task = celery_app.tasks.get(current_task_name)
        if task is None:
            execution.status = ExecutionStatus.FAILED
            execution.error = f"No task registered for '{current_task_name}'"
            execution.finished_at = datetime.now()
            return execution

        context = {
            "execution_id": execution.execution_id,
            "flow_id": execution.flow_id,
            "previous_results": [r.model_dump(mode="json") for r in execution.task_results],
        }

        result = TaskResult(
            task_name=current_task_name,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(),
        )

        try:
            raw = await asyncio.to_thread(
                lambda: task.apply(kwargs={"context": context}).get()
            )
            actual_outcome = raw.get("outcome", "failure")
            result.output = raw.get("data")
            result.status = TaskStatus.SUCCESS if actual_outcome == "success" else TaskStatus.FAILURE
        except Exception as e:
            actual_outcome = "failure"
            result.status = TaskStatus.FAILURE
            result.error = str(e)

        result.finished_at = datetime.now()
        execution.task_results.append(result)
        execution.current_task = current_task_name

        condition = condition_index.get(current_task_name)
        if condition is None:
            break

        if actual_outcome == condition.outcome:
            current_task_name = condition.target_task_success
        else:
            current_task_name = condition.target_task_failure

    execution.status = ExecutionStatus.COMPLETED
    execution.finished_at = datetime.now()
    return execution

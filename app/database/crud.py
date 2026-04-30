from typing import Optional

from sqlalchemy import select

from database.db import AsyncSessionLocal
from database.models import ExecutionModel, FlowModel
from schemas import FlowDefinition, FlowExecution


async def save_flow(flow: FlowDefinition) -> None:
    data = flow.model_dump(mode="json")
    async with AsyncSessionLocal() as db:
        existing = await db.get(FlowModel, flow.id)
        if existing:
            existing.name = data["name"]
            existing.start_task = data["start_task"]
            existing.tasks = data["tasks"]
            existing.conditions = data["conditions"]
        else:
            db.add(FlowModel(
                id=data["id"],
                name=data["name"],
                start_task=data["start_task"],
                tasks=data["tasks"],
                conditions=data["conditions"],
            ))
        await db.commit()


async def get_flow(flow_id: str) -> Optional[FlowDefinition]:
    async with AsyncSessionLocal() as db:
        row = await db.get(FlowModel, flow_id)
        if row is None:
            return None
        return FlowDefinition.model_validate({
            "id": row.id,
            "name": row.name,
            "start_task": row.start_task,
            "tasks": row.tasks,
            "conditions": row.conditions,
        })


async def list_flows() -> list[FlowDefinition]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(FlowModel))
        return [
            FlowDefinition.model_validate({
                "id": r.id,
                "name": r.name,
                "start_task": r.start_task,
                "tasks": r.tasks,
                "conditions": r.conditions,
            })
            for r in result.scalars().all()
        ]


async def delete_flow(flow_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        row = await db.get(FlowModel, flow_id)
        if row is None:
            return False
        await db.delete(row)
        await db.commit()
        return True


async def save_execution(execution: FlowExecution) -> None:
    data = execution.model_dump(mode="json")
    async with AsyncSessionLocal() as db:
        existing = await db.get(ExecutionModel, execution.execution_id)
        if existing:
            existing.status = data["status"]
            existing.current_task = data.get("current_task")
            existing.task_results = data["task_results"]
            existing.finished_at = execution.finished_at
            existing.error = data.get("error")
        else:
            db.add(ExecutionModel(
                execution_id=data["execution_id"],
                flow_id=data["flow_id"],
                status=data["status"],
                current_task=data.get("current_task"),
                task_results=data["task_results"],
                started_at=execution.started_at,
                finished_at=execution.finished_at,
                error=data.get("error"),
            ))
        await db.commit()


async def get_execution(execution_id: str) -> Optional[FlowExecution]:
    async with AsyncSessionLocal() as db:
        row = await db.get(ExecutionModel, execution_id)
        if row is None:
            return None
        return FlowExecution.model_validate({
            "execution_id": row.execution_id,
            "flow_id": row.flow_id,
            "status": row.status,
            "current_task": row.current_task,
            "task_results": row.task_results,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "error": row.error,
        })


async def list_executions_for_flow(flow_id: str) -> list[FlowExecution]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ExecutionModel).where(ExecutionModel.flow_id == flow_id)
        )
        return [
            FlowExecution.model_validate({
                "execution_id": r.execution_id,
                "flow_id": r.flow_id,
                "status": r.status,
                "current_task": r.current_task,
                "task_results": r.task_results,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "error": r.error,
            })
            for r in result.scalars().all()
        ]

from fastapi import APIRouter, HTTPException

from database import crud
from schemas.flow import FlowExecution

router = APIRouter(prefix="/api/v1", tags=["executions"])


@router.get("/executions/{execution_id}", response_model=FlowExecution)
async def get_execution(execution_id: str):
    execution = await crud.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution

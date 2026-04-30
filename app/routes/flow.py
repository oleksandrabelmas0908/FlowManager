from fastapi import APIRouter, HTTPException

from database import crud
from schemas import FlowDefinition, FlowEnvelope, FlowExecution
from utils import executer

router = APIRouter(prefix="/api/v1", tags=["flows"])


@router.post("/flows", status_code=201, response_model=FlowDefinition)
async def create_flow(body: FlowEnvelope):
    flow = body.flow
    if await crud.get_flow(flow.id):
        raise HTTPException(status_code=409, detail=f"Flow '{flow.id}' already exists")
    await crud.save_flow(flow)
    return flow


@router.get("/flows", response_model=list[FlowDefinition])
async def list_flows():
    return await crud.list_flows()


@router.get("/flows/{flow_id}", response_model=FlowDefinition)
async def get_flow(flow_id: str):
    flow = await crud.get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")
    return flow


@router.delete("/flows/{flow_id}", status_code=204)
async def delete_flow(flow_id: str):
    if not await crud.delete_flow(flow_id):
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")


@router.post("/flows/{flow_id}/execute", status_code=202, response_model=FlowExecution)
async def execute_flow(flow_id: str):
    flow = await crud.get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")
    execution = FlowExecution(flow_id=flow_id)
    result = await executer.execute_flow(flow, execution)
    await crud.save_execution(result)
    return result


@router.get("/flows/{flow_id}/executions", response_model=list[FlowExecution])
async def list_executions(flow_id: str):
    return await crud.list_executions_for_flow(flow_id)

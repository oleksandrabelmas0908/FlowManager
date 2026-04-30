from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB

from database.db import Base


class FlowModel(Base):
    __tablename__ = "flows"

    id         = Column(String, primary_key=True)
    name       = Column(String, nullable=False)
    start_task = Column(String, nullable=False)
    tasks      = Column(JSONB, nullable=False)
    conditions = Column(JSONB, nullable=False)


class ExecutionModel(Base):
    __tablename__ = "executions"

    execution_id = Column(String, primary_key=True)
    flow_id      = Column(String, nullable=False, index=True)
    status       = Column(String, nullable=False)
    current_task = Column(String, nullable=True)
    task_results = Column(JSONB, nullable=False)
    started_at   = Column(DateTime, nullable=False)
    finished_at  = Column(DateTime, nullable=True)
    error        = Column(String, nullable=True)

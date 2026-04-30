from contextlib import asynccontextmanager

from fastapi import FastAPI

from database.db import Base, engine
from routes import flow_router, execution_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Flow Manager",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(flow_router)
app.include_router(execution_router)

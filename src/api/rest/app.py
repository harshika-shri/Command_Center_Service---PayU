from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from src.api.rest.middleware.cors import add_cors_middleware
from src.api.rest.middleware.error_handler import add_error_handlers
from src.api.rest.routes.dashboard import router as dashboard_router
from src.api.rest.routes.health import router as health_router
from src.consumers.validation_stream_consumer import (
    get_validation_stream_consumer,
)
from src.data.clients.postgres_client import get_or_create_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = get_or_create_engine()

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

        print("Database connected")

    except Exception as error:
        print("Database connection failed")
        print(error)

    consumer = get_validation_stream_consumer()
    await consumer.start()

    yield

    await consumer.stop()
    await engine.dispose()

    print("Database connections closed")


app = FastAPI(
    title="PayU Command Center",
    lifespan=lifespan,
)

add_cors_middleware(app)
add_error_handlers(app)

app.include_router(router=health_router)
app.include_router(router=dashboard_router)

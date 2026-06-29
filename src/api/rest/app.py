from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from src.api.rest.middleware.cors import add_cors_middleware
from src.api.rest.middleware.error_handler import add_error_handlers
from src.api.rest.routes.dashboard import router as dashboard_router
from src.api.rest.routes.events import router as events_router
from src.api.rest.routes.finance_associate import (
    router as finance_associate_router,
)
from src.api.rest.routes.finance_manager import (
    router as finance_manager_router,
)
from src.api.rest.routes.events import (
    router as events_router,
)
from src.api.rest.routes.health import router as health_router
from src.api.rest.routes.invoice_approval import (
    router as invoice_approval_router,
)
from src.api.rest.routes.invoice_clarification import (
    router as invoice_clarification_router,
)
from src.api.rest.routes.invoice_escalation import (
    router as invoice_escalation_router,
)
from src.api.rest.routes.invoice_rejection import (
    router as invoice_rejection_router,
)
from src.api.rest.routes.invoice_review import (
    router as invoice_review_router,
)
from src.api.rest.routes.invoice_take_ownership import (
    router as invoice_take_ownership_router,
)
from src.api.rest.routes.notifications import (
    router as notifications_router,
)
from src.api.rest.routes.report_router import (
    router as reports_router,
)
from src.api.rest.routes.users import (
    router as users_router,
)
from src.consumers.validation_stream_consumer import (
    get_validation_stream_consumer,
)
from src.core.sse.sse_manager import get_sse_manager
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

    sse_manager = get_sse_manager()
    await sse_manager.start()

    yield

    await sse_manager.stop()
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
app.include_router(router=events_router)
app.include_router(router=finance_associate_router)
app.include_router(router=finance_manager_router)
app.include_router(router=invoice_review_router)
app.include_router(router=invoice_approval_router)
app.include_router(router=invoice_escalation_router)
app.include_router(router=invoice_clarification_router)
app.include_router(router=invoice_rejection_router)
app.include_router(router=invoice_take_ownership_router)
app.include_router(router=notifications_router)
app.include_router(router=events_router)
app.include_router(router=reports_router)
app.include_router(router=users_router)

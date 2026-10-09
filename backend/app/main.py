from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, bookings, feedback, health, ingestion, labs, student, users
from app.core.config import get_settings

# Import models so they register on Base.metadata before create_all.
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Dev convenience only -- Alembic migrations are the source of truth once
    # the schema needs to evolve without dropping local data.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SCIT Computing Lab Scheduling API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(ingestion.router, prefix="/api")
app.include_router(labs.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(student.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")

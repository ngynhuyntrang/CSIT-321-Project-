from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password, hash_token, new_session_token
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models.user import ROLE_ADMIN, ROLE_STUDENT, STATUS_ACTIVE, AuthSession, User
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(
    db_session: Session, *, role: str, email: str | None = None, status: str = STATUS_ACTIVE
) -> tuple[User, str]:
    """Creates a user with a live session and returns (user, bearer token)."""
    user = User(
        email=email or f"{role}@uow.edu.au",
        full_name=f"Test {role.title()}",
        role=role,
        status=status,
        password_hash=hash_password("password123"),
    )
    db_session.add(user)
    db_session.flush()
    token = new_session_token()
    db_session.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
        )
    )
    db_session.commit()
    return user, token


@pytest.fixture()
def admin_client(client: TestClient, db_session: Session) -> TestClient:
    _, token = make_user(db_session, role=ROLE_ADMIN)
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture()
def student_client(client: TestClient, db_session: Session) -> TestClient:
    _, token = make_user(db_session, role=ROLE_STUDENT, email="student@uowmail.edu.au")
    client.headers["Authorization"] = f"Bearer {token}"
    return client

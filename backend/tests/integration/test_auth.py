from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.user import ROLE_ADMIN, AuthSession, User
from tests.conftest import make_user

STUDENT = {
    "email": "Alex.Nguyen@uowmail.edu.au",
    "full_name": "Alex Nguyen",
    "student_number": "7654321",
    "role": "student",
    "password": "password123",
}


def _login(client: TestClient, email: str, password: str = "password123", **extra: object):
    return client.post("/api/auth/login", json={"email": email, "password": password, **extra})


def test_student_signup_is_active_and_can_log_in(client: TestClient):
    response = client.post("/api/auth/signup", json=STUDENT)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alex.nguyen@uowmail.edu.au"
    assert body["status"] == "active"
    assert "password_hash" not in body

    login = _login(client, "alex.nguyen@uowmail.edu.au")
    assert login.status_code == 200
    token = login.json()["token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "student"


def test_signup_rejects_non_uow_email(client: TestClient):
    response = client.post("/api/auth/signup", json={**STUDENT, "email": "alex@gmail.com"})
    assert response.status_code == 422
    assert "uowmail" in response.text


def test_signup_rejects_weak_password(client: TestClient):
    response = client.post("/api/auth/signup", json={**STUDENT, "password": "short"})
    assert response.status_code == 422


def test_signup_cannot_self_assign_admin(client: TestClient):
    response = client.post("/api/auth/signup", json={**STUDENT, "role": "admin"})
    assert response.status_code == 422


def test_duplicate_email_rejected(client: TestClient):
    client.post("/api/auth/signup", json=STUDENT)
    assert client.post("/api/auth/signup", json=STUDENT).status_code == 409


def test_wrong_password_gives_generic_error(client: TestClient):
    client.post("/api/auth/signup", json=STUDENT)
    response = _login(client, STUDENT["email"], "wrongpassword1")
    assert response.status_code == 401
    assert response.json()["detail"] == "Email or password is incorrect."


def test_staff_signup_is_pending_until_admin_approves(client: TestClient, db_session: Session):
    staff = {**STUDENT, "email": "coord@uow.edu.au", "role": "staff", "student_number": None}
    assert client.post("/api/auth/signup", json=staff).json()["status"] == "pending"
    pending_login = _login(client, "coord@uow.edu.au")
    assert pending_login.status_code == 403
    assert "awaiting approval" in pending_login.json()["detail"]

    _, admin_token = make_user(db_session, role=ROLE_ADMIN)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    pending = client.get("/api/users?status=pending", headers=admin_headers).json()
    assert [u["email"] for u in pending] == ["coord@uow.edu.au"]

    approve = client.patch(
        f"/api/users/{pending[0]['id']}", json={"status": "active"}, headers=admin_headers
    )
    assert approve.status_code == 200
    assert _login(client, "coord@uow.edu.au").status_code == 200


def test_logout_revokes_token(client: TestClient):
    client.post("/api/auth/signup", json=STUDENT)
    headers = {"Authorization": f"Bearer {_login(client, STUDENT['email']).json()['token']}"}
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_remember_me_extends_session(client: TestClient):
    client.post("/api/auth/signup", json=STUDENT)
    short = datetime.fromisoformat(_login(client, STUDENT["email"]).json()["expires_at"])
    long = datetime.fromisoformat(
        _login(client, STUDENT["email"], remember_me=True).json()["expires_at"]
    )
    assert long - short > timedelta(days=25)


def test_expired_session_is_rejected(client: TestClient, db_session: Session):
    user, token = make_user(db_session, role="student")
    session = db_session.query(AuthSession).filter(AuthSession.user_id == user.id).one()
    session.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
    db_session.commit()
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_missing_token_is_401(client: TestClient):
    assert client.get("/api/labs").status_code == 401


def test_student_cannot_upload_or_manage_users(student_client: TestClient):
    upload = student_client.post("/api/ingestion/upload", files={"file": ("x.xlsx", b"")})
    assert upload.status_code == 403
    assert student_client.get("/api/users").status_code == 403
    assert student_client.get("/api/labs").status_code == 200


def test_disabling_a_user_ends_their_sessions(client: TestClient, db_session: Session):
    student, student_token = make_user(db_session, role="student")
    _, admin_token = make_user(db_session, role=ROLE_ADMIN)
    client.patch(
        f"/api/users/{student.id}",
        json={"status": "disabled"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {student_token}"})
    assert response.status_code == 401
    assert db_session.get(User, student.id).status == "disabled"

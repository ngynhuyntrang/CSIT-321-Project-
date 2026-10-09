from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.user import ROLE_ADMIN
from tests.booking_helpers import make_baseline, make_entry, make_lab
from tests.conftest import make_user


def _submit(client: TestClient, **overrides: object):
    body = {"category": "room", "rating": 2, "comment": "Not enough working PCs.", **overrides}
    return client.post("/api/feedback", json=body)


def test_student_submits_and_sees_own_feedback(student_client: TestClient, db_session: Session):
    run = make_baseline(db_session)
    lab = make_lab(db_session, "3-230", 26)
    entry = make_entry(db_session, run, lab, subject="CSIT213", name="CSIT213-CL/01")

    response = _submit(student_client, entry_id=entry.id)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "received"
    assert body["lab_code"] == "3-230"
    assert "CSIT213" in body["class_label"]

    mine = student_client.get("/api/feedback/mine").json()
    assert [f["id"] for f in mine] == [body["id"]]


def test_feedback_validation(student_client: TestClient):
    assert _submit(student_client, rating=6).status_code == 422
    assert _submit(student_client, category="vibes").status_code == 422
    assert _submit(student_client, entry_id=999).status_code == 404


def test_admin_reviews_and_anonymous_hides_author(
    student_client: TestClient, client: TestClient, db_session: Session
):
    _submit(student_client, anonymous=True)
    _submit(student_client, comment="Thursday has a long gap.", category="days")

    _, admin_token = make_user(db_session, role=ROLE_ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}
    listed = client.get("/api/feedback", headers=headers).json()
    authors = {f["comment"]: f["author"] for f in listed}
    assert authors["Not enough working PCs."] is None
    assert authors["Thursday has a long gap."] == "Test Student"

    reviewed = client.patch(f"/api/feedback/{listed[0]['id']}", json={"status": "reviewed"}, headers=headers)
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "reviewed"
    assert len(client.get("/api/feedback?status=received", headers=headers).json()) == 1


def test_students_cannot_list_everyones_feedback(student_client: TestClient):
    assert student_client.get("/api/feedback").status_code == 403

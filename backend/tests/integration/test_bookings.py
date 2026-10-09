from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.baseline import BaselineScheduleEntry, ScheduleOccurrence
from app.db.models.booking import BookingChange
from app.schemas.booking import Recurrence
from tests.booking_helpers import TUE, make_baseline, make_entry, make_lab


@pytest.fixture()
def baseline(db_session: Session) -> dict:
    run = make_baseline(db_session)
    small = make_lab(db_session, "3-124", 28)
    big = make_lab(db_session, "3-125", 40)
    unknown = make_lab(db_session, "3-999", None)
    held = make_entry(db_session, run, small, subject="CSIT213", start=time(10, 0), cohort=26)
    return {"run": run, "small": small, "big": big, "unknown": unknown, "held": held}


def _new(lab_id: int, **overrides: object) -> dict:
    body = {
        "subject_codes": ["csci235"],
        "activity_name": "CSCI235-CL/05",
        "class_type": "Computer Lab",
        "lab_id": lab_id,
        "start_time": "12:30",
        "duration_minutes": 60,
        "cohort_size": 36,
        "recurrence": {"first_date": str(TUE), "occurrences": 4, "frequency": "weekly"},
    }
    body.update(overrides)
    return body


def test_recurrence_skips_dates_without_shortening():
    recurrence = Recurrence(
        first_date=date(2026, 3, 3), occurrences=3, frequency="weekly", skip_dates=[date(2026, 3, 10)]
    )
    assert recurrence.dates() == [date(2026, 3, 3), date(2026, 3, 17), date(2026, 3, 24)]
    fortnightly = Recurrence(first_date=date(2026, 3, 3), occurrences=2, frequency="fortnightly")
    assert fortnightly.dates() == [date(2026, 3, 3), date(2026, 3, 17)]


def test_create_booking_writes_occurrences_and_history(
    admin_client: TestClient, db_session: Session, baseline: dict
):
    response = admin_client.post("/api/bookings", json=_new(baseline["big"].id))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source"] == "manual"
    assert body["subject_codes"] == ["CSCI235"]
    assert body["day_of_week"] == "tue"
    assert body["occurrence_count"] == 4
    assert body["dates"][0] == str(TUE)
    assert [h["action"] for h in body["history"]] == ["create"]


def test_clashing_create_is_rejected_with_detail(admin_client: TestClient, baseline: dict):
    response = admin_client.post(
        "/api/bookings", json=_new(baseline["small"].id, start_time="10:30", cohort_size=20)
    )
    assert response.status_code == 409
    assert "3-124" in response.json()["detail"]
    assert "CSIT213" in response.json()["detail"]


def test_back_to_back_booking_is_allowed(admin_client: TestClient, baseline: dict):
    response = admin_client.post(
        "/api/bookings", json=_new(baseline["small"].id, start_time="11:00", cohort_size=20)
    )
    assert response.status_code == 201


def test_check_reports_capacity_levels(admin_client: TestClient, baseline: dict):
    def levels(lab_id: int, cohort: int) -> dict[str, str]:
        body = admin_client.post(
            "/api/bookings/check", json=_new(lab_id, cohort_size=cohort)
        ).json()
        return {c["title"]: c["level"] for c in body["checks"]}

    assert levels(baseline["big"].id, 36)["Fits room capacity"] == "ok"
    assert levels(baseline["small"].id, 30)["Over capacity"] == "warning"
    assert levels(baseline["small"].id, 28)["At capacity"] == "warning"
    assert levels(baseline["unknown"].id, 10)["Capacity unknown"] == "warning"


def test_check_flags_double_booking_without_saving(
    admin_client: TestClient, db_session: Session, baseline: dict
):
    body = admin_client.post(
        "/api/bookings/check", json=_new(baseline["small"].id, start_time="10:00")
    ).json()
    assert body["can_save"] is False
    assert body["checks"][0]["title"] == "Double-booking"
    assert db_session.query(BaselineScheduleEntry).count() == 1


def test_edit_moves_room_and_resolves_clash(
    admin_client: TestClient, db_session: Session, baseline: dict
):
    clashing = make_entry(
        db_session, baseline["run"], baseline["small"], subject="CSCI203", start=time(10, 30)
    )
    stats = admin_client.get("/api/bookings").json()["stats"]
    assert stats["clashes"] == 2

    response = admin_client.patch(
        f"/api/bookings/{clashing.id}",
        json={"lab_id": baseline["big"].id, "reason": "Resolve Tue clash in 3-124"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lab_code"] == "3-125"
    assert body["history"][0]["changes"]["room"] == ["3-124", "3-125"]
    assert body["history"][0]["reason"] == "Resolve Tue clash in 3-124"
    assert admin_client.get("/api/bookings").json()["stats"]["clashes"] == 0
    occ_labs = {
        o.lab_id
        for o in db_session.query(ScheduleOccurrence).filter_by(baseline_entry_id=clashing.id)
    }
    assert occ_labs == {baseline["big"].id}


def test_edit_into_a_clash_is_rejected(admin_client: TestClient, db_session: Session, baseline: dict):
    other = make_entry(db_session, baseline["run"], baseline["small"], start=time(13, 0))
    response = admin_client.patch(
        f"/api/bookings/{other.id}", json={"start_time": "10:00", "reason": "Move earlier"}
    )
    assert response.status_code == 409


def test_day_change_shifts_each_date(admin_client: TestClient, baseline: dict):
    held = baseline["held"]
    body = admin_client.patch(
        f"/api/bookings/{held.id}", json={"day_of_week": "thu", "reason": "Move to Thursday"}
    ).json()
    assert body["day_of_week"] == "thu"
    assert body["dates"][0] == "2026-03-05"
    assert len(body["dates"]) == 4
    assert body["history"][0]["changes"]["day"] == ["Tue", "Thu"]


def test_edit_requires_reason_and_a_change(admin_client: TestClient, baseline: dict):
    held = baseline["held"]
    assert admin_client.patch(f"/api/bookings/{held.id}", json={"cohort_size": 10}).status_code == 422
    unchanged = admin_client.patch(
        f"/api/bookings/{held.id}", json={"cohort_size": 26, "reason": "No-op"}
    )
    assert unchanged.status_code == 400


def test_cancel_frees_the_room_and_keeps_audit(
    admin_client: TestClient, db_session: Session, baseline: dict
):
    held = baseline["held"]
    response = admin_client.post(f"/api/bookings/{held.id}/cancel", json={"reason": "Subject withdrawn"})
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert db_session.query(ScheduleOccurrence).filter_by(baseline_entry_id=held.id).count() == 0
    assert db_session.query(BookingChange).filter_by(entry_id=held.id, action="cancel").count() == 1

    # The slot is now free.
    assert admin_client.post(
        "/api/bookings", json=_new(baseline["small"].id, start_time="10:00", cohort_size=20)
    ).status_code == 201
    # A cancelled booking can't be edited or cancelled again.
    again = admin_client.post(f"/api/bookings/{held.id}/cancel", json={"reason": "Again"})
    assert again.status_code == 409


def test_list_filters_and_stats(admin_client: TestClient, db_session: Session, baseline: dict):
    make_entry(db_session, baseline["run"], baseline["small"], subject="CSCI235", start=time(14, 0), cohort=30)
    body = admin_client.get("/api/bookings").json()
    assert body["stats"] == {"total": 2, "manual": 0, "clashes": 0, "over_capacity": 1}

    assert admin_client.get("/api/bookings?q=csit213").json()["total"] == 1
    assert admin_client.get("/api/bookings?flag=over_capacity").json()["items"][0]["cohort_size"] == 30
    assert admin_client.get("/api/bookings?day=wed").json()["total"] == 0


def test_staff_can_read_but_not_write(client: TestClient, db_session: Session, baseline: dict):
    from tests.conftest import make_user

    _, token = make_user(db_session, role="staff", email="coord@uow.edu.au")
    client.headers["Authorization"] = f"Bearer {token}"
    assert client.get("/api/bookings").status_code == 200
    assert client.post("/api/bookings", json=_new(baseline["big"].id)).status_code == 403


def test_students_cannot_see_bookings(student_client: TestClient, baseline: dict):
    assert student_client.get("/api/bookings").status_code == 403


def test_export_returns_xlsx(admin_client: TestClient, baseline: dict):
    response = admin_client.get("/api/bookings/export.xlsx")
    assert response.status_code == 200
    assert response.content[:2] == b"PK"

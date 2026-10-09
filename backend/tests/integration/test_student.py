from datetime import date, datetime, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.routes import student as student_routes
from app.db.models.student import ClassSelection
from tests.booking_helpers import make_baseline, make_entry, make_lab, weekly

MON = date(2026, 3, 2)
TUE = date(2026, 3, 3)
THU = date(2026, 3, 5)
# Campus wall-clock time, naive like the stored occurrences.
NOW = datetime(2026, 3, 10, 9, 0)  # noqa: DTZ001 -- a Tuesday morning, mid-period


@pytest.fixture(autouse=True)
def fixed_now(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(student_routes, "_now", lambda: NOW)


@pytest.fixture()
def timetable(db_session: Session) -> dict:
    run = make_baseline(db_session)
    small = make_lab(db_session, "3-124", 28)
    big = make_lab(db_session, "3-127", 48)
    e = {
        "lecture": make_entry(db_session, run, big, name="CSCI235-LEC", class_type="Lecture", dates=weekly(MON, 4), start=time(10, 0), minutes=120, cohort=30),
        "cl01": make_entry(db_session, run, small, name="CSCI235-CL/01", dates=weekly(TUE, 4), start=time(12, 30), cohort=26),
        "cl02": make_entry(db_session, run, small, name="CSCI235-CL/02", dates=weekly(TUE, 4), start=time(13, 30), cohort=28),
        "cl03": make_entry(db_session, run, big, name="CSCI235-CL/03", dates=weekly(THU, 4), start=time(10, 30), cohort=20),
        "tut": make_entry(db_session, run, small, subject="CSIT213", name="CSIT213-TU/01", class_type="Tutorial", dates=weekly(THU, 4), start=time(10, 30), cohort=10),
        # A second teaching period (Spring) for the same subject.
        "spring": make_entry(db_session, run, small, name="CSCI235-CL/S1", dates=weekly(date(2026, 8, 4), 4), start=time(9, 30), cohort=5),
    }
    return e


def _options(client: TestClient, period_id: str | None = None) -> dict:
    url = "/api/student/classes" + (f"?period_id={period_id}" if period_id else "")
    return client.get(url).json()


def _option(body: dict, entry_id: int) -> dict:
    for subject in body["subjects"]:
        for group in subject["groups"]:
            for option in group["options"]:
                if option["entry_id"] == entry_id:
                    return option
    raise AssertionError(f"option {entry_id} not listed")


def test_periods_are_derived_from_dates(student_client: TestClient, timetable: dict):
    periods = student_client.get("/api/periods").json()
    assert [p["id"] for p in periods] == ["2026-03-02", "2026-08-04"]
    assert "CSCI235" in student_client.get("/api/subjects").json()


def test_adding_a_subject_auto_picks_single_option_types(student_client: TestClient, timetable: dict):
    assert student_client.post("/api/student/subjects", json={"subject_code": "csci235"}).status_code == 204
    body = _options(student_client)
    assert body["period"]["id"] == "2026-03-02"
    assert _option(body, timetable["lecture"].id)["selected"] is True
    assert _option(body, timetable["cl01"].id)["selected"] is False
    # The Spring class is in another period, so it isn't offered here.
    all_ids = {o["entry_id"] for s in body["subjects"] for g in s["groups"] for o in g["options"]}
    assert timetable["spring"].id not in all_ids


def test_unknown_subject_is_rejected(student_client: TestClient, timetable: dict):
    assert student_client.post("/api/student/subjects", json={"subject_code": "XXXX999"}).status_code == 404


def test_seats_left_formula_and_full_class(student_client: TestClient, timetable: dict):
    student_client.post("/api/student/subjects", json={"subject_code": "CSCI235"})
    body = _options(student_client)
    # capacity 28 - cohort 26 - 0 picks
    assert _option(body, timetable["cl01"].id)["seats_left"] == 2
    full = _option(body, timetable["cl02"].id)
    assert full["seats_left"] == 0 and full["full"] is True

    response = student_client.put("/api/student/selections", json={"entry_id": timetable["cl02"].id})
    assert response.status_code == 409
    assert "full" in response.json()["detail"]

    assert student_client.put("/api/student/selections", json={"entry_id": timetable["cl01"].id}).status_code == 204
    after = _option(_options(student_client), timetable["cl01"].id)
    assert after["selected"] is True
    assert after["picks"] == 1
    assert after["seats_left"] == 1


def test_repicking_replaces_the_earlier_choice(
    student_client: TestClient, db_session: Session, timetable: dict
):
    student_client.post("/api/student/subjects", json={"subject_code": "CSCI235"})
    student_client.put("/api/student/selections", json={"entry_id": timetable["cl01"].id})
    student_client.put("/api/student/selections", json={"entry_id": timetable["cl03"].id})
    picked = {s.entry_id for s in db_session.query(ClassSelection).all()}
    assert picked == {timetable["lecture"].id, timetable["cl03"].id}


def test_clashing_choice_is_flagged_and_rejected(student_client: TestClient, timetable: dict):
    student_client.post("/api/student/subjects", json={"subject_code": "CSCI235"})
    student_client.put("/api/student/selections", json={"entry_id": timetable["cl03"].id})
    # CSIT213's only tutorial clashes with CL/03, so it isn't auto-picked.
    student_client.post("/api/student/subjects", json={"subject_code": "CSIT213"})
    tutorial = _option(_options(student_client), timetable["tut"].id)
    assert tutorial["selected"] is False
    assert tutorial["clashes_with"] == ["CSCI235-CL/03"]

    response = student_client.put("/api/student/selections", json={"entry_id": timetable["tut"].id})
    assert response.status_code == 409
    assert "CSCI235-CL/03" in response.json()["detail"]


def test_adds_day_hint(student_client: TestClient, timetable: dict):
    student_client.post("/api/student/subjects", json={"subject_code": "CSCI235"})
    body = _options(student_client)
    assert body["on_campus_days"] == ["mon"]
    assert _option(body, timetable["cl01"].id)["adds_day"] is True
    assert _option(body, timetable["cl01"].id)["days_after"] == 2

    # Swapping a pick for one on another day keeps the count the same.
    student_client.put("/api/student/selections", json={"entry_id": timetable["cl01"].id})
    swap = _option(_options(student_client), timetable["cl03"].id)
    assert swap["days_after"] == 2
    assert swap["adds_day"] is False


def test_choosing_requires_the_subject(student_client: TestClient, timetable: dict):
    response = student_client.put("/api/student/selections", json={"entry_id": timetable["cl01"].id})
    assert response.status_code == 400


def test_removing_a_subject_drops_its_choices(
    student_client: TestClient, db_session: Session, timetable: dict
):
    student_client.post("/api/student/subjects", json={"subject_code": "CSCI235"})
    student_client.put("/api/student/selections", json={"entry_id": timetable["cl01"].id})
    assert student_client.delete("/api/student/subjects/CSCI235").status_code == 204
    assert db_session.query(ClassSelection).count() == 0
    assert _options(student_client)["subjects"] == []


def test_timetable_week_and_on_campus_days(student_client: TestClient, timetable: dict):
    student_client.post("/api/student/subjects", json={"subject_code": "CSCI235"})
    student_client.put("/api/student/selections", json={"entry_id": timetable["cl01"].id})

    body = student_client.get("/api/student/timetable").json()
    assert body["week_start"] == "2026-03-09"  # week containing NOW
    assert [e["activity_name"] for e in body["events"]] == ["CSCI235-LEC", "CSCI235-CL/01"]
    assert body["on_campus_days"] == ["mon", "tue"]
    assert body["next_class"]["start"] == "2026-03-10T12:30:00"
    assert len(body["weeks"]) == 4

    empty = student_client.get("/api/student/timetable?week_start=2026-04-20").json()
    assert empty["events"] == [] and empty["on_campus_days"] == []


def test_availability_free_hours_and_free_now(student_client: TestClient, timetable: dict):
    body = student_client.get("/api/rooms/availability?week_start=2026-03-09").json()
    rooms = {r["lab_code"]: r["free_minutes"] for r in body["rooms"]}
    # 08:30-18:30 window = 600 min; the 2 hr Monday lecture is in 3-127.
    assert rooms["3-127"]["mon"] == 480
    # 3-124 on Tuesday: CL/01 12:30-13:30 and CL/02 13:30-14:30 (back to back).
    assert rooms["3-124"]["tue"] == 480
    assert rooms["3-124"]["fri"] == 600

    free_now = {r["lab_code"]: r for r in body["free_now"]}
    assert free_now["3-124"]["free"] is True
    assert free_now["3-124"]["until"] == "2026-03-10T12:30:00"


def test_staff_cannot_use_student_endpoints(admin_client: TestClient, timetable: dict):
    assert admin_client.get("/api/student/classes").status_code == 403
    # Availability is readable by any signed-in user.
    assert admin_client.get("/api/rooms/availability").status_code == 200

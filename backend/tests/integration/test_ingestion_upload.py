from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.lab import Lab

FIXTURES = Path(__file__).parent.parent / "fixtures"

REAL_ROOM_CODES = ["3-124", "3-125", "3-126", "3-127", "3-128", "3-230", "39A-104"]


def _seed_real_rooms(db_session: Session) -> None:
    for code in REAL_ROOM_CODES:
        db_session.add(Lab(code=code, room_type="computing", capacity=None, weekly_available_hours=None))
    db_session.commit()


def test_upload_real_shaped_export_reports_valid_invalid_and_warnings(
    admin_client: TestClient, db_session: Session
):
    _seed_real_rooms(db_session)

    with open(FIXTURES / "sample_upload.xlsx", "rb") as f:
        response = admin_client.post(
            "/api/ingestion/upload",
            files={
                "file": (
                    "sample_upload.xlsx",
                    f,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["total_rows"] == 8
    assert body["valid_rows"] == 5
    assert body["invalid_rows"] == 3
    assert body["rows_with_warnings"] == 3

    error_types = {(e["error_type"], e["severity"]) for e in body["errors"]}
    assert ("invalid_room_code", "error") in error_types
    assert ("malformed_duration", "error") in error_types
    assert ("malformed_date", "error") in error_types
    assert ("zero_cohort_size", "warning") in error_types
    assert ("duration_end_time_mismatch", "warning") in error_types
    assert ("date_count_mismatch", "warning") in error_types


def test_joint_subject_row_stores_both_subject_codes(admin_client: TestClient, db_session: Session):
    _seed_real_rooms(db_session)
    with open(FIXTURES / "sample_upload.xlsx", "rb") as f:
        admin_client.post("/api/ingestion/upload", files={"file": ("sample_upload.xlsx", f)})

    from app.db.models.baseline import BaselineScheduleEntry

    entry = (
        db_session.query(BaselineScheduleEntry)
        .filter(BaselineScheduleEntry.activity_name == "AUTM-CSCI410-WG-OC-LC/01")
        .one()
    )
    assert entry.subject_codes == ["CSCI410", "CSCI910"]


def test_occurrences_use_start_plus_duration_not_raw_end_time(
    admin_client: TestClient, db_session: Session
):
    _seed_real_rooms(db_session)
    with open(FIXTURES / "sample_upload.xlsx", "rb") as f:
        admin_client.post("/api/ingestion/upload", files={"file": ("sample_upload.xlsx", f)})

    from app.db.models.baseline import BaselineScheduleEntry

    entry = (
        db_session.query(BaselineScheduleEntry)
        .filter(BaselineScheduleEntry.activity_name == "AUTM-CSIT375-WG-OC-CL/01")
        .one()
    )
    occurrence = entry.occurrences[0]
    # Raw end time in the fixture says 11:00 AM, but start (9:00 AM) + duration
    # (1h) = 10:00 AM should win, and every occurrence's week_number is null.
    assert occurrence.end_datetime.time().strftime("%H:%M") == "10:00"
    assert occurrence.week_number is None


def test_get_summary_after_upload(admin_client: TestClient, db_session: Session):
    _seed_real_rooms(db_session)
    with open(FIXTURES / "sample_upload.xlsx", "rb") as f:
        upload_response = admin_client.post(
            "/api/ingestion/upload", files={"file": ("sample_upload.xlsx", f)}
        )
    run_id = upload_response.json()["id"]

    summary_response = admin_client.get(f"/api/ingestion/{run_id}/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["id"] == run_id


def test_missing_required_column_fails_whole_file(admin_client: TestClient, db_session: Session):
    _seed_real_rooms(db_session)
    with open(FIXTURES / "missing_room_column.xlsx", "rb") as f:
        response = admin_client.post(
            "/api/ingestion/upload", files={"file": ("missing_room_column.xlsx", f)}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert len(body["errors"]) == 1
    assert "room_code" in body["errors"][0]["field"]

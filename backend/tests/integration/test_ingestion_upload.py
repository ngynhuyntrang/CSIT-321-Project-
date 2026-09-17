from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.lab import Lab

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _seed_labs(db_session: Session) -> None:
    for code, capacity in [("3.G17", 48), ("3.G18", 25), ("6.101", 48), ("6.102", 25)]:
        db_session.add(Lab(code=code, capacity=capacity, room_type="computing"))
    db_session.commit()


def test_upload_sample_export_reports_valid_and_invalid_rows(
    client: TestClient, db_session: Session
):
    _seed_labs(db_session)

    with open(FIXTURES / "sample_upload.xlsx", "rb") as f:
        response = client.post(
            "/api/ingestion/upload",
            files={
                "file": (
                    "semester_export_sample.xlsx",
                    f,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["total_rows"] == 50
    assert body["valid_rows"] == 47
    assert body["invalid_rows"] == 3

    error_types = {e["error_type"] for e in body["errors"]}
    assert {"missing_value", "invalid_room_code", "malformed_time_block"} <= error_types


def test_get_summary_after_upload(client: TestClient, db_session: Session):
    _seed_labs(db_session)
    with open(FIXTURES / "sample_upload.xlsx", "rb") as f:
        upload_response = client.post(
            "/api/ingestion/upload", files={"file": ("sample.xlsx", f)}
        )
    run_id = upload_response.json()["id"]

    summary_response = client.get(f"/api/ingestion/{run_id}/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["id"] == run_id


def test_missing_required_column_fails_whole_file(client: TestClient, db_session: Session):
    _seed_labs(db_session)
    with open(FIXTURES / "missing_room_column.xlsx", "rb") as f:
        response = client.post(
            "/api/ingestion/upload", files={"file": ("missing_room_column.xlsx", f)}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert len(body["errors"]) == 1
    assert "room_code" in body["errors"][0]["field"]

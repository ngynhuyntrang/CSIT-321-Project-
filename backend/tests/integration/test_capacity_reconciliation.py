import io

import pandas as pd
from sqlalchemy.orm import Session

from app.db.models.lab import Lab
from app.ingestion.service import run_ingestion
from app.ingestion.validators import CAPACITY_MISMATCH, WARNING

ROOM = "3-125"


def _row(**overrides: object) -> dict:
    base = {
        "Activity Type Name": "Computer Lab",
        "Module Name": "AUTM-CSIT121-WG-OC",
        "Name": "AUTM-CSIT121-WG-OC-CL/01",
        "Size": "20",
        "Duration": "01:00",
        "Scheduled Days": "Monday",
        "Scheduled Start Time": "9:00 AM",
        "Scheduled End Time": "10:00 AM",
        "Allocated Location Name": ROOM,
        "Capicity": "40",
        "Number Of Teaching Weeks": "1",
        "Teaching Week Pattern": "1",
        "Activity Dates (Individual)": "2/03/2026",
    }
    base.update(overrides)
    return base


def _xlsx_bytes(rows: list[dict]) -> bytes:
    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False)
    return buffer.getvalue()


def _seed_room(db_session: Session) -> None:
    db_session.add(Lab(code=ROOM, room_type="computing", capacity=None, weekly_available_hours=None))
    db_session.commit()


def test_first_row_sets_lab_capacity_from_export(db_session: Session):
    _seed_room(db_session)
    content = _xlsx_bytes([_row(), _row()])

    run_ingestion(db_session, "upload.xlsx", content)

    lab = db_session.query(Lab).filter(Lab.code == ROOM).one()
    assert lab.capacity == 40


def test_conflicting_capacity_is_flagged_and_first_value_is_kept(db_session: Session):
    _seed_room(db_session)
    content = _xlsx_bytes([_row(Capicity="40"), _row(Capicity="99")])

    run = run_ingestion(db_session, "upload.xlsx", content)

    lab = db_session.query(Lab).filter(Lab.code == ROOM).one()
    assert lab.capacity == 40
    assert run.rows_with_warnings == 1
    mismatch_errors = [e for e in run.errors if e.error_type == CAPACITY_MISMATCH]
    assert len(mismatch_errors) == 1
    assert mismatch_errors[0].severity == WARNING
    assert mismatch_errors[0].row_number == 3


def test_missing_capacity_cell_does_not_touch_lab_capacity(db_session: Session):
    _seed_room(db_session)
    content = _xlsx_bytes([_row(Capicity="")])

    run_ingestion(db_session, "upload.xlsx", content)

    lab = db_session.query(Lab).filter(Lab.code == ROOM).one()
    assert lab.capacity is None

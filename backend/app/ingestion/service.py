from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.baseline import BaselineScheduleEntry, ScheduleOccurrence
from app.db.models.ingestion import IngestionError, IngestionRun
from app.db.models.lab import Lab
from app.ingestion.occurrence_expander import expand_occurrences
from app.ingestion.parser import UnsupportedFileTypeError, parse_upload
from app.ingestion.validators import MISSING_VALUE, validate_rows


def run_ingestion(db: Session, filename: str, content: bytes) -> IngestionRun:
    ingestion_run = IngestionRun(filename=filename, status="processing")
    db.add(ingestion_run)
    db.flush()

    try:
        df, missing_required_fields = parse_upload(filename, content)
    except UnsupportedFileTypeError as exc:
        ingestion_run.status = "failed"
        ingestion_run.total_rows = 0
        db.add(
            IngestionError(
                ingestion_run_id=ingestion_run.id,
                row_number=0,
                field="file",
                error_type="unsupported_file_type",
                raw_value=filename,
                message=str(exc),
            )
        )
        db.commit()
        db.refresh(ingestion_run)
        return ingestion_run

    if missing_required_fields:
        ingestion_run.status = "failed"
        ingestion_run.total_rows = len(df)
        db.add(
            IngestionError(
                ingestion_run_id=ingestion_run.id,
                row_number=0,
                field=", ".join(missing_required_fields),
                error_type=MISSING_VALUE,
                raw_value=None,
                message=(
                    "File is missing required column(s): "
                    f"{', '.join(missing_required_fields)}. Check the export's headers."
                ),
            )
        )
        db.commit()
        db.refresh(ingestion_run)
        return ingestion_run

    labs = {lab.code: lab for lab in db.query(Lab).filter(Lab.active.is_(True)).all()}
    known_room_codes = set(labs.keys())

    results = validate_rows(df, known_room_codes)

    ingestion_run.total_rows = len(results)
    ingestion_run.valid_rows = sum(1 for r in results if r.is_valid)
    ingestion_run.invalid_rows = sum(1 for r in results if not r.is_valid)

    semester_week1_monday = get_settings().semester_week1_monday

    for result in results:
        if not result.is_valid:
            for err in result.errors:
                db.add(
                    IngestionError(
                        ingestion_run_id=ingestion_run.id,
                        row_number=err.row_number,
                        field=err.field,
                        error_type=err.error_type,
                        raw_value=err.raw_value,
                        message=err.message,
                    )
                )
            continue

        cleaned = result.cleaned
        assert cleaned is not None
        lab = labs[cleaned.room_code]

        entry = BaselineScheduleEntry(
            ingestion_run_id=ingestion_run.id,
            subject_code=cleaned.subject_code,
            class_type=cleaned.class_type,
            lab_id=lab.id,
            day_of_week=cleaned.day_of_week,
            start_time=cleaned.start_time,
            duration_minutes=cleaned.duration_minutes,
            delivery_weeks=cleaned.delivery_weeks,
            session_frequency=cleaned.session_frequency,
            cohort_size=cleaned.cohort_size,
        )
        db.add(entry)
        db.flush()

        for occ in expand_occurrences(
            lab_id=lab.id,
            day_of_week=cleaned.day_of_week,
            start_time=cleaned.start_time,
            duration_minutes=cleaned.duration_minutes,
            delivery_weeks=cleaned.delivery_weeks,
            semester_week1_monday=semester_week1_monday,
        ):
            db.add(
                ScheduleOccurrence(
                    baseline_entry_id=entry.id,
                    lab_id=occ.lab_id,
                    week_number=occ.week_number,
                    start_datetime=occ.start_datetime,
                    end_datetime=occ.end_datetime,
                )
            )

    ingestion_run.status = "completed"
    db.commit()
    db.refresh(ingestion_run)
    return ingestion_run

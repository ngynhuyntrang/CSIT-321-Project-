from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.baseline import BaselineScheduleEntry, ScheduleOccurrence
from app.db.models.ingestion import IngestionError, IngestionRun
from app.db.models.lab import Lab
from app.ingestion.occurrence_expander import expand_occurrences
from app.ingestion.parser import UnsupportedFileTypeError, parse_upload
from app.ingestion.validators import CAPACITY_MISMATCH, ERROR, WARNING, RowError, validate_rows


def _record_file_level_error(
    db: Session, ingestion_run: IngestionRun, field: str, error_type: str, message: str
) -> None:
    ingestion_run.status = "failed"
    db.add(
        IngestionError(
            ingestion_run_id=ingestion_run.id,
            row_number=0,
            field=field,
            error_type=error_type,
            severity=ERROR,
            raw_value=None,
            message=message,
        )
    )
    db.commit()
    db.refresh(ingestion_run)


def run_ingestion(db: Session, filename: str, content: bytes) -> IngestionRun:
    ingestion_run = IngestionRun(filename=filename, status="processing")
    db.add(ingestion_run)
    db.flush()

    try:
        df, missing_required_fields = parse_upload(filename, content)
    except UnsupportedFileTypeError as exc:
        ingestion_run.total_rows = 0
        _record_file_level_error(db, ingestion_run, "file", "unsupported_file_type", str(exc))
        return ingestion_run

    if missing_required_fields:
        ingestion_run.total_rows = len(df)
        _record_file_level_error(
            db,
            ingestion_run,
            ", ".join(missing_required_fields),
            "missing_value",
            "File is missing required column(s): "
            f"{', '.join(missing_required_fields)}. Check the export's headers.",
        )
        return ingestion_run

    labs = {lab.code: lab for lab in db.query(Lab).filter(Lab.active.is_(True)).all()}
    known_room_codes = set(labs.keys())

    results = validate_rows(df, known_room_codes)

    # Reconcile each row's room_capacity against Lab.capacity before the
    # summary counts below are computed, so a conflicting row is reflected
    # in rows_with_warnings. First value wins for a room; later conflicting
    # rows are flagged rather than silently overwriting it (see
    # docs/architecture.md -- unknown/conflicting numbers are never guessed).
    for result in results:
        if not result.is_valid:
            continue
        cleaned = result.cleaned
        assert cleaned is not None
        if cleaned.room_capacity is None:
            continue
        lab = labs[cleaned.room_code]
        if lab.capacity is None:
            lab.capacity = cleaned.room_capacity
        elif lab.capacity != cleaned.room_capacity:
            result.errors.append(
                RowError(
                    row_number=result.row_number,
                    field="room_capacity",
                    error_type=CAPACITY_MISMATCH,
                    severity=WARNING,
                    raw_value=str(cleaned.room_capacity),
                    message=(
                        f"Row reports capacity {cleaned.room_capacity} for room "
                        f"'{cleaned.room_code}', but it is already recorded with "
                        f"capacity {lab.capacity}. Keeping the existing value."
                    ),
                )
            )

    ingestion_run.total_rows = len(results)
    ingestion_run.valid_rows = sum(1 for r in results if r.is_valid)
    ingestion_run.invalid_rows = sum(1 for r in results if not r.is_valid)
    ingestion_run.rows_with_warnings = sum(
        1 for r in results if r.is_valid and any(e.severity == WARNING for e in r.errors)
    )

    for result in results:
        for err in result.errors:
            db.add(
                IngestionError(
                    ingestion_run_id=ingestion_run.id,
                    row_number=err.row_number,
                    field=err.field,
                    error_type=err.error_type,
                    severity=err.severity,
                    raw_value=err.raw_value,
                    message=err.message,
                )
            )

        if not result.is_valid:
            continue

        cleaned = result.cleaned
        assert cleaned is not None
        lab = labs[cleaned.room_code]

        entry = BaselineScheduleEntry(
            ingestion_run_id=ingestion_run.id,
            activity_name=cleaned.activity_name,
            subject_codes=cleaned.subject_codes,
            class_type=cleaned.class_type,
            lab_id=lab.id,
            day_of_week=cleaned.day_of_week,
            start_time=cleaned.start_time,
            duration_minutes=cleaned.duration_minutes,
            cohort_size=cleaned.cohort_size,
            week_pattern_raw=cleaned.week_pattern_raw,
            teaching_weeks_count=cleaned.teaching_weeks_count,
        )
        db.add(entry)
        db.flush()

        for occ in expand_occurrences(
            lab_id=lab.id,
            dates=cleaned.dates,
            start_time=cleaned.start_time,
            duration_minutes=cleaned.duration_minutes,
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

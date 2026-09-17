from datetime import date

import pandas as pd
import pytest

from app.ingestion.validators import (
    DATE_COUNT_MISMATCH,
    DURATION_END_TIME_MISMATCH,
    ERROR,
    INVALID_ROOM_CODE,
    MALFORMED_DATE,
    MALFORMED_DURATION,
    WARNING,
    ZERO_COHORT_SIZE,
    parse_activity_dates,
    validate_row,
)

KNOWN_ROOMS = {"3-125"}


def _row(**overrides: object) -> pd.Series:
    base = {
        "class_type": "Computer Lab",
        "module_name_raw": "AUTM-CSIT121-WG-OC",
        "cohort_size": "20",
        "duration_raw": "01:00",
        "day_of_week": "Monday",
        "start_time_raw": "9:00 AM",
        "end_time_raw": "10:00 AM",
        "room_code": "3-125",
        "activity_dates_raw": "2/03/2026,9/03/2026",
        "teaching_weeks_count_raw": "2",
        "week_pattern_raw": "1,2",
        "activity_name": "AUTM-CSIT121-WG-OC-CL/01",
    }
    base.update(overrides)
    return pd.Series(base)


def test_valid_row_has_no_errors():
    result = validate_row(2, _row(), KNOWN_ROOMS)
    assert result.is_valid
    assert result.errors == []
    assert result.cleaned.subject_codes == ["CSIT121"]
    assert result.cleaned.duration_minutes == 60


def test_unrecognized_room_code_is_blocking_error():
    result = validate_row(2, _row(room_code="9-999"), KNOWN_ROOMS)
    assert not result.is_valid
    assert any(e.error_type == INVALID_ROOM_CODE and e.severity == ERROR for e in result.errors)


def test_malformed_duration_is_blocking_error():
    result = validate_row(2, _row(duration_raw="abc"), KNOWN_ROOMS)
    assert not result.is_valid
    assert any(e.error_type == MALFORMED_DURATION and e.severity == ERROR for e in result.errors)


def test_malformed_activity_dates_is_blocking_error():
    result = validate_row(2, _row(activity_dates_raw="not-a-date"), KNOWN_ROOMS)
    assert not result.is_valid
    assert any(e.error_type == MALFORMED_DATE and e.severity == ERROR for e in result.errors)


def test_zero_cohort_size_is_valid_with_warning():
    result = validate_row(2, _row(cohort_size="0"), KNOWN_ROOMS)
    assert result.is_valid
    assert result.cleaned.cohort_size == 0
    assert any(e.error_type == ZERO_COHORT_SIZE and e.severity == WARNING for e in result.errors)


def test_negative_cohort_size_is_blocking_error():
    result = validate_row(2, _row(cohort_size="-1"), KNOWN_ROOMS)
    assert not result.is_valid


def test_start_end_duration_mismatch_is_warning_and_uses_start_plus_duration():
    # 9:00 AM + 1h should be 10:00 AM, not 11:00 AM.
    result = validate_row(2, _row(end_time_raw="11:00 AM"), KNOWN_ROOMS)
    assert result.is_valid
    assert any(
        e.error_type == DURATION_END_TIME_MISMATCH and e.severity == WARNING
        for e in result.errors
    )


def test_date_count_vs_teaching_weeks_mismatch_is_warning_not_blocking():
    result = validate_row(
        2,
        _row(activity_dates_raw="2/03/2026,9/03/2026,16/03/2026", teaching_weeks_count_raw="5"),
        KNOWN_ROOMS,
    )
    assert result.is_valid
    assert any(
        e.error_type == DATE_COUNT_MISMATCH and e.severity == WARNING for e in result.errors
    )


def test_joint_subject_module_name_extracts_both_codes():
    result = validate_row(
        2, _row(module_name_raw="AUTM-CSCI410-WG-OC, AUTM-CSCI910-WG-OC"), KNOWN_ROOMS
    )
    assert result.is_valid
    assert result.cleaned.subject_codes == ["CSCI410", "CSCI910"]


def test_missing_required_field_blocks_further_checks():
    result = validate_row(2, _row(room_code=None), KNOWN_ROOMS)
    assert not result.is_valid
    # Only the missing-field error should be reported, not room-code errors too.
    assert len(result.errors) == 1


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("17/03/2026", [date(2026, 3, 17)]),
        ("7/04/2026,14/04/2026", [date(2026, 4, 7), date(2026, 4, 14)]),
        ("", None),
        ("not-a-date", None),
    ],
)
def test_parse_activity_dates(raw, expected):
    assert parse_activity_dates(raw) == expected

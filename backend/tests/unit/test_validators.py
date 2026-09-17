import pandas as pd

from app.ingestion.validators import (
    INVALID_ROOM_CODE,
    MALFORMED_TIME_BLOCK,
    MISSING_VALUE,
    parse_week_range,
    validate_row,
)

KNOWN_ROOMS = {"3.G17", "6.101"}


def _row(**overrides) -> pd.Series:
    base = {
        "subject_code": "CSIT121",
        "class_type": "Lab",
        "room_code": "3.G17",
        "day_of_week": "Mon",
        "start_time": "09:00",
        "duration_minutes": "120",
        "delivery_weeks": "1-5,7-12",
        "session_frequency": "weekly",
        "cohort_size": "24",
    }
    base.update(overrides)
    return pd.Series(base)


def test_valid_row_passes():
    result = validate_row(2, _row(), KNOWN_ROOMS)
    assert result.is_valid
    assert result.cleaned is not None
    assert result.cleaned.room_code == "3.G17"
    assert result.cleaned.delivery_weeks == [1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12]


def test_missing_value_flagged():
    result = validate_row(3, _row(cohort_size=None), KNOWN_ROOMS)
    assert not result.is_valid
    assert any(e.error_type == MISSING_VALUE and e.field == "cohort_size" for e in result.errors)


def test_unrecognized_room_code_flagged():
    result = validate_row(4, _row(room_code="9.ZZZ"), KNOWN_ROOMS)
    assert not result.is_valid
    assert any(e.error_type == INVALID_ROOM_CODE for e in result.errors)


def test_malformed_time_block_flagged():
    result = validate_row(
        5, _row(start_time="not-a-time", duration_minutes="-30", delivery_weeks="abc"), KNOWN_ROOMS
    )
    assert not result.is_valid
    error_fields = {e.field for e in result.errors}
    assert {"start_time", "duration_minutes", "delivery_weeks"} <= error_fields
    assert all(e.error_type == MALFORMED_TIME_BLOCK for e in result.errors)


def test_parse_week_range_valid():
    assert parse_week_range("1-3,5,9-10") == [1, 2, 3, 5, 9, 10]


def test_parse_week_range_invalid():
    assert parse_week_range("abc") is None
    assert parse_week_range("5-3") is None
    assert parse_week_range("") is None
    assert parse_week_range("0-3") is None

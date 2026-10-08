"""Maps UOW Enterprise export column headers to canonical field names.

Column names/order can vary slightly between export runs, so aliases are kept
as data (not hardcoded column positions). `subject_code` is deliberately not
one of these fields -- the real export doesn't have a subject-code column, it
embeds one or more subject codes inside `module_name_raw` (e.g.
"AUTM-CSCI235-WG-OC", or a comma-separated pair for jointly-taught subjects),
which `app.ingestion.parser.parse_module_name` extracts.
"""

from __future__ import annotations

import re

import pandas as pd

CANONICAL_FIELDS = [
    "class_type",
    "module_name_raw",
    "activity_name",
    "cohort_size",
    "duration_raw",
    "day_of_week",
    "start_time_raw",
    "end_time_raw",
    "room_code",
    "room_capacity_raw",
    "teaching_weeks_count_raw",
    "week_pattern_raw",
    "activity_dates_raw",
]

# teaching_weeks_count_raw / week_pattern_raw / room_capacity_raw are
# cross-check-only fields (see validators.py) and activity_name is
# descriptive -- none are required to ingest a row.
REQUIRED_FIELDS = [
    "class_type",
    "module_name_raw",
    "cohort_size",
    "duration_raw",
    "day_of_week",
    "start_time_raw",
    "end_time_raw",
    "room_code",
    "activity_dates_raw",
]

_ALIASES: dict[str, list[str]] = {
    "class_type": ["activity type name", "activity type", "class type", "session type"],
    "module_name_raw": ["module name", "module"],
    "activity_name": ["name", "activity name"],
    "cohort_size": ["size", "cohort size", "class size", "enrolments", "enrollment"],
    "duration_raw": ["duration", "class duration"],
    "day_of_week": ["scheduled days", "day", "day of week", "weekday"],
    "start_time_raw": ["scheduled start time", "start time"],
    "end_time_raw": ["scheduled end time", "end time"],
    "room_code": ["allocated location name", "room number", "room code", "location", "venue"],
    # "capicity" is a misspelling in the real export (docs/SCIT 2026 Lab
    # Bookings.xlsx) -- kept as an alias rather than fixed upstream, since we
    # don't control the Enterprise export.
    "room_capacity_raw": ["capicity", "capacity", "room capacity"],
    "teaching_weeks_count_raw": ["number of teaching weeks", "teaching weeks"],
    "week_pattern_raw": ["teaching week pattern", "week pattern"],
    "activity_dates_raw": [
        "activity dates individual",
        "activity dates",
        "scheduled dates",
    ],
}


def _normalize(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(header).strip().lower()).strip()


def build_rename_map(columns: list[str]) -> dict[str, str]:
    """Returns {original_column_name: canonical_field_name} for recognized columns."""
    normalized_aliases = {
        canonical: {_normalize(alias) for alias in [canonical, *aliases]}
        for canonical, aliases in _ALIASES.items()
    }

    rename_map: dict[str, str] = {}
    for column in columns:
        normalized = _normalize(column)
        for canonical, aliases in normalized_aliases.items():
            if normalized in aliases:
                rename_map[column] = canonical
                break
    return rename_map


def map_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Renames recognized columns to canonical names.

    Returns (renamed_df, missing_required_fields). Unrecognized columns are
    left untouched (and simply ignored downstream) rather than dropped, so
    the caller can still see what was in the original file.
    """
    rename_map = build_rename_map(list(df.columns))
    renamed = df.rename(columns=rename_map)
    missing = [field for field in REQUIRED_FIELDS if field not in renamed.columns]
    return renamed, missing

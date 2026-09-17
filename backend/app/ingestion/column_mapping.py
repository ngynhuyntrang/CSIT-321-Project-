"""Maps flexible Enterprise export column headers to canonical field names.

Real UOW Enterprise exports may use different header spellings than our fixtures
(e.g. "Room" vs "Room Code" vs "Location"). Keep aliases here as data, not as
hardcoded column positions, so this can be extended once real export files
are available.
"""

from __future__ import annotations

import re

import pandas as pd

CANONICAL_FIELDS = [
    "subject_code",
    "class_type",
    "room_code",
    "day_of_week",
    "start_time",
    "duration_minutes",
    "delivery_weeks",
    "session_frequency",
    "cohort_size",
]

REQUIRED_FIELDS = [
    "subject_code",
    "room_code",
    "day_of_week",
    "start_time",
    "duration_minutes",
    "delivery_weeks",
    "cohort_size",
]

_ALIASES: dict[str, list[str]] = {
    "subject_code": ["subject code", "subject", "unit code", "unitcode"],
    "class_type": ["class type", "activity type", "session type", "type"],
    "room_code": ["room number", "room code", "room", "location", "venue"],
    "day_of_week": ["day", "day of week", "weekday"],
    "start_time": ["start time", "starttime", "time"],
    "duration_minutes": [
        "duration",
        "duration (mins)",
        "duration minutes",
        "class duration",
        "length (mins)",
    ],
    "delivery_weeks": ["delivery weeks", "weeks", "teaching weeks", "week pattern"],
    "session_frequency": ["frequency", "session frequency", "recurrence"],
    "cohort_size": ["cohort size", "class size", "enrolments", "enrollment", "students"],
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

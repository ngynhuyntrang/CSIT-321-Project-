import pandas as pd

from app.ingestion.column_mapping import map_columns

REAL_HEADERS = [
    "Activity Type Name",
    "Module Name",
    "Name",
    "Size",
    "Duration",
    "Scheduled Days",
    "Scheduled Start Time",
    "Scheduled End Time",
    "Allocated Location Name",
    "Number Of Teaching Weeks",
    "Teaching Week Pattern",
    "Activity Dates (Individual)",
]


def test_real_enterprise_headers_map_to_all_required_fields():
    df = pd.DataFrame([["x"] * len(REAL_HEADERS)], columns=REAL_HEADERS)
    renamed, missing = map_columns(df)
    assert missing == []
    assert "room_code" in renamed.columns
    assert "activity_dates_raw" in renamed.columns
    assert "class_type" in renamed.columns


def test_missing_location_column_is_reported():
    headers = [h for h in REAL_HEADERS if h != "Allocated Location Name"]
    df = pd.DataFrame([["x"] * len(headers)], columns=headers)
    _, missing = map_columns(df)
    assert missing == ["room_code"]

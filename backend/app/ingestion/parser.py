from __future__ import annotations

import io
import re

import pandas as pd

from app.ingestion.column_mapping import map_columns

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}

_SUBJECT_CODE_RE = re.compile(r"[A-Z]{3,5}\d{3,4}")


class UnsupportedFileTypeError(ValueError):
    pass


def read_upload(filename: str, content: bytes) -> pd.DataFrame:
    """Reads an uploaded Enterprise export into a raw (un-mapped) DataFrame."""
    lower = filename.lower()
    buffer = io.BytesIO(content)
    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(buffer, dtype=str)
    if lower.endswith(".csv"):
        return pd.read_csv(buffer, dtype=str)
    raise UnsupportedFileTypeError(f"Unsupported file type: {filename}")


def parse_upload(filename: str, content: bytes) -> tuple[pd.DataFrame, list[str]]:
    """Reads and column-maps an upload.

    Returns (canonical_df, missing_required_fields). Row indices in the
    returned DataFrame are 0-based pandas positions; add 2 to get the
    1-based spreadsheet row number (row 1 is the header).
    """
    raw_df = read_upload(filename, content)
    return map_columns(raw_df)


def to_row_number(pandas_index: int) -> int:
    """Converts a 0-based pandas row index to a 1-based spreadsheet row number."""
    return pandas_index + 2


def parse_module_name(raw: str) -> list[str]:
    """Extracts subject code(s) out of a Module Name like "AUTM-CSCI235-WG-OC",
    or a comma-separated pair for jointly-taught undergrad/postgrad offerings
    like "AUTM-CSCI410-WG-OC, AUTM-CSCI910-WG-OC".

    Returns codes in the order found; empty if none matched.
    """
    codes: list[str] = []
    for part in raw.split(","):
        for token in part.strip().split("-"):
            if _SUBJECT_CODE_RE.fullmatch(token.strip()):
                codes.append(token.strip())
    return codes

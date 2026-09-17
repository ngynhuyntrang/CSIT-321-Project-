from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IngestionErrorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row_number: int
    field: str
    error_type: str
    raw_value: str | None
    message: str


class IngestionRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    uploaded_at: datetime
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[IngestionErrorOut] = []

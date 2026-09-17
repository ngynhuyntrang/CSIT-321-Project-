from pydantic import BaseModel, ConfigDict


class LabCreate(BaseModel):
    code: str
    building: str | None = None
    capacity: int | None = None
    room_type: str | None = None
    weekly_available_hours: float | None = None


class LabOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    building: str | None
    capacity: int | None
    room_type: str | None
    weekly_available_hours: float | None
    active: bool

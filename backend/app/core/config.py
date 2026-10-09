from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SCIT_")

    env: str = "dev"
    database_url: str = "sqlite:///./scit_lab_scheduling.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    # Display window for the student "Lab Availability" page only. This is NOT
    # "Available Lab Hours" for utilisation (still unconfirmed with SCIT Ops,
    # see docs/architecture.md).
    student_day_start: str = "08:30"
    student_day_end: str = "18:30"
    # Occurrence times in the export are campus wall-clock times (naive).
    campus_timezone: str = "Australia/Sydney"


@lru_cache
def get_settings() -> Settings:
    return Settings()

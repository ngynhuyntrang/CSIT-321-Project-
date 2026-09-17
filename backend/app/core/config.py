from datetime import date
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SCIT_")

    env: str = "dev"
    database_url: str = "sqlite:///./scit_lab_scheduling.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    # Monday of teaching week 1 for the semester currently being ingested.
    # TODO: move to a per-ingestion-run field once multiple semesters are supported.
    semester_week1_monday: date = date(2026, 7, 20)


@lru_cache
def get_settings() -> Settings:
    return Settings()

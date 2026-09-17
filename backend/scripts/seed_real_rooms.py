"""Seeds the 7 room codes found in the real SCIT Enterprise export
(docs/SCIT 2026 Lab Bookings.xlsx) so ingestion can recognize them.

The export carries no room capacity or operating-hours data, so `capacity`
and `weekly_available_hours` are left null (unknown) rather than guessed or
defaulted to 0/48/25 -- those numbers must come from Ridwan Haq (SCIT
Operations) before any capacity- or utilisation-percentage calculation can
use them. Room type is set to "computing" since every one of these rooms
hosts at least one "Computer Lab" booking in the export.

Usage: `python -m scripts.seed_real_rooms` (from `backend/`, with the venv
active and `SCIT_DATABASE_URL` pointed at the target database).
"""

from __future__ import annotations

from app.db.base import Base
from app.db.models.lab import Lab
from app.db.session import SessionLocal, engine

REAL_ROOM_CODES = ["3-124", "3-125", "3-126", "3-127", "3-128", "3-230", "39A-104"]


def seed_real_rooms() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        existing = {code for (code,) in db.query(Lab.code).all()}
        added = 0
        for code in REAL_ROOM_CODES:
            if code in existing:
                continue
            db.add(Lab(code=code, room_type="computing", capacity=None, weekly_available_hours=None))
            added += 1
        db.commit()
        print(f"Seeded {added} new room(s); {len(existing)} already present.")


if __name__ == "__main__":
    seed_real_rooms()

"""Creates (or promotes) the first SCIT Operations admin account.

Sign-up only creates student or pending-staff accounts, so the first admin
has to be bootstrapped here; after that, admins approve staff in the app.

Usage: `python -m scripts.create_admin <email> "<full name>"` (from
`backend/`, with the venv active). The password is prompted for, not passed
on the command line, so it doesn't end up in shell history.
"""

from __future__ import annotations

import getpass
import sys

from app.core.security import hash_password
from app.db.base import Base
from app.db.models.user import ROLE_ADMIN, STATUS_ACTIVE, User
from app.db.session import SessionLocal, engine
from app.schemas.auth import SignupRequest


def create_admin(email: str, full_name: str, password: str) -> None:
    # Reuse sign-up validation for the email domain and password rules.
    payload = SignupRequest(email=email, full_name=full_name, role="staff", password=password)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == payload.email).first()
        if user is None:
            user = User(email=payload.email, full_name=payload.full_name)
            db.add(user)
            action = "Created"
        else:
            action = "Promoted"
        user.role = ROLE_ADMIN
        user.status = STATUS_ACTIVE
        user.password_hash = hash_password(payload.password)
        db.commit()
        print(f"{action} admin {payload.email}.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit('Usage: python -m scripts.create_admin <email> "<full name>"')
    pw = getpass.getpass("Password: ")
    if pw != getpass.getpass("Confirm password: "):
        sys.exit("Passwords don't match.")
    create_admin(sys.argv[1], sys.argv[2], pw)

from datetime import datetime, time

from sqlalchemy.orm import Session

from app.bookings.clashes import (
    all_clashing_entry_ids,
    cohort_overlaps,
    find_clashes,
    overlaps,
)
from app.db.models.ingestion import IngestionRun
from tests.booking_helpers import TUE, make_baseline, make_entry, make_lab


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(TUE, time(hour, minute))


def test_back_to_back_is_not_overlap():
    assert not overlaps((_at(9), _at(10)), (_at(10), _at(11)))
    assert overlaps((_at(9), _at(10, 30)), (_at(10), _at(11)))


def test_find_clashes_same_room_only(db_session: Session):
    run = make_baseline(db_session)
    a, b = make_lab(db_session, "3-124", 28), make_lab(db_session, "3-125", 40)
    existing = make_entry(db_session, run, a, start=time(10, 0))
    make_entry(db_session, run, b, start=time(10, 0))

    clashes = find_clashes(db_session, a.id, [(_at(10, 30), _at(11, 30))])
    assert {c.entry_id for c in clashes} == {existing.id}
    assert find_clashes(db_session, a.id, [(_at(11), _at(12))]) == []
    # Excluding the booking itself (an edit) clears the clash.
    assert find_clashes(db_session, a.id, [(_at(10), _at(11))], exclude_entry_id=existing.id) == []


def test_inactive_baseline_and_cancelled_entries_are_ignored(db_session: Session):
    old_run = IngestionRun(filename="old.xlsx", status="completed", is_active_baseline=False)
    db_session.add(old_run)
    db_session.flush()
    lab = make_lab(db_session, "3-124", 28)
    make_entry(db_session, old_run, lab)
    run = make_baseline(db_session)
    cancelled = make_entry(db_session, run, lab)
    cancelled.status = "cancelled"
    db_session.commit()

    assert find_clashes(db_session, lab.id, [(_at(10), _at(11))]) == []


def test_all_clashing_entry_ids_sweep(db_session: Session):
    run = make_baseline(db_session)
    lab = make_lab(db_session, "3-124", 28)
    a = make_entry(db_session, run, lab, start=time(10, 0), minutes=60)
    b = make_entry(db_session, run, lab, start=time(10, 30), minutes=120)
    c = make_entry(db_session, run, lab, start=time(12, 0), minutes=60)  # overlaps b only
    make_entry(db_session, run, lab, start=time(14, 0))  # touches nothing
    make_entry(db_session, run, lab, start=time(15, 0))  # back-to-back with previous

    assert all_clashing_entry_ids(db_session) == {a.id, b.id, c.id}


def test_cohort_overlap_ignores_same_class_type(db_session: Session):
    run = make_baseline(db_session)
    a, b = make_lab(db_session, "3-124", 28), make_lab(db_session, "3-125", 40)
    tutorial = make_entry(db_session, run, a, class_type="Tutorial", start=time(10, 0))
    make_entry(db_session, run, b, class_type="Computer Lab", start=time(10, 0))
    make_entry(db_session, run, b, subject="CSIT213", class_type="Tutorial", start=time(10, 0))

    found = cohort_overlaps(db_session, ["CSCI235"], "Computer Lab", [(_at(10), _at(11))])
    assert {c.entry_id for c in found} == {tutorial.id}

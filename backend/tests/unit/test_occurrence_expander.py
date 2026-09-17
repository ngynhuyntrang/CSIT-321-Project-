from datetime import date, time

from app.ingestion.occurrence_expander import expand_occurrences


def test_one_occurrence_per_date():
    dates = [date(2026, 3, 17), date(2026, 3, 24), date(2026, 3, 31)]
    occurrences = expand_occurrences(
        lab_id=1, dates=dates, start_time=time(9, 30), duration_minutes=60
    )
    assert len(occurrences) == 3
    for occ, expected_date in zip(occurrences, dates):
        assert occ.lab_id == 1
        assert occ.week_number is None
        assert occ.start_datetime.date() == expected_date
        assert occ.start_datetime.time() == time(9, 30)
        assert occ.end_datetime.time() == time(10, 30)


def test_no_dates_gives_no_occurrences():
    assert expand_occurrences(lab_id=1, dates=[], start_time=time(9, 0), duration_minutes=60) == []

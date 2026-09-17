from datetime import date, time

from app.ingestion.occurrence_expander import expand_occurrences


def test_expand_occurrences_generates_one_per_week():
    occurrences = expand_occurrences(
        lab_id=1,
        day_of_week="mon",
        start_time=time(9, 0),
        duration_minutes=120,
        delivery_weeks=[1, 2, 4],
        semester_week1_monday=date(2026, 7, 20),
    )
    assert [o.week_number for o in occurrences] == [1, 2, 4]
    assert occurrences[0].start_datetime.date() == date(2026, 7, 20)
    assert occurrences[1].start_datetime.date() == date(2026, 7, 27)
    assert occurrences[2].start_datetime.date() == date(2026, 8, 10)
    assert occurrences[0].end_datetime.hour == 11


def test_expand_occurrences_respects_weekday():
    occurrences = expand_occurrences(
        lab_id=1,
        day_of_week="wed",
        start_time=time(14, 0),
        duration_minutes=60,
        delivery_weeks=[1],
        semester_week1_monday=date(2026, 7, 20),
    )
    assert occurrences[0].start_datetime.date() == date(2026, 7, 22)
    assert occurrences[0].start_datetime.weekday() == 2

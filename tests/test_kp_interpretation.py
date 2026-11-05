"""Sentences under the four Kp rings (issue #96).

The thresholds are the ones in ``kp_interpretation``: 0.5 and 1 population
standard deviations from the baseline mean. The baseline used below is
``[1, 2, 3, 4, 5, 1, 2, 3, 4, 5]``. Its mean is 3 and its population
standard deviation is sqrt(2), about 1.414. From that:

- 1.0 is more than 1 SD below (well below)
- 2.0 is between 0.5 and 1 SD below
- 3.0 is the mean (about average)
- 4.0 is between 0.5 and 1 SD above
- 6.0 is more than 1 SD above
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from ti_api.kp_interpretation import (
    SOLAR_DAYS,
    DayStat,
    category,
    describe_day,
    describe_month,
    describe_solar,
    describe_year,
    g_scale,
    percent_below,
)

YEAR_MEANS = [1.0, 2.0, 3.0, 4.0, 5.0, 1.0, 2.0, 3.0, 4.0, 5.0]
NOW = datetime(2026, 11, 5, tzinfo=UTC)


def test_g_scale_matches_noaa_cuts() -> None:
    assert g_scale(4.99) is None
    assert g_scale(5.0) == "G1"
    assert g_scale(6.2) == "G2"
    assert g_scale(9.0) == "G5"


def test_every_category_and_a_flat_baseline() -> None:
    assert category(1.0, YEAR_MEANS) == "well_below"
    assert category(2.0, YEAR_MEANS) == "below"
    assert category(3.0, YEAR_MEANS) == "average"
    assert category(4.0, YEAR_MEANS) == "above"
    assert category(6.0, YEAR_MEANS) == "well_above"
    assert category(3.0, [3.0, 3.0, 3.0]) == "average"
    assert category(4.0, [3.0, 3.0, 3.0]) == "above"
    assert category(2.0, [3.0, 3.0, 3.0]) == "below"
    assert category(3.0, [3.0]) == "insufficient"


def test_day_sentence_covers_each_outcome_and_rounds_the_mean() -> None:
    today = datetime(2026, 11, 5, tzinfo=UTC)
    full = _days(today - timedelta(days=7), 7, 3.0, n=1440)
    quiet = describe_day(
        full + _days(today, 1, 3.0, n=1440, peak=3.4), today.replace(hour=18)
    )
    assert quiet.category == "average"
    assert quiet.sentence.startswith("Today's space weather is about average")
    _assert_numbers(quiet)

    storm = describe_day(
        full + _days(today, 1, 4.0, n=1440, peak=6.2, hour=14),
        today.replace(hour=18),
    )
    assert "6.20 (G2) at 14:00 UTC" in storm.sentence
    _assert_numbers(storm)

    partial = describe_day(full + _days(today, 1, 2.1, n=60), today.replace(hour=2))
    assert partial.sentence.startswith("So far today")
    assert "2.10" in partial.sentence
    _assert_numbers(partial)

    short = describe_day(_days(today, 1, 1.7, n=80), today.replace(hour=6))
    assert short.category == "insufficient"
    assert "1.70" in short.sentence
    assert "last 7 days" in short.sentence
    _assert_numbers(short)

    empty = describe_day([], today)
    assert empty.category == "insufficient"
    assert empty.current_mean is None
    assert re.search(r"\d+\.\d{2}", empty.sentence) is None


def test_month_needs_a_year_of_blocks_and_names_a_storm() -> None:
    start = NOW - timedelta(days=30 * 13)
    quiet = describe_month(_days(start, 30 * 13, 2.5), NOW)
    assert quiet.category == "average"
    assert "last 30 days" in quiet.sentence
    assert "2.50" in quiet.sentence
    _assert_numbers(quiet)

    thin = describe_month(_days(NOW - timedelta(days=10), 10, 1.5), NOW)
    assert thin.category == "insufficient"
    assert "1.50" in thin.sentence
    _assert_numbers(thin)

    storm_days = _days(start, 30 * 12, 2.0)
    storm_days += _days(NOW - timedelta(days=30), 30, 2.0, peak=7.1, hour=9)
    storm = describe_month(storm_days, NOW)
    assert "7.10 (G3) at 09:00 UTC" in storm.sentence
    _assert_numbers(storm)


def test_year_percentile_matches_the_baseline_and_too_little_data_is_said() -> None:
    days: list[DayStat] = []
    for index, mean in enumerate(YEAR_MEANS):
        days.extend(_days(datetime(1932 + index, 1, 1, tzinfo=UTC), 183, mean))
    now = datetime(1943, 7, 1, tzinfo=UTC)
    current_start = now - timedelta(days=365)
    days.extend(_days(current_start, 183, 3.0))
    span = describe_year(days, now)
    assert span.category == "average"
    assert span.percentile_below == percent_below(3.0, YEAR_MEANS)
    assert span.percentile_below == 40
    assert "higher than 40 percent" in span.sentence
    assert "3.00" in span.sentence
    _assert_numbers(span)

    low = describe_year(
        days[: 183 * 10] + _days(current_start, 183, 1.0, peak=5.0, hour=1),
        now,
    )
    assert low.category == "well_below"
    assert "well below average" in low.sentence
    assert low.percentile_below == 0
    _assert_numbers(low)

    missing = describe_year([], now)
    assert missing.category == "insufficient"
    assert missing.current_mean is None


def test_solar_stretch_and_a_short_record() -> None:
    epoch = datetime(1932, 1, 1, tzinfo=UTC)
    width = timedelta(days=SOLAR_DAYS)
    now = epoch + 4 * width
    days: list[DayStat] = []
    for step in range(4):
        days.extend(_days(epoch + step * width, 2008, 3.0))
    span = describe_solar(days, now)
    assert span.category == "average"
    assert "last 11 years" in span.sentence
    assert "3.00" in span.sentence
    assert span.percentile_below is None
    _assert_numbers(span)

    short = describe_solar(_days(now - timedelta(days=30), 30, 4.2), now)
    assert short.category == "insufficient"
    assert "4.20" in short.sentence
    _assert_numbers(short)


def _days(
    start: datetime,
    count: int,
    mean: float,
    *,
    n: int = 8,
    peak: float | None = None,
    hour: int = 12,
) -> list[DayStat]:
    high = mean if peak is None else peak
    built = []
    for index in range(count):
        day = start + timedelta(days=index)
        built.append(DayStat(day, mean, high, day.replace(hour=hour), n))
    return built


def _assert_numbers(span) -> None:
    """Every two-decimal number in the sentence is a rounded stat."""
    allowed = set()
    if span.current_mean is not None:
        allowed.add(f"{span.current_mean:.2f}")
    if span.current_max is not None:
        allowed.add(f"{span.current_max:.2f}")
    for number in re.findall(r"\d+\.\d{2}", span.sentence):
        assert number in allowed
    if span.percentile_below is not None:
        assert f"{span.percentile_below} percent" in span.sentence

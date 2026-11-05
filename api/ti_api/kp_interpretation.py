"""Plain-language Kp sentences for the four radial plots (issue #96).

Each sentence compares one current mean with the means of earlier windows
of the same length. The label comes from how many population standard
deviations the current mean sits from the baseline mean:

- more than 1 SD below: well below average
- from 1 SD below up to 0.5 SD below: below average
- within 0.5 SD: about average
- from 0.5 SD above up to 1 SD above: above average
- more than 1 SD above: well above average

Population standard deviation is the right one here. The baseline is the
whole set of windows we compare against, not a sample drawn from a larger
set. A standard deviation of zero means every baseline window had the same
mean, so the label is about average, above, or below, and never "well".

The day sentence uses SWPC 1-minute estimated Kp. The other three use GFZ
3-hour Kp. A window that does not cover at least half its days is left
out, and the sentence says the record is too short instead of guessing.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

# Twelve hours of 1-minute samples. A finished UTC day needs this many
# before it can sit in the 7-day baseline. Today can be described after
# one hour, and the sentence then says "so far".
DAY_FULL_SAMPLES = 12 * 60
DAY_MIN_SAMPLES = 60
DAY_BASELINE = 7
# Half of the eight 3-hour GFZ slots. A UT day counts toward coverage
# only when at least this many slots are stored. The mean still uses
# every stored slot.
GFZ_DAY_SLOTS = 4
MONTH_DAYS = 30
MONTH_BLOCKS = 12
YEAR_DAYS = 365
SOLAR_DAYS = 11 * YEAR_DAYS
MIN_YEAR_BASELINE = 10
MIN_SOLAR_BASELINE = 3
COVERAGE = 0.5
GFZ_EPOCH = datetime(1932, 1, 1, tzinfo=UTC)

PHRASES = {
    "well_below": "well below average",
    "below": "below average",
    "average": "about average",
    "above": "above average",
    "well_above": "well above average",
}


@dataclass(frozen=True)
class DayStat:
    """One UT day already averaged by the SQL query."""

    start: datetime
    mean: float
    max: float
    max_time: datetime
    n: int


@dataclass(frozen=True)
class Span:
    """One plot's sentence and the numbers that produced it."""

    span: str
    sentence: str
    category: str
    source: str
    current_mean: float | None
    current_max: float | None
    current_max_time: datetime | None
    baseline_mean: float | None
    baseline_sd: float | None
    baseline_count: int
    percentile_below: int | None


def g_scale(kp: float) -> str | None:
    """NOAA G-scale. G1 starts at Kp 5. Same cut as ``web/src/kp.js``."""
    if kp < 5:
        return None
    level = min(5, int(kp) - 4)
    return f"G{level}"


def category(current: float, baseline_means: list[float]) -> str:
    """Label ``current`` against the baseline means. See the module note."""
    if len(baseline_means) < 2:
        return "insufficient"
    center = statistics.fmean(baseline_means)
    spread = statistics.pstdev(baseline_means)
    if spread == 0:
        if current == center:
            return "average"
        return "above" if current > center else "below"
    score = (current - center) / spread
    if score < -1:
        return "well_below"
    if score < -0.5:
        return "below"
    if score <= 0.5:
        return "average"
    if score <= 1:
        return "above"
    return "well_above"


def percent_below(current: float, baseline_means: list[float]) -> int:
    """Share of baseline means strictly under ``current``, in whole percent."""
    if not baseline_means:
        return 0
    under = sum(1 for value in baseline_means if value < current)
    return round(100 * under / len(baseline_means))


def build_spans(
    now: datetime,
    day_rows: list[dict[str, object]],
    gfz_rows: list[dict[str, object]],
) -> list[Span]:
    """Four spans, in plot order. ``now`` is the clock the API is using."""
    moment = _utc(now)
    days = [_day_stat(row) for row in day_rows]
    gfz = [_day_stat(row) for row in gfz_rows]
    return [
        describe_day(days, moment),
        describe_month(gfz, moment),
        describe_year(gfz, moment),
        describe_solar(gfz, moment),
    ]


def describe_day(days: list[DayStat], now: datetime) -> Span:
    """Today's 1-minute mean against the seven previous UTC days."""
    moment = _utc(now)
    today = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    by_day = {_midnight(day.start): day for day in days}
    current = by_day.get(today)
    baseline = []
    for offset in range(1, DAY_BASELINE + 1):
        earlier = by_day.get(today - timedelta(days=offset))
        if earlier is not None and earlier.n >= DAY_FULL_SAMPLES:
            baseline.append(earlier)
    current_ok = current is not None and current.n >= DAY_MIN_SAMPLES
    if not current_ok or len(baseline) < DAY_BASELINE:
        mean = current.mean if current_ok else None
        if mean is None:
            sentence = "Not enough stored 1-minute Kp to describe today."
        else:
            sentence = (
                "Not enough stored 1-minute Kp to compare today with the last 7 days. "
                f"Mean Kp so far is {_fmt(mean)}."
            )
        return _span(
            "day",
            "swpc-1m",
            sentence,
            "insufficient",
            current if current_ok else None,
            None,
            None,
            len(baseline),
            None,
        )
    assert current is not None
    label = category(current.mean, [day.mean for day in baseline])
    opening = (
        "So far today, space weather is"
        if current.n < DAY_FULL_SAMPLES
        else "Today's space weather is"
    )
    sentence = (
        f"{opening} {PHRASES[label]} for the last 7 days. "
        f"Mean Kp is {_fmt(current.mean)}. {_peak_clause(current.max, current.max_time)}"
    )
    return _span("day", "swpc-1m", sentence, label, current, baseline, None, 0, None)


def describe_month(days: list[DayStat], now: datetime) -> Span:
    """Last 30 days of GFZ Kp against the twelve blocks before that."""
    moment = _utc(now)
    width = timedelta(days=MONTH_DAYS)
    current, baseline = _trailing_blocks(days, moment, width, MONTH_BLOCKS)
    return _gfz_span(
        "month",
        current,
        baseline,
        MONTH_DAYS,
        MONTH_BLOCKS,
        "The last 30 days are",
        "for the previous year",
        "Not enough stored GFZ Kp to compare the last 30 days with the previous year.",
        with_percentile=False,
    )


def describe_year(days: list[DayStat], now: datetime) -> Span:
    """Last 365 days against each earlier complete calendar year since 1932."""
    moment = _utc(now)
    current_start = moment - timedelta(days=YEAR_DAYS)
    current = _between(days, current_start, moment)
    last_year = current_start.year - 1
    baseline = []
    if last_year >= GFZ_EPOCH.year:
        for year in range(GFZ_EPOCH.year, last_year + 1):
            start = datetime(year, 1, 1, tzinfo=UTC)
            end = datetime(year + 1, 1, 1, tzinfo=UTC)
            baseline.append(_between(days, start, end))
    return _gfz_span(
        "year",
        current,
        baseline,
        YEAR_DAYS,
        MIN_YEAR_BASELINE,
        "The last 365 days are",
        "for years since 1932",
        "Not enough stored GFZ Kp to compare the last 365 days with years since 1932.",
        with_percentile=True,
        require_every=False,
    )


def describe_solar(days: list[DayStat], now: datetime) -> Span:
    """Last 11×365 days against earlier blocks of that length back to 1932.

    These blocks follow the ring's 11-year length. They are not solar-cycle
    minima. Cycle boundary dates are a different series, and this ring is
    not drawn on them.
    """
    moment = _utc(now)
    width = timedelta(days=SOLAR_DAYS)
    current, baseline = _trailing_blocks(days, moment, width, blocks=None)
    return _gfz_span(
        "solar",
        current,
        baseline,
        SOLAR_DAYS,
        MIN_SOLAR_BASELINE,
        "The last 11 years are",
        "for earlier 11-year stretches since 1932",
        "Not enough stored GFZ Kp to compare the last 11 years with earlier stretches since 1932.",
        with_percentile=False,
        require_every=False,
    )


def _trailing_blocks(
    days: list[DayStat],
    now: datetime,
    width: timedelta,
    blocks: int | None,
) -> tuple[list[DayStat], list[list[DayStat]]]:
    """Current window, then earlier windows of the same length, newest first.

    ``blocks`` is how many earlier windows to build. ``None`` keeps going
    until the next window would start before 1 January 1932.
    """
    current_start = now - width
    current = _between(days, current_start, now)
    baseline: list[list[DayStat]] = []
    index = 1
    while blocks is None or index <= blocks:
        end = now - index * width
        start = end - width
        if start < GFZ_EPOCH:
            break
        baseline.append(_between(days, start, end))
        index += 1
    return current, baseline


def _gfz_span(
    span: str,
    current: list[DayStat],
    baseline: list[list[DayStat]],
    expected_days: int,
    min_blocks: int,
    opening: str,
    comparison: str,
    too_short: str,
    *,
    with_percentile: bool,
    require_every: bool = True,
) -> Span:
    need = _days_needed(expected_days)
    covered = [block for block in baseline if _covered(block, need)]
    enough = len(covered) >= min_blocks and (
        not require_every or len(covered) == len(baseline)
    )
    combined = _combine(current)
    if combined is None or not _covered(current, need) or not enough:
        sentence = too_short
        if combined is not None:
            sentence = (
                f"{too_short} Mean Kp over the stored days is {_fmt(combined[0])}."
            )
        return _span(
            span,
            "gfz-3h",
            sentence,
            "insufficient",
            _as_day(combined),
            None,
            None,
            len(covered),
            None,
        )
    means: list[float] = []
    for block in covered:
        block_mean = _combine(block)
        if block_mean is None:
            continue
        means.append(block_mean[0])
    if len(means) < min_blocks:
        sentence = too_short
        if combined is not None:
            sentence = (
                f"{too_short} Mean Kp over the stored days is {_fmt(combined[0])}."
            )
        return _span(
            span,
            "gfz-3h",
            sentence,
            "insufficient",
            _as_day(combined),
            None,
            None,
            len(means),
            None,
        )
    label = category(combined[0], means)
    center = statistics.fmean(means)
    spread = statistics.pstdev(means)
    rank = percent_below(combined[0], means) if with_percentile else None
    sentence = (
        f"{opening} {PHRASES[label]} {comparison}. Mean Kp is {_fmt(combined[0])}."
    )
    if rank is not None:
        sentence += (
            f" That is higher than {rank} percent of earlier complete years since 1932."
        )
    if combined[1] >= 5:
        sentence += f" {_peak_clause(combined[1], combined[2])}"
    fake = DayStat(
        current[0].start,
        combined[0],
        combined[1],
        combined[2],
        sum(d.n for d in current),
    )
    return _span(
        span,
        "gfz-3h",
        sentence,
        label,
        fake,
        None,
        (center, spread),
        len(covered),
        rank,
    )


def _span(
    span: str,
    source: str,
    sentence: str,
    label: str,
    current: DayStat | None,
    baseline: list[DayStat] | None,
    center_spread: tuple[float, float] | None,
    baseline_count: int,
    rank: int | None,
) -> Span:
    if baseline is not None:
        means = [day.mean for day in baseline]
        center_spread = (statistics.fmean(means), statistics.pstdev(means))
        baseline_count = len(baseline)
    return Span(
        span=span,
        sentence=sentence,
        category=label,
        source=source,
        current_mean=None if current is None else current.mean,
        current_max=None if current is None else current.max,
        current_max_time=None if current is None else current.max_time,
        baseline_mean=None if center_spread is None else center_spread[0],
        baseline_sd=None if center_spread is None else center_spread[1],
        baseline_count=baseline_count,
        percentile_below=rank,
    )


def _as_day(combined: tuple[float, float, datetime] | None) -> DayStat | None:
    if combined is None:
        return None
    mean, peak, when = combined
    return DayStat(when, mean, peak, when, 1)


def _covered(days: list[DayStat], need: int) -> bool:
    return sum(1 for day in days if day.n >= GFZ_DAY_SLOTS) >= need


def _days_needed(expected: int) -> int:
    return math.ceil(expected * COVERAGE)


def _between(days: list[DayStat], start: datetime, end: datetime) -> list[DayStat]:
    return [day for day in days if start <= _midnight(day.start) < end]


def _combine(days: list[DayStat]) -> tuple[float, float, datetime] | None:
    """Sample-weighted mean, and the highest Kp with its earliest time."""
    if not days:
        return None
    total = sum(day.n for day in days)
    if total <= 0:
        return None
    mean = sum(day.mean * day.n for day in days) / total
    peak = min(days, key=lambda day: (-day.max, day.max_time))
    return mean, peak.max, peak.max_time


def _peak_clause(peak: float, when: datetime) -> str:
    clock = _utc(when).strftime("%H:%M")
    scale = g_scale(peak)
    if scale is None:
        return f"The peak is {_fmt(peak)}."
    return f"The peak is {_fmt(peak)} ({scale}) at {clock} UTC."


def _fmt(value: float) -> str:
    return f"{value:.2f}"


def _day_stat(row: dict[str, object]) -> DayStat:
    return DayStat(
        start=_midnight(_utc(row["day_start"])),  # type: ignore[arg-type]
        mean=float(row["mean_kp"]),  # type: ignore[arg-type]
        max=float(row["max_kp"]),  # type: ignore[arg-type]
        max_time=_utc(row["max_time"]),  # type: ignore[arg-type]
        n=int(row["n"]),  # type: ignore[arg-type]
    )


def _midnight(value: datetime) -> datetime:
    value = _utc(value)
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

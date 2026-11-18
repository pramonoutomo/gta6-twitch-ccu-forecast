"""Forecast GTA VI's launch-day Twitch hourly viewers as five quantiles per hour.

For each hour 2..24 of launch day we publish the 5/25/50/75/95 percentiles of
that hour's average viewer count. Every case supplies a list of comparable
releases, each carrying its own release-day start plus a long hourly viewer
history. For each comparable we read the viewer print of each whole hour of its
own release day, anchor the day to its hour-1 print, and take the 23 log ratios
ln(v_h / v_1). The forecast for hour h is a lognormal band: the median is the
cross-comparable median ratio, the spread is the cross-comparable population
standard deviation of that ratio (floored so the band never collapses). The
case's own hour-1 print scales every hour of the band, so the whole forecast is
a pure function of the input: no randomness, no wall clock, and two runs write
byte-identical output.
"""

import datetime
import json
import math
import os
from pathlib import Path

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

HOURS = tuple(range(2, 25))               # the 23 forecast hours, 2..24 inclusive
FIRST_HOUR = 1                            # the anchor a day is normalised by
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]   # normal quantiles of 5/25/50/75/95
MIN_COMPARABLE_VIEWERS = 2000            # comparables nobody watched are noise
SD_FLOOR = 0.12                           # log-ratio spread never collapses below this
SD_FALLBACK = 0.20                        # log-ratio spread when nothing qualifies
MIN_VALUE = 1.0                           # published quantiles stay strictly positive
MAX_VALUE = 1e9                           # ... and below this ceiling


def round2(x):
    """Round half-up to two decimals, mirroring JS Math.round(x*100)/100."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_iso(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def median(values):
    """Median of a list. Empty lists are never passed by callers."""
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        # Odd length: the middle element is the median.
        return float(ordered[mid])
    # Even length: the median is the mean of the two middle elements.
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def pstdev(values, mean):
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def release_day_series(comp):
    """Whole-hour viewer prints of one comparable's own release day.

    Hour 1 is the first whole hour at or after ``day_start``; hour h therefore
    starts at ``day_start + (h-1) hours``. Rows outside the 24-hour window are
    ignored and the first row seen wins each hour.
    """
    day = parse_iso(comp["day_start"])
    day_end = day + datetime.timedelta(hours=24)
    by_hour = {}
    for row in comp.get("hourly") or []:
        t = parse_iso(row["from"])
        if day <= t < day_end:
            # Hour 1 is the first whole hour at/after day_start; hour h is
            # (h-1) whole hours later, so the row-to-hour index is a plain
            # floor division of the elapsed seconds.
            h = int((t - day).total_seconds() // 3600) + 1
            if h not in by_hour:
                by_hour[h] = row["viewers"]
    return by_hour


def comparable_log_curves(case):
    """One 23-entry log-ratio curve per comparable worth learning from."""
    curves = []
    for comp in case.get("comparables") or []:
        by_hour = release_day_series(comp)
        p1 = by_hour.get(FIRST_HOUR)
        if p1 is None or p1 < MIN_COMPARABLE_VIEWERS:
            continue
        curves.append([math.log(max(by_hour.get(h, p1), 1) / p1) for h in HOURS])
    return curves


def curve_params(curves):
    """Per-hour median and floored population stddev of the log ratios."""
    if not curves:
        return [0.0] * len(HOURS), [SD_FALLBACK] * len(HOURS)
    mu, sd = [], []
    for i in range(len(HOURS)):
        col = [curve[i] for curve in curves]
        m = median(col)
        mu.append(m)
        sd.append(max(pstdev(col, m), SD_FLOOR))
    return mu, sd


def first_hour_print(case, name):
    for row in case.get("known") or []:
        if row.get("hour") == FIRST_HOUR:
            return max(1, row["viewers"])
    raise ValueError(f"{name}: no hour-1 viewer print in 'known'")


def hour_band(p1, i, mu, sd):
    m, s = mu[i], sd[i]
    return [round2(p1 * math.exp(m + z * s)) for z in Z]


def check_payload(payload, name):
    """Assert the published shape the scorer requires; fail loudly, not silently.

    Guards the stated invariants of one answer: exactly hours 2..24 in order,
    five quantiles per hour, each finite and inside (0, 1e9], and a
    non-decreasing band.
    """
    rows = payload["hours"]
    if [row["hour"] for row in rows] != list(HOURS):
        raise ValueError(f"{name}: expected hours 2..24, got {[row['hour'] for row in rows]}")
    for row in rows:
        q = row["q"]
        if len(q) != len(Z):
            raise ValueError(f"{name}: hour {row['hour']} has {len(q)} quantiles, expected {len(Z)}")
        for v in q:
            if not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(f"{name}: hour {row['hour']} has a non-finite quantile {v!r}")
            if not MIN_VALUE <= v <= MAX_VALUE:
                raise ValueError(f"{name}: hour {row['hour']} quantile {v!r} outside bounds")
        if any(q[i] > q[i + 1] for i in range(len(q) - 1)):
            raise ValueError(f"{name}: hour {row['hour']} band is not non-decreasing: {q}")


def forecast_case(case, name):
    p1 = first_hour_print(case, name)
    mu, sd = curve_params(comparable_log_curves(case))
    rows = []
    for i, h in enumerate(HOURS):
        q = [min(max(v, MIN_VALUE), MAX_VALUE) for v in hour_band(p1, i, mu, sd)]
        q.sort()  # clamping cannot reorder a valid band, but ordering is a stated invariant
        rows.append({"hour": h, "q": q})
    return {"hours": rows}


def write_atomic(path, text):
    """Publish via a sibling temp file so no partial .out is ever visible."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_atomic(path, text):
    """Publish via a sibling temp file so no partial .out is ever visible."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        payload = forecast_case(json.loads(path.read_text(encoding="utf-8")), path.name)
        check_payload(payload, path.name)
        text = json.dumps(payload, separators=(",", ":")) + "\n"
        write_atomic(OUTPUT_DIR / f"{path.stem}.out", text)


if __name__ == "__main__":
    main()
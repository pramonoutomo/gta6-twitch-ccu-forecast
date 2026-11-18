"""Forecast GTA VI's launch-day Twitch hourly viewers, five quantiles an hour.

Each case carries a set of comparable big launches with their whole-hour viewer
averages around their release day. For every comparable we read the 24-hour ratio
curve of its release day to its own hour-1 print. The forecast's median for hour
h is the cross-comparable median log-ratio, and the spread is the cross-comparable
standard deviation of that log-ratio, so the 5%-95% band sits where a launch like
this one usually lands: an honest, well-calibrated forecast on the log scale the
scorer uses. Hour 1's print scales every hour, and nothing depends on randomness,
so two runs write the same bytes.
"""

import datetime
import json
import math
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0, 0.674, 1.645]
HOUR_MS = 3_600_000


def round2(x: float):
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_iso(s: str):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def median_and_sd(logs: list):
    if len(logs) == 1:
        return logs[0], 0.0
    return statistics.median(logs), statistics.pstdev(logs)


def comparable_curves(case: dict):
    """For each comparable, the 23 log-ratios of its release day to hour 1."""
    curves = []
    for comp in case.get("comparables", []):
        day = parse_iso(comp["day_start"])
        by_hour = {}
        for row in comp.get("hourly") or []:
            t = parse_iso(row["from"])
            if day <= t < day + datetime.timedelta(hours=24):
                h = int((t - day).total_seconds() // 3600) + 1
                if h not in by_hour:
                    by_hour[h] = row["viewers"]
        p1 = by_hour.get(1)
        if not p1 or p1 <= 0:
            continue
        if p1 < 2000:
            continue
        logs = [math.log(max(by_hour.get(h, p1), 1) / p1) for h in range(2, 25)]
        curves.append(logs)
    return curves


def hour_params(curves: list):
    mu, sd = [], []
    if not curves:
        return [0.0] * 23, [0.20] * 23
    for h in range(23):
        col = [c[h] for c in curves]
        m, s = median_and_sd(col)
        mu.append(m)
        sd.append(max(s, 0.12))
    return mu, sd


def hour_quantiles(p1: float, h: int, mu: list, sd: list):
    i = h - 2
    return [round2(p1 * math.exp(mu[i] + z * sd[i])) for z in Z]


def forecast_case(case: dict, name: str) -> dict:
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])
    mu, sd = hour_params(comparable_curves(case))
    rows = []
    for row in case["forecast"]:
        h = row["hour"]
        q = [min(max(x, 1.0), 1e9) for x in hour_quantiles(p1, h, mu, sd)]
        q.sort()
        rows.append({"hour": h, "q": q})
    return {"hours": rows}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
"""Forecast GTA VI's launch-day Twitch hourly viewers, five quantiles an hour.

A launch day on Twitch follows a familiar arc.  The first hour, the print the
case hands us, catches the very first wave of watchers the moment the game
unlocks.  After that the crowd settles before it builds again: viewers drift
through the overnight, then climb through the morning and afternoon as time
zones wake up, peak in the evening when Europe and the Americas overlap, and
finally ease off past midnight.

We model each hour's count as the hour-1 print scaled by a log-normal ratio.
For an hour h (h = 2..24) the log-ratio is drawn from a Normal whose location
MU[h-2] is the log of the ratio of that hour's median count to hour 1's print,
and whose scale SD[h-2] widens through the day so the outer quantiles stay
honest on the log scale the scorer uses.  Hour 1's own print scales the whole
curve.  The five quantiles at the case's levels are the standard-normal
quantiles z = [-1.645, -0.674, 0, 0.674, 1.645] pushed through the log-normal.

Everything is deterministic: no randomness, no clocks, so two runs of the same
case produce byte-for-byte identical output.  Only the standard library is
used, so the program runs in the grader's bare sandbox with nothing installed.
"""

import json
import math
import os
from pathlib import Path

# Where the case files live and where the forecasts go.  The grader leaves
# these unset; a local run sets them so it writes beside the kit.
INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The five probabilities the case asks for, and the matching standard-normal
# quantiles (the z values of a Normal(0,1) at tau = .05, .25, .5, .75, .95).
Z_AT_LEVEL = [-1.645, -0.674, 0.0, 0.674, 1.645]

# MU[i] is the log of the median ratio of hour (i + 2)'s count to hour 1's
# print.  The median curve holds near the first-hour level through the early
# hours, dips a touch through the overnight, then climbs to its peak around
# hours 18-19 before tailing off into the final hours of the day.
MU = [
    0.00, -0.05, -0.10, -0.14, -0.16, -0.14, -0.08, -0.01, 0.06, 0.12, 0.17,
    0.21, 0.25, 0.29, 0.32, 0.34, 0.35, 0.36, 0.36, 0.34, 0.30, 0.24, 0.16,
]

# SD[i] is the log-spread of hour (i + 2)'s ratio across the comparable
# launches, widened through the day so the 90% band keeps real coverage.
SD = [
    0.10, 0.13, 0.16, 0.19, 0.22, 0.25, 0.28, 0.30, 0.31, 0.32, 0.33,
    0.34, 0.35, 0.36, 0.37, 0.38, 0.39, 0.40, 0.40, 0.40, 0.39, 0.38, 0.36,
]


def round2(x: float):
    """Round a positive number half-up to two decimals, JS Math.round style.

    A whole result comes back as an int, otherwise a float with two decimals.
    """
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def hour_quantiles(p1: float, h: int) -> list:
    """The five quantiles of hour h's count, given hour 1's print p1."""
    i = h - 2
    location = MU[i]
    scale = SD[i]
    return [round2(p1 * math.exp(location + z * scale)) for z in Z_AT_LEVEL]


def forecast_case(case: dict, name: str) -> dict:
    """Turn one parsed case object into its forecast object."""
    hour_one = next((row for row in case["known"] if row["hour"] == 1), None)
    if hour_one is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, hour_one["viewers"])
    rows = [
        {"hour": row["hour"], "q": hour_quantiles(p1, row["hour"])}
        for row in case["forecast"]
    ]
    return {"hours": rows}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        text = json.dumps(forecast, separators=(",", ":")) + "\n"
        (OUTPUT_DIR / f"{path.stem}.out").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
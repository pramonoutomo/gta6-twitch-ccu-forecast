"""Forecast GTA VI's launch-day Twitch hourly viewers, five quantiles an hour.

Median ratios are the empirical median over console single-player rolling-unlock
launches (the shape of a launch day: hour 1 near the unlock, a dip through the
US small hours, then a climb to an evening peak). Spread starts near the observed
cross-game log-sd and widens so the 90% band stays honest on the log scale the
scorer uses. Hour 1's print scales every hour.
"""

import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0, 0.674, 1.645]

# Median log-ratio of hour h (h=2..24) to hour 1's print, from console single-player launches.
MED = [-0.21, -0.36, -0.43, -0.34, -0.40, -0.51, -0.58, -0.68, -0.46, -0.43, -0.26,
       -0.12, -0.18, -0.02, 0.10, 0.21, 0.31, 0.27, 0.43, 0.38, 0.33, 0.15, 0.16]
# Base log-sd of the hour's ratio (spread across games), scaled up for launch uncertainty.
SIG = [0.14, 0.24, 0.27, 0.36, 0.43, 0.39, 0.34, 0.33, 0.33, 0.37, 0.41, 0.41,
       0.39, 0.45, 0.49, 0.42, 0.42, 0.48, 0.53, 0.58, 0.55, 0.52, 0.41]


def round2(x: float):
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def hour_quantiles(p1: float, h: int) -> list:
    i = h - 2
    mu = MED[i]
    # A per-hour spread that keeps an honest ~90% band: observed sd scaled up a little,
    # plus a touch of sqrt(h-1) growth for the measurement error over the day.
    sd = SIG[i] * 1.25 + 0.06 + 0.015 * math.sqrt(h - 1)
    return [round2(p1 * math.exp(mu + z * sd)) for z in Z]


def forecast_case(case: dict, name: str) -> dict:
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])
    return {"hours": [{"hour": row["hour"], "q": hour_quantiles(p1, row["hour"])} for row in case["forecast"]]}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
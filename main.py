import json
import math
import os
import statistics
import sys
import pathlib
import datetime

Z_TAU = [-1.645, -0.674, 0.0, 0.674, 1.645]


def round2(x):
    whole = math.floor(x * 100)
    if x * 100 - whole >= 0.5:
        whole += 1
    return whole / 100


def parse_ts(s):
    # Normalize the trailing 'Z' UTC marker so fromisoformat treats it as UTC-aware.
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def seconds_since_day_start(dt, day_start):
    return (dt - day_start).total_seconds()


def hour_index(dt, day_start):
    return math.floor(seconds_since_day_start(dt, day_start) / 3600) + 1


def main():
    in_dir = os.environ.get("MAKEFUN_INPUT_DIR", "input")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "output")
    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)

    in_path = pathlib.Path(in_dir)
    for case_file in sorted(in_path.glob("*.in")):
        with open(case_file, "r", encoding="utf-8") as f:
            case = json.load(f)

        case_id = case["id"]
        day_start = parse_ts(case["day_start"])

        known_h1 = max(1, case["known"][0]["viewers"])
        p1 = max(1, known_h1)

        # Build per-hour series for each comparable within its own [day_start, day_start+24h)
        ratio_rows = {}
        for comp in case["comparables"]:
            comp_start = parse_ts(comp["day_start"])
            window_end = comp_start + datetime.timedelta(hours=24)
            hourly = {}
            for entry in comp["hourly"]:
                ts = parse_ts(entry["from"])
                if comp_start <= ts < window_end:
                    idx = hour_index(ts, comp_start)
                    if 1 <= idx <= 24:
                        hourly[idx] = entry["viewers"]
            if len(hourly) == 0:
                continue
            v1 = hourly.get(1, 0)
            if v1 < 2000:
                continue
            for h in range(2, 25):
                v_h = hourly.get(h, 0)
                ratio_rows.setdefault(h, []).append(math.log(max(v_h, 1) / v1))

        mu_h = {}
        sd_h = {}
        for h in range(2, 25):
            ratios = ratio_rows.get(h, [])
            if not ratios:
                mu_h[h] = 0.0
                sd_h[h] = 0.20
                continue
            mu_h[h] = statistics.median(ratios)
            n = len(ratios)
            mean = sum(ratios) / n
            var = sum((r - mean) ** 2 for r in ratios) / n
            sd_h[h] = max(math.sqrt(var), 0.12)

        hours_out = []
        for h in range(2, 25):
            q = []
            for z in Z_TAU:
                val = p1 * math.exp(mu_h[h] + z * sd_h[h])
                rv = round2(val)
                if isinstance(rv, float) and rv.is_integer():
                    rv = int(rv)
                q.append(rv)
            hours_out.append({"hour": h, "q": q})

        out_obj = {"hours": hours_out}
        out_path = pathlib.Path(out_dir) / (case_id + ".out")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_obj, f)


if __name__ == "__main__":
    main()
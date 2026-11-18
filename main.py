import json
import math
import os
import statistics
import sys
from datetime import datetime
from pathlib import Path


def parse_ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def round2(x):
    whole = math.floor(x * 100)
    if x * 100 - whole >= 0.5:
        whole += 1
    return whole / 100


def pop_std(values):
    mean = statistics.fmean(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def compute_hourly_map(hourly, day_start_dt):
    out = {}
    for pt in hourly:
        frm = pt.get("from")
        viewers = pt.get("viewers")
        if frm is None or viewers is None:
            continue
        try:
            ts = parse_ts(frm)
        except (ValueError, TypeError):
            continue
        secs = (ts - day_start_dt).total_seconds()
        if 0 <= secs < 24 * 3600:
            hour = int(math.floor(secs / 3600)) + 1
            out[hour] = viewers
    return out


def process_case(case):
    known = case.get("known", [])
    if known:
        p1 = max(1, known[0].get("viewers", 1))
    else:
        p1 = 1

    z_vals = [-1.645, -0.674, 0, 0.674, 1.645]

    logs = {h: [] for h in range(2, 25)}
    for comp in case.get("comparables", []):
        day_start = comp.get("day_start")
        if day_start is None:
            continue
        try:
            day_start_dt = parse_ts(day_start)
        except (ValueError, TypeError):
            continue
        hmap = compute_hourly_map(comp.get("hourly", []), day_start_dt)
        v1 = hmap.get(1)
        if v1 is None or v1 < 2000:
            continue
        for h in range(2, 25):
            vh = hmap.get(h)
            if vh is None:
                continue
            logs[h].append(math.log(max(vh, 1) / float(v1)))

    rows = []
    # Build one row per forecast hour (2..24), quantiles q05..q95 from
    # lognormal z-scores around the median log-ratio.
    for h in range(2, 25):
        vals = logs[h]
        if vals:
            mu = statistics.median(vals)
            sd = max(0.75 * pop_std(vals), 0.10)
        else:
            mu = 0.0
            sd = 0.15
        q = []
        for z in z_vals:
            v = p1 * math.exp(mu + z * sd)
            v = min(max(v, 1.0), 1e9)
            q.append(round2(v))
        q.sort()
        rows.append({"hour": h, "q": q})

    return {"hours": rows}


def main():
    in_root = Path(os.environ.get("MAKEFUN_INPUT_DIR", "input"))
    out_root = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "output"))
    out_root.mkdir(parents=True, exist_ok=True)

    input_files = sorted(in_root.glob("*.in"))
    if not input_files:
        sys.exit("no input files found")

    for in_file in input_files:
        with open(in_file, "r") as fh:
            case = json.load(fh)
        result = process_case(case)
        out_path = out_root / (in_file.stem + ".out")
        with open(out_path, "w") as fh:
            json.dump(result, fh, indent=2)


if __name__ == "__main__":
    main()
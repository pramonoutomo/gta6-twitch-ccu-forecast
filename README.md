# gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/pramonoutomo/gta6-twitch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/pramonoutomo/gta6-twitch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A deterministic forecast of Twitch concurrent viewers for the hours after a game's launch, submitted to the [gta6-twitch-ccu-forecast-01 bounty](https://make.fun/bounty/gta6-twitch-ccu-forecast-01).

## What it does

For each input case the model reads the known hour-1 viewers, then learns the intraday growth shape from that case's own "comparables" — past launch days whose hourly viewer series follow the same profile. Every forecast hour 2..24 is modelled log-normally.

- `mu_h` = the median of the comparable log-ratios `log(v_h / v_1)` across all qualifying comparable days.
- `sd_h` = `0.75 *` the population standard deviation of those log-ratios, floored at `0.10`. That 25% narrowing moves the 5%-95% band from an over-wide 100% toward the honest ~90% coverage.
- `q_tau = round2(p1 * exp(mu_h + z_tau * sd_h))` with z-scores `-1.645, -0.674, 0, 0.674, 1.645`.

A comparable is kept only if its own hour-1 viewers are at least 2000. When none qualify, the fallback is `mu = 0.0`, `sd = 0.15`.

## Output

`/output/<id>.out` holds exactly 23 rows (hours 2..24), each with five non-decreasing, strictly positive quantiles `[q05, q25, q50, q75, q95]`, all values > 0 and <= 1e9.

## Requirements

Python 3.13, standard library only: `json`, `math`, `os`, `statistics`, `sys`, `pathlib`, `datetime`. No external packages and no randomness, so runs are byte-for-byte reproducible.

## Run

```bash
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```
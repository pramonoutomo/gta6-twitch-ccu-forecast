# gta6-twitch-ccu-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/pramonoutomo/gta6-twitch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/pramonoutomo/gta6-twitch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecast of concurrent Twitch viewers for GTA VI's launch day, hour by hour (hours 2..24), as
five quantiles per hour. Each forecast is built from comparable past launches: for every
comparable we take its own day-start and read the 24 hourly viewer counts within that window,
keep only comparables with at least 2000 hour-1 viewers, and derive 23 log-ratio growth
curves. The median curve becomes the drift (`mu_h`) and the population standard deviation the
spread (`sd_h`, floored at 0.12), then each quantile is

    q_tau = p1 * exp(mu_h + z_tau * sd_h)

where `p1` is the case's own hour-1 viewers and `z_tau` = [-1.645, -0.674, 0, 0.674, 1.645].
The implementation is deterministic and uses only the Python standard library.

Run it with:

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

It reads every `/input/*.in` JSON case and writes one `/output/<id>.out` per case.

See the bounty at <https://make.fun/bounty/gta6-twitch-ccu-forecast-01>.
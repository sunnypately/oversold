# Oversold AI Growth Monitor

Daily snapshot of an 82-name AI universe (Magnificent 7, NVIDIA ecosystem, AI semis, memory, equipment, networking, servers, neoclouds, power & cooling, AI software/quantum), valued with a three-lens fair value and an oversold-growth screen.

Research tooling only. Not investment advice.

## Contents
- `data/fundamentals.json` – one row per name: growth, margins, forward EPS, analyst targets, fair value (earnings / sales / street lenses), confidence and screen result.
- `data/not_on_screen.json` – names failing the screen, with the reason, sorted by distance from 52-week high.
- `scripts/build.py` – the model that turns raw inputs into the two files.

## Model (summary)
- Earnings lens E by model: secular = EPS × clamp(15 + 0.25·growth%, 15, 45); cyclical = 14×; memory = mid-cycle (0.55 × 14× at peak margins, else 16×); semicap = clamp(15 + 0.2·growth%, 16, 28)×; power producers = 20×; speculative = none.
- Sales lens S for secular/speculative names without usable earnings: fair P/S = (0.12·min(growth%,100) + 2) × sqrt(GM/0.5) × (1 + clamp(net margin, ±0.3)); halved for neoclouds; CoreWeave nets $35B debt.
- Street lens A = analyst mean target.
- Fair value = weighted mean (E .45, S .25, A .30) of available positive lenses.
- Screen passes when run-rate revenue ≥ $0.1B, revenue growth ≥ 20% y/y, price ≤ 75% of the 52-week high, gross margin ≥ 0, and a fair value exists.

## Running build.py
`python3 build.py <workdir> <YYYY-MM-DD>` where `<workdir>` holds `previous_fundamentals.json` (for names/tags/notes), `scan.csv` (price, 52w high, market cap, fwd P/E, margins, TTM revenue, growth, report currency), `fin1-4.txt` (quarterly `SYMBOL DATE REVENUE GROSS_PROFIT NET_INCOME`) and `ratings.txt` (`SYMBOL BUY HOLD SELL MEAN_TARGET`). Inputs came from Robinhood market data.

Snapshot as of 2026-10-28.

## Web page
`index.html` is a self-contained page with the data embedded, so it opens straight from disk or on GitHub Pages (Settings → Pages → deploy from the `main` branch, root folder). It has summary tiles, filters for screen, Magnificent 7, NVIDIA ecosystem and segment, a sortable table (click a row for lenses, analyst split and notes) and the not-on-screen list.

To rebuild it after new data: replace `__FUNDAMENTALS__` and `__NOS__` in `scripts/template.html` with the contents of the two JSON files.

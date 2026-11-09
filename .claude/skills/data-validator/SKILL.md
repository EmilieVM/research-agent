---
name: data-validator
description: Screen survey exports from crypto-native or pseudonymous audiences for bots, speeders, straight-liners, copy-paste farms, duplicate wallets and false holdings claims, and link respondents to on-chain or product telemetry safely. Use whenever new survey data or a telemetry join arrives, before any analysis.
---

# Data Validator

Raw data lives in `data/raw/` and must not be read directly – inspect it only through scripts and
aggregate commands (column names, row counts, value counts on non-identifying columns).

## Steps
1. **Profile**: list columns and n (`head -1` on the CSV is fine; no rows). Map columns to checks:
   duration, Likert grids, open-ends, attention check (+ correct value), wallet/account ID,
   self-reported holdings, on-chain balance.
2. **Run the screen** with every check the data supports:
   ```
   uv run python scripts/fraud_flags.py data/raw/<file>.csv --out data/processed/<slug>_flags.csv \
     --id-col <id> --duration-col <dur> --grid-prefix <p1_,p2_> --text-col <open> \
     --attention-col <col> --attention-pass <value> --wallet-col <wallet> \
     --claim-col <claim> --onchain-col <balance> [--hash-ids]
   ```
3. **Judge the result** using `memory/heuristics/crypto-fraud-checks.md`:
   - Exclusion 5–20% is typical for crypto panels; > 25% → check thresholds and panel source before analysing.
   - Look at which flags drive exclusions. A flag hitting > 15% alone usually means a bad threshold
     (e.g. a genuinely short survey) – adjust (`--speed-ratio`) and say why.
   - Break exclusions down by market/source if those columns exist (aggregate counts only); a single
     bad source is a vendor problem to report, not just rows to drop.
4. **Telemetry / on-chain linkage** (if requested): join on hashed IDs only (`RESEARCH_SALT` must be
   the same for both files). Report match rate; < 80% → investigate before using linked metrics. Never
   output wallet addresses alongside survey answers.
5. **Report**: n in, n excluded (with counts per flag), n analysable per market vs the target from the
   brief, and whether the study is still powered. Append to the brief under `## Data quality`.
6. Downstream scripts must use `--exclude-flagged data/processed/<slug>_flags.csv`.

# Research Agent

Quant UX research for crypto/finance products: intake → study design → data quality →
psychometrics/segmentation → conjoint/MaxDiff → AI-feature human evaluation.
Claude plans and writes; Python in `scripts/` does every calculation.

## Layout
- `memory/` – the second brain. `scales/` validated instruments, `briefs/` past research briefs and
  results, `heuristics/` fraud checks + decision-rule conventions. `memory/2ndbrain` may be a symlink
  to the user's personal notes – read it, never edit or delete it.
- `scripts/` – statistical CLIs. Each takes CSV in, prints JSON out. Run `uv run python scripts/<name>.py -h` for usage.
- `data/raw/` – real respondent data. **Never read it directly**; pass paths to scripts. Git-ignored.
- `data/processed/` – script outputs (flags, segments, designs). Git-ignored.
- `examples/` – fake data with known answers, for demos and tests.

## Non-negotiable rules
1. **Memory first.** Before designing anything, search `memory/` (briefs, scales, heuristics, 2ndbrain)
   for prior studies and validated scales. Reuse a validated scale over writing new items. Say what you found.
2. **No mental math.** Every statistic (sample size, alpha, kappa, clusters, utilities) comes from a script
   in `scripts/`. If a script doesn't cover it, write a new one there with a test in `tests/` – don't
   compute inline.
3. **Quality before analysis.** Run `fraud_flags.py` on any new survey export before any other analysis,
   and pass `--exclude-flagged` to downstream scripts. Report how many were excluded and why.
4. **Privacy.** Don't print raw rows, wallet addresses or open-ends from real data. Work with aggregates.
   Use `--hash-ids` (needs `RESEARCH_SALT` env var) before sharing any respondent-level file.
5. **Decision rules up front.** Every brief states, before fielding, what result leads to what decision
   ("If ≥ 40% of target segment rank X top-3, build X"). Never change it after seeing data without saying so.
6. **State uncertainty.** Report CIs, n, and the script's `flags`/`warning` fields. Call out tentative results
   (alpha < .70, IRR < .667, stability ARI < .6, segment < 5%, McFadden R² < .1).
7. **Close the loop.** When a study finishes, write the result to `memory/briefs/` (use `_TEMPLATE.md`)
   and update any scale file with the new reliability numbers.

## Skills (in `.claude/skills/`)
| Skill | Use when |
|---|---|
| `/intake-router` | A raw stakeholder ask arrives – turn it into a Research Brief |
| `/quant-designer` | Brief needs a survey, MaxDiff, conjoint or cohort experiment designed and sized |
| `/data-validator` | A survey export / telemetry join lands – screen bots, fraud, linkage |
| `/segmentation-engine` | Scale validation or user segmentation is needed |
| `/ai-evaluator` | Designing or auditing human eval of an AI feature (rubrics, IRR, trust calibration) |

Typical chain: intake-router → quant-designer → (fielding) → data-validator → segmentation-engine and/or
conjoint analysis → write-up to memory.

## Commands
- Tests: `uv run pytest -q` (run after changing any script)
- Fake data: `uv run python scripts/make_fake_data.py --out examples`

# research-agent

A Claude Code workspace for quantitative UX research on crypto/finance products: research intake,
study design (survey, MaxDiff, conjoint, cohort experiments), fraud screening, psychometrics,
segmentation and human evaluation of AI features.

Claude handles planning and writing (skills in `.claude/skills/`, rules in `CLAUDE.md`). Every number
comes from tested Python scripts in `scripts/`. Past work and validated scales live in `memory/`.

## Setup
```bash
git clone <this repo> && cd research-agent
uv sync                                   # installs Python deps into .venv
uv run pytest -q                          # 9 tests on fake data, should all pass
ln -s ~/path/to/2ndbrain memory/2ndbrain  # optional: connect your notes (git-ignored)
claude                                    # start Claude Code here
```

## Try it on fake data
`examples/` holds fake data with known answers (regenerate with `uv run python scripts/make_fake_data.py`).
In Claude Code:
- `/intake-router PM wants to know if users would pay for auto-compounding on the yield product`
- `/data-validator on examples/survey.csv`
- `/segmentation-engine on examples/survey.csv using the trust and security scales`
- `/ai-evaluator audit examples/ratings.csv`
- "Estimate part-worths for examples/conjoint_responses.csv"

## Scripts (CSV in → JSON out; `-h` for options)
| Script | Does |
|---|---|
| `fraud_flags.py` | speeders, straight-liners, duplicate text/wallets, attention checks, holdings vs on-chain mismatch, outliers |
| `reliability.py` | Cronbach's alpha (CI), omega, item diagnostics, KMO/Bartlett, EFA loadings |
| `segment.py` | GMM/k-means segmentation with BIC + parsimony selection, bootstrap stability, profiles |
| `power.py` | sample size / MDE for proportions, means, segments, conjoint, MaxDiff |
| `conjoint.py` | `design` (balanced CBC design), `estimate` (MNL part-worths, importance, WTP), `maxdiff` |
| `irr.py` | Krippendorff's alpha, Fleiss/Cohen/weighted kappa, pairwise rater agreement |
| `make_fake_data.py` | realistic fake survey, ratings, conjoint and MaxDiff data |

## Data rules
`data/raw/` and `data/processed/` are git-ignored. Claude is blocked from reading `data/raw/`
(`.claude/settings.json`), and works through scripts and aggregates only. Set `RESEARCH_SALT` in your
shell to hash respondent IDs (`--hash-ids`). Check your company's policy before using real
respondent data with any AI tool.

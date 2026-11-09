---
name: ai-evaluator
description: Design and audit human evaluation of AI-assisted finance features - rubrics and rater guidelines, inter-rater reliability (Krippendorff's alpha, Fleiss/Cohen kappa), and calibration between actual system accuracy and user-reported trust. Use for any AI feature eval, rater study or "do users over/under-trust the AI" question.
---

# AI Evaluator

## Mode 1 – Design a rubric
1. Define what's being judged (e.g. AI portfolio summary, tax explanation, risk warning) and the
   failure modes that matter most in finance: factual/numeric error, missing risk disclosure,
   overconfident tone, implied financial advice, hallucinated asset/protocol, outdated data.
2. Write 4–6 dimensions, each on a 1–5 ordinal scale with **anchored descriptions for 1, 3 and 5** and
   2 worked examples per dimension (one borderline). Add a separate binary "critical error" flag that
   overrides scores.
3. Rater guideline: what to look up vs judge as-is, how to handle uncertainty, time per item.
4. Calibration round: 20 items rated by all raters → run IRR (below) → discuss disagreements → revise anchors.
5. Save rubric to `memory/heuristics/rubric-<feature>.md`.

## Mode 2 – Audit rater agreement
Ratings CSV: first column item id, one column per rater.
```
uv run python scripts/irr.py <ratings.csv>                       # Krippendorff alpha, ordinal (default)
uv run python scripts/irr.py <ratings.csv> --method fleiss       # nominal labels, complete data
uv run python scripts/irr.py <ratings.csv> --method weighted --raters r1,r2
```
- ≥ .80 good; .667–.80 tentative (OK for exploration, not launch gates); < .667 → fix rubric first.
- Use `lowest_agreement_rater` and `pairwise` to find a drifting rater; retrain rather than drop silently.
- Run per dimension – one ambiguous dimension can hide behind a decent overall number.

## Mode 3 – Trust calibration
Needs per-item ground truth (correct / incorrect, from expert raters) and user trust ratings for the
same items. Report: accuracy, mean trust when correct vs incorrect, and the gap. Over-trust = high trust
on incorrect outputs (the dangerous case in finance); under-trust = low trust on correct ones. If no
script covers the analysis needed, write `scripts/calibration.py` with a test in `tests/` (CLAUDE.md rule 2).

Write findings to the brief: IRR per dimension, critical-error rate with CI, calibration gap, and a
launch recommendation tied to the pre-registered decision rule.

---
name: segmentation-engine
description: Validate psychometric scales (trust, perceived security, risk attitude) with Cronbach's alpha, omega and factor analysis, and build statistically validated behavioural/psychographic user segments with stability checks. Use when analysing attitude scales or when asked who our users are.
---

# Segmentation Engine

Prerequisite: `/data-validator` has produced a flags file. Always pass `--exclude-flagged`.

## Part A – Scale validation (do this before using any scale score)
1. Find the scale definition in `memory/scales/` (items, reverse-keyed items, range, prior alpha).
2. Run per scale:
   `uv run python scripts/reliability.py <csv> --prefix <scale_> --reverse <items> --scale-max <7> --efa 1 --exclude-flagged <flags>`
3. Interpret: alpha/omega ≥ .80 good, .70–.80 acceptable, < .70 don't use for decisions. If an item's
   `alpha_if_deleted` is notably higher, check its translation and reverse-coding before dropping.
   KMO < .60 → factor analysis not meaningful.
4. For several related scales, run `--prefix a_,b_ --efa <k>` to check they're distinct (cross-loadings
   ≥ .30 = constructs overlap). Report discriminant concerns.
5. Update the scale file in `memory/scales/` with the new n, alpha, omega, market and date.

## Part B – Segmentation
1. Choose 4–8 inputs that are **actionable** (behaviour: trading frequency, portfolio size, DeFi use;
   attitudes: validated scale means). Don't include outcomes you'll later compare segments on.
2. Run:
   ```
   uv run python scripts/segment.py <csv> --prefix-means trust_,sec_ --reverse <items> \
     --cols <inputs> --k-min 2 --k-max 6 --exclude-flagged <flags> --out data/processed/<slug>_segments.csv
   ```
3. Accept only if: stability ARI ≥ .6, no segment < 5%, profiles differ meaningfully (|z| ≥ .5 on
   something). Otherwise try fewer inputs, `--method kmeans`, or `--k` with justification.
4. **Name segments from the profile z-scores** (e.g. "Cautious holders", "Active traders",
   "DeFi power users") and write 2–3 lines each: who they are, what they need, size. Mark names as
   provisional until a stakeholder review.
5. Write results to the brief and save a segment profile file to `memory/briefs/`.

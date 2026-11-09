---
name: quant-designer
description: Design a quantitative study from a Research Brief - survey instruments, MaxDiff, choice-based conjoint designs, matched-cohort pre-launch experiments - including sample size, experimental design files and a cognitive-interview pre-test protocol. Use after intake-router or when asked to design/size a study.
---

# Quant Designer

Input: a brief in `memory/briefs/` (or the user's description). Read it fully first.

## Steps
1. **Confirm the design inputs** from the brief: decision rule, target population, method. If the
   brief has no decision rule, write one and flag it.
2. **Measures.** For each construct, look in `memory/scales/` first. Use validated scales verbatim
   (wording, anchors, order); note the file path. New items: mark `UNVALIDATED`, write 2–3 more than
   needed, avoid double-barrelled/leading wording, include one reverse-keyed item per construct.
   Add an instructed attention check and a speeder benchmark (expected median minutes).
3. **Method-specific design**
   - *Conjoint*: write attributes to `data/processed/<slug>_attributes.json`
     (`{"attr": ["ref level", "level2", ...]}`; first level = reference; ≤ 6 attributes, ≤ 5 levels;
     check for impossible combinations and list them as prohibitions). Then:
     `uv run python scripts/conjoint.py design <attrs.json> --versions 10 --tasks 10 --alts 3 --out data/processed/<slug>_design.csv`
     Require `tasks_with_duplicate_alts == 0` and pairwise balance CV < 0.2; otherwise re-run with a new `--seed`.
     Size with `scripts/power.py conjoint`.
   - *MaxDiff*: ≤ 30 items, 4–5 per task. Size with `scripts/power.py maxdiff` (watch the fatigue warning).
   - *Experiment / cohorts*: define unit of randomisation, primary metric, guardrail metrics, matching
     variables (tenure, portfolio size, region, activity), and run `scripts/power.py proportions|means`.
   - *Segmentation survey*: size with `scripts/power.py segments`.
4. **Localisation** (global crypto audiences): list markets, flag terms that don't translate (e.g.
   "staking", "self-custody", APY vs APR), require back-translation for validated scales, and note
   regulatory wording constraints per market (yield/interest language).
5. **Cognitive-interview pre-test protocol** (5–8 people per key market): think-aloud on each new item,
   probes ("What does *<term>* mean to you?", "How did you pick your answer?"), and a fix log table.
6. **Output**: append a `## Design` section to the brief with the instrument outline, design file paths,
   sample per market and fielding plan; set status to `designed`. Suggest `/data-validator` for after fielding.

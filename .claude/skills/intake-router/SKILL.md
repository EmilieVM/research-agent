---
name: intake-router
description: Turn a raw product, design or GTM request (Slack message, ticket, email, "should we research X?") into a structured Research Brief with hypotheses, recommended method, sample size and a pre-registered decision rule. Use at the start of any new research ask.
---

# Intake Router

Input: the stakeholder's request, pasted or described. If it's vague, ask at most 3 clarifying
questions (decision owner, deadline, what they'd do differently with each answer) – then proceed with
stated assumptions rather than stalling.

## Steps
1. **Extract the decision.** What will someone build, ship, price or kill based on this? Who owns it?
   By when? If there is no decision, say so: the request may not need research.
2. **Score the bet** (1–5 each, with one line of reasoning per score):
   - *Uncertainty* – how unsure are we about user response? (5 = no data, contested)
   - *Impact* – cost of being wrong (eng effort, revenue, trust/regulatory risk)
   - *Reversibility* – 5 = hard to undo (pricing, custody model, launches in new countries)
   Routing: uncertainty ≤ 2 **and** impact ≤ 2 → "ship and monitor, no study". Otherwise continue.
3. **Search memory.** Grep `memory/briefs/`, `memory/scales/`, `memory/heuristics/` and
   `memory/2ndbrain/` (if present) for related studies, reusable scales, and prior effect sizes.
   List what you found with paths. Prior results may answer the question outright.
4. **Pick the method** (explain why, and why not the runner-up):
   | Question shape | Method |
   |---|---|
   | Which of many features/messages matter most? | MaxDiff |
   | Trade-offs between attributes, incl. price/APY/lock-up | Choice-based conjoint |
   | Does feature X change behaviour? | Matched-cohort or A/B pre-launch experiment |
   | Who are our users / how do attitudes differ? | Survey + segmentation |
   | Can people use it / do they understand it? | Usability / cognitive interviews (qual) |
   | Is the AI feature's output good and trusted? | Human eval + trust survey (`/ai-evaluator`) |
5. **Size it.** Run `uv run python scripts/power.py <mode> ...` with a realistic effect size (from memory
   if available) and `--dropout 0.15` for crypto panels. Quote the script output.
6. **Write the decision rule** before any data: "If <metric> <threshold> in <population>, then <action>;
   otherwise <other action>." Include the minimum detectable effect so nobody over-reads a null.
7. **Write the brief** using the template below and save it to
   `memory/briefs/YYYY-MM-DD-<slug>.md`. Then suggest `/quant-designer` as the next step.

## Brief template
```markdown
# <Title>
- Date / Requester / Decision owner / Deadline:
- Decision being made:
- Bet score: uncertainty _/5, impact _/5, reversibility _/5 → <study | no study>
## Hypotheses
H1 … (each falsifiable, with direction)
## Prior evidence (from memory)
## Method & why
## Population, sample & power   (paste power.py output)
## Measures   (reused scales with paths; new items flagged as unvalidated)
## Decision rule   (pre-registered)
## Risks   (sampling, fraud, translation, regulatory, timing)
## Status: proposed
```

# Willingness to pay for auto-compounding on the yield product
- Date / Requester / Decision owner / Deadline: 2026-11-09 / PM, yield product / **ASSUMED: requesting PM, confirm** / **TBD, confirm**
- Decision being made: Whether to build auto-compounding, and if so how to charge for it: (a) build it as a paid feature with a performance fee on compounded rewards, (b) build it free as a retention/AUM driver, or (c) don't build it.
- Bet score: uncertainty 4/5, impact 3/5, reversibility 4/5 → **study**
  - Uncertainty 4: there's no prior study in memory, and users' stated interest in "set and forget" often doesn't hold up once a visible fee is attached.
  - Impact 3: moderate eng effort (keeper/automation infra, gas cost), plus revenue upside or fee backlash on a core product.
  - Reversibility 4: once a fee is live, cutting it is easy but raising it later costs trust. In some markets a fee on yield can also trigger disclosure or regulatory review.

## Hypotheses
- H1: When auto-compounding is offered at a 0% fee, it is preferred over manual claiming (positive part-worth vs. manual).
- H2: Willingness to pay for auto-compounding, expressed as a performance fee on rewards, is > 0 and at least as large as the lowest fee level tested (5% of rewards).
- H3: WTP is higher among larger-balance users (≥ USD 10k in yield products) than among smaller-balance users, because compounding gains scale with balance and manual claiming costs gas.
- H4: Showing the net-APY uplift explicitly raises preference for auto-compounding at a given fee. This is exploratory and only tested if /quant-designer adds a framing arm.

## Prior evidence (from memory)
- `memory/briefs/`: only `_TEMPLATE.md`. There are no prior pricing, yield or WTP studies, and no prior effect sizes.
- `memory/scales/`: only `_TEMPLATE.md`. There are no validated scales. Any attitude items will be **new and unvalidated**.
- `memory/heuristics/decision-rules.md`: use conjoint WTP only with a numeric price attribute, and report part-worths with SEs. The fee attribute is designed to meet this.
- `memory/heuristics/crypto-fraud-checks.md`: expect 5–20% exclusions, and prefer verified panels or wallet-signed participation. This is why 15% dropout is used below.
- `memory/2ndbrain`: the symlink points to `/Users/user/2ndbrainnvm`, which **does not exist** (broken link), so personal notes were not searched.

## Method & why
**Choice-based conjoint (CBC)** with a numeric fee attribute, so WTP can be estimated directly.
- Why: the question is a trade-off. Auto-compounding raises effective APY but costs a fee, and users weigh it against headline APY and lock-up. CBC makes respondents give something up for the feature. Stated-interest questions don't, and they inflate WTP.
- Runner-up: a **pre-launch A/B or fake-door test** (offer an auto-compound toggle with a fee and measure opt-in). It measures real behaviour, but it tests only one or two price points, needs eng work, and exposes users to a fee we may never launch. It is a good **follow-up to validate** the price point CBC picks.
- Not MaxDiff: this is one feature priced against attributes, not a ranking of many features.
- Draft attributes (max 4 levels, which /quant-designer will finalise):
  - Compounding: manual claim / auto weekly / auto daily
  - Performance fee on rewards: 0% / 5% / 10% / 15%
  - Headline APY: 3 levels around the current product rate
  - Lock-up / withdrawal: instant / 7-day / 30-day

## Population, sample & power
Population: active users of the yield product in the last 90 days, plus users who hold eligible assets but don't use the yield product. Recruit from the product (verified accounts), not open panels. Quota: two balance subgroups (< USD 10k vs. ≥ USD 10k).

`power.py conjoint --tasks 10 --alts 3 --max-levels 4 --subgroups 2 --dropout 0.15`
```json
{"mode": "conjoint", "alpha": 0.05, "power": 0.8, "total_n": 400, "total_n_with_dropout": 471,
 "rule": "Orme: n*t*a/c >= 500 (1000 for subgroups), floor 200 per group for stable estimates"}
```
Without the subgroup comparison: `total_n` 200, 236 with dropout.

`power.py mde --n 200 --kind proportions --p1 0.40` (choice share between balance subgroups):
```json
{"mode": "mde", "alpha": 0.05, "power": 0.8, "n_per_group": 200, "min_detectable_effect": 0.28,
 "interpretation": "from baseline 40% you can detect a lift to ~53.9%"}
```
→ **Field n = 471 (≈ 236 per balance subgroup) to land ≥ 400 clean.** Subgroup differences in share smaller than ~14 points (40% → 54%) are not detectable, so don't read a null there as "no difference". (`min_detectable_effect` 0.28 is on the effect-size scale; the interpretation line gives the share terms.)

## Measures
- CBC: 10 tasks × 3 alternatives + "none" option. One holdout task for validation.
- Current behaviour: balance band, how often they claim or compound manually, chains used. These are self-reported, so link to telemetry if consent allows.
- Understanding check: one comprehension item on what a "% of rewards" fee means. **New, unvalidated.**
- Trust in automated execution (2–3 items). **New, unvalidated**, since memory has no validated trust scale. Run through `/segmentation-engine` for alpha, and save it to `memory/scales/` if alpha ≥ .70.
- Quality: instructed attention check, completion time, wallet/account dedupe (per `crypto-fraud-checks.md`).

## Decision rule (pre-registered)
WTP is estimated from the conjoint as the fee (% of rewards) at which auto-compounding (best auto level) is preferred to manual at equal APY and lock-up. It is reported with a 95% CI from `conjoint.py`.
- **If the WTP CI lower bound ≥ 10% fee** among all clean respondents → **build auto-compounding as a paid feature**, priced at or below the point estimate. Validate with a 2-arm fake-door/A-B before full launch.
- **If WTP > 0 but the CI lower bound is < 10%**, or WTP is ≥ 10% only in the ≥ USD 10k subgroup → **build it, but free or as a tier perk** (e.g. no fee above a balance threshold). Treat the value as retention/AUM, not fee revenue.
- **If the auto-compounding part-worth is not significantly > manual at 0% fee** (H1 fails) → **don't build**. Revisit only if telemetry shows heavy manual compounding.
- Model-quality gate: if McFadden R² < .1 or holdout hit rate < 60%, results are **tentative** and the decision goes back to the PM with that caveat. No pricing decision is made on them.
- The 10% threshold is a placeholder for **the fee that covers keeper/gas costs plus margin**. Finance or the PM must confirm it **before fielding**. After fielding it can't be changed without saying so.

## Risks
- **Sampling:** in-product recruitment skews towards engaged users and overstates interest. Weight to the active-user base by balance band, and report unweighted results too.
- **Fraud:** token incentives attract farms. Use verified accounts and dedupe on account/wallet. Run `fraud_flags.py` first. More than 25% exclusions means a bad source.
- **Comprehension:** "% of rewards" fees are often misread as "% of balance". Pre-test in cognitive interviews, and exclude or segment respondents who fail the comprehension check.
- **Hypothetical bias:** stated WTP runs above real WTP. Treat the CBC estimate as an upper bound, and confirm with a behavioural test.
- **Regulatory:** fees on yield, and on automatic re-staking, may carry disclosure obligations in some markets. Check with legal before showing fee levels to users in regulated markets.
- **Timing:** APY swings change how valuable compounding feels. Hold the APY attribute relative to the current rate and note the market conditions at fielding.

## Design
## Data quality
## Results
## Decision taken & what we learned
## Status: proposed

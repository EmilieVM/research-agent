# Crypto survey fraud & quality heuristics

Used by `/data-validator` and `scripts/fraud_flags.py`. Update this when you learn something new.

## Hard flags (exclude on one)
- Failed instructed attention check.
- Same wallet / account ID behind several respondent IDs (incentive farming).
- Claims to hold an asset but the linked wallet shows none (only if wallet ownership was verified,
  e.g. signed message – otherwise treat as soft).

## Soft flags (exclude on two or more)
- Speeder: < 1/3 of median completion time.
- Straight-lining across a Likert grid (zero variance).
- Duplicate or near-duplicate open-ends (copy-paste farms, airdrop-hunter templates, LLM boilerplate).
- Multivariate outlier on numeric answers.

## Expectations
- 5–20% exclusion is normal for crypto panels; > 25% means a bad source or bad thresholds.
- Incentives paid in tokens attract farms – prefer verified panels or wallet-signed participation.
- Check exclusion rate by source and market; report vendors with outsized rates.
- Never put wallet addresses next to survey answers in any shared file; hash with RESEARCH_SALT.

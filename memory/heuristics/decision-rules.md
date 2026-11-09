# Decision-rule conventions

- Write the rule before fielding: "If <metric> <threshold> in <population>, then <action>; else <action>."
- Always state the minimum detectable effect (from `scripts/power.py mde`) next to the rule, so a
  null result isn't read as "no effect".
- MaxDiff: act on items whose share of preference CI clears the next item's, not on raw rank.
- Conjoint: report importance and part-worths with SEs; use willingness-to-pay only with a numeric price attribute.
- Segments: a segment must be ≥ 5% of the market and stable (ARI ≥ .6) before it gets its own roadmap item.
- AI eval launch gate: IRR ≥ .80 on every dimension used in the gate, and critical-error rate CI upper bound below the agreed threshold.

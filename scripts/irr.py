"""Inter-rater reliability for human evaluation of AI outputs.

Usage:
  uv run python scripts/irr.py ratings.csv                    # Krippendorff's alpha (default)
  uv run python scripts/irr.py ratings.csv --method fleiss
  uv run python scripts/irr.py ratings.csv --method weighted --raters rater_1,rater_2

CSV: first column = item id, remaining columns = one per rater. Blank = not rated.

Methods
  kripp     Krippendorff's alpha. Any number of raters, tolerates missing. Best default.
  fleiss    Fleiss' kappa. 3+ raters, nominal categories, drops items with any missing.
  cohen     Cohen's kappa. Exactly 2 raters, nominal.
  weighted  Quadratic-weighted Cohen's kappa. 2 raters, ordinal (e.g. 1-5 rubric).

Rule of thumb: >= 0.80 good, 0.67-0.80 tentative, < 0.67 fix the rubric / retrain raters.
Also reports pairwise agreement so you can spot a drifting rater.
"""
import argparse
import itertools
import json

import krippendorff
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa


def verdict(v):
    return "good" if v >= 0.8 else "tentative" if v >= 0.667 else "poor - revise rubric or retrain raters"


def compute(df, method, level="ordinal"):
    if method in ("cohen", "weighted"):
        if df.shape[1] != 2:
            raise SystemExit("cohen/weighted need exactly 2 raters (use --raters a,b)")
        d = df.dropna()
        return cohen_kappa_score(d.iloc[:, 0], d.iloc[:, 1], weights="quadratic" if method == "weighted" else None), len(d)
    if method == "fleiss":
        d = df.dropna()
        table, _ = aggregate_raters(d.astype(int).to_numpy())
        return fleiss_kappa(table), len(d)
    data = df.T.to_numpy(dtype=float)  # raters x items
    return krippendorff.alpha(reliability_data=data, level_of_measurement=level), int((~np.isnan(data)).sum(0).__ge__(2).sum())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv")
    p.add_argument("--method", choices=["kripp", "fleiss", "cohen", "weighted"], default="kripp")
    p.add_argument("--level", choices=["nominal", "ordinal", "interval"], default="ordinal",
                   help="measurement level for Krippendorff's alpha")
    p.add_argument("--raters", help="comma-separated rater columns to use (default: all)")
    a = p.parse_args()

    df = pd.read_csv(a.csv, index_col=0)
    if a.raters:
        df = df[a.raters.split(",")]
    value, n_used = compute(df, a.method, a.level)

    pairs = {}
    for r1, r2 in itertools.combinations(df.columns, 2):
        d = df[[r1, r2]].dropna()
        pairs[f"{r1}~{r2}"] = {"exact_agreement": round(float((d[r1] == d[r2]).mean()), 3),
                               "weighted_kappa": round(float(cohen_kappa_score(d[r1], d[r2], weights="quadratic")), 3)}
    worst_rater = None
    if df.shape[1] > 2:
        mean_k = {r: np.mean([v["weighted_kappa"] for k, v in pairs.items() if r in k.split("~")]) for r in df.columns}
        worst_rater = min(mean_k, key=mean_k.get)

    print(json.dumps({"method": a.method, "value": round(float(value), 3), "verdict": verdict(value),
                      "n_items": len(df), "n_items_used": n_used, "n_raters": df.shape[1],
                      "pairwise": pairs, "lowest_agreement_rater": worst_rater}, indent=2))


if __name__ == "__main__":
    main()

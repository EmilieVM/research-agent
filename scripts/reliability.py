"""Scale reliability and structure: Cronbach's alpha, McDonald's omega, item diagnostics, EFA.

Usage:
  uv run python scripts/reliability.py survey.csv --items trust_1,trust_2,trust_3,trust_4,trust_5,trust_6 --reverse trust_4 --scale-max 7
  uv run python scripts/reliability.py survey.csv --prefix trust_ --reverse trust_4 --efa 1
  uv run python scripts/reliability.py survey.csv --prefix trust_,sec_ --efa 2

Outputs JSON: alpha (+95% CI), omega, alpha-if-item-deleted, corrected item-total r,
and with --efa: KMO, Bartlett test, rotated loadings, and items with weak/cross loadings.

Thresholds used in flags: alpha >= .70 acceptable (>= .80 good); item-total r < .30 weak;
loading < .40 weak; cross-loading >= .30 on a second factor.
"""
import argparse
import json
import warnings

import numpy as np
import pandas as pd
import pingouin as pg
from factor_analyzer import FactorAnalyzer
from factor_analyzer.factor_analyzer import calculate_bartlett_sphericity, calculate_kmo

warnings.filterwarnings("ignore", category=FutureWarning)  # factor_analyzer vs newer sklearn


def omega_total(items):
    fa = FactorAnalyzer(n_factors=1, rotation=None, method="minres").fit(items)
    lam = fa.loadings_[:, 0]
    if lam.sum() < 0:
        lam = -lam
    uniq = fa.get_uniquenesses()
    return float(lam.sum() ** 2 / (lam.sum() ** 2 + uniq.sum()))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--items", help="comma-separated item columns")
    g.add_argument("--prefix", help="comma-separated column prefixes, e.g. trust_,sec_")
    p.add_argument("--reverse", default="", help="comma-separated reverse-keyed items")
    p.add_argument("--scale-min", type=float, default=1)
    p.add_argument("--scale-max", type=float, default=7)
    p.add_argument("--efa", type=int, default=0, help="number of factors for exploratory factor analysis")
    p.add_argument("--exclude-flagged", help="CSV from fraud_flags.py; drop rows where exclude==1")
    a = p.parse_args()

    df = pd.read_csv(a.csv)
    if a.exclude_flagged:
        fl = pd.read_csv(a.exclude_flagged)
        df = df[~df.index.isin(fl.index[fl["exclude"] == 1])]
    cols = a.items.split(",") if a.items else [c for c in df.columns if c.startswith(tuple(a.prefix.split(",")))]
    items = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    for r in filter(None, a.reverse.split(",")):
        items[r] = a.scale_max + a.scale_min - items[r]

    alpha, ci = pg.cronbach_alpha(data=items)
    total = items.sum(axis=1)
    diag = {}
    for c in cols:
        rest = total - items[c]
        diag[c] = {"mean": round(items[c].mean(), 2), "sd": round(items[c].std(), 2),
                   "corrected_item_total_r": round(float(np.corrcoef(items[c], rest)[0, 1]), 3),
                   "alpha_if_deleted": round(float(pg.cronbach_alpha(data=items.drop(columns=c))[0]), 3)}
    flags = [f"{c}: weak item-total r" for c, d in diag.items() if d["corrected_item_total_r"] < 0.30]
    flags += [f"{c}: alpha rises if removed" for c, d in diag.items() if d["alpha_if_deleted"] > alpha + 0.02]
    if alpha < 0.70:
        flags.append("alpha below .70 - scale not reliable enough for decisions")

    out = {"n": len(items), "items": cols, "reversed": [r for r in a.reverse.split(",") if r],
           "cronbach_alpha": round(float(alpha), 3), "alpha_95ci": [round(float(x), 3) for x in ci],
           "omega_total": round(omega_total(items), 3), "item_diagnostics": diag}

    if a.efa:
        chi2, pval = calculate_bartlett_sphericity(items)
        _, kmo = calculate_kmo(items)
        fa = FactorAnalyzer(n_factors=a.efa, rotation="oblimin" if a.efa > 1 else None, method="minres").fit(items)
        L = pd.DataFrame(fa.loadings_, index=cols, columns=[f"F{i + 1}" for i in range(a.efa)]).round(3)
        _, prop, cum = fa.get_factor_variance()
        absL = L.abs()
        for c in cols:
            srt = absL.loc[c].sort_values(ascending=False)
            if srt.iloc[0] < 0.40:
                flags.append(f"{c}: weak loading ({srt.iloc[0]:.2f})")
            if a.efa > 1 and srt.iloc[1] >= 0.30:
                flags.append(f"{c}: cross-loads ({srt.index[0]} {srt.iloc[0]:.2f}, {srt.index[1]} {srt.iloc[1]:.2f})")
        if kmo < 0.6:
            flags.append(f"KMO {kmo:.2f} < .60 - data not suitable for factor analysis")
        out["efa"] = {"kmo": round(float(kmo), 3), "bartlett_chi2": round(float(chi2), 1), "bartlett_p": float(pval),
                      "eigenvalues": [round(float(e), 3) for e in fa.get_eigenvalues()[0]],
                      "variance_explained": [round(float(x), 3) for x in prop],
                      "cumulative_variance": round(float(cum[-1]), 3), "loadings": L.to_dict(orient="index")}
    out["flags"] = flags
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

"""Behavioural / psychographic segmentation with model selection and stability checks.

Usage:
  uv run python scripts/segment.py survey.csv --cols trades_per_month,portfolio_usd_log10,defi_protocols_used,trust_mean,sec_mean \
      --k-min 2 --k-max 6 --out data/processed/segments.csv
  uv run python scripts/segment.py survey.csv --prefix-means trust_,sec_ --reverse trust_4 --cols trades_per_month,... \
      --exclude-flagged data/processed/survey_flags.csv

Steps: (optional) build scale means -> log-transform skewed cols -> standardise -> fit Gaussian Mixture
(or k-means) for each k -> drop solutions with a segment < --min-share -> pick the SIMPLEST k whose BIC
is within --bic-tolerance of the best (GMM) or best silhouette (k-means) -> bootstrap stability
(adjusted Rand index of 80% refits vs full fit) -> profile segments in original units.

Read the output critically: stability ARI < 0.6 means the segments are not reproducible; a segment
under 5% of the sample is usually not actionable. Names for segments are for a human to choose.
"""
import argparse
import json

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler


def fit(X, k, method, seed, cov="tied"):
    if method == "gmm":
        m = GaussianMixture(k, covariance_type=cov, n_init=5, random_state=seed).fit(X)
    else:
        m = KMeans(k, n_init=10, random_state=seed).fit(X)
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv")
    p.add_argument("--cols", required=True, help="comma-separated clustering variables")
    p.add_argument("--prefix-means", help="comma-separated item prefixes; adds <prefix>mean columns, e.g. trust_mean")
    p.add_argument("--reverse", default="", help="reverse-keyed items for --prefix-means")
    p.add_argument("--scale-max", type=float, default=7)
    p.add_argument("--method", choices=["gmm", "kmeans"], default="gmm")
    p.add_argument("--k-min", type=int, default=2)
    p.add_argument("--k-max", type=int, default=6)
    p.add_argument("--k", type=int, help="force a number of segments")
    p.add_argument("--covariance", choices=["tied", "full", "diag", "spherical"], default="tied",
                   help="GMM covariance. 'tied' is robust when inputs include counts/zeros; 'full' can overfit them")
    p.add_argument("--min-share", type=float, default=0.05, help="reject solutions with a segment smaller than this")
    p.add_argument("--bic-tolerance", type=float, default=10,
                   help="pick the smallest k whose BIC is within this many points of the best (parsimony)")
    p.add_argument("--log", default="auto", help="'auto' logs cols with skew > 1, or comma list, or 'none'")
    p.add_argument("--boot", type=int, default=20)
    p.add_argument("--exclude-flagged")
    p.add_argument("--out")
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()

    df = pd.read_csv(a.csv)
    if a.exclude_flagged:
        fl = pd.read_csv(a.exclude_flagged)
        df = df[(fl["exclude"] == 0).to_numpy()].reset_index(drop=True)
    rev = set(filter(None, a.reverse.split(",")))
    for pre in filter(None, (a.prefix_means or "").split(",")):
        items = [c for c in df.columns if c.startswith(pre) and not c.endswith("mean")]
        vals = df[items].copy()
        for r in rev & set(items):
            vals[r] = a.scale_max + 1 - vals[r]
        df[pre + "mean"] = vals.mean(axis=1)

    cols = a.cols.split(",")
    raw = df[cols].apply(pd.to_numeric, errors="coerce")
    keep = raw.notna().all(axis=1)
    raw = raw[keep]
    X = raw.copy()
    logged = [c for c in cols if X[c].skew() > 1 and X[c].min() >= 0] if a.log == "auto" else \
        [] if a.log == "none" else a.log.split(",")
    for c in logged:
        X[c] = np.log1p(X[c])
    Xs = StandardScaler().fit_transform(X)

    ks = [a.k] if a.k else list(range(a.k_min, a.k_max + 1))
    fit_stats = {}
    for k in ks:
        m = fit(Xs, k, a.method, a.seed, a.covariance)
        lab = m.predict(Xs)
        fit_stats[k] = {"silhouette": round(float(silhouette_score(Xs, lab)), 3),
                        "smallest_share": round(float(np.bincount(lab, minlength=k).min() / len(lab)), 3)}
        if a.method == "gmm":
            fit_stats[k]["bic"] = round(float(m.bic(Xs)), 1)
    if a.k:
        best = a.k
    else:
        ok = [k for k in fit_stats if fit_stats[k]["smallest_share"] >= a.min_share] or list(fit_stats)
        if a.method == "gmm":
            top = min(fit_stats[k]["bic"] for k in ok)
            best = min(k for k in ok if fit_stats[k]["bic"] <= top + a.bic_tolerance)
        else:
            best = max(ok, key=lambda k: fit_stats[k]["silhouette"])

    model = fit(Xs, best, a.method, a.seed, a.covariance)
    labels = model.predict(Xs)
    rng = np.random.default_rng(a.seed)
    aris = []
    for b in range(a.boot):
        idx = rng.choice(len(Xs), int(0.8 * len(Xs)), replace=False)
        mb = fit(Xs[idx], best, a.method, a.seed + b + 1, a.covariance)
        aris.append(adjusted_rand_score(labels, mb.predict(Xs)))
    stability = float(np.mean(aris))

    # order segments by size for readable output
    order = pd.Series(labels).value_counts().index.tolist()
    remap = {old: new + 1 for new, old in enumerate(order)}
    seg = pd.Series(labels).map(remap).to_numpy()
    prof = raw.assign(segment=seg).groupby("segment")
    profiles = {}
    overall = raw.mean()
    for s, g in prof:
        z = ((g.mean() - overall) / raw.std()).round(2)
        profiles[int(s)] = {"n": len(g), "share": round(len(g) / len(raw), 3),
                            "means": g.mean().round(2).to_dict(),
                            "distinctive (z vs overall)": z[z.abs() >= 0.5].sort_values(key=abs, ascending=False).to_dict()}

    flags = []
    if stability < 0.6:
        flags.append(f"stability ARI {stability:.2f} < 0.60 - segments not reproducible")
    flags += [f"segment {s} is {v['share']:.0%} of sample - likely too small to act on" for s, v in profiles.items() if v["share"] < 0.05]

    out = {"method": a.method, "n": int(len(raw)), "variables": cols, "log_transformed": logged,
           "fit_by_k": fit_stats, "chosen_k": best, "stability_ari": round(stability, 3),
           "profiles": profiles, "flags": flags}
    if "true_segment" in df:
        out["fake_data_check_ari_vs_truth"] = round(float(adjusted_rand_score(df.loc[keep, "true_segment"], seg)), 3)
    if a.out:
        res = df.loc[keep].copy()
        res["segment"] = seg
        id_col = "respondent_id" if "respondent_id" in res else res.columns[0]
        res[[id_col, "segment"]].to_csv(a.out, index=False)
        out["output"] = a.out
    print(json.dumps(out, indent=2, default=float))


if __name__ == "__main__":
    main()

"""Choice-based conjoint and MaxDiff: design generation and estimation.

Usage:
  # 1. Make a design from an attributes file ({"apy": ["3%","6%","9%"], "lockup": [...], ...})
  uv run python scripts/conjoint.py design attrs.json --versions 10 --tasks 10 --alts 3 --out design.csv

  # 2. Estimate part-worths from responses (long format: resp_id, task, alt, <attributes>, chosen)
  uv run python scripts/conjoint.py estimate responses.csv --attributes attrs.json [--price-col price]

  # 3. MaxDiff scores (long format: resp_id, task, item, best, worst)
  uv run python scripts/conjoint.py maxdiff maxdiff.csv

design   Random design with level balance (each level appears ~equally often within each attribute),
         minimal overlap (no identical alternatives in a task), and a D-efficiency-style balance report.
estimate Aggregate multinomial logit (xlogit). Effects are dummy-coded vs the FIRST level in attrs.json.
         Reports part-worths, SE, p-values, attribute importance, and willingness-to-pay if --price-col
         is a numeric price attribute. Aggregate MNL hides heterogeneity: for individual-level
         utilities use hierarchical Bayes (e.g. Sawtooth / Conjointly) and note that in the brief.
maxdiff  Best-minus-worst count scores per item, plus MNL-on-best logit scores rescaled to a
         0-100 share-of-preference.
"""
import argparse
import json
import itertools

import numpy as np
import pandas as pd


def design(a):
    attrs = json.loads(open(a.attrs).read())
    rng = np.random.default_rng(a.seed)
    rows = []
    for v in range(1, a.versions + 1):
        n_cells = a.tasks * a.alts
        cols = {}
        for name, levels in attrs.items():
            reps = int(np.ceil(n_cells / len(levels)))
            seq = np.array(levels * reps)[:n_cells]
            rng.shuffle(seq)
            cols[name] = seq.reshape(a.tasks, a.alts)
        for t in range(a.tasks):
            # repair identical alternatives within a task by swapping with another task
            for _ in range(50):
                profs = [tuple(cols[n][t, j] for n in attrs) for j in range(a.alts)]
                if len(set(profs)) == a.alts:
                    break
                n = rng.choice(list(attrs))
                j, t2, j2 = rng.integers(a.alts), rng.integers(a.tasks), rng.integers(a.alts)
                cols[n][t, j], cols[n][t2, j2] = cols[n][t2, j2], cols[n][t, j]
            for j in range(a.alts):
                rows.append({"version": v, "task": t + 1, "alt": j + 1, **{n: cols[n][t, j] for n in attrs}})
    d = pd.DataFrame(rows)
    d.to_csv(a.out, index=False)
    balance = {n: d[n].value_counts().to_dict() for n in attrs}
    dupes = int(d.groupby(["version", "task"]).apply(lambda g: g[list(attrs)].duplicated().any()).sum())
    pair_cv = {}
    for n1, n2 in itertools.combinations(attrs, 2):
        c = pd.crosstab(d[n1], d[n2]).to_numpy().ravel()
        pair_cv[f"{n1}x{n2}"] = round(float(c.std() / c.mean()), 3)
    print(json.dumps({"rows": len(d), "versions": a.versions, "tasks": a.tasks, "alts": a.alts,
                      "level_counts": balance, "tasks_with_duplicate_alts": dupes,
                      "pairwise_balance_cv (lower=better, <0.2 good)": pair_cv, "output": a.out}, indent=2, default=int))


def estimate(a):
    from xlogit import MultinomialLogit
    attrs = json.loads(open(a.attributes).read())
    df = pd.read_csv(a.csv)
    df["cs_id"] = df[a.resp_col].astype(str) + "_" + df[a.task_col].astype(str)
    df = df.sort_values(["cs_id", a.alt_col]).reset_index(drop=True)
    varnames = []
    price_numeric = None
    for name, levels in attrs.items():
        if name == a.price_col:
            df[name] = pd.to_numeric(df[name].astype(str).str.replace(r"[^0-9.\-]", "", regex=True))
            price_numeric = name
            varnames.append(name)
            continue
        for lv in levels[1:]:
            col = f"{name}[{lv}]"
            df[col] = (df[name].astype(str) == str(lv)).astype(float)
            varnames.append(col)
    m = MultinomialLogit()
    m.fit(X=df[varnames], y=df[a.choice_col], varnames=varnames, alts=df[a.alt_col], ids=df["cs_id"], verbose=0)
    coef = dict(zip(m.coeff_names, m.coeff_))
    se = dict(zip(m.coeff_names, m.stderr))
    pv = dict(zip(m.coeff_names, m.pvalues))

    partworths, ranges = {}, {}
    for name, levels in attrs.items():
        if name == price_numeric:
            pr = [float(str(x).replace("$", "").replace(",", "")) for x in levels]
            ranges[name] = abs(coef[name]) * (max(pr) - min(pr))
            partworths[name] = {"per_unit": round(float(coef[name]), 4), "se": round(float(se[name]), 4)}
            continue
        pw = {levels[0]: {"utility": 0.0, "note": "reference"}}
        for lv in levels[1:]:
            k = f"{name}[{lv}]"
            pw[lv] = {"utility": round(float(coef[k]), 3), "se": round(float(se[k]), 3), "p": round(float(pv[k]), 4)}
        partworths[name] = pw
        u = [v["utility"] for v in pw.values()]
        ranges[name] = max(u) - min(u)
    tot = sum(ranges.values())
    importance = {k: round(100 * v / tot, 1) for k, v in sorted(ranges.items(), key=lambda x: -x[1])}
    out = {"model": "aggregate MNL", "n_respondents": int(df[a.resp_col].nunique()), "n_tasks": int(df["cs_id"].nunique()),
           "log_likelihood": round(float(m.loglikelihood), 2), "partworths": partworths, "importance_pct": importance}
    n_alts = df.groupby("cs_id").size().mean()
    ll0 = df["cs_id"].nunique() * np.log(1 / n_alts)
    out["mcfadden_r2"] = round(float(1 - m.loglikelihood / ll0), 3)
    if price_numeric and coef[price_numeric] < 0:
        b = -coef[price_numeric]
        out["willingness_to_pay"] = {f"{n}[{lv}]": round(float(coef[f'{n}[{lv}]'] / b), 2)
                                     for n, lvs in attrs.items() if n != price_numeric for lv in lvs[1:]}
    print(json.dumps(out, indent=2))


def maxdiff(a):
    df = pd.read_csv(a.csv)
    g = df.groupby(a.item_col)
    counts = pd.DataFrame({"shown": g.size(), "best": g[a.best_col].sum(), "worst": g[a.worst_col].sum()})
    counts["bw_score"] = ((counts["best"] - counts["worst"]) / counts["shown"]).round(3)
    # conditional logit on 'best' choices: share of preference
    from xlogit import MultinomialLogit
    items = sorted(df[a.item_col].unique())
    ref = counts["bw_score"].idxmin()
    df["cs_id"] = df[a.resp_col].astype(str) + "_" + df[a.task_col].astype(str)
    df = df.sort_values("cs_id").reset_index(drop=True)
    df["alt"] = df.groupby("cs_id").cumcount()
    vn = []
    for it in items:
        if it == ref:
            continue
        c = f"item[{it}]"
        df[c] = (df[a.item_col] == it).astype(float)
        vn.append(c)
    m = MultinomialLogit()
    m.fit(X=df[vn], y=df[a.best_col], varnames=vn, alts=df["alt"], ids=df["cs_id"], verbose=0)
    util = {it: 0.0 for it in items}
    util.update({n[5:-1]: float(c) for n, c in zip(m.coeff_names, m.coeff_)})
    e = np.exp(pd.Series(util))
    counts["logit_utility"] = pd.Series(util).round(3)
    counts["share_of_preference"] = (100 * e / e.sum()).round(1)
    counts = counts.sort_values("share_of_preference", ascending=False)
    print(json.dumps({"n_respondents": int(df[a.resp_col].nunique()), "reference_item": ref,
                      "ranking": counts.index.tolist(), "scores": counts.to_dict(orient="index")}, indent=2, default=float))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("design")
    d.add_argument("attrs")
    d.add_argument("--versions", type=int, default=10)
    d.add_argument("--tasks", type=int, default=10)
    d.add_argument("--alts", type=int, default=3)
    d.add_argument("--seed", type=int, default=0)
    d.add_argument("--out", required=True)
    e = sub.add_parser("estimate")
    e.add_argument("csv")
    e.add_argument("--attributes", required=True)
    e.add_argument("--price-col")
    m = sub.add_parser("maxdiff")
    m.add_argument("csv")
    m.add_argument("--item-col", default="item")
    m.add_argument("--best-col", default="best")
    m.add_argument("--worst-col", default="worst")
    for s in (e, m):
        s.add_argument("--resp-col", default="resp_id")
        s.add_argument("--task-col", default="task")
    e.add_argument("--alt-col", default="alt")
    e.add_argument("--choice-col", default="chosen")
    a = p.parse_args()
    {"design": design, "estimate": estimate, "maxdiff": maxdiff}[a.cmd](a)


if __name__ == "__main__":
    main()

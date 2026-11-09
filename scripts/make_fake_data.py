"""Generate realistic FAKE datasets for trying the pipeline end to end.

Usage: uv run python scripts/make_fake_data.py [--out examples] [--seed 7]

Writes:
  survey.csv          300 respondents, trust + security scales (1-7), behaviour, ~10% planted bots
  ratings.csv         60 AI answers rated 1-5 by 4 raters (some missing)
  conjoint_attributes.json + conjoint_responses.csv   choice-based conjoint with known part-worths
  maxdiff.csv         MaxDiff best/worst choices over 8 features with known ranking

Nothing here is real. Known "true" values are printed so you can check the scripts recover them.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

TRUE_CONJOINT = {  # part-worths vs the first (reference) level of each attribute
    "apy": {"3%": 0.0, "6%": 0.9, "9%": 1.5},
    "lockup": {"none": 0.0, "30 days": -0.6, "90 days": -1.3},
    "custody": {"self-custody": 0.0, "exchange": -0.4},
    "insurance": {"no": 0.0, "yes": 0.7},
}
MAXDIFF_ITEMS = ["auto-compounding", "instant withdrawal", "insurance cover", "tax reports",
                 "price alerts", "staking rewards", "hardware wallet support", "copy trading"]
MAXDIFF_TRUE = [1.2, 1.5, 1.0, 0.2, -0.3, 0.6, 0.0, -0.8]


def survey(rng, n=300):
    seg = rng.choice(3, size=n, p=[0.45, 0.35, 0.20])  # 0 cautious holder, 1 active trader, 2 DeFi power user
    trust_mu = np.array([3.2, 4.6, 5.4])[seg]
    sec_mu = np.array([3.0, 4.4, 5.6])[seg]

    def likert(mu, k, reverse=()):
        cols = {}
        for i in range(1, k + 1):
            x = np.clip(np.round(mu + rng.normal(0, 0.9, n)), 1, 7).astype(int)
            cols[i] = 8 - x if i in reverse else x
        return cols

    df = pd.DataFrame({"respondent_id": [f"R{i:04d}" for i in range(n)],
                       "wallet_address": ["0x" + rng.bytes(20).hex() for _ in range(n)],
                       "country": rng.choice(["US", "BR", "NG", "DE", "KR", "IN"], n)})
    for i, v in likert(trust_mu, 6, reverse={4}).items():
        df[f"trust_{i}"] = v  # trust_4 is reverse-keyed
    for i, v in likert(sec_mu, 4).items():
        df[f"sec_{i}"] = v
    df["trades_per_month"] = np.round(np.exp(np.array([0.5, 2.8, 2.0])[seg] + rng.normal(0, 0.4, n)), 1)
    df["portfolio_usd_log10"] = np.round(np.array([3.0, 3.8, 4.6])[seg] + rng.normal(0, 0.35, n), 2)
    df["defi_protocols_used"] = rng.poisson(np.array([0.3, 1.5, 6.0])[seg])
    df["duration_sec"] = np.round(rng.lognormal(np.log(540), 0.35, n)).astype(int)
    df["attention_check"] = np.where(rng.random(n) < 0.97, 4, rng.integers(1, 8, n))  # instructed: pick 4
    holds = rng.random(n) < np.array([0.6, 0.85, 0.95])[seg]
    df["claims_holds_eth"] = np.where(holds, "yes", "no")
    df["onchain_eth_balance"] = np.where(holds, np.round(rng.lognormal(0, 1.2, n), 3), 0.0)
    phrases = ["I worry about losing access to my keys", "Fees are too high on most platforms",
               "I want better yield without lockups", "Security audits matter most to me",
               "I mostly hold long term", "I use several DeFi apps every week"]
    coins = ["ETH", "BTC", "SOL", "USDC", "stablecoins", "altcoins", "LSTs", "memecoins"]

    def answer():
        a, b = rng.choice(len(phrases), 2, replace=False)
        return (f"{phrases[a]}. {phrases[b]} {rng.choice(['honestly', 'mostly', 'for me', 'lately'])}. "
                f"In crypto since {rng.integers(2013, 2025)}, mostly {rng.choice(coins)}.")
    df["open_text"] = [answer() for _ in range(n)]
    df["true_segment"] = seg  # ground truth, for checking only - drop before real analysis

    # plant bots/fraud in ~10% of rows
    bots = rng.choice(n, size=int(n * 0.10), replace=False)
    grid = [c for c in df if c.startswith(("trust_", "sec_"))]
    for j, b in enumerate(bots):
        kind = j % 4
        if kind == 0:  # speeder + straightliner
            df.loc[b, "duration_sec"] = int(rng.integers(40, 90))
            df.loc[b, grid] = 4
        elif kind == 1:  # copy-paste farm text + failed attention
            df.loc[b, "open_text"] = "Very good project, great team, to the moon"
            df.loc[b, "attention_check"] = 7
        elif kind == 2:  # claims holdings the wallet doesn't show
            df.loc[b, "claims_holds_eth"] = "yes"
            df.loc[b, "onchain_eth_balance"] = 0.0
            df.loc[b, "duration_sec"] = int(rng.integers(60, 120))
        else:  # duplicate wallet reused across accounts
            df.loc[b, "wallet_address"] = df.loc[bots[0], "wallet_address"]
            df.loc[b, "open_text"] = "Very good project, great team, to the moon"
    df["is_planted_bot"] = df.index.isin(bots).astype(int)
    return df


def ratings(rng, n_items=60, n_raters=4):
    truth = rng.integers(1, 6, n_items)
    data = {"item_id": [f"A{i:03d}" for i in range(n_items)]}
    for r in range(1, n_raters + 1):
        noise = rng.choice([-1, 0, 0, 0, 0, 1], n_items) if r < n_raters else rng.choice([-2, -1, 0, 0, 1, 2], n_items)
        x = np.clip(truth + noise, 1, 5).astype(float)
        x[rng.random(n_items) < 0.05] = np.nan  # missing ratings
        data[f"rater_{r}"] = x
    return pd.DataFrame(data)


def conjoint(rng, n_resp=250, tasks=10, alts=3):
    attrs = {a: list(lv) for a, lv in TRUE_CONJOINT.items()}
    rows = []
    for r in range(n_resp):
        for t in range(tasks):
            utils, profiles = [], []
            for a in range(alts):
                prof = {k: rng.choice(v) for k, v in attrs.items()}
                profiles.append(prof)
                utils.append(sum(TRUE_CONJOINT[k][v] for k, v in prof.items()) + rng.gumbel())
            pick = int(np.argmax(utils))
            for a, prof in enumerate(profiles):
                rows.append({"resp_id": f"R{r:04d}", "task": t + 1, "alt": a + 1, **prof, "chosen": int(a == pick)})
    return attrs, pd.DataFrame(rows)


def maxdiff(rng, n_resp=200, tasks=8, per_task=4):
    rows = []
    true = np.array(MAXDIFF_TRUE)
    for r in range(n_resp):
        for t in range(tasks):
            shown = rng.choice(len(MAXDIFF_ITEMS), per_task, replace=False)
            u = true[shown] + rng.gumbel(size=per_task)
            best, worst = shown[np.argmax(u)], shown[np.argmin(u)]
            for i in shown:
                rows.append({"resp_id": f"R{r:04d}", "task": t + 1, "item": MAXDIFF_ITEMS[i],
                             "best": int(i == best), "worst": int(i == worst)})
    return pd.DataFrame(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="examples")
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()
    rng = np.random.default_rng(a.seed)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    survey(rng).to_csv(out / "survey.csv", index=False)
    ratings(rng).to_csv(out / "ratings.csv", index=False)
    attrs, cj = conjoint(rng)
    (out / "conjoint_attributes.json").write_text(json.dumps(attrs, indent=2))
    cj.to_csv(out / "conjoint_responses.csv", index=False)
    maxdiff(rng).to_csv(out / "maxdiff.csv", index=False)
    print(json.dumps({"written_to": str(out), "true_conjoint_partworths": TRUE_CONJOINT,
                      "true_maxdiff_order": [MAXDIFF_ITEMS[i] for i in np.argsort(MAXDIFF_TRUE)[::-1]]},
                     indent=2))


if __name__ == "__main__":
    main()

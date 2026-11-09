"""Survey data-quality and fraud screening for (pseudo)anonymous crypto audiences.

Usage:
  uv run python scripts/fraud_flags.py survey.csv --out data/processed/survey_flags.csv \
      --id-col respondent_id --duration-col duration_sec --grid-prefix trust_,sec_ \
      --text-col open_text --attention-col attention_check --attention-pass 4 \
      --wallet-col wallet_address --claim-col claims_holds_eth --onchain-col onchain_eth_balance

Every check is optional: only the ones whose columns you pass are run.

Flags (1 = triggered)
  speeder          duration < --speed-ratio x median (default 0.33)
  straightliner    zero variance across the grid items
  dup_text         same normalised open-end (>= 15 chars) as another respondent
  failed_attention attention check != pass value
  dup_wallet       wallet shared with another respondent ID
  claim_mismatch   says they hold the asset but on-chain balance is 0
  multivariate_outlier  IsolationForest on numeric answers (top --contamination share)

exclude = 1 if any hard flag (failed_attention, dup_wallet, claim_mismatch) OR >= 2 soft flags.
Output CSV holds ID (hashed if --hash-ids), flags, score, exclude - no answers, so it is safe to share.
Summary JSON goes to stdout.
"""
import argparse
import hashlib
import json
import os
import re

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

HARD = ["failed_attention", "dup_wallet", "claim_mismatch"]


def hash_id(x, salt):
    return hashlib.sha256((salt + str(x)).encode()).hexdigest()[:16]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv")
    p.add_argument("--out", required=True)
    p.add_argument("--id-col", default="respondent_id")
    p.add_argument("--duration-col")
    p.add_argument("--speed-ratio", type=float, default=0.33)
    p.add_argument("--grid-prefix", help="comma-separated prefixes of Likert grid items")
    p.add_argument("--text-col")
    p.add_argument("--attention-col")
    p.add_argument("--attention-pass")
    p.add_argument("--wallet-col")
    p.add_argument("--claim-col", help="self-reported holding column (yes/no, 1/0, true/false)")
    p.add_argument("--onchain-col", help="observed on-chain balance column")
    p.add_argument("--contamination", type=float, default=0.05)
    p.add_argument("--hash-ids", action="store_true", help="hash IDs with salt from env RESEARCH_SALT")
    a = p.parse_args()

    df = pd.read_csv(a.csv)
    f = pd.DataFrame(index=df.index)

    if a.duration_col:
        med = df[a.duration_col].median()
        f["speeder"] = (df[a.duration_col] < a.speed_ratio * med).astype(int)
    grid = []
    if a.grid_prefix:
        grid = [c for c in df.columns if c.startswith(tuple(a.grid_prefix.split(",")))]
        f["straightliner"] = (df[grid].nunique(axis=1) == 1).astype(int)
    if a.text_col:
        norm = df[a.text_col].fillna("").str.lower().map(lambda s: re.sub(r"[^a-z0-9]+", " ", s).strip())
        f["dup_text"] = ((norm.str.len() >= 15) & norm.duplicated(keep=False)).astype(int)
    if a.attention_col and a.attention_pass is not None:
        f["failed_attention"] = (df[a.attention_col].astype(str) != str(a.attention_pass)).astype(int)
    if a.wallet_col:
        w = df[a.wallet_col].astype(str).str.lower()
        f["dup_wallet"] = (w.duplicated(keep=False) & df[a.wallet_col].notna()).astype(int)
    if a.claim_col and a.onchain_col:
        claims = df[a.claim_col].astype(str).str.lower().isin(["yes", "1", "true", "y"])
        f["claim_mismatch"] = (claims & (pd.to_numeric(df[a.onchain_col], errors="coerce").fillna(0) <= 0)).astype(int)

    num = df.select_dtypes("number").drop(columns=[c for c in ["is_planted_bot", "true_segment"] if c in df], errors="ignore")
    if num.shape[1] >= 3:
        iso = IsolationForest(contamination=a.contamination, random_state=0).fit(num.fillna(num.median()))
        f["multivariate_outlier"] = (iso.predict(num.fillna(num.median())) == -1).astype(int)

    hard = [c for c in HARD if c in f]
    soft = [c for c in f.columns if c not in HARD]
    f["fraud_score"] = f[hard].sum(axis=1) * 2 + f[soft].sum(axis=1)
    f["exclude"] = ((f[hard].sum(axis=1) > 0) | (f[soft].sum(axis=1) >= 2)).astype(int)

    salt = os.environ.get("RESEARCH_SALT", "")
    if a.hash_ids and not salt:
        raise SystemExit("set RESEARCH_SALT env var before --hash-ids (keep it out of git)")
    ids = df[a.id_col].map(lambda x: hash_id(x, salt)) if a.hash_ids else df[a.id_col]
    f.insert(0, a.id_col, ids)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    f.to_csv(a.out, index=False)

    summary = {"n": len(df), "n_excluded": int(f["exclude"].sum()),
               "pct_excluded": round(100 * f["exclude"].mean(), 1),
               "flag_counts": {c: int(f[c].sum()) for c in hard + soft}, "output": a.out}
    if "is_planted_bot" in df:  # only exists in fake data: measure detection quality
        truth, pred = df["is_planted_bot"] == 1, f["exclude"] == 1
        summary["fake_data_check"] = {"recall": round(float((truth & pred).sum() / truth.sum()), 3),
                                      "precision": round(float((truth & pred).sum() / max(pred.sum(), 1)), 3)}
    if summary["pct_excluded"] > 25:
        summary["warning"] = "over 25% excluded - check thresholds or panel quality before trusting results"
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

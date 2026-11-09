"""End-to-end tests: generate fake data with known answers, check each script recovers them.

Run: uv run pytest -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "scripts"


def run(*args):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.fixture(scope="session")
def data(tmp_path_factory):
    d = tmp_path_factory.mktemp("fake")
    run(S / "make_fake_data.py", "--out", d, "--seed", 7)
    return d


@pytest.fixture(scope="session")
def flags(data):
    out = data / "flags.csv"
    res = run(S / "fraud_flags.py", data / "survey.csv", "--out", out, "--duration-col", "duration_sec",
              "--grid-prefix", "trust_,sec_", "--text-col", "open_text", "--attention-col", "attention_check",
              "--attention-pass", 4, "--wallet-col", "wallet_address", "--claim-col", "claims_holds_eth",
              "--onchain-col", "onchain_eth_balance")
    return out, res


def test_irr_methods(data):
    k = run(S / "irr.py", data / "ratings.csv")
    assert 0.6 < k["value"] < 0.95 and k["n_raters"] == 4
    assert k["lowest_agreement_rater"] == "rater_4"  # the planted noisy rater
    w = run(S / "irr.py", data / "ratings.csv", "--method", "weighted", "--raters", "rater_1,rater_2")
    assert w["value"] > 0.7
    f = run(S / "irr.py", data / "ratings.csv", "--method", "fleiss")
    assert -1 <= f["value"] <= 1


def test_reliability_needs_reverse_coding(data):
    good = run(S / "reliability.py", data / "survey.csv", "--prefix", "trust_", "--reverse", "trust_4", "--efa", 1)
    bad = run(S / "reliability.py", data / "survey.csv", "--prefix", "trust_")
    assert good["cronbach_alpha"] >= 0.75 and not good["flags"]
    assert bad["cronbach_alpha"] < good["cronbach_alpha"]
    assert any("trust_4" in f for f in bad["flags"])  # catches the forgotten reverse item
    assert good["efa"]["kmo"] > 0.6


def test_fraud_catches_planted_bots(flags):
    _, res = flags
    assert res["fake_data_check"]["recall"] >= 0.9
    assert res["fake_data_check"]["precision"] >= 0.6
    assert res["pct_excluded"] < 25


def test_fraud_output_has_no_answers(flags):
    out, _ = flags
    header = out.read_text().splitlines()[0]
    assert "wallet_address" not in header and "open_text" not in header


def test_segments_recovers_truth(data, flags):
    out, _ = flags
    r = run(S / "segment.py", data / "survey.csv", "--prefix-means", "trust_,sec_", "--reverse", "trust_4",
            "--cols", "trades_per_month,portfolio_usd_log10,defi_protocols_used,trust_mean,sec_mean",
            "--exclude-flagged", out)
    assert r["chosen_k"] == 3
    assert r["stability_ari"] > 0.8
    assert r["fake_data_check_ari_vs_truth"] > 0.8


def test_power_sanity():
    assert run(S / "power.py", "means", "--d", 0.5)["n_per_group"] == 64  # textbook value
    p = run(S / "power.py", "proportions", "--p1", 0.2, "--p2", 0.25, "--dropout", 0.2)
    assert p["n_per_group_with_dropout"] > p["n_per_group"]
    assert run(S / "power.py", "conjoint", "--tasks", 10, "--alts", 3, "--max-levels", 4)["total_n"] >= 200


def test_conjoint_design_balanced(data, tmp_path):
    r = run(S / "conjoint.py", "design", data / "conjoint_attributes.json", "--out", tmp_path / "d.csv")
    assert r["tasks_with_duplicate_alts"] == 0
    for counts in r["level_counts"].values():
        assert max(counts.values()) - min(counts.values()) <= 0.1 * max(counts.values())


def test_conjoint_recovers_partworths(data):
    r = run(S / "conjoint.py", "estimate", data / "conjoint_responses.csv",
            "--attributes", data / "conjoint_attributes.json")
    pw = r["partworths"]
    assert abs(pw["apy"]["9%"]["utility"] - 1.5) < 0.25
    assert abs(pw["lockup"]["90 days"]["utility"] + 1.3) < 0.25
    assert abs(pw["insurance"]["yes"]["utility"] - 0.7) < 0.2
    assert list(r["importance_pct"])[:2] == ["apy", "lockup"]


def test_maxdiff_ranking(data):
    r = run(S / "conjoint.py", "maxdiff", data / "maxdiff.csv")
    assert set(r["ranking"][:2]) == {"instant withdrawal", "auto-compounding"}
    assert r["ranking"][-1] == "copy trading"

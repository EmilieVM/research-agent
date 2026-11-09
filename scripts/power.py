"""Sample size and minimum detectable effect.

Usage:
  uv run python scripts/power.py proportions --p1 0.20 --p2 0.25            # A/B or matched cohorts, conversion-style
  uv run python scripts/power.py means --d 0.3                              # Likert / scale score difference (Cohen's d)
  uv run python scripts/power.py means --mean-diff 0.4 --sd 1.2             # same, in raw units
  uv run python scripts/power.py mde --n 400 --kind means                   # what effect can n=400 per group detect?
  uv run python scripts/power.py segments --n-segments 4 --min-per-segment 100 --smallest-share 0.15
  uv run python scripts/power.py conjoint --tasks 10 --alts 3 --max-levels 4
  uv run python scripts/power.py maxdiff --items 20 --per-task 5 --times-shown 3

Defaults: alpha .05 two-sided, power .80, equal groups. Add --dropout 0.15 to inflate for
fraud/quality exclusions (crypto panels often lose 10-25%).
"""
import argparse
import json
import math

from statsmodels.stats.power import NormalIndPower, TTestIndPower
from statsmodels.stats.proportion import proportion_effectsize


def inflate(n, dropout):
    return math.ceil(n / (1 - dropout))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="mode", required=True)
    for name in ["proportions", "means", "mde", "segments", "conjoint", "maxdiff"]:
        s = sub.add_parser(name)
        s.add_argument("--alpha", type=float, default=0.05)
        s.add_argument("--power", type=float, default=0.80)
        s.add_argument("--dropout", type=float, default=0.0)
        if name == "proportions":
            s.add_argument("--p1", type=float, required=True)
            s.add_argument("--p2", type=float, required=True)
        if name == "means":
            s.add_argument("--d", type=float)
            s.add_argument("--mean-diff", type=float)
            s.add_argument("--sd", type=float)
        if name == "mde":
            s.add_argument("--n", type=int, required=True, help="per group")
            s.add_argument("--kind", choices=["means", "proportions"], default="means")
            s.add_argument("--p1", type=float, default=0.2, help="baseline rate for proportions")
        if name == "segments":
            s.add_argument("--n-segments", type=int, required=True)
            s.add_argument("--min-per-segment", type=int, default=100)
            s.add_argument("--smallest-share", type=float, required=True, help="expected share of smallest segment")
        if name == "conjoint":
            s.add_argument("--tasks", type=int, required=True)
            s.add_argument("--alts", type=int, required=True)
            s.add_argument("--max-levels", type=int, required=True)
            s.add_argument("--subgroups", type=int, default=1, help="segments you need to compare")
        if name == "maxdiff":
            s.add_argument("--items", type=int, required=True)
            s.add_argument("--per-task", type=int, required=True)
            s.add_argument("--times-shown", type=int, default=3, help="target exposures per item per respondent")
    a = p.parse_args()
    out = {"mode": a.mode, "alpha": a.alpha, "power": a.power}

    if a.mode == "proportions":
        h = proportion_effectsize(a.p2, a.p1)
        n = NormalIndPower().solve_power(effect_size=abs(h), alpha=a.alpha, power=a.power)
        out.update(cohens_h=round(h, 3), n_per_group=math.ceil(n), n_per_group_with_dropout=inflate(n, a.dropout))
    elif a.mode == "means":
        d = a.d if a.d is not None else a.mean_diff / a.sd
        n = TTestIndPower().solve_power(effect_size=abs(d), alpha=a.alpha, power=a.power)
        out.update(cohens_d=round(d, 3), n_per_group=math.ceil(n), n_per_group_with_dropout=inflate(n, a.dropout))
    elif a.mode == "mde":
        eff = (TTestIndPower() if a.kind == "means" else NormalIndPower()).solve_power(nobs1=a.n, alpha=a.alpha, power=a.power)
        out.update(n_per_group=a.n, min_detectable_effect=round(eff, 3))
        if a.kind == "means":
            out["interpretation"] = f"smallest detectable Cohen's d = {eff:.2f} (~{eff:.2f} SD difference)"
        else:  # invert Cohen's h around baseline
            p2 = math.sin(math.asin(math.sqrt(a.p1)) + eff / 2) ** 2
            out["interpretation"] = f"from baseline {a.p1:.0%} you can detect a lift to ~{p2:.1%}"
    elif a.mode == "segments":
        n = max(a.min_per_segment / a.smallest_share, a.n_segments * a.min_per_segment)
        out.update(total_n=math.ceil(n), total_n_with_dropout=inflate(n, a.dropout),
                   rule=f"need >= {a.min_per_segment} in the smallest segment ({a.smallest_share:.0%} share)")
    elif a.mode == "conjoint":
        # Orme's rule of thumb: n * tasks * alts / max_levels >= 500 (1000 for subgroup comparisons)
        target = 500 if a.subgroups == 1 else 1000
        n = target * a.max_levels / (a.tasks * a.alts)
        n = max(n, 200) * a.subgroups if a.subgroups > 1 else max(n, 200)
        out.update(total_n=math.ceil(n), total_n_with_dropout=inflate(n, a.dropout),
                   rule="Orme: n*t*a/c >= 500 (1000 for subgroups), floor 200 per group for stable estimates")
    elif a.mode == "maxdiff":
        sets = math.ceil(a.times_shown * a.items / a.per_task)
        out.update(tasks_per_respondent=sets, total_n=max(200, inflate(200, a.dropout)),
                   rule="each item shown ~3x per respondent; 200+ respondents for stable aggregate scores, 300+ for HB")
        if sets > 15:
            out["warning"] = f"{sets} tasks is fatiguing - reduce items or show each fewer times"
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

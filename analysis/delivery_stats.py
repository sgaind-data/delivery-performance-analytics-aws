"""
delivery_stats.py  —  Milestone 6: statistical tests on delivery performance.

Reads the dbt marts in Redshift (one row per DELIVERED order) and runs:
  1. Welch's t-test: review score, late vs on-time orders
  2. Chi-squared test of independence: late delivery vs customer state
     (+ Cramér's V effect size and an expected-count assumption check)

Writes:
  results/stats_results.csv   machine-readable results (every number used later)
  results/stats_summary.md    plain-English summary

Run from the repo root with the project venv active and DBT_REDSHIFT_PASSWORD set:
    python analysis/delivery_stats.py

Definitions come from the dbt models (int_orders__delivery_metrics):
  - Scope: is_delivered = true (status 'delivered' and a delivery date exists)
  - is_late: delivered DATE > estimated delivery DATE
  - review_score: one review per order (latest answered), from the DynamoDB copy
"""

import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import redshift_connector
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

QUERY = """
select
    f.order_id,
    f.is_late,
    f.delay_days,
    f.review_score,
    c.customer_state
from marts.fact_orders as f
join marts.dim_customers as c
    on f.customer_id = c.customer_id
where f.is_first_item_in_order   -- one row per order
  and f.is_delivered
"""


def fmt_p(p: float) -> str:
    """Format a p-value; scipy returns 0.0 when it underflows double precision."""
    return "< 1e-300" if p == 0.0 else f"{p:.3e}"


def main() -> None:
    conn = redshift_connector.connect(
        host="olist-wg.387265682464.us-east-2.redshift-serverless.amazonaws.com",
        port=5439,
        database="dev",
        user="sarika_admin",
        password=os.environ["DBT_REDSHIFT_PASSWORD"],
        ssl=True,
    )
    cur = conn.cursor()
    cur.execute(QUERY)
    df = cur.fetch_dataframe()
    conn.close()

    df["is_late"] = df["is_late"].astype(bool)
    n_orders = len(df)
    print(f"Delivered orders loaded: {n_orders:,}")

    # ------------------------------------------------------------------
    # 1. Welch's t-test: review score, late vs on-time
    # ------------------------------------------------------------------
    rev = df.dropna(subset=["review_score"])
    late_scores = rev.loc[rev["is_late"], "review_score"].astype(float)
    ontime_scores = rev.loc[~rev["is_late"], "review_score"].astype(float)

    t_res = stats.ttest_ind(late_scores, ontime_scores, equal_var=False)

    # Welch-Satterthwaite degrees of freedom
    v1, v2 = late_scores.var(ddof=1), ontime_scores.var(ddof=1)
    n1, n2 = len(late_scores), len(ontime_scores)
    welch_df = (v1 / n1 + v2 / n2) ** 2 / (
        (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    )
    # Cohen's d with pooled SD (effect size)
    pooled_sd = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    cohens_d = (late_scores.mean() - ontime_scores.mean()) / pooled_sd

    # Share of 1-2 star reviews in each group
    low_late = (late_scores <= 2).mean()
    low_ontime = (ontime_scores <= 2).mean()

    print("\nWelch's t-test: review score, late vs on-time")
    print(f"  late:    n={n1:,}  mean={late_scores.mean():.4f}  1-2 star share={low_late:.4%}")
    print(f"  on-time: n={n2:,}  mean={ontime_scores.mean():.4f}  1-2 star share={low_ontime:.4%}")
    print(f"  t={t_res.statistic:.4f}  df={welch_df:.1f}  p={fmt_p(t_res.pvalue)}  Cohen's d={cohens_d:.4f}")

    # ------------------------------------------------------------------
    # 2. Chi-squared test of independence: late delivery vs customer state
    # ------------------------------------------------------------------
    table = pd.crosstab(df["customer_state"], df["is_late"])
    chi2, chi_p, chi_dof, expected = stats.chi2_contingency(table)
    n_table = table.to_numpy().sum()
    r, k = table.shape
    cramers_v = math.sqrt(chi2 / (n_table * (min(r, k) - 1)))
    cells_below_5 = int((expected < 5).sum())
    min_expected = float(expected.min())

    print("\nChi-squared test: late delivery vs customer state")
    print(f"  table: {r} states x {k} outcomes, n={n_table:,}")
    print(f"  chi2={chi2:.4f}  dof={chi_dof}  p={fmt_p(chi_p)}  Cramer's V={cramers_v:.4f}")
    print(f"  expected counts < 5: {cells_below_5} of {expected.size} cells (min expected={min_expected:.2f})")

    # ------------------------------------------------------------------
    # Save results
    # ------------------------------------------------------------------
    overall_late_rate = df["is_late"].mean()
    rows = [
        {"test": "scope", "metric": "delivered_orders", "value": n_orders},
        {"test": "scope", "metric": "overall_late_rate", "value": round(overall_late_rate, 6)},
        {"test": "welch_t_test", "metric": "variable", "value": "review_score"},
        {"test": "welch_t_test", "metric": "groups", "value": "late vs on-time (delivered orders with a review)"},
        {"test": "welch_t_test", "metric": "n_late", "value": n1},
        {"test": "welch_t_test", "metric": "n_on_time", "value": n2},
        {"test": "welch_t_test", "metric": "mean_late", "value": round(late_scores.mean(), 6)},
        {"test": "welch_t_test", "metric": "mean_on_time", "value": round(ontime_scores.mean(), 6)},
        {"test": "welch_t_test", "metric": "pct_1_2_star_late", "value": round(low_late, 6)},
        {"test": "welch_t_test", "metric": "pct_1_2_star_on_time", "value": round(low_ontime, 6)},
        {"test": "welch_t_test", "metric": "t_statistic", "value": round(t_res.statistic, 6)},
        {"test": "welch_t_test", "metric": "welch_df", "value": round(welch_df, 2)},
        {"test": "welch_t_test", "metric": "p_value", "value": fmt_p(t_res.pvalue)},
        {"test": "welch_t_test", "metric": "cohens_d", "value": round(cohens_d, 6)},
        {"test": "chi_squared", "metric": "variables", "value": "customer_state x is_late"},
        {"test": "chi_squared", "metric": "table_shape", "value": f"{r}x{k}"},
        {"test": "chi_squared", "metric": "n", "value": int(n_table)},
        {"test": "chi_squared", "metric": "chi2_statistic", "value": round(chi2, 6)},
        {"test": "chi_squared", "metric": "degrees_of_freedom", "value": int(chi_dof)},
        {"test": "chi_squared", "metric": "p_value", "value": fmt_p(chi_p)},
        {"test": "chi_squared", "metric": "cramers_v", "value": round(cramers_v, 6)},
        {"test": "chi_squared", "metric": "cells_expected_below_5", "value": cells_below_5},
        {"test": "chi_squared", "metric": "min_expected_count", "value": round(min_expected, 4)},
    ]
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "stats_results.csv", index=False)

    summary = f"""# Statistical tests: delivery performance

Source: `marts.fact_orders` joined to `marts.dim_customers`, one row per delivered order
(n = {n_orders:,}). Generated by `analysis/delivery_stats.py`.

## Welch's t-test: review score, late vs on-time

| Group | Orders with a review | Mean review score | Share of 1-2 star reviews |
| --- | --- | --- | --- |
| Late | {n1:,} | {late_scores.mean():.2f} | {low_late:.1%} |
| On-time | {n2:,} | {ontime_scores.mean():.2f} | {low_ontime:.1%} |

t = {t_res.statistic:.2f}, Welch df = {welch_df:.1f}, p = {fmt_p(t_res.pvalue)}, Cohen's d = {cohens_d:.2f}.

## Chi-squared test of independence: late delivery vs customer state

{r} states x {k} outcomes, n = {n_table:,}.
chi-squared = {chi2:.2f}, df = {chi_dof}, p = {fmt_p(chi_p)}, Cramér's V = {cramers_v:.3f}.
Expected counts below 5: {cells_below_5} of {expected.size} cells (minimum expected = {min_expected:.2f}).
"""
    (RESULTS_DIR / "stats_summary.md").write_text(summary)
    print(f"\nSaved: {RESULTS_DIR / 'stats_results.csv'}")
    print(f"Saved: {RESULTS_DIR / 'stats_summary.md'}")


if __name__ == "__main__":
    main()

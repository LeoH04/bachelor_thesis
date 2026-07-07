#!/usr/bin/env python3
"""Exploratory math-facing diagnostics for the thesis discussion.

This script is intentionally standalone. It reads an existing processed metrics
CSV and prints compact summaries that help frame explicit SMM memory as a
conditioning state, belief-convergence mechanism, and possible persuasion aid.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_INPUT = Path("01_data/processed/simulation_metrics_final_100_gpt_oss_120b.csv")
VOTE_COLUMNS = [
    "votes_candidate_a",
    "votes_candidate_b",
    "votes_candidate_c",
    "votes_candidate_d",
]


def normalized_entropy(row: pd.Series) -> float:
    votes = np.array([row[col] for col in VOTE_COLUMNS], dtype=float)
    total = votes.sum()
    if total <= 0:
        return np.nan
    probs = votes[votes > 0] / total
    entropy = -float(np.sum(probs * np.log(probs)))
    return entropy / math.log(len(VOTE_COLUMNS))


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["decision_correct_num"] = out["decision_correct"].astype(float)
    out["cell"] = out["context_transparency_condition"] + "_" + out["smm_mode"]
    out["final_vote_entropy"] = out.apply(normalized_entropy, axis=1)
    out["vote_concentration"] = out[VOTE_COLUMNS].max(axis=1) / out[VOTE_COLUMNS].sum(axis=1)
    out["correct_candidate_vote_share"] = np.nan
    for candidate in ["a", "b", "c", "d"]:
        mask = out["correct_candidate"].str.lower().eq(f"candidate {candidate}")
        out.loc[mask, "correct_candidate_vote_share"] = (
            out.loc[mask, f"votes_candidate_{candidate}"]
            / out.loc[mask, VOTE_COLUMNS].sum(axis=1)
        )
    out["log_total_tokens"] = np.log1p(out["total_tokens"].astype(float))
    return out


def summarize_by_cell(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "decision_correct_num",
        "correct_candidate_vote_share",
        "vote_concentration",
        "final_vote_entropy",
        "smm_similarity",
        "smm_evidence_share",
        "team_process_communication",
        "team_process_cooperation",
        "agent_tool_calls",
        "total_tokens",
    ]
    summary = df.groupby("cell")[columns].agg(["mean", "std", "count"])
    return summary.round(3)


def corr_table(df: pd.DataFrame, variables: list[str], target: str) -> pd.DataFrame:
    rows = []
    for variable in variables:
        subset = df[[variable, target]].dropna()
        if len(subset) < 3 or subset[variable].nunique() < 2:
            corr = np.nan
        else:
            corr = subset[variable].corr(subset[target])
        rows.append({"variable": variable, f"corr_with_{target}": corr, "n": len(subset)})
    return pd.DataFrame(rows).round(3)


def ols_hc3(df: pd.DataFrame, y_col: str, x_cols: list[str]) -> pd.DataFrame:
    x_cols = [col for col in x_cols if df[col].notna().sum() > 0]
    subset = df[[y_col, *x_cols]].dropna()
    if len(subset) <= len(x_cols) + 1:
        return pd.DataFrame()

    y = subset[y_col].to_numpy(dtype=float)
    x = subset[x_cols].to_numpy(dtype=float)
    x = np.column_stack([np.ones(len(x)), x])
    names = ["Intercept", *x_cols]

    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ beta
    xtx_inv = np.linalg.pinv(x.T @ x)
    hat = np.sum((x @ xtx_inv) * x, axis=1)
    scale = (residuals / np.clip(1 - hat, 1e-8, None)) ** 2
    cov = xtx_inv @ (x.T @ (scale[:, None] * x)) @ xtx_inv
    se = np.sqrt(np.diag(cov))
    t_stat = beta / se

    return pd.DataFrame(
        {
            "term": names,
            "estimate": beta,
            "hc3_se": se,
            "t": t_stat,
            "n": len(subset),
        }
    ).round(4)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()

    df = add_derived_columns(pd.read_csv(args.input))
    treatment = df[df["smm_mode"].eq("treatment")].copy()

    print(f"Input: {args.input}")
    print(f"Rows: {len(df)} total, {len(treatment)} treatment")
    print("\n=== Cell means ===")
    print(summarize_by_cell(df).to_string())

    variables = [
        "smm_similarity",
        "smm_evidence_share",
        "smm_quality",
        "team_process_communication",
        "team_process_cooperation",
        "agent_tool_calls",
        "log_total_tokens",
    ]

    print("\n=== Treatment correlations: correctness ===")
    print(corr_table(treatment, variables, "decision_correct_num").to_string(index=False))

    print("\n=== Treatment correlations: correct-candidate vote share ===")
    print(corr_table(treatment, variables, "correct_candidate_vote_share").to_string(index=False))

    print("\n=== Linear probability probe: decision correctness, treatment only ===")
    print(
        ols_hc3(
            treatment,
            "decision_correct_num",
            [
                "smm_similarity",
                "smm_evidence_share",
                "team_process_communication",
                "team_process_cooperation",
                "agent_tool_calls",
                "log_total_tokens",
            ],
        ).to_string(index=False)
    )

    print("\n=== Vote-share probe: correct-candidate vote share, treatment only ===")
    print(
        ols_hc3(
            treatment,
            "correct_candidate_vote_share",
            [
                "smm_similarity",
                "smm_evidence_share",
                "team_process_communication",
                "team_process_cooperation",
                "agent_tool_calls",
                "log_total_tokens",
            ],
        ).to_string(index=False)
    )


if __name__ == "__main__":
    main()

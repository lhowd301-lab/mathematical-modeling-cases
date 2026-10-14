from __future__ import annotations

import numpy as np

from common_storage_lp import load_annual_data, output_dates
from q2_model import run_q2
from q3_model import run_q3


def _block_bootstrap_prices(price_matrix, scenario_count, block_length, seed):
    rng = np.random.default_rng(seed)
    price_matrix = np.asarray(price_matrix, dtype=float)
    day_mean = price_matrix.mean(axis=1, keepdims=True)
    residual_matrix = price_matrix - day_mean
    flattened = residual_matrix.reshape(-1)
    block_starts = np.arange(0, len(flattened) - block_length + 1)
    blocks_per_path = int(np.ceil(144 / block_length))
    scenarios = np.empty(
        (scenario_count, price_matrix.shape[0], 144), dtype=float
    )
    for scenario_index in range(scenario_count):
        for day_index in range(price_matrix.shape[0]):
            pieces = []
            for _ in range(blocks_per_path):
                start = int(rng.choice(block_starts))
                pieces.append(flattened[start : start + block_length])
            residual = np.concatenate(pieces)[:144]
            scenarios[scenario_index, day_index] = np.maximum(
                0.0, day_mean[day_index, 0] + residual
            )
    return scenarios


def scenario_stress(q4_2_result, scenario_count=200, block_length=6, seed=20250101):
    annual = load_annual_data()
    dates = output_dates(annual)
    price_matrix = (
        annual[annual["date"].isin(dates)]
        .sort_values(["date", "interval_id"])["price_actual_yuan_per_kwh"]
        .to_numpy(dtype=float)
        .reshape(len(dates), 144)
    )
    scenarios = _block_bootstrap_prices(
        price_matrix,
        scenario_count=scenario_count,
        block_length=block_length,
        seed=seed,
    )
    purchase_matrix = np.vstack(
        [np.asarray(q4_2_result["days"][day]["purchase_kwh"], dtype=float) for day in dates]
    )
    costs = np.einsum("snt,nt->s", scenarios, purchase_matrix)
    var_95 = float(np.quantile(costs, 0.95))
    cvar_95 = float(costs[costs >= var_95].mean()) if np.any(costs >= var_95) else var_95
    return {
        "method": "block_bootstrap_cvar_stress_on_deterministic_schedule",
        "status": "computed",
        "scenario_count": int(scenario_count),
        "block_length": int(block_length),
        "seed": int(seed),
        "metrics": {
            "mean_cost_yuan": float(costs.mean()),
            "std_cost_yuan": float(costs.std(ddof=0)),
            "var_95_yuan": var_95,
            "cvar_95_yuan": cvar_95,
            "worst_cost_yuan": float(costs.max()),
        },
        "note": "This risk test evaluates the deterministic Q4-2 schedule under bootstrapped annual price paths and computes VaR/CVaR; it does not re-optimize each scenario.",
    }


def run_q4(enable_stochastic=True, scenario_count=200, block_length=6, seed=20250101):
    q4_2 = run_q2(price_column="price_actual_yuan_per_kwh")
    q4_2.update({"question_id": "Q4-2", "source_question": "Q2"})
    q4_3 = run_q3(price_column="price_actual_yuan_per_kwh")
    q4_3.update({"question_id": "Q4-3", "source_question": "Q3"})
    stress = {
        "status": "not_run",
        "reason": "Optional stochastic extension disabled for the required deterministic result run.",
    }
    if enable_stochastic:
        stress = scenario_stress(
            q4_2,
            scenario_count=scenario_count,
            block_length=block_length,
            seed=seed,
        )
    return {
        "question_id": "Q4",
        "status": "computed",
        "q4_2": q4_2,
        "q4_3": q4_3,
        "stochastic_extension": stress,
        "result_summary": {
            "q4_2_total_cost_yuan": float(q4_2["result_summary"]["total_cost_yuan"]),
            "q4_3_total_cost_yuan": float(q4_3["result_summary"]["total_cost_yuan"]),
            "q4_3_saving_vs_q4_2_yuan": float(
                q4_2["result_summary"]["total_cost_yuan"]
                - q4_3["result_summary"]["total_cost_yuan"]
            ),
            "q4_3_minus_q4_2_yuan": float(
                q4_3["result_summary"]["total_cost_yuan"]
                - q4_2["result_summary"]["total_cost_yuan"]
            ),
            "risk_mean_cost_yuan": float(
                stress["metrics"]["mean_cost_yuan"]
            ) if stress.get("status") == "computed" else None,
            "risk_var_95_yuan": float(
                stress["metrics"]["var_95_yuan"]
            ) if stress.get("status") == "computed" else None,
            "risk_cvar_95_yuan": float(
                stress["metrics"]["cvar_95_yuan"]
            ) if stress.get("status") == "computed" else None,
        },
    }


def metrics_from_q4(result):
    metrics = [
        {
            "name": "q4_2_total_cost_yuan",
            "value": float(result["result_summary"]["q4_2_total_cost_yuan"]),
            "unit": "yuan",
            "status": "computed",
        },
        {
            "name": "q4_3_total_cost_yuan",
            "value": float(result["result_summary"]["q4_3_total_cost_yuan"]),
            "unit": "yuan",
            "status": "computed",
        },
        {
            "name": "q4_3_minus_q4_2_yuan",
            "value": float(result["result_summary"]["q4_3_minus_q4_2_yuan"]),
            "unit": "yuan",
            "status": "computed",
        },
        {
            "name": "q4_3_saving_vs_q4_2_yuan",
            "value": float(result["result_summary"]["q4_3_saving_vs_q4_2_yuan"]),
            "unit": "yuan",
            "status": "computed",
        },
    ]
    stress = result.get("stochastic_extension") or {}
    if stress.get("status") == "computed":
        for name, value in stress["metrics"].items():
            metrics.append(
                {
                    "name": name,
                    "value": float(value),
                    "unit": "yuan",
                    "status": "computed",
                }
            )
    return {"question_id": "Q4", "metrics": metrics}

from __future__ import annotations

import numpy as np

from common_storage_lp import INITIAL_SOC, load_attachment1_data, solve_dispatch


def run_q1():
    frame = load_attachment1_data()
    prices = frame["price_fixed_yuan_per_kwh"].to_numpy(dtype=float)
    load_kwh = frame["load_kwh"].to_numpy(dtype=float)
    pv_kwh = frame["pv_forecast_kwh"].to_numpy(dtype=float)
    result = solve_dispatch(
        prices=prices,
        load_kwh=load_kwh,
        pv_kwh=pv_kwh,
        initial_soc=INITIAL_SOC,
        terminal_soc=INITIAL_SOC,
    )
    result.update(
        {
            "question_id": "Q1",
            "date": "representative_day",
            "slot_start": frame["slot_start"].tolist(),
            "slot_end": frame["slot_end"].tolist(),
            "interval_label": frame["result1_interval_label"].tolist(),
            "price_yuan_per_kwh": prices.tolist(),
            "load_kwh": load_kwh.tolist(),
            "pv_forecast_kwh": pv_kwh.tolist(),
        }
    )
    result["result_summary"] = {
        "total_purchase_kwh": float(np.sum(result["purchase_kwh"])),
        "total_cost_yuan": float(result["cost_yuan"]),
        "total_charge_kwh": float(np.sum(result["charge_kwh"])),
        "total_discharge_kwh": float(np.sum(result["discharge_kwh"])),
        "terminal_soc_gap_kwh": float(result["terminal_soc_kwh"] - INITIAL_SOC),
        "curtailment_kwh": float(np.sum(result["curtailment_kwh"])),
    }
    result["status"] = "computed"
    return result


def metrics_from_q1(result):
    return {
        "question_id": "Q1",
        "metrics": [
            {
                "name": "total_purchase_kwh",
                "value": float(np.sum(result["purchase_kwh"])),
                "unit": "kWh",
                "status": "computed",
            },
            {
                "name": "total_cost_yuan",
                "value": float(result["cost_yuan"]),
                "unit": "yuan",
                "status": "computed",
            },
            {
                "name": "terminal_soc_gap_kwh",
                "value": abs(float(result["terminal_soc_kwh"] - INITIAL_SOC)),
                "unit": "kWh",
                "status": "computed",
            },
            {
                "name": "curtailment_kwh",
                "value": float(np.sum(result["curtailment_kwh"])),
                "unit": "kWh",
                "status": "computed",
            },
        ],
    }


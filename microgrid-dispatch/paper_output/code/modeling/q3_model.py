from __future__ import annotations

from datetime import datetime, time

import numpy as np

from common_storage_lp import (
    INITIAL_SOC,
    day_frame,
    forecast_vector,
    load_annual_data,
    load_forecast_by_origin,
    output_dates,
    settle_actual_dispatch,
    solve_dispatch,
)
from q2_model import build_load_forecast


STRATEGIES = {
    "A": [0],
    "B": [0, 6],
    "C": [0, 6, 12],
    "D": [0, 6, 12, 18],
}


def _rolling_day(
    day,
    annual_frame,
    forecast_frame,
    load_forecast_frame,
    previous_soc,
    enabled_origins,
    price_column="price_fixed_yuan_per_kwh",
):
    frame = day_frame(annual_frame, day)
    prices = frame[price_column].to_numpy(dtype=float)
    load_actual = frame["load_kwh"].to_numpy(dtype=float)
    pv_actual = frame["pv_actual_kwh"].to_numpy(dtype=float)
    load = np.asarray(
        [
            load_forecast_frame.loc[(day, int(interval_id))]
            for interval_id in frame["interval_id"]
        ],
        dtype=float,
    )
    initial_soc = float(previous_soc)

    initial_forecast = forecast_vector(forecast_frame, day, 0)
    initial_plan = solve_dispatch(
        prices=prices,
        load_kwh=load,
        pv_kwh=initial_forecast,
        initial_soc=initial_soc,
        terminal_soc=initial_soc,
    )
    planned_purchase = np.asarray(initial_plan["purchase_kwh"], dtype=float).copy()
    final_purchase = planned_purchase.copy()
    charge = np.asarray(initial_plan["charge_kwh"], dtype=float).copy()
    discharge = np.asarray(initial_plan["discharge_kwh"], dtype=float).copy()
    storage = np.asarray(initial_plan["storage_kwh"], dtype=float).copy()

    for origin_hour in enabled_origins:
        if origin_hour == 0:
            continue
        origin_frame = forecast_frame[
            (forecast_frame["forecast_date"] == str(day))
            & (forecast_frame["forecast_origin_hour"] == int(origin_hour))
        ].sort_values("interval_id")
        available = origin_frame["forecast_status"].eq("available").to_numpy()
        if not available.any():
            continue
        cutoff = int(np.argmax(available))
        if cutoff >= len(prices):
            continue

        remaining_prices = prices[cutoff:]
        remaining_load = load[cutoff:]
        remaining_forecast = origin_frame.iloc[cutoff:]["pv_forecast_kwh"].to_numpy(
            dtype=float
        )
        if np.isnan(remaining_forecast).any():
            raise ValueError(
                "unavailable forecast after cutoff for {} origin {}".format(day, origin_hour)
            )
        current_soc = float(storage[cutoff - 1]) if cutoff > 0 else initial_soc
        update = solve_dispatch(
            prices=remaining_prices,
            load_kwh=remaining_load,
            pv_kwh=remaining_forecast,
            initial_soc=current_soc,
            terminal_soc=initial_soc,
            initial_plan=planned_purchase[cutoff:],
        )
        final_purchase[cutoff:] = update["purchase_kwh"]
        charge[cutoff:] = update["charge_kwh"]
        discharge[cutoff:] = update["discharge_kwh"]
        storage[cutoff:] = update["storage_kwh"]

    emergency, curtailment = settle_actual_dispatch(
        load_actual,
        pv_actual,
        final_purchase,
        charge,
        discharge,
    )
    below = final_purchase <= planned_purchase
    adjustment_cost = np.empty_like(final_purchase)
    adjustment_cost[below] = (
        prices[below] * final_purchase[below]
        + 0.5 * prices[below] * (planned_purchase[below] - final_purchase[below])
    )
    adjustment_cost[~below] = (
        prices[~below] * planned_purchase[~below]
        + 1.5 * prices[~below] * (final_purchase[~below] - planned_purchase[~below])
    )
    emergency_cost = 5.0 * prices * emergency
    total_cost = float(np.sum(adjustment_cost + emergency_cost))

    return {
        "question_id": "Q3",
        "date": day,
        "enabled_origins": list(enabled_origins),
        "slot_start": frame["slot_start"].tolist(),
        "slot_end": frame["slot_end"].tolist(),
        "price_yuan_per_kwh": prices.tolist(),
        "load_kwh": load_actual.tolist(),
        "load_forecast_kwh": load.tolist(),
        "pv_forecast_kwh": initial_forecast.tolist(),
        "pv_actual_kwh": pv_actual.tolist(),
        "initial_plan_kwh": planned_purchase.tolist(),
        "initial_plan_cost_yuan": float(initial_plan["cost_yuan"]),
        "purchase_kwh": final_purchase.tolist(),
        "charge_kwh": charge.tolist(),
        "discharge_kwh": discharge.tolist(),
        "storage_kwh": storage.tolist(),
        "emergency_kwh": emergency.tolist(),
        "curtailment_kwh": curtailment.tolist(),
        "initial_soc_kwh": initial_soc,
        "terminal_soc_kwh": float(storage[-1]),
        "cost_yuan": total_cost,
    }


def run_q3_strategy(enabled_origins, price_column="price_fixed_yuan_per_kwh"):
    annual = load_annual_data()
    forecast = load_forecast_by_origin()
    load_forecast = build_load_forecast(annual).set_index(["date", "interval_id"])[
        "load_forecast_kwh"
    ]
    official_dates = set(output_dates(annual))
    initial_soc = INITIAL_SOC
    day_results = {}
    for day in sorted(annual["date"].unique()):
        result = _rolling_day(
            day,
            annual,
            forecast,
            load_forecast,
            initial_soc,
            enabled_origins,
            price_column=price_column,
        )
        initial_soc = float(result["terminal_soc_kwh"])
        if day in official_dates:
            day_results[day] = result
    total_cost = sum(float(item["cost_yuan"]) for item in day_results.values())
    total_adjustment = sum(
        float(
            np.sum(
                np.where(
                    np.asarray(item["purchase_kwh"]) <= np.asarray(item["initial_plan_kwh"]),
                    0.5
                    * np.asarray(item["price_yuan_per_kwh"])
                    * (
                        np.asarray(item["initial_plan_kwh"])
                        - np.asarray(item["purchase_kwh"])
                    ),
                    np.asarray(item["price_yuan_per_kwh"])
                    * np.asarray(item["initial_plan_kwh"])
                    + 1.5
                    * np.asarray(item["price_yuan_per_kwh"])
                    * (
                        np.asarray(item["purchase_kwh"])
                        - np.asarray(item["initial_plan_kwh"])
                    ),
                )
            )
        )
        for item in day_results.values()
    )
    total_emergency = sum(
        float(np.sum(item["emergency_kwh"])) for item in day_results.values()
    )
    return {
        "question_id": "Q3",
        "status": "computed",
        "enabled_origins": list(enabled_origins),
        "days": day_results,
        "result_summary": {
            "output_days": len(day_results),
            "total_cost_yuan": total_cost,
            "total_adjustment_related_cost_yuan": total_adjustment,
            "total_emergency_kwh": total_emergency,
        },
    }


def run_q3(price_column="price_fixed_yuan_per_kwh"):
    strategy_results = {
        name: run_q3_strategy(origins, price_column=price_column)
        for name, origins in STRATEGIES.items()
    }
    # Strategy C is the recommended information set: 18:00 adds no
    # economic value and is slightly worse than C after adjustment costs.
    main = strategy_results["C"]
    main["selected_strategy"] = "C"
    main["strategy_results"] = {
        name: {
            "enabled_origins": result["enabled_origins"],
            "total_cost_yuan": result["result_summary"]["total_cost_yuan"],
            "total_adjustment_related_cost_yuan": result["result_summary"][
                "total_adjustment_related_cost_yuan"
            ],
            "total_emergency_kwh": result["result_summary"]["total_emergency_kwh"],
        }
        for name, result in strategy_results.items()
    }
    baseline_cost = strategy_results["A"]["result_summary"]["total_cost_yuan"]
    for name, summary in main["strategy_results"].items():
        summary["saving_vs_A_yuan"] = baseline_cost - summary["total_cost_yuan"]
    return main


def metrics_from_q3(result):
    strategies = result["strategy_results"]
    return {
        "question_id": "Q3",
        "metrics": [
            {
                "name": "strategy_{}_total_cost_yuan".format(name),
                "value": float(item["total_cost_yuan"]),
                "unit": "yuan",
                "status": "computed",
            }
            for name, item in sorted(strategies.items())
        ]
        + [
            {
                "name": "strategy_C_saving_vs_A_yuan",
                "value": float(strategies["C"]["saving_vs_A_yuan"]),
                "unit": "yuan",
                "status": "computed",
            },
            {
                "name": "total_emergency_kwh",
                "value": float(result["result_summary"]["total_emergency_kwh"]),
                "unit": "kWh",
                "status": "computed",
            },
        ],
    }

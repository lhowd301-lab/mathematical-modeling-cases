from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from common_storage_lp import (
    ETA_CHARGE,
    ETA_DISCHARGE,
    INITIAL_SOC,
    MAX_PERIOD_ENERGY,
    SOC_MAX,
    SOC_MIN,
    day_frame,
    forecast_vector,
    load_annual_data,
    load_forecast_by_origin,
    output_dates,
    settle_actual_dispatch,
    solve_dispatch,
)


def build_load_forecast(annual_frame):
    """Build a strictly past-only day-ahead load forecast.

    The forecast for a date uses the mean of the same weekday and 10-minute
    interval from the previous four weeks. A previous-day fallback is used
    only for the initial warm-up observations, which are not reported.
    """
    pivot = annual_frame.pivot(
        index="date", columns="interval_id", values="load_kwh"
    ).sort_index()
    index = pd.to_datetime(pivot.index)
    pivot.index = index
    forecast = pd.DataFrame(index=pivot.index, columns=pivot.columns, dtype=float)
    position = {date: offset for offset, date in enumerate(pivot.index)}

    for offset, date in enumerate(pivot.index):
        history = [
            date - timedelta(days=days)
            for days in (7, 14, 21, 28)
            if date - timedelta(days=days) in position
        ]
        if history:
            forecast.iloc[offset] = pivot.loc[history].mean(axis=0).to_numpy()
        elif offset > 0:
            forecast.iloc[offset] = pivot.iloc[offset - 1].to_numpy()
        else:
            forecast.iloc[offset] = 0.0

    long_frame = (
        forecast.reset_index()
        .melt(id_vars="date", var_name="interval_id", value_name="load_forecast_kwh")
        .sort_values(["date", "interval_id"])
        .reset_index(drop=True)
    )
    long_frame["date"] = long_frame["date"].dt.strftime("%Y-%m-%d")
    return long_frame


def run_peak_valley_rule(load_kwh, pv_kwh, prices, initial_soc):
    """A transparent fixed-time peak-valley storage heuristic."""
    load_kwh = np.asarray(load_kwh, dtype=float)
    pv_kwh = np.asarray(pv_kwh, dtype=float)
    prices = np.asarray(prices, dtype=float)
    n = len(load_kwh)
    low_slots = list(range(0, 24)) + list(range(120, 144))
    high_slots = list(range(24, 48)) + list(range(96, 120))

    max_charge = max(
        0.0,
        min(
            SOC_MAX - float(initial_soc),
            ETA_CHARGE * len(low_slots) * MAX_PERIOD_ENERGY,
        ),
    )
    # Charge energy is selected so that a full charge-discharge cycle returns
    # to the initial SOC when all rule actions are physically available.
    total_charge = min(max_charge, 6000.0)
    total_discharge = total_charge * ETA_CHARGE * ETA_DISCHARGE
    charge_target = total_charge / len(low_slots)
    discharge_target = total_discharge / len(high_slots)

    purchase = np.zeros(n, dtype=float)
    charge = np.zeros(n, dtype=float)
    discharge = np.zeros(n, dtype=float)
    storage = np.zeros(n, dtype=float)
    curtailment = np.zeros(n, dtype=float)
    soc = float(initial_soc)

    for t in range(n):
        residual = load_kwh[t] - pv_kwh[t]
        if t in low_slots:
            charge[t] = min(charge_target, max(0.0, (SOC_MAX - soc) / ETA_CHARGE))
            purchase[t] = max(0.0, residual + charge[t])
            curtailment[t] = max(0.0, -(residual + charge[t]))
        elif t in high_slots:
            available = max(0.0, (soc - SOC_MIN) * ETA_DISCHARGE)
            discharge[t] = min(discharge_target, available, max(residual, 0.0))
            purchase[t] = max(0.0, residual - discharge[t])
            curtailment[t] = max(0.0, -residual)
        else:
            purchase[t] = max(0.0, residual)
            curtailment[t] = max(0.0, -residual)

        soc = soc + ETA_CHARGE * charge[t] - discharge[t] / ETA_DISCHARGE
        storage[t] = soc

    return {
        "purchase_kwh": purchase,
        "charge_kwh": charge,
        "discharge_kwh": discharge,
        "storage_kwh": storage,
        "curtailment_kwh": curtailment,
        "terminal_soc_kwh": float(soc),
        "planned_cost_yuan": float(np.sum(prices * purchase)),
        "price_yuan_per_kwh": prices,
    }


def run_q2(price_column="price_fixed_yuan_per_kwh"):
    annual = load_annual_data()
    forecast = load_forecast_by_origin()
    load_forecast = build_load_forecast(annual)
    load_forecast_lookup = load_forecast.set_index(["date", "interval_id"])[
        "load_forecast_kwh"
    ]
    dates = sorted(annual["date"].unique())
    official_dates = set(output_dates(annual))
    initial_soc = INITIAL_SOC
    day_results = {}

    for day in dates:
        frame = day_frame(annual, day)
        prices = frame[price_column].to_numpy(dtype=float)
        load_actual = frame["load_kwh"].to_numpy(dtype=float)
        pv_actual = frame["pv_actual_kwh"].to_numpy(dtype=float)
        load_plan = np.asarray(
            [
                load_forecast_lookup.loc[(day, int(interval_id))]
                for interval_id in frame["interval_id"]
            ],
            dtype=float,
        )
        pv_plan = forecast_vector(forecast, day, 0)

        plan = solve_dispatch(
            prices=prices,
            load_kwh=load_plan,
            pv_kwh=pv_plan,
            initial_soc=initial_soc,
            terminal_soc=initial_soc,
        )
        emergency, curtailment = settle_actual_dispatch(
            load_actual,
            pv_actual,
            plan["purchase_kwh"],
            plan["charge_kwh"],
            plan["discharge_kwh"],
        )
        planned_cost = float(np.sum(prices * np.asarray(plan["purchase_kwh"])))
        emergency_cost = float(5.0 * np.sum(prices * emergency))
        actual_cost = planned_cost + emergency_cost

        rule = run_peak_valley_rule(load_plan, pv_plan, prices, initial_soc)
        rule_emergency, _ = settle_actual_dispatch(
            load_actual,
            pv_actual,
            rule["purchase_kwh"],
            rule["charge_kwh"],
            rule["discharge_kwh"],
        )
        rule_cost = float(
            np.sum(prices * rule["purchase_kwh"])
            + 5.0 * np.sum(prices * rule_emergency)
        )

        result = {
            "question_id": "Q2",
            "date": day,
            "price_yuan_per_kwh": prices.tolist(),
            "slot_start": frame["slot_start"].tolist(),
            "slot_end": frame["slot_end"].tolist(),
            "load_actual_kwh": load_actual.tolist(),
            "pv_actual_kwh": pv_actual.tolist(),
            "load_forecast_kwh": load_plan.tolist(),
            "pv_forecast_kwh": pv_plan.tolist(),
            "purchase_kwh": np.asarray(plan["purchase_kwh"]).tolist(),
            "charge_kwh": np.asarray(plan["charge_kwh"]).tolist(),
            "discharge_kwh": np.asarray(plan["discharge_kwh"]).tolist(),
            "storage_kwh": np.asarray(plan["storage_kwh"]).tolist(),
            "emergency_kwh": emergency.tolist(),
            "curtailment_kwh": curtailment.tolist(),
            "initial_soc_kwh": float(initial_soc),
            "terminal_soc_kwh": float(plan["terminal_soc_kwh"]),
            "planned_cost_yuan": planned_cost,
            "emergency_cost_yuan": emergency_cost,
            "cost_yuan": actual_cost,
            "rule_cost_yuan": rule_cost,
            "rule_purchase_kwh": np.asarray(rule["purchase_kwh"]).tolist(),
            "rule_charge_kwh": np.asarray(rule["charge_kwh"]).tolist(),
            "rule_discharge_kwh": np.asarray(rule["discharge_kwh"]).tolist(),
            "rule_storage_kwh": np.asarray(rule["storage_kwh"]).tolist(),
            "rule_emergency_kwh": rule_emergency.tolist(),
        }
        if day in official_dates:
            day_results[day] = result
        initial_soc = float(plan["terminal_soc_kwh"])

    total_purchase = sum(
        float(np.sum(result["purchase_kwh"])) for result in day_results.values()
    )
    total_emergency = sum(
        float(np.sum(result["emergency_kwh"])) for result in day_results.values()
    )
    total_cost = sum(float(result["cost_yuan"]) for result in day_results.values())
    planned_cost = sum(
        float(result["planned_cost_yuan"]) for result in day_results.values()
    )
    rule_cost = sum(float(result["rule_cost_yuan"]) for result in day_results.values())
    rule_emergency = sum(
        float(np.sum(result["rule_emergency_kwh"])) for result in day_results.values()
    )
    return {
        "question_id": "Q2",
        "status": "computed",
        "days": day_results,
        "result_summary": {
            "output_days": len(day_results),
            "total_purchase_kwh": total_purchase,
            "total_emergency_kwh": total_emergency,
            "total_cost_yuan": total_cost,
            "planned_cost_yuan": planned_cost,
            "rule_total_cost_yuan": rule_cost,
            "rule_total_emergency_kwh": rule_emergency,
            "saving_vs_rule_yuan": rule_cost - total_cost,
            "saving_vs_rule_percent": (
                100.0 * (rule_cost - total_cost) / rule_cost if rule_cost else 0.0
            ),
            "minimum_soc_kwh": min(
                float(np.min(result["storage_kwh"])) for result in day_results.values()
            ),
            "maximum_soc_kwh": max(
                float(np.max(result["storage_kwh"])) for result in day_results.values()
            ),
        },
    }


def metrics_from_q2(result):
    days = result["days"]
    terminal_gap = []
    ordered = sorted(days)
    for previous, current in zip(ordered[:-1], ordered[1:]):
        terminal_gap.append(
            abs(days[previous]["terminal_soc_kwh"] - days[current]["initial_soc_kwh"])
        )
    summary = result["result_summary"]
    return {
        "question_id": "Q2",
        "metrics": [
            {"name": "output_days", "value": float(len(days)), "unit": "days"},
            {
                "name": "total_purchase_kwh",
                "value": float(summary["total_purchase_kwh"]),
                "unit": "kWh",
            },
            {
                "name": "total_emergency_kwh",
                "value": float(summary["total_emergency_kwh"]),
                "unit": "kWh",
            },
            {
                "name": "total_cost_yuan",
                "value": float(summary["total_cost_yuan"]),
                "unit": "yuan",
            },
            {
                "name": "rule_total_cost_yuan",
                "value": float(summary["rule_total_cost_yuan"]),
                "unit": "yuan",
            },
            {
                "name": "saving_vs_rule_yuan",
                "value": float(summary["saving_vs_rule_yuan"]),
                "unit": "yuan",
            },
            {
                "name": "saving_vs_rule_percent",
                "value": float(summary["saving_vs_rule_percent"]),
                "unit": "percent",
            },
            {
                "name": "maximum_daily_terminal_gap_kwh",
                "value": float(max(terminal_gap) if terminal_gap else 0.0),
                "unit": "kWh",
            },
        ],
    }

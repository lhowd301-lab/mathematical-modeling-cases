from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix


ROOT = Path(__file__).resolve().parents[3]
CLEAN_DIR = ROOT / "paper_output" / "data_cleaned"

DELTA_HOURS = 1.0 / 6.0
ETA_CHARGE = 0.9
ETA_DISCHARGE = 0.9
SOC_MIN = 1200.0
SOC_MAX = 10800.0
INITIAL_SOC = 6000.0
MAX_PERIOD_ENERGY = 5000.0 * DELTA_HOURS
OUTPUT_START = "2025-02-01"
OUTPUT_END = "2025-12-31"
ORIGIN_HOURS = [0, 6, 12, 18]
SPECIFIED_DATES = ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"]


def load_annual_data():
    path = CLEAN_DIR / "annual_10min.csv"
    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame["date"] = frame["date"].astype(str)
    frame["interval_id"] = frame["interval_id"].astype(int)
    return frame.sort_values(["date", "interval_id"]).reset_index(drop=True)


def load_attachment1_data():
    path = CLEAN_DIR / "attachment1_10min.csv"
    frame = pd.read_csv(path, encoding="utf-8-sig")
    return frame.sort_values("interval_id").reset_index(drop=True)


def load_forecast_by_origin():
    path = CLEAN_DIR / "pv_forecast_10min_by_origin.csv"
    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame["forecast_date"] = frame["forecast_date"].astype(str)
    frame["interval_id"] = frame["interval_id"].astype(int)
    frame["forecast_origin_hour"] = frame["forecast_origin_hour"].astype(int)
    return frame.sort_values(
        ["forecast_date", "forecast_origin_hour", "interval_id"]
    ).reset_index(drop=True)


def day_frame(annual_frame, day):
    subset = annual_frame[annual_frame["date"] == str(day)].sort_values("interval_id")
    if len(subset) != 144:
        raise ValueError("day {} does not contain 144 intervals".format(day))
    return subset


def output_dates(annual_frame):
    dates = sorted(annual_frame["date"].unique())
    return [day for day in dates if OUTPUT_START <= day <= OUTPUT_END]


def forecast_vector(forecast_frame, day, origin_hour):
    subset = forecast_frame[
        (forecast_frame["forecast_date"] == str(day))
        & (forecast_frame["forecast_origin_hour"] == int(origin_hour))
    ].sort_values("interval_id")
    if len(subset) != 144:
        raise ValueError(
            "forecast {} origin {} does not contain 144 intervals".format(
                day, origin_hour
            )
        )
    values = subset["pv_forecast_kwh"].to_numpy(dtype=float)
    missing = np.isnan(values)
    if missing.any():
        raise ValueError(
            "forecast {} origin {} contains unavailable values in requested vector".format(
                day, origin_hour
            )
        )
    return values


def _add_equation(rows, cols, values, rhs, coefficients, right_hand_side):
    row_index = len(rhs)
    for column, coefficient in coefficients:
        if coefficient == 0:
            continue
        rows.append(row_index)
        cols.append(column)
        values.append(coefficient)
    rhs.append(right_hand_side)


def _actual_adjustment_cost(prices, initial_plan, final_purchase, emergency):
    below = final_purchase <= initial_plan
    cost = np.empty_like(final_purchase)
    cost[below] = (
        prices[below] * final_purchase[below]
        + 0.5 * prices[below] * (initial_plan[below] - final_purchase[below])
    )
    cost[~below] = (
        prices[~below] * initial_plan[~below]
        + 1.5 * prices[~below] * (final_purchase[~below] - initial_plan[~below])
    )
    emergency_cost = 5.0 * np.sum(prices * emergency)
    return float(np.sum(cost) + emergency_cost)


def settle_actual_dispatch(load_kwh, pv_kwh, purchase_kwh, charge_kwh, discharge_kwh):
    """Settle a planned dispatch against realized load and PV."""
    actual_gap = (
        np.asarray(load_kwh, dtype=float)
        + np.asarray(charge_kwh, dtype=float)
        - np.asarray(purchase_kwh, dtype=float)
        - np.asarray(pv_kwh, dtype=float)
        - np.asarray(discharge_kwh, dtype=float)
    )
    emergency = np.maximum(actual_gap, 0.0)
    curtailment = np.maximum(-actual_gap, 0.0)
    return emergency, curtailment


def solve_dispatch(
    prices,
    load_kwh,
    pv_kwh,
    initial_soc,
    terminal_soc=None,
    initial_plan=None,
):
    """Solve the common storage dispatch LP.

    When initial_plan is None, the objective is normal purchase cost.
    When initial_plan is provided, purchase is priced as the problem-3
    adjustment contract relative to the initial 00:00 plan.
    """
    prices = np.asarray(prices, dtype=float)
    load_kwh = np.asarray(load_kwh, dtype=float)
    pv_kwh = np.asarray(pv_kwh, dtype=float)
    n = len(prices)
    if len(load_kwh) != n or len(pv_kwh) != n:
        raise ValueError("dispatch vectors must have equal length")
    adjustment_mode = initial_plan is not None
    if adjustment_mode:
        initial_plan = np.asarray(initial_plan, dtype=float)
        if len(initial_plan) != n:
            raise ValueError("initial_plan must have the same length")
        base = slice(0, n)
        excess = slice(n, 2 * n)
        charge = slice(2 * n, 3 * n)
        discharge = slice(3 * n, 4 * n)
        soc = slice(4 * n, 5 * n)
        curtail = slice(5 * n, 6 * n)
        emergency = slice(6 * n, 7 * n)
        variable_count = 7 * n
    else:
        purchase = slice(0, n)
        charge = slice(n, 2 * n)
        discharge = slice(2 * n, 3 * n)
        soc = slice(3 * n, 4 * n)
        curtail = slice(4 * n, 5 * n)
        emergency = slice(5 * n, 6 * n)
        variable_count = 6 * n

    rows = []
    cols = []
    values = []
    rhs = []

    for t in range(n):
        coefficients = []
        if adjustment_mode:
            coefficients.extend(
                [
                    (base.start + t, 1.0),
                    (excess.start + t, 1.0),
                    (discharge.start + t, 1.0),
                    (emergency.start + t, 1.0),
                    (charge.start + t, -1.0),
                    (curtail.start + t, -1.0),
                ]
            )
        else:
            coefficients.extend(
                [
                    (purchase.start + t, 1.0),
                    (discharge.start + t, 1.0),
                    (emergency.start + t, 1.0),
                    (charge.start + t, -1.0),
                    (curtail.start + t, -1.0),
                ]
            )
        _add_equation(
            rows,
            cols,
            values,
            rhs,
            coefficients,
            load_kwh[t] - pv_kwh[t],
        )

    for t in range(n):
        coefficients = [
            (soc.start + t, 1.0),
            (charge.start + t, -ETA_CHARGE),
            (discharge.start + t, 1.0 / ETA_DISCHARGE),
        ]
        if t > 0:
            coefficients.append((soc.start + t - 1, -1.0))
            right_hand_side = 0.0
        else:
            right_hand_side = float(initial_soc)
        _add_equation(rows, cols, values, rhs, coefficients, right_hand_side)

    if terminal_soc is not None:
        _add_equation(
            rows,
            cols,
            values,
            rhs,
            [(soc.start + n - 1, 1.0)],
            float(terminal_soc),
        )

    a_eq = coo_matrix(
        (values, (rows, cols)),
        shape=(len(rhs), variable_count),
    ).tocsr()
    b_eq = np.asarray(rhs, dtype=float)

    objective = np.zeros(variable_count, dtype=float)
    if adjustment_mode:
        for t in range(n):
            objective[base.start + t] = 0.5 * prices[t]
            objective[excess.start + t] = 1.5 * prices[t]
        constant_cost = 0.5 * float(np.sum(prices * initial_plan))
    else:
        constant_cost = 0.0
        for t in range(n):
            objective[purchase.start + t] = prices[t]
    for t in range(n):
        objective[emergency.start + t] = 5.0 * prices[t]

    bounds = []
    if adjustment_mode:
        bounds.extend([(0.0, float(initial_plan[t])) for t in range(n)])
        bounds.extend([(0.0, None) for _ in range(n)])
    else:
        bounds.extend([(0.0, None) for _ in range(n)])
    bounds.extend([(0.0, MAX_PERIOD_ENERGY) for _ in range(n)])
    bounds.extend([(0.0, MAX_PERIOD_ENERGY) for _ in range(n)])
    bounds.extend([(SOC_MIN, SOC_MAX) for _ in range(n)])
    bounds.extend([(0.0, None) for _ in range(n)])
    bounds.extend([(0.0, None) for _ in range(n)])

    result = linprog(
        objective,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        raise RuntimeError("dispatch LP failed: {}".format(result.message))

    solution = result.x
    if adjustment_mode:
        final_purchase = solution[base] + solution[excess]
    else:
        final_purchase = solution[purchase]
    charge_values = solution[charge]
    discharge_values = solution[discharge]
    soc_values = solution[soc]
    curtail_values = solution[curtail]
    emergency_values = solution[emergency]
    if adjustment_mode:
        actual_cost = _actual_adjustment_cost(
            prices,
            initial_plan,
            final_purchase,
            emergency_values,
        )
    else:
        actual_cost = float(
            np.sum(prices * final_purchase)
            + 5.0 * np.sum(prices * emergency_values)
        )

    return {
        "status": "optimal",
        "purchase_kwh": final_purchase,
        "charge_kwh": charge_values,
        "discharge_kwh": discharge_values,
        "storage_kwh": soc_values,
        "curtailment_kwh": curtail_values,
        "emergency_kwh": emergency_values,
        "cost_yuan": actual_cost,
        "objective_value": float(result.fun + constant_cost),
        "initial_soc_kwh": float(initial_soc),
        "terminal_soc_kwh": float(soc_values[-1]),
    }


def aggregate_four_hour(values):
    values = np.asarray(values, dtype=float)
    if len(values) != 144:
        raise ValueError("four-hour aggregation requires 144 values")
    return values.reshape(6, 24).sum(axis=1)


def interval_labels(frame=None):
    if frame is not None:
        return frame["result_template_interval_label"].tolist()
    path = CLEAN_DIR / "attachment1_10min.csv"
    table = pd.read_csv(path, encoding="utf-8-sig")
    return table["result2_interval_label"].tolist()


def finite_or_none(value):
    if value is None:
        return None
    number = float(value)
    if np.isfinite(number):
        return number
    return None

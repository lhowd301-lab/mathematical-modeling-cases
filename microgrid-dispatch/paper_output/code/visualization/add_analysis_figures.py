from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd


matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "paper_output" / "figures"
DATA = ROOT / "paper_output" / "data_cleaned"
RESULTS = ROOT / "paper_output" / "results"


def style():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.25
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["savefig.dpi"] = 300


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def workflow_figure():
    fig, axis = plt.subplots(figsize=(11, 5.6))
    axis.set_xlim(0, 12)
    axis.set_ylim(0, 6)
    axis.axis("off")
    boxes = [
        (0.5, 4.3, "附件1\n单日电价与光伏"),
        (3.2, 4.3, "附件2\n全年负载与光伏"),
        (5.9, 4.3, "附件3\n四时刻整点预报"),
        (8.6, 4.3, "附件4\n实时波动电价"),
        (2.0, 2.7, "统一时间轴\n144个10分钟时段"),
        (5.3, 2.7, "单位与状态转移\nkW→kWh，SOC动态"),
        (8.6, 2.7, "数据质量检验\n缺失、边界与映射"),
        (1.3, 0.9, "Q1确定性LP"),
        (3.8, 0.9, "Q2全年逐日LP"),
        (6.3, 0.9, "Q3滚动时域LP"),
        (8.8, 0.9, "Q4波动价重算"),
    ]
    for x, y, text in boxes:
        axis.add_patch(
            FancyBboxPatch(
                (x, y),
                2.0,
                0.8,
                boxstyle="round,pad=0.08,rounding_size=0.08",
                linewidth=1.2,
                edgecolor="#4c78a8",
                facecolor="#eef3fa",
            )
        )
        axis.text(x + 1.0, y + 0.4, text, ha="center", va="center", fontsize=9)
    arrows = [
        ((1.5, 4.3), (3.0, 3.5)),
        ((4.2, 4.3), (3.0, 3.5)),
        ((6.9, 4.3), (6.3, 3.5)),
        ((9.6, 4.3), (9.6, 3.5)),
        ((3.0, 2.7), (2.3, 1.7)),
        ((6.3, 2.7), (4.8, 1.7)),
        ((6.3, 2.7), (7.3, 1.7)),
        ((9.6, 2.7), (9.8, 1.7)),
    ]
    for start, end in arrows:
        axis.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=12,
                linewidth=1.1,
                color="#6b7280",
            )
        )
    axis.set_title("数据、预报展开与四问求解的技术路线", fontsize=14, pad=14)
    return save(fig, "fig_data_workflow.png")


def charge_heatmap():
    frame = pd.read_excel(RESULTS / "result2.xlsx", sheet_name="充放电量")
    charge = frame["充电量"].to_numpy(dtype=float).reshape(334, 6)
    discharge = frame["放电量"].to_numpy(dtype=float).reshape(334, 6)
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    for axis, matrix, title, cmap in [
        (axes[0], charge, "充电量", "Blues"),
        (axes[1], discharge, "放电量", "Greens"),
    ]:
        image = axis.imshow(matrix.T, aspect="auto", cmap=cmap, interpolation="nearest")
        axis.set_yticks(range(6))
        axis.set_yticklabels(["0-4", "4-8", "8-12", "12-16", "16-20", "20-24"])
        axis.set_ylabel("四小时时段")
        axis.set_title("问题二全年储能{}热力图".format(title))
        fig.colorbar(image, ax=axis, label="kWh")
    axes[1].set_xlabel("输出期日期序号（2025-02-01 起）")
    return save(fig, "fig_q2_charge_heatmap.png")


def saving_waterfall():
    strategies = ["A", "B", "C", "D"]
    costs = [17884109.548795793, 17867845.74392725, 17768207.967099786, 17768214.41249766]
    base = costs[0]
    fig, axis = plt.subplots(figsize=(9, 5))
    labels = ["A 基准", "B 节省", "C 再节省", "D 相对C"]
    deltas = [base, costs[0] - costs[1], costs[1] - costs[2], costs[2] - costs[3]]
    running = [0, costs[0] - costs[1], costs[0] - costs[2], costs[0] - costs[3]]
    colors = ["#4c78a8", "#54a24b", "#54a24b", "#e45756"]
    for index, (label, delta, start, color) in enumerate(zip(labels, deltas, running, colors)):
        if index == 0:
            axis.bar(label, delta, color=color)
            axis.text(index, delta, "{:.0f}".format(delta), ha="center", va="bottom", fontsize=9)
        else:
            axis.bar(label, delta, bottom=start, color=color)
            axis.text(index, start + delta, "{:+.2f}".format(-delta), ha="center", va="bottom", fontsize=9)
    axis.set_ylabel("全年费用变化/元")
    axis.set_title("问题三预报时点增加带来的费用变化")
    return save(fig, "fig_q3_saving_waterfall.png")


def adjustment_error():
    plan = pd.read_excel(RESULTS / "result3.xlsx", sheet_name="计划购电量").iloc[:, 1:145]
    adjustment = pd.read_excel(RESULTS / "result3.xlsx", sheet_name="调整购电量").iloc[:, 1:145]
    adjustment_daily = np.abs(adjustment.to_numpy(dtype=float) - plan.to_numpy(dtype=float)).sum(axis=1)
    actual = pd.read_csv(DATA / "annual_10min.csv", encoding="utf-8-sig")
    forecast = pd.read_csv(DATA / "pv_forecast_10min_asof.csv", encoding="utf-8-sig")
    merged = actual.merge(
        forecast[["date", "interval_id", "pv_forecast_kw"]],
        on=["date", "interval_id"],
        how="left",
    )
    merged["date"] = merged["date"].astype(str)
    error = (
        merged.assign(abs_error=lambda x: (x["pv_actual_kw"] - x["pv_forecast_kw"]).abs())
        .groupby("date", as_index=False)["abs_error"]
        .mean()
    )
    error = error[error["date"] >= "2025-02-01"].reset_index(drop=True)
    fig, axis = plt.subplots(figsize=(8.5, 5.2))
    axis.scatter(error["abs_error"], adjustment_daily, alpha=0.5, s=14, color="#4c78a8")
    axis.set_xlabel("日均光伏预报绝对误差/kW")
    axis.set_ylabel("日计划调整绝对量/kWh")
    axis.set_title("问题三预报误差与滚动调整幅度")
    return save(fig, "fig_q3_adjust_forecast_error.png")


def sensitivity_figure():
    labels = ["基准", "无储能", "往返效率90%", "功率3000kW", "功率4000kW"]
    values = [35126.948589289634, 48052.046590846665, 33801.495542222016, 35788.440070007324, 35247.87089961686]
    fig, axis = plt.subplots(figsize=(9.5, 5.2))
    bars = axis.bar(labels, values, color=["#4c78a8", "#e45756", "#f58518", "#72b7b2", "#54a24b"])
    axis.set_ylabel("问题一购电费/元")
    axis.set_title("问题一关键参数敏感性")
    axis.tick_params(axis="x", rotation=15)
    for bar, value in zip(bars, values):
        axis.text(bar.get_x() + bar.get_width() / 2, value, "{:.0f}".format(value), ha="center", va="bottom", fontsize=8)
    return save(fig, "fig_sensitivity_q1.png")


def main():
    style()
    paths = [
        workflow_figure(),
        charge_heatmap(),
        saving_waterfall(),
        adjustment_error(),
        sensitivity_figure(),
    ]
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()

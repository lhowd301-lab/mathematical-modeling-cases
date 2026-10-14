from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np


matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[3]
FIGURE_DIR = ROOT / "paper_output" / "figures"


def _style():
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Source Han Sans SC",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.25
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["savefig.dpi"] = 300


def _record(figure_id, question_id, title, path, purpose):
    return {
        "figure_id": figure_id,
        "question_id": question_id,
        "title": title,
        "path": Path(path).relative_to(ROOT).as_posix(),
        "exists": Path(path).exists(),
        "ok": Path(path).exists(),
        "placeholder": False,
        "status": "ready" if Path(path).exists() else "failed",
        "paper_usage": purpose,
    }


def _save(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _q1_figures(q1):
    records = []
    x = np.arange(1, 145)

    path = FIGURE_DIR / "fig_q1_1.png"
    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    axes[0].plot(x, q1["price_yuan_per_kwh"], color="#d62728")
    axes[0].set_ylabel("电价 (元/kWh)")
    axes[1].plot(x, q1["load_kwh"], color="#1f77b4")
    axes[1].set_ylabel("负载 (kWh/10min)")
    axes[2].plot(x, q1["pv_forecast_kwh"], color="#2ca02c")
    axes[2].set_ylabel("预测光伏 (kWh/10min)")
    axes[2].set_xlabel("10 分钟时段序号")
    fig.suptitle("问题一：电价、负载和光伏预测日曲线")
    _save(fig, path)
    records.append(_record("fig_q1_1", "Q1", "电价-负载-光伏日曲线", path, "问题一结果分析"))

    path = FIGURE_DIR / "fig_q1_2.png"
    fig, axis = plt.subplots(figsize=(11, 4.8))
    axis.plot(x, q1["purchase_kwh"], color="#1f77b4", label="购电量")
    axis.plot(x, q1["charge_kwh"], color="#ff7f0e", label="充电量")
    axis.plot(x, -np.asarray(q1["discharge_kwh"]), color="#2ca02c", label="放电量（负向）")
    axis.axhline(0, color="#444444", linewidth=0.8)
    axis.set_xlabel("10 分钟时段序号")
    axis.set_ylabel("能量 (kWh/10min)")
    axis.set_title("问题一：购电量与储能充放电量")
    axis.legend(ncol=3)
    _save(fig, path)
    records.append(_record("fig_q1_2", "Q1", "购电量与储能充放电量叠加图", path, "问题一调度行为分析"))

    path = FIGURE_DIR / "fig_q1_3.png"
    fig, axis = plt.subplots(figsize=(11, 4.8))
    axis.plot(x, q1["storage_kwh"], color="#9467bd", label="储电量")
    axis.axhline(1200, color="#d62728", linestyle="--", label="下界 1200")
    axis.axhline(10800, color="#d62728", linestyle="--", label="上界 10800")
    axis.set_xlabel("10 分钟时段序号")
    axis.set_ylabel("储电量 (kWh)")
    axis.set_title("问题一：储能 SOC 轨迹与边界")
    axis.legend()
    _save(fig, path)
    records.append(_record("fig_q1_3", "Q1", "储能 SOC 轨迹与上下界", path, "问题一约束检验"))
    return records


def _q2_figures(q2):
    records = []
    days = sorted(q2["days"])
    daily_cost = [q2["days"][day]["cost_yuan"] for day in days]

    path = FIGURE_DIR / "fig_q2_1.png"
    fig, axis = plt.subplots(figsize=(11, 4.8))
    axis.plot(days, daily_cost, color="#1f77b4", linewidth=1.0)
    axis.set_xlabel("日期")
    axis.set_ylabel("日购电费 (元)")
    axis.set_title("问题二：2025 年逐日购电费")
    axis.tick_params(axis="x", rotation=45)
    step = max(1, len(days) // 12)
    for index, label in enumerate(axis.get_xticklabels()):
        if index % step:
            label.set_visible(False)
    _save(fig, path)
    records.append(_record("fig_q2_1", "Q2", "逐日购电费时间序列", path, "问题二全年结果分析"))

    selected = [day for day in ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"] if day in q2["days"]]
    path = FIGURE_DIR / "fig_q2_2.png"
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    for color, day in zip(colors, selected):
        result = q2["days"][day]
        x = np.arange(1, 145)
        axes[0].plot(x, result["purchase_kwh"], color=color, label=day)
        axes[1].plot(x, result["storage_kwh"], color=color, label=day)
    axes[0].set_ylabel("购电量 (kWh)")
    axes[1].set_ylabel("储电量 (kWh)")
    axes[1].set_xlabel("10 分钟时段序号")
    axes[0].set_title("问题二：四个指定日期购电与储能轨迹")
    axes[0].legend(ncol=2)
    _save(fig, path)
    records.append(_record("fig_q2_2", "Q2", "四个指定日期调度曲线", path, "问题二指定日期结果分析"))

    path = FIGURE_DIR / "fig_q2_3.png"
    soc_min = [float(np.min(q2["days"][day]["storage_kwh"])) for day in days]
    soc_mean = [float(np.mean(q2["days"][day]["storage_kwh"])) for day in days]
    soc_max = [float(np.max(q2["days"][day]["storage_kwh"])) for day in days]
    fig, axis = plt.subplots(figsize=(11, 4.8))
    axis.fill_between(days, soc_min, soc_max, color="#9467bd", alpha=0.25, label="日内 SOC 范围")
    axis.plot(days, soc_mean, color="#9467bd", linewidth=1.2, label="日均 SOC")
    axis.axhline(1200, color="#d62728", linestyle="--", linewidth=1.0)
    axis.axhline(10800, color="#d62728", linestyle="--", linewidth=1.0)
    axis.set_xlabel("日期")
    axis.set_ylabel("储电量 (kWh)")
    axis.set_title("问题二：储能 SOC 全年轨迹")
    axis.tick_params(axis="x", rotation=45)
    for index, label in enumerate(axis.get_xticklabels()):
        if index % step:
            label.set_visible(False)
    axis.legend()
    _save(fig, path)
    records.append(_record("fig_q2_3", "Q2", "储能 SOC 全年轨迹", path, "问题二储能连续性检验"))

    path = FIGURE_DIR / "fig_q2_rule_compare.png"
    labels = ["预报信息 LP", "固定峰谷规则"]
    values = [
        float(q2["result_summary"]["total_cost_yuan"]),
        float(q2["result_summary"]["rule_total_cost_yuan"]),
    ]
    fig, axis = plt.subplots(figsize=(8, 4.8))
    bars = axis.bar(labels, values, color=["#4c78a8", "#f58518"])
    axis.set_ylabel("全年总费用 (元)")
    axis.set_title("问题二：线性规划与固定峰谷规则策略对比")
    for bar, value in zip(bars, values):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value,
            "{:.0f}".format(value),
            ha="center",
            va="bottom",
            fontsize=9,
        )
    _save(fig, path)
    records.append(
        _record(
            "fig_q2_rule_compare",
            "Q2",
            "线性规划与固定峰谷规则策略对比",
            path,
            "量化优化模型的策略增益",
        )
    )
    return records


def _q3_figures(q3):
    records = []
    selected_day = "2025-06-21"
    day = q3["days"][selected_day]
    x = np.arange(1, 145)

    path = FIGURE_DIR / "fig_q3_1.png"
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(x, day["initial_plan_kwh"], color="#1f77b4", label="0:00 初始计划")
    axes[0].plot(x, day["purchase_kwh"], color="#d62728", label="滚动调整后")
    axes[0].set_ylabel("购电量 (kWh)")
    axes[0].legend()
    axes[1].plot(x, day["storage_kwh"], color="#9467bd", label="最终储电量")
    axes[1].axhline(1200, color="#d62728", linestyle="--")
    axes[1].axhline(10800, color="#d62728", linestyle="--")
    axes[1].set_xlabel("10 分钟时段序号")
    axes[1].set_ylabel("储电量 (kWh)")
    fig.suptitle("问题三：初始计划、滚动调整和储能轨迹（{}）".format(selected_day))
    _save(fig, path)
    records.append(_record("fig_q3_1", "Q3", "初始计划与调整计划对比图", path, "问题三滚动策略分析"))

    path = FIGURE_DIR / "fig_q3_2.png"
    strategies = sorted(q3["strategy_results"])
    costs = [q3["strategy_results"][name]["total_cost_yuan"] for name in strategies]
    fig, axis = plt.subplots(figsize=(8, 4.8))
    bars = axis.bar(strategies, costs, color=["#4c78a8", "#f58518", "#54a24b", "#e45756"])
    axis.set_xlabel("预报策略")
    axis.set_ylabel("全年总费用 (元)")
    axis.set_title("问题三：预报时点消融实验")
    for bar, value in zip(bars, costs):
        axis.text(bar.get_x() + bar.get_width() / 2, value, "{:.0f}".format(value), ha="center", va="bottom", fontsize=8)
    _save(fig, path)
    records.append(_record("fig_q3_2", "Q3", "预报时点消融实验柱状图", path, "问题三回答是否需要新增预报"))

    path = FIGURE_DIR / "fig_q3_3.png"
    adjustment = [
        float(np.sum(np.abs(np.asarray(q3["days"][date]["purchase_kwh"]) - np.asarray(q3["days"][date]["initial_plan_kwh"]))))
        for date in sorted(q3["days"])
    ]
    costs = [q3["days"][date]["cost_yuan"] for date in sorted(q3["days"])]
    fig, axis = plt.subplots(figsize=(8, 5))
    axis.scatter(adjustment, costs, color="#4c78a8", alpha=0.65, s=18)
    axis.set_xlabel("每日计划调整绝对量 (kWh)")
    axis.set_ylabel("日费用 (元)")
    axis.set_title("问题三：计划调整幅度与日费用")
    _save(fig, path)
    records.append(_record("fig_q3_3", "Q3", "计划调整幅度与日费用", path, "问题三滚动调整效果分析"))

    path = FIGURE_DIR / "fig_q3_saving_waterfall.png"
    labels = ["A 基准", "B 相对A", "C 相对A", "D 相对A"]
    baseline = float(q3["strategy_results"]["A"]["total_cost_yuan"])
    changes = [
        0.0,
        float(q3["strategy_results"]["B"]["total_cost_yuan"]) - baseline,
        float(q3["strategy_results"]["C"]["total_cost_yuan"]) - baseline,
        float(q3["strategy_results"]["D"]["total_cost_yuan"]) - baseline,
    ]
    colors = ["#4c78a8", "#e45756", "#54a24b", "#8f8f8f"]
    fig, axis = plt.subplots(figsize=(8.4, 4.8))
    bars = axis.bar(labels, changes, color=colors)
    axis.axhline(0.0, color="#333333", linewidth=1)
    axis.set_ylabel("相对A策略的费用变化 (元)")
    axis.set_title("问题三：新增预报时点的费用变化")
    for bar, value in zip(bars, changes):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value,
            "{:+.2f}".format(value),
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=9,
        )
    _save(fig, path)
    records.append(_record("fig_q3_saving_waterfall", "Q3", "新增预报时点费用变化", path, "比较A/B/C/D策略的相对费用"))
    return records


def _q4_figures(q4, q2):
    records = []
    q4_2_days = sorted(q4["q4_2"]["days"])
    q4_3_days = sorted(q4["q4_3"]["days"])
    daily_2 = np.asarray([q4["q4_2"]["days"][day]["cost_yuan"] for day in q4_2_days])
    daily_3 = np.asarray([q4["q4_3"]["days"][day]["cost_yuan"] for day in q4_3_days])

    path = FIGURE_DIR / "fig_q4_1.png"
    price_matrix = np.asarray(
        [
            np.asarray(q4["q4_2"]["days"][day]["price_yuan_per_kwh"], dtype=float)
            for day in q4_2_days
        ]
    )
    quantiles = np.quantile(price_matrix, [0.05, 0.25, 0.5, 0.75, 0.95], axis=0)
    x = np.arange(1, 145)
    fig, axis = plt.subplots(figsize=(11, 4.8))
    axis.fill_between(x, quantiles[0], quantiles[4], color="#4c78a8", alpha=0.18, label="5%-95%")
    axis.fill_between(x, quantiles[1], quantiles[3], color="#4c78a8", alpha=0.28, label="25%-75%")
    axis.plot(x, quantiles[2], color="#e45756", label="中位数")
    axis.set_xlabel("10 分钟时段序号")
    axis.set_ylabel("电价 (元/kWh)")
    axis.set_title("问题四：全年波动电价的日内分位带")
    axis.legend()
    _save(fig, path)
    records.append(_record("fig_q4_1", "Q4", "波动电价日内分位带", path, "问题四价格波动特征"))

    path = FIGURE_DIR / "fig_q4_2.png"
    fig, axis = plt.subplots(figsize=(9, 5))
    axis.hist(daily_2, bins=30, alpha=0.55, color="#4c78a8", label="Q4-2")
    axis.hist(daily_3, bins=30, alpha=0.55, color="#e45756", label="Q4-3")
    axis.set_xlabel("日费用 (元)")
    axis.set_ylabel("天数")
    axis.set_title("问题四：Q4-2 与 Q4-3 日费用分布")
    axis.legend()
    _save(fig, path)
    records.append(_record("fig_q4_2", "Q4", "Q4-2 与 Q4-3 日费用分布", path, "问题四费用分布分析"))

    path = FIGURE_DIR / "fig_q4_3.png"
    diff = daily_3 - daily_2
    fig, axis = plt.subplots(figsize=(9, 5))
    axis.hist(diff, bins=30, color="#54a24b", alpha=0.8)
    axis.axvline(0, color="#333333", linewidth=1)
    axis.set_xlabel("Q4-3 日费用 - Q4-2 日费用 (元)")
    axis.set_ylabel("天数")
    axis.set_title("问题四：滚动调整的逐日费用差")
    _save(fig, path)
    records.append(_record("fig_q4_3", "Q4", "滚动调整的逐日费用差", path, "问题四滚动调整影响"))

    path = FIGURE_DIR / "fig_q4_4.png"
    labels = ["固定价 Q2", "波动价 Q4-2", "固定价 Q3", "波动价 Q4-3"]
    values = [
        float(q2["result_summary"]["total_cost_yuan"]),
        q4["result_summary"]["q4_2_total_cost_yuan"],
        q4["q4_3"]["strategy_results"]["C"]["total_cost_yuan"],
        q4["result_summary"]["q4_3_total_cost_yuan"],
    ]
    fig, axis = plt.subplots(figsize=(9, 5))
    bars = axis.bar(labels, values, color=["#4c78a8", "#f58518", "#54a24b", "#e45756"])
    axis.set_ylabel("全年费用 (元)")
    axis.set_title("问题四：固定价、波动价和滚动策略费用对比")
    axis.tick_params(axis="x", rotation=15)
    for bar, value in zip(bars, values):
        axis.text(bar.get_x() + bar.get_width() / 2, value, "{:.0f}".format(value), ha="center", va="bottom", fontsize=8)
    _save(fig, path)
    records.append(_record("fig_q4_4", "Q4", "固定价、波动价与多策略费用对比", path, "问题四费用对比分析"))
    return records


def generate_model_figures(q1, q2, q3, q4):
    _style()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    records.extend(_q1_figures(q1))
    records.extend(_q2_figures(q2))
    records.extend(_q3_figures(q3))
    records.extend(_q4_figures(q4, q2))
    return records

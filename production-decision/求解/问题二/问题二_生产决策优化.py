"""问题二：二零件单工序生产决策优化。

以“最终向一名顾客交付一件合格品”为单位建立再生过程模型：
- 检测通过的零配件记作“已认证”，拆解失败成品时可以无风险回收；
- 未检测零配件每次装配后若发生失败则被视为消耗品，需重新购入；
- 成品检测/拆解策略与两类误风险共同进入目标函数。
"""

import itertools
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "公共"))
from 绘图公共 import setup_chinese, despine, save_fig

setup_chinese()

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
FIG = BASE / "图片"
OUT = BASE / "结果"
LOG_DIR = BASE / "日志"
for d in (FIG, OUT, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "run.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger("q2")


def effective_certified_cost(price, test_cost, p):
    """检测情形：反复购入并检测，直到得到一个合格零配件的期望支出。"""
    return (price + test_cost) / max(1e-12, 1 - p)


def eval_strategy(row, decision):
    test1, test2, test_product, dismantle = decision
    p1, p2 = row["零配件1次品率"], row["零配件2次品率"]
    q = row["成品次品率"]
    price1, price2 = row["零配件1购买单价"], row["零配件2购买单价"]
    c1, c2 = row["零配件1检测成本"], row["零配件2检测成本"]
    c_assembly = row["成品装配成本"]
    c_product_test = row["成品检测成本"]
    sell = row["市场售价"]
    exchange = row["调换损失"]
    c_dis = row["拆解费用"]

    # 成功概率：未检测零配件必须恰好是正品，且装配工艺成功。
    good = 1.0
    untested_per_attempt = 0.0
    certified_once = 0.0
    effective_all = 0.0
    for tested, p, price, ctest in [
        (test1, p1, price1, c1),
        (test2, p2, price2, c2),
    ]:
        if tested:
            certified_once += effective_certified_cost(price, ctest, p)
            effective_all += effective_certified_cost(price, ctest, p)
        else:
            good *= 1 - p
            untested_per_attempt += price
            effective_all += price
    g = (1 - q) * good
    m = 1.0 / max(g, 1e-12)
    failures = m - 1.0

    if dismantle:
        expected_components = certified_once + m * untested_per_attempt
    else:
        expected_components = m * effective_all

    expected_cost = expected_components + c_assembly * m
    if test_product:
        expected_cost += c_product_test * m
    else:
        expected_cost += exchange * failures
    if dismantle:
        expected_cost += c_dis * failures

    profit = sell - expected_cost
    return {
        "profit_per_customer": profit,
        "expected_assembly_attempts": m,
        "expected_failures": failures,
        "expected_cost_per_customer": expected_cost,
        "success_probability": g,
        "expected_components_cost": expected_components,
    }


def label_decision(decision):
    return {
        "零配件1": "检测" if decision[0] else "不检测",
        "零配件2": "检测" if decision[1] else "不检测",
        "成品": "检测" if decision[2] else "不检测",
        "不合格成品": "拆解" if decision[3] else "不拆解",
    }


def main():
    table = pd.read_csv(ROOT / "数据" / "表1_问题二.csv")
    decisions = sorted(itertools.product([0, 1], repeat=4), key=lambda d: -sum(d))
    rows = []
    bests = []
    for _, row in table.iterrows():
        evals = []
        for dec in decisions:
            r = eval_strategy(row, dec)
            r["情况"] = int(row["情况"])
            r["检测零配件1"] = dec[0]
            r["检测零配件2"] = dec[1]
            r["检测成品"] = dec[2]
            r["拆解不合格成品"] = dec[3]
            evals.append(r)
        evals = pd.DataFrame(evals)
        evals["百件利润"] = evals["profit_per_customer"] * 100
        evals["百件装配次数"] = evals["expected_assembly_attempts"] * 100
        rows.append(evals)
        best_idx = int(evals["profit_per_customer"].idxmax())
        best = evals.loc[best_idx].to_dict()
        best["情况"] = int(row["情况"])
        best["方案说明"] = label_decision(
            (best["检测零配件1"], best["检测零配件2"], best["检测成品"], best["拆解不合格成品"])
        )
        bests.append(best)

    all_eval = pd.concat(rows, ignore_index=True)
    all_eval.to_csv(OUT / "全部策略指标.csv", index=False, encoding="utf-8-sig")
    best_df = pd.DataFrame(bests)
    columns = [
        "情况",
        "检测零配件1",
        "检测零配件2",
        "检测成品",
        "拆解不合格成品",
        "profit_per_customer",
        "expected_cost_per_customer",
        "expected_assembly_attempts",
        "expected_failures",
        "百件利润",
        "百件装配次数",
        "success_probability",
    ]
    best_df = best_df[columns].rename(
        columns={
            "profit_per_customer": "单顾客期望利润",
            "expected_cost_per_customer": "单顾客期望成本",
            "expected_assembly_attempts": "单顾客期望装配次数",
            "expected_failures": "单顾客期望退货或废品数",
            "success_probability": "单次装配成功概率",
            "百件利润": "百件期望利润",
            "百件装配次数": "百件期望装配次数",
        }
    )
    best_df.to_csv(OUT / "最优决策.csv", index=False, encoding="utf-8-sig")

    summary = {
        "problem": "问题二",
        "status": "success",
        "model": "不合格品再生过程期望利润模型",
        "sample_size_basis": "每名顾客对应一件最终合格品，百件口径由单顾客指标线性放大",
        "best_decisions": best_df.to_dict(orient="records"),
        "main_results": best_df.to_dict(orient="records"),
    }
    with open(OUT / "结果摘要.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    # 关键图：六种情况下 16 种策略的百件利润排序与最优利润对比。
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    order = decisions[:]
    legend = {}
    for idx, dec in enumerate(order):
        sub = all_eval[
            (all_eval["检测零配件1"] == dec[0])
            & (all_eval["检测零配件2"] == dec[1])
            & (all_eval["检测成品"] == dec[2])
            & (all_eval["拆解不合格成品"] == dec[3])
        ].sort_values("情况")
        vals = sub["百件利润"].values
        color = plt.cm.viridis(idx / 15)
        line, = ax.plot(vals, marker="o", ms=3, lw=1.0, color=color)
        legend[f"{'测' if dec[0] else '否'}1-{'测' if dec[1] else '否'}2-"
               f"{'测' if dec[2] else '否'}成-{'拆' if dec[3] else '不拆'}"] = line
    best_profit = best_df["百件期望利润"].values
    ax.scatter(best_df["情况"], best_profit, s=65, facecolors="none", edgecolors="#d62728", zorder=5, label="最优方案")
    ax.set_xlabel("情况")
    ax.set_ylabel("百件期望利润（元）")
    ax.set_xticks(best_df["情况"])
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7)
    ax.grid(alpha=0.3, linestyle="--")
    despine(ax)
    save_fig(fig, FIG / "问题二各策略利润对比.png")

    # 最优方案利润与结构对比柱状图
    fig2, ax2 = plt.subplots(figsize=(7.6, 4.4))
    x = best_df["情况"].astype(int).values
    ax2.bar(x, best_df["单顾客期望利润"], color="#4c72b0", width=0.52, edgecolor="white")
    ax2.set_xlabel("情况")
    ax2.set_ylabel("单顾客期望利润（元）")
    ax2.set_xticks(x)
    for xi, yi in zip(x, best_df["单顾客期望利润"]):
        ax2.text(xi, yi + 0.25, f"{yi:.2f}", ha="center", fontsize=8)
    ax2.grid(axis="y", alpha=0.3, linestyle="--")
    despine(ax2)
    save_fig(fig2, FIG / "问题二最优方案利润.png")

    logger.info("Q2 completed")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    t0 = time.time()
    main()
    print("elapsed_seconds", round(time.time() - t0, 3))

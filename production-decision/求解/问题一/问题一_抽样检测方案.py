"""问题一：最小二项双风险抽样方案。

把标称次品率 p0 视为接收质量限 AQL，把 2p0 视为明显不可接受的 LTPD，
分别控制两类误判风险，并在单次抽样的条件下搜索最小样本量。
"""

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "公共"))
from 绘图公共 import setup_chinese, despine, save_fig

setup_chinese()

BASE = Path(__file__).resolve().parent
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
logger = logging.getLogger("q1")


def reject_plan(p0, alpha=0.05, beta=0.10, p1=None):
    """拒收方案：拒绝区域 X>=c。

    要求 P(X>=c | p0)<=alpha 且 P(X>=c | p1)>=1-beta，样本量 n 最小。
    """
    p1 = p1 or 2 * p0
    for n in range(1, 2000):
        k = np.arange(1, n + 1)
        t0 = binom.sf(k - 1, n, p0)
        t1 = binom.sf(k - 1, n, p1)
        ok = np.where((t0 <= alpha) & (t1 >= 1 - beta))[0]
        if ok.size:
            c = int(ok[0]) + 1
            return {
                "n": n,
                "c": c,
                "reject_prob_at_p0": float(binom.sf(c - 1, n, p0)),
                "reject_prob_at_p1": float(binom.sf(c - 1, n, p1)),
                "accept_prob_at_p1": float(binom.cdf(c - 1, n, p1)),
                "alpha": alpha,
                "beta": beta,
                "p0": p0,
                "p1": p1,
            }
    raise RuntimeError("no reject plan found")


def accept_plan(p0, alpha=0.10, beta=0.10, p1=None):
    """接收方案：接受区域 X<=c。

    要求 P(X<=c | p0)>=1-alpha 且 P(X<=c | p1)<=beta，样本量 n 最小。
    """
    p1 = p1 or 2 * p0
    for n in range(1, 2000):
        k = np.arange(0, n)
        a0 = binom.cdf(k, n, p0)
        a1 = binom.cdf(k, n, p1)
        ok = np.where((a0 >= 1 - alpha) & (a1 <= beta))[0]
        if ok.size:
            c = int(ok[0])
            return {
                "n": n,
                "c": c,
                "accept_prob_at_p0": float(binom.cdf(c, n, p0)),
                "accept_prob_at_p1": float(binom.cdf(c, n, p1)),
                "reject_prob_at_p0": float(binom.sf(c, n, p0)),
                "alpha": alpha,
                "beta": beta,
                "p0": p0,
                "p1": p1,
            }
    raise RuntimeError("no accept plan found")


def main():
    p0 = 0.10
    plan_reject = reject_plan(p0, alpha=0.05, beta=0.10, p1=0.20)
    plan_accept = accept_plan(p0, alpha=0.10, beta=0.10, p1=0.20)

    # 敏感性：若把“超标不可接受水平”改为 1.5/2/3 倍标称值，方案如何变化。
    sens_rows = []
    for mult, alpha, beta in [
        (1.5, 0.05, 0.10),
        (2.0, 0.05, 0.10),
        (3.0, 0.05, 0.10),
        (2.0, 0.05, 0.05),
        (2.0, 0.10, 0.10),
    ]:
        pr = reject_plan(p0, alpha=alpha, beta=beta, p1=p0 * mult)
        pa = accept_plan(p0, alpha=0.10, beta=beta, p1=p0 * mult)
        sens_rows.append(
            {
                "超标倍数": mult,
                "拒收alpha": alpha,
                "拒收beta": beta,
                "拒收样本量n": pr["n"],
                "拒收阈值c": pr["c"],
                "接收样本量n": pa["n"],
                "接收阈值c": pa["c"],
            }
        )
    sens = pd.DataFrame(sens_rows)

    # OC 曲线按 p 从 0 到 0.4 计算。
    grid = np.linspace(0.0, 0.40, 401)
    oc_reject = np.array([binom.sf(plan_reject["c"] - 1, plan_reject["n"], p) for p in grid])
    oc_accept = np.array([binom.cdf(plan_accept["c"], plan_accept["n"], p) for p in grid])
    oc = pd.DataFrame(
        {
            "真实次品率p": grid,
            "95%拒收方案拒收概率": oc_reject,
            "90%接收方案接收概率": oc_accept,
        }
    )

    summary = {
        "problem": "问题一",
        "status": "success",
        "nominal": p0,
        "scenario_1_95_reject": plan_reject,
        "scenario_2_90_accept": plan_accept,
        "rule_text": {
            "scenario_1": "抽取109件，若不合格件数>=17，则以不超过5%的伪拒风险认定次品率超过10%并拒收",
            "scenario_2": "抽取86件，若不合格件数<=12，则接受该批；在p=10%时接收概率>=90%，在p=20%时误收概率<=10%",
        },
        "main_results": {
            "n_reject": plan_reject["n"],
            "c_reject": plan_reject["c"],
            "n_accept": plan_accept["n"],
            "c_accept": plan_accept["c"],
        },
        "sensitivity_sample_size": sens.to_dict(orient="records"),
    }
    with open(OUT / "结果摘要.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    pd.DataFrame([plan_reject, plan_accept]).to_csv(OUT / "主要结果.csv", index=False, encoding="utf-8-sig")
    sens.to_csv(OUT / "样本量敏感性.csv", index=False, encoding="utf-8-sig")
    oc.to_csv(OUT / "OC曲线数据.csv", index=False, encoding="utf-8-sig")

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(grid, oc_reject, label="95%信度拒收方案", color="#1f77b4", lw=1.8)
    ax.plot(grid, oc_accept, label="90%信度接收方案", color="#d62728", lw=1.8)
    ax.axvline(0.10, color="gray", ls=":", lw=1)
    ax.axvline(0.20, color="gray", ls=":", lw=1)
    ax.text(0.105, 0.96, "标称值 10%", fontsize=9, color="dimgray")
    ax.text(0.205, 0.96, "不可接受水平 20%", fontsize=9, color="dimgray")
    ax.set_xlabel("真实次品率 $p$")
    ax.set_ylabel("采取指定行动的概率")
    ax.legend(loc="center right")
    ax.grid(alpha=0.3, linestyle="--")
    despine(ax)
    save_fig(fig, FIG / "抽检方案OC曲线.png")

    logger.info("Q1 completed: n_reject=%s c_reject=%s n_accept=%s c_accept=%s",
                plan_reject["n"], plan_reject["c"], plan_accept["n"], plan_accept["c"])
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    t0 = time.time()
    main()
    print("elapsed_seconds", round(time.time() - t0, 3))

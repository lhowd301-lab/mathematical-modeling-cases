"""问题四：把题二/题三的次品率视为抽样估计结果并重新决策。

用问题一中的双风险抽样框架对每个名义次品率求保守估计：
- 先按 95% 拒收、p1=2p0、beta=10% 求出该批次的最小样本量 n；
- 假设抽样观测数 x=round(p0*n)，再取单侧 95% Wilson 上界作为风险调整点估计；
- 将保守点估计代回问题二、问题三的期望利润模型重新求解。
"""

import itertools
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom, norm

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


def reject_plan(p0, alpha=0.05, beta=0.10, p1=None):
    p1 = p1 or 2 * p0
    for n in range(1, 4000):
        k = np.arange(1, n + 1)
        t0 = binom.sf(k - 1, n, p0)
        t1 = binom.sf(k - 1, n, p1)
        ok = np.where((t0 <= alpha) & (t1 >= 1 - beta))[0]
        if ok.size:
            return n, int(ok[0]) + 1
    raise RuntimeError("no plan")


def wilson_upper(x, n, z=norm.ppf(0.95)):
    if n <= 0:
        return 1.0
    phat = x / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return min(1.0, center + half)


def conservative_estimate(p0):
    n, _ = reject_plan(p0, alpha=0.05, beta=0.10, p1=2 * p0)
    x = int(round(p0 * n))
    x = max(1, min(x, n))
    return {"p0": p0, "n": n, "x": x, "p_high": float(wilson_upper(x, n))}


def certified_cost(price, test_cost, p):
    return (price + test_cost) / max(1e-12, 1 - p)


def q2_eval(row, dec):
    test1, test2, test_product, dismantle = dec
    p1, p2 = row["零配件1次品率"], row["零配件2次品率"]
    q = row["成品次品率"]
    price1, price2 = row["零配件1购买单价"], row["零配件2购买单价"]
    c1, c2 = row["零配件1检测成本"], row["零配件2检测成本"]
    c_assembly = row["成品装配成本"]
    c_product_test = row["成品检测成本"]
    sell = row["市场售价"]
    exchange = row["调换损失"]
    c_dis = row["拆解费用"]
    good = 1.0
    certified_once = 0.0
    untested_per_attempt = 0.0
    effective_all = 0.0
    for tested, p, price, ctest in [
        (test1, p1, price1, c1),
        (test2, p2, price2, c2),
    ]:
        if tested:
            v = certified_cost(price, ctest, p)
            certified_once += v
            effective_all += v
        else:
            good *= 1 - p
            untested_per_attempt += price
            effective_all += price
    g = (1 - q) * good
    m = 1.0 / max(g, 1e-12)
    fail = m - 1.0
    comp = (certified_once + m * untested_per_attempt) if dismantle else m * effective_all
    cost = comp + c_assembly * m
    cost += (c_product_test * m) if test_product else (exchange * fail)
    if dismantle:
        cost += c_dis * fail
    return sell - cost


def solve_q2(table):
    decisions = list(itertools.product([0, 1], repeat=4))
    out = []
    for _, row in table.iterrows():
        values = [q2_eval(row, dec) for dec in decisions]
        idx = int(np.argmax(values))
        out.append(
            {
                "情况": int(row["情况"]),
                "检测零配件1": decisions[idx][0],
                "检测零配件2": decisions[idx][1],
                "检测成品": decisions[idx][2],
                "拆解不合格成品": decisions[idx][3],
                "单顾客期望利润": float(values[idx]),
                "百件期望利润": float(values[idx] * 100),
            }
        )
    return pd.DataFrame(out)


def build_groups_high(phigh_part, phigh_semi, phigh_final):
    groups = [
        {"name": "半成品1", "parts": [1, 2, 3], "parts_data": {
            1: {"p": phigh_part[1], "price": 2, "test": 1},
            2: {"p": phigh_part[2], "price": 8, "test": 1},
            3: {"p": phigh_part[3], "price": 12, "test": 2},
        }},
        {"name": "半成品2", "parts": [4, 5, 6], "parts_data": {
            4: {"p": phigh_part[4], "price": 2, "test": 1},
            5: {"p": phigh_part[5], "price": 8, "test": 1},
            6: {"p": phigh_part[6], "price": 12, "test": 2},
        }},
        {"name": "半成品3", "parts": [7, 8], "parts_data": {
            7: {"p": phigh_part[7], "price": 8, "test": 1},
            8: {"p": phigh_part[8], "price": 12, "test": 2},
        }},
    ]
    for g in groups:
        g["q"] = phigh_semi[int(g["name"][-1])]
        g["assembly"] = 8
        g["semi_test"] = 4
        g["semi_dis"] = 6
    final = {
        "q": phigh_final,
        "assembly": 8,
        "final_test": 6,
        "final_dis": 10,
        "sell": 200,
        "exchange": 40,
    }
    return groups, final


def semi_candidates_high(group):
    candidates = []
    ids = group["parts"]
    for bits in itertools.product([0, 1], repeat=len(ids)):
        for output_test in (0, 1):
            for dis in (0, 1):
                cert_once = 0.0
                untested = 0.0
                eff_all = 0.0
                good = 1.0
                for bit, pid in zip(bits, ids):
                    d = group["parts_data"][pid]
                    if bit:
                        val = certified_cost(d["price"], d["test"], d["p"])
                        cert_once += val
                        eff_all += val
                    else:
                        good *= 1 - d["p"]
                        untested += d["price"]
                        eff_all += d["price"]
                g = (1 - group["q"]) * good
                m = 1.0 / max(g, 1e-12)
                fail = m - 1.0
                if output_test:
                    comp = (cert_once + m * untested) if dis else m * eff_all
                    cost = comp + 8 * m + 4 * m + (6 * fail if dis else 0)
                    candidates.append({"cert": True, "cost": cost, "p": 0.0, "parts": dict(zip(ids, bits)),
                                       "semi_test": output_test, "semi_dis": dis})
                else:
                    p_eff = 1 - (1 - group["q"]) * good
                    candidates.append({"cert": False, "cost": eff_all + 8, "p": p_eff,
                                       "parts": dict(zip(ids, bits)), "semi_test": output_test, "semi_dis": 0})
    return candidates


def final_eval_high(semi_cands, groups, final, ftest, fdis):
    cert_cost = 0.0
    uncost = 0.0
    good = 1.0
    for cand in semi_cands:
        if cand["cert"]:
            cert_cost += cand["cost"]
        else:
            good *= 1 - cand["p"]
            uncost += cand["cost"]
    g = (1 - final["q"]) * good
    m = 1.0 / max(g, 1e-12)
    fail = m - 1.0
    comp = (cert_cost + m * uncost) if fdis else m * (cert_cost + uncost)
    cost = comp + final["assembly"] * m
    cost += (final["final_test"] * m) if ftest else (final["exchange"] * fail)
    if fdis:
        cost += final["final_dis"] * fail
    return 200 - cost


def solve_q3(phigh_part, phigh_semi, phigh_final):
    groups, final = build_groups_high(phigh_part, phigh_semi, phigh_final)
    cl = [semi_candidates_high(g) for g in groups]
    best_score = -np.inf
    best = None
    for c0, c1, c2 in itertools.product(*cl):
        for ft in (0, 1):
            for fd in (0, 1):
                score = final_eval_high([c0, c1, c2], groups, final, ft, fd)
                if score > best_score:
                    best_score = score
                    best = {"c0": c0, "c1": c1, "c2": c2, "ftest": ft, "fdis": fd}
    return best, best_score, groups


def main():
    ests = {}
    for p0 in (0.05, 0.10, 0.20):
        ests[p0] = conservative_estimate(p0)

    # 问题二
    table = pd.read_csv(ROOT / "数据" / "表1_问题二.csv")
    high = table.copy()
    for col in ["零配件1次品率", "零配件2次品率", "成品次品率"]:
        high[col] = high[col].map(lambda v: ests[float(v)]["p_high"])
    q2_high = solve_q2(high)
    q2_high.to_csv(OUT / "问题二抽样后最优决策.csv", index=False, encoding="utf-8-sig")

    # 问题三
    phigh_part = {i: ests[0.10]["p_high"] for i in range(1, 9)}
    phigh_semi = {i: ests[0.10]["p_high"] for i in (1, 2, 3)}
    phigh_final = ests[0.10]["p_high"]
    best, score, groups = solve_q3(phigh_part, phigh_semi, phigh_final)

    q3_row = {
        "半成品内部零件检测": [best["c0"]["parts"], best["c1"]["parts"], best["c2"]["parts"]],
        "半成品检测": [best["c0"]["semi_test"], best["c1"]["semi_test"], best["c2"]["semi_test"]],
        "半成品拆解": [best["c0"]["semi_dis"], best["c1"]["semi_dis"], best["c2"]["semi_dis"]],
        "半成品检测后成本": [best["c0"]["cost"], best["c1"]["cost"], best["c2"]["cost"]],
        "半成品是否已认证": [best["c0"]["cert"], best["c1"]["cert"], best["c2"]["cert"]],
        "成品检测": best["ftest"],
        "成品拆解": best["fdis"],
        "单顾客期望利润": float(score),
        "百件期望利润": float(score * 100),
    }
    with open(OUT / "问题三抽样后结果.json", "w", encoding="utf-8") as fh:
        json.dump(q3_row, fh, ensure_ascii=False, indent=2)

    summary = {
        "problem": "问题四",
        "status": "success",
        "method": "双风险抽样+单侧95%Wilson上界的风险调整重估",
        "estimates": {str(k): v for k, v in ests.items()},
        "q2_decisions": q2_high.to_dict(orient="records"),
        "q3_decisions": q3_row,
        "main_results": {
            "q2_百件利润": q2_high["百件期望利润"].tolist(),
            "q3_百件利润": score * 100,
        },
    }
    with open(OUT / "结果摘要.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    import matplotlib.pyplot as plt

    est_df = pd.DataFrame([{"p0": k, "p_high": v["p_high"], "n": v["n"]} for k, v in ests.items()]).sort_values("p0")
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.plot(est_df["p0"], est_df["p0"], "o-", label="名义次品率", color="#1f77b4")
    ax.plot(est_df["p0"], est_df["p_high"], "s--", label="95% Wilson 上界估计", color="#d62728")
    ax.set_xlabel("名义次品率")
    ax.set_ylabel("抽样保守估计值")
    ax.legend()
    ax.grid(alpha=0.3, linestyle="--")
    despine(ax)
    save_fig(fig, FIG / "问题四抽样重估对比.png")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    t0 = time.time()
    main()
    print("elapsed_seconds", round(time.time() - t0, 3))

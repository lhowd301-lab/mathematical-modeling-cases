"""问题三：两道工序、8 个零配件的树状生产决策。

装配结构：零配件 1-3 -> 半成品1；4-6 -> 半成品2；7-8 -> 半成品3；
三个半成品再装配为最终成品。每个半成品组独立枚举内部检测/拆解策略，
成品阶段再与半成品策略联合枚举。
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
logger = logging.getLogger("q3")


def certified_cost(price, test_cost, p):
    return (price + test_cost) / max(1e-12, 1 - p)


def build_groups():
    groups = [
        {
            "name": "半成品1",
            "parts": [1, 2, 3],
            "parts_data": {
                1: {"p": 0.10, "price": 2, "test": 1},
                2: {"p": 0.10, "price": 8, "test": 1},
                3: {"p": 0.10, "price": 12, "test": 2},
            },
        },
        {
            "name": "半成品2",
            "parts": [4, 5, 6],
            "parts_data": {
                4: {"p": 0.10, "price": 2, "test": 1},
                5: {"p": 0.10, "price": 8, "test": 1},
                6: {"p": 0.10, "price": 12, "test": 2},
            },
        },
        {
            "name": "半成品3",
            "parts": [7, 8],
            "parts_data": {
                7: {"p": 0.10, "price": 8, "test": 1},
                8: {"p": 0.10, "price": 12, "test": 2},
            },
        },
    ]
    semi_common = {"q": 0.10, "assembly": 8, "semi_test": 4, "semi_dis": 6}
    for g in groups:
        g.update(semi_common)
    final = {
        "q": 0.10,
        "assembly": 8,
        "final_test": 6,
        "final_dis": 10,
        "sell": 200,
        "exchange": 40,
        "semi_names": ["半成品1", "半成品2", "半成品3"],
    }
    return groups, final


def semi_candidates(group):
    """返回半成品组的所有内部策略候选。

    若 output_test=True，候选给出“得到一个检测合格半成品”的期望成本；
    否则给出“生产一个未检测半成品”的单次期望成本及该半成品的实际次品率。
    """
    part_ids = group["parts"]
    part_data = group["parts_data"]
    candidates = []
    for test_bits in itertools.product([0, 1], repeat=len(part_ids)):
        for output_test in (0, 1):
            for dis in (0, 1):
                certified_once = 0.0
                untested_per_attempt = 0.0
                effective_all = 0.0
                good = 1.0
                for bit, pid in zip(test_bits, part_ids):
                    info = part_data[pid]
                    if bit:
                        val = certified_cost(info["price"], info["test"], info["p"])
                        certified_once += val
                        effective_all += val
                    else:
                        good *= 1 - info["p"]
                        untested_per_attempt += info["price"]
                        effective_all += info["price"]
                g = (1 - group["q"]) * good
                m = 1.0 / max(g, 1e-12)
                fail = m - 1.0
                if output_test:
                    if dis:
                        comp = certified_once + m * untested_per_attempt
                    else:
                        comp = m * effective_all
                    cost = comp + group["assembly"] * m + group["semi_test"] * m
                    if dis:
                        cost += group["semi_dis"] * fail
                    candidates.append(
                        {
                            "certified": True,
                            "cost_cert": cost,
                            "p_eff": 0.0,
                            "parts_tests": dict(zip(part_ids, test_bits)),
                            "semi_test": output_test,
                            "semi_dis": dis,
                            "cost_attempt": None,
                        }
                    )
                else:
                    p_eff = 1.0 - (1 - group["q"]) * good
                    cost_attempt = effective_all + group["assembly"]
                    candidates.append(
                        {
                            "certified": False,
                            "cost_cert": None,
                            "p_eff": p_eff,
                            "cost_attempt": cost_attempt,
                            "parts_tests": dict(zip(part_ids, test_bits)),
                            "semi_test": output_test,
                            "semi_dis": 0,
                        }
                    )
    return candidates


def final_eval(semi_policies, groups, final, final_test, final_dis):
    certified_cost = 0.0
    uncertified_cost_per_attempt = 0.0
    good = 1.0
    cert_names = []
    for cand, group in zip(semi_policies, groups):
        if cand["certified"]:
            certified_cost += cand["cost_cert"]
            cert_names.append(group["name"])
        else:
            good *= 1 - cand["p_eff"]
            uncertified_cost_per_attempt += cand["cost_attempt"]
    g = (1 - final["q"]) * good
    m = 1.0 / max(g, 1e-12)
    fail = m - 1.0
    if final_dis:
        component_cost = certified_cost + m * uncertified_cost_per_attempt
    else:
        component_cost = m * (certified_cost + uncertified_cost_per_attempt)
    cost = component_cost + final["assembly"] * m
    if final_test:
        cost += final["final_test"] * m
    else:
        cost += final["exchange"] * fail
    if final_dis:
        cost += final["final_dis"] * fail
    profit = final["sell"] - cost
    return {
        "profit_per_customer": profit,
        "expected_assembly_attempts": m,
        "expected_failures": fail,
        "expected_cost_per_customer": cost,
        "success_probability": g,
        "certified_semi_names": cert_names,
    }


def main():
    groups, final = build_groups()
    candidate_lists = [semi_candidates(g) for g in groups]
    rows = []
    best_state = None
    best_score = -np.inf
    n_cases = 0
    for p0, p1, p2 in itertools.product(*candidate_lists):
        for final_test in (0, 1):
            for final_dis in (0, 1):
                out = final_eval([p0, p1, p2], groups, final, final_test, final_dis)
                n_cases += 1
                if out["profit_per_customer"] > best_score:
                    best_score = out["profit_per_customer"]
                    best_state = (p0, p1, p2, final_test, final_dis, out)
    cand0, cand1, cand2, final_test, final_dis, best = best_state
    semi_result = []
    for idx, cand in enumerate([cand0, cand1, cand2]):
        parts_tests = {str(k): ("检测" if v else "不检测") for k, v in cand["parts_tests"].items()}
        semi_result.append(
            {
                "半成品": groups[idx]["name"],
                "零配件检测": parts_tests,
                "半成品检测": "检测" if cand["semi_test"] else "不检测",
                "半成品拆解": "拆解" if cand["semi_dis"] else "不拆解",
                "certified": cand["certified"],
                "cost_cert_or_attempt": cand["cost_cert"] if cand["certified"] else cand["cost_attempt"],
                "semi_eff_defect": cand["p_eff"],
            }
        )
    rows.append(
        {
            "半成品1方案": cand0["parts_tests"],
            "半成品2方案": cand1["parts_tests"],
            "半成品3方案": cand2["parts_tests"],
            "半成品检测": [cand0["semi_test"], cand1["semi_test"], cand2["semi_test"]],
            "成品检测": final_test,
            "成品拆解": final_dis,
            "单顾客期望利润": best["profit_per_customer"],
            "单顾客期望成本": best["expected_cost_per_customer"],
            "单顾客期望装配次数": best["expected_assembly_attempts"],
            "百件期望利润": best["profit_per_customer"] * 100,
            "百件期望装配次数": best["expected_assembly_attempts"] * 100,
            "半成品成本明细": semi_result,
        }
    )
    result_df = pd.DataFrame(rows)
    result_df.to_csv(OUT / "最优方案.csv", index=False, encoding="utf-8-sig")

    # 保存各半成品候选，用于绘制候选成本分布。
    candidates_df_rows = []
    for gi, (g, cands) in enumerate(zip(groups, candidate_lists)):
        for cand in cands:
            candidates_df_rows.append(
                {
                    "半成品": g["name"],
                    "零件检测组合": str(cand["parts_tests"]),
                    "是否检测半成品": cand["semi_test"],
                    "是否拆解半成品": cand["semi_dis"],
                    "certified": cand["certified"],
                    "成本或单次成本": cand["cost_cert"] if cand["certified"] else cand["cost_attempt"],
                    "半成品有效次品率": cand["p_eff"],
                }
            )
    pd.DataFrame(candidates_df_rows).to_csv(OUT / "半成品候选成本.csv", index=False, encoding="utf-8-sig")

    summary = {
        "problem": "问题三",
        "status": "success",
        "assembly_structure": {
            "半成品1": [1, 2, 3],
            "半成品2": [4, 5, 6],
            "半成品3": [7, 8],
            "成品": ["半成品1", "半成品2", "半成品3"],
        },
        "searched_policy_combinations": n_cases,
        "best_decision": rows[0],
        "main_results": rows[0],
    }
    with open(OUT / "结果摘要.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    import matplotlib.pyplot as plt

    cert_costs = []
    names = []
    for cand in [cand0, cand1, cand2]:
        cert_costs.append(cand["cost_cert"])
        names.append("")
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    semi_names = [g["name"] for g in groups]
    costs = [s["cost_cert_or_attempt"] for s in semi_result]
    x = np.arange(3)
    ax.bar(x, costs, color=["#4c72b0", "#55a868", "#dd8452"], width=0.45, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{s['半成品']}\n({('已检测' if s['certified'] else '未检测')})" for s in semi_result])
    ax.set_ylabel("提供一件半成品的期望成本（元）")
    for xi, yi in zip(x, costs):
        ax.text(xi, yi + 0.7, f"{yi:.2f}", ha="center")
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    despine(ax)
    save_fig(fig, FIG / "问题三半成品期望成本.png")
    logger.info("Q3 completed; searched=%s best_profit=%.4f", n_cases, best["profit_per_customer"])
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    t0 = time.time()
    main()
    print("elapsed_seconds", round(time.time() - t0, 3))

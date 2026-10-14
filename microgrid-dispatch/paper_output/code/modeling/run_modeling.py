from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from common_storage_lp import aggregate_four_hour
from q1_model import metrics_from_q1, run_q1
from q2_model import metrics_from_q2, run_q2
from q3_model import metrics_from_q3, run_q3
from q4_model import metrics_from_q4, run_q4
from result_contract_io import (
    RESULT_DIR,
    ROOT,
    TABLE_DIR,
    build_run_manifest,
    provenance,
    sha256_file,
    write_json,
    write_result1,
    write_result2,
    write_result3,
)

VISUALIZATION_DIR = ROOT / "paper_output" / "code" / "visualization"
sys.path.insert(0, str(VISUALIZATION_DIR))
from generate_model_figures import generate_model_figures


INPUT_PATHS = [
    ROOT / "paper_output" / "data_cleaned" / "attachment1_10min.csv",
    ROOT / "paper_output" / "data_cleaned" / "annual_10min.csv",
    ROOT / "paper_output" / "data_cleaned" / "pv_forecast_10min_by_origin.csv",
    ROOT / "paper_output" / "data_cleaned" / "pv_forecast_10min_asof.csv",
    ROOT / "paper_output" / "plan" / "model_route.json",
]


def jsonable(value):
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _table_index_item(question_id, table_id, path, title, purpose):
    path = Path(path)
    return {
        "question_id": question_id,
        "table_id": table_id,
        "title": title,
        "purpose": purpose,
        "path": path.relative_to(ROOT).as_posix(),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
        "status": "computed",
        "evidence_status": "computed",
    }


def _result_item(
    question_id,
    summary_text,
    details,
    run_context,
    output_artifacts,
):
    return {
        "question_id": question_id,
        "status": "computed",
        "evidence_status": "computed",
        "result_summary": summary_text,
        "details": jsonable(details),
        "execution_provenance": provenance(
            run_context,
            question_id,
            output_artifacts,
        ),
    }


def _metric_item(question_id, name, value, unit, role="primary"):
    return {
        "question_id": question_id,
        "metric_name": name,
        "metric_role": role,
        "value": float(value),
        "unit": unit,
        "status": "computed",
        "evidence_status": "computed",
    }


def _conclusion_item(question_id, text):
    return {
        "question_id": question_id,
        "conclusion_text": text,
        "status": "computed",
        "evidence_status": "computed",
    }


def write_tables(q1, q2, q3, q4):
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    tables = []

    q1_purchase = pd.DataFrame(
        {
            "interval_id": range(1, 145),
            "interval_label": q1["interval_label"],
            "purchase_kwh": q1["purchase_kwh"],
            "price_yuan_per_kwh": q1["price_yuan_per_kwh"],
            "purchase_cost_yuan": np.asarray(q1["purchase_kwh"])
            * np.asarray(q1["price_yuan_per_kwh"]),
        }
    )
    path = TABLE_DIR / "table_q1_purchase.csv"
    q1_purchase.to_csv(path, index=False, encoding="utf-8-sig")
    tables.append(
        _table_index_item("Q1", "table_q1_purchase", path, "问题一购电策略表", "保存144个时段的购电量和费用。")
    )

    q1_charge = pd.DataFrame(
        {
            "period": ["0:00-4:00", "4:00-8:00", "8:00-12:00", "12:00-16:00", "16:00-20:00", "20:00-24:00"],
            "charge_kwh": aggregate_four_hour(q1["charge_kwh"]),
            "discharge_kwh": aggregate_four_hour(q1["discharge_kwh"]),
        }
    )
    path = TABLE_DIR / "table_q1_charge_discharge.csv"
    q1_charge.to_csv(path, index=False, encoding="utf-8-sig")
    tables.append(
        _table_index_item("Q1", "table_q1_charge_discharge", path, "问题一储能充放电表", "保存六个四小时区间的充放电量。")
    )

    q2_daily = pd.DataFrame(
        [
            {
                "date": day,
                "purchase_kwh": float(np.sum(item["purchase_kwh"])),
                "charge_kwh": float(np.sum(item["charge_kwh"])),
                "discharge_kwh": float(np.sum(item["discharge_kwh"])),
                "emergency_kwh": float(np.sum(item["emergency_kwh"])),
                "planned_cost_yuan": float(item["planned_cost_yuan"]),
                "emergency_cost_yuan": float(item["emergency_cost_yuan"]),
                "cost_yuan": float(item["cost_yuan"]),
                "rule_cost_yuan": float(item["rule_cost_yuan"]),
                "rule_emergency_kwh": float(np.sum(item["rule_emergency_kwh"])),
                "initial_soc_kwh": float(item["initial_soc_kwh"]),
                "terminal_soc_kwh": float(item["terminal_soc_kwh"]),
            }
            for day, item in sorted(q2["days"].items())
        ]
    )
    path = TABLE_DIR / "table_q2_daily_summary.csv"
    q2_daily.to_csv(path, index=False, encoding="utf-8-sig")
    tables.append(
        _table_index_item("Q2", "table_q2_daily_summary", path, "问题二全年逐日汇总", "保存334天购电、储能和费用。")
    )

    q2_rule_summary = pd.DataFrame(
        [
            {
                "strategy": "forecast_linear_programming",
                "total_cost_yuan": q2["result_summary"]["total_cost_yuan"],
                "total_emergency_kwh": q2["result_summary"]["total_emergency_kwh"],
            },
            {
                "strategy": "fixed_peak_valley_rule",
                "total_cost_yuan": q2["result_summary"]["rule_total_cost_yuan"],
                "total_emergency_kwh": q2["result_summary"]["rule_total_emergency_kwh"],
            },
        ]
    )
    path = TABLE_DIR / "table_q2_rule_comparison.csv"
    q2_rule_summary.to_csv(path, index=False, encoding="utf-8-sig")
    tables.append(
        _table_index_item(
            "Q2",
            "table_q2_rule_comparison",
            path,
            "问题二线性规划与规则策略对比",
            "比较预报信息下线性规划与固定峰谷规则的全年费用和紧急购电量。",
        )
    )

    q3_strategy = pd.DataFrame(
        [
            {
                "strategy": name,
                "enabled_origins": ",".join(str(value) for value in item["enabled_origins"]),
                "total_cost_yuan": item["total_cost_yuan"],
                "total_adjustment_related_cost_yuan": item[
                    "total_adjustment_related_cost_yuan"
                ],
                "total_emergency_kwh": item["total_emergency_kwh"],
                "saving_vs_A_yuan": item["saving_vs_A_yuan"],
            }
            for name, item in sorted(q3["strategy_results"].items())
        ]
    )
    path = TABLE_DIR / "table_q3_forecast_ablation.csv"
    q3_strategy.to_csv(path, index=False, encoding="utf-8-sig")
    tables.append(
        _table_index_item("Q3", "table_q3_forecast_ablation", path, "问题三预报时点消融实验", "比较四种预报时刻策略的总费用和节约。")
    )

    q4_summary = pd.DataFrame(
        [
            {"scenario": "Q4-2", "total_cost_yuan": q4["q4_2"]["result_summary"]["total_cost_yuan"]},
            {"scenario": "Q4-3", "total_cost_yuan": q4["q4_3"]["result_summary"]["total_cost_yuan"]},
            {"scenario": "Q4-3 minus Q4-2", "total_cost_yuan": q4["result_summary"]["q4_3_minus_q4_2_yuan"]},
            {"scenario": "Risk mean", "total_cost_yuan": q4["result_summary"].get("risk_mean_cost_yuan")},
            {"scenario": "Risk VaR 95", "total_cost_yuan": q4["result_summary"].get("risk_var_95_yuan")},
            {"scenario": "Risk CVaR 95", "total_cost_yuan": q4["result_summary"].get("risk_cvar_95_yuan")},
        ]
    )
    path = TABLE_DIR / "table_q4_cost_summary.csv"
    q4_summary.to_csv(path, index=False, encoding="utf-8-sig")
    tables.append(
        _table_index_item("Q4", "table_q4_cost_summary", path, "问题四波动电价费用汇总", "比较问题4-2和问题4-3的费用。")
    )
    return tables


def main():
    parser = argparse.ArgumentParser(description="Run the complete C-problem modeling pipeline.")
    parser.add_argument(
        "--skip-stochastic",
        action="store_true",
        help="Skip the block-bootstrap VaR/CVaR price stress test.",
    )
    parser.add_argument("--scenario-count", type=int, default=200)
    parser.add_argument("--block-length", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20250101)
    args = parser.parse_args()

    started_at = datetime.now().isoformat(timespec="seconds")
    run_command = "python paper_output/code/modeling/run_modeling.py"
    if args.skip_stochastic:
        run_command += " --skip-stochastic"
    else:
        run_command += " --scenario-count {} --block-length {} --seed {}".format(
            args.scenario_count,
            args.block_length,
            args.seed,
        )
    source_path = ROOT / "paper_output" / "code" / "modeling" / "run_modeling.py"
    run_context = {
        "source_code_path": source_path.relative_to(ROOT).as_posix(),
        "source_code_sha256": sha256_file(source_path),
        "run_command": run_command,
        "run_exit_code": 0,
    }

    try:
        q1 = run_q1()
        q2 = run_q2()
        q3 = run_q3()
        q4 = run_q4(
            enable_stochastic=not args.skip_stochastic,
            scenario_count=args.scenario_count,
            block_length=args.block_length,
            seed=args.seed,
        )

        result1_path = RESULT_DIR / "result1.xlsx"
        result2_path = RESULT_DIR / "result2.xlsx"
        result3_path = RESULT_DIR / "result3.xlsx"
        result4_2_path = RESULT_DIR / "result4-2.xlsx"
        result4_3_path = RESULT_DIR / "result4-3.xlsx"
        write_result1(result1_path, q1)
        write_result2(result2_path, q2)
        write_result3(result3_path, q3)
        write_result2(result4_2_path, q4["q4_2"])
        write_result3(result4_3_path, q4["q4_3"])

        tables = write_tables(q1, q2, q3, q4)
        figure_records = generate_model_figures(q1, q2, q3, q4)
        figure_index_path = ROOT / "paper_output" / "figure_index.json"
        existing_index = json.loads(figure_index_path.read_text(encoding="utf-8"))
        by_id = {
            item["figure_id"]: item
            for item in existing_index.get("figures", [])
            if item.get("figure_id")
        }
        for item in figure_records:
            by_id[item["figure_id"]] = item
        figure_index = {
            "schema_version": "1.1",
            "stage": "S5",
            "status": "complete",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "figures": list(by_id.values()),
            "summary": {
                "total": len(by_id),
                "ready": sum(
                    1
                    for item in by_id.values()
                    if item.get("status") == "ready" and item.get("exists")
                ),
                "planned": sum(
                    1 for item in by_id.values() if item.get("status") == "planned"
                ),
            },
        }
        write_json(figure_index_path, figure_index)
        visualization_plan_path = ROOT / "paper_output" / "plan" / "visualization_plan.json"
        visualization_plan = json.loads(visualization_plan_path.read_text(encoding="utf-8"))
        plan_by_id = {
            item["figure_id"]: item
            for item in visualization_plan.get("figures", [])
            if item.get("figure_id")
        }
        for item in figure_records:
            if item["figure_id"] in plan_by_id:
                plan_by_id[item["figure_id"]].update(
                    {
                        "status": item["status"],
                        "output_path": item["path"],
                    }
                )
        visualization_plan["figures"] = list(plan_by_id.values())
        visualization_plan["ready_count"] = sum(
            1 for item in plan_by_id.values() if item.get("status") == "ready"
        )
        visualization_plan["planned_count"] = sum(
            1 for item in plan_by_id.values() if item.get("status") == "planned"
        )
        write_json(visualization_plan_path, visualization_plan)

        figure_paths = {
            "Q1": [
                ROOT / item["path"]
                for item in figure_records
                if item["question_id"] == "Q1"
            ],
            "Q2": [
                ROOT / item["path"]
                for item in figure_records
                if item["question_id"] == "Q2"
            ],
            "Q3": [
                ROOT / item["path"]
                for item in figure_records
                if item["question_id"] == "Q3"
            ],
            "Q4": [
                ROOT / item["path"]
                for item in figure_records
                if item["question_id"] == "Q4"
            ],
        }
        output_artifacts = {
            "Q1": [result1_path, TABLE_DIR / "table_q1_purchase.csv"] + figure_paths["Q1"],
            "Q2": [
                result2_path,
                TABLE_DIR / "table_q2_daily_summary.csv",
                TABLE_DIR / "table_q2_rule_comparison.csv",
            ]
            + figure_paths["Q2"],
            "Q3": [result3_path, TABLE_DIR / "table_q3_forecast_ablation.csv"] + figure_paths["Q3"],
            "Q4": [
                result4_2_path,
                result4_3_path,
                TABLE_DIR / "table_q4_cost_summary.csv",
            ]
            + figure_paths["Q4"],
        }
        results = [
            _result_item(
                "Q1",
                "问题一求得单日最优购电与储能调度方案，并满足储能首末电量一致。",
                q1["result_summary"],
                run_context,
                output_artifacts["Q1"],
            ),
            _result_item(
                "Q2",
                "问题二使用严格历史信息构造0:00计划，并以实际负载和光伏结算紧急购电；结果同时包含固定峰谷规则对照。",
                q2["result_summary"],
                run_context,
                output_artifacts["Q2"],
            ),
            _result_item(
                "Q3",
                "问题三完成四预报时刻滚动优化，并给出预报时点消融结果。",
                q3["result_summary"],
                run_context,
                output_artifacts["Q3"],
            ),
            _result_item(
                "Q4",
                "问题四完成附件4实际波动电价下的问题2和问题3重算。",
                q4["result_summary"],
                run_context,
                output_artifacts["Q4"],
            ),
        ]

        metrics_items = []
        for payload in [
            metrics_from_q1(q1),
            metrics_from_q2(q2),
            metrics_from_q3(q3),
            metrics_from_q4(q4),
        ]:
            qid = payload["question_id"]
            for item in payload["metrics"]:
                metrics_items.append(
                    _metric_item(
                        qid,
                        item["name"],
                        item["value"],
                        item["unit"],
                    )
                )

        conclusions_items = [
            _conclusion_item(
                "Q1",
                "问题一的最优策略满足负载、储能边界和首末储电量一致约束，全天购电费用由分时购电量复算得到。",
            ),
            _conclusion_item(
                "Q2",
                "问题二在2月1日至12月31日形成334天计划，0:00仅使用历史负载和光伏预报，实际结算产生紧急购电，并与固定峰谷规则策略完成对照。",
            ),
            _conclusion_item(
                "Q3",
                "问题三通过A/B/C/D四种策略比较新增预报时刻的边际价值，并输出最终滚动调整策略。",
            ),
            _conclusion_item(
                "Q4",
                "问题四使用附件4实际波动电价重算问题2和问题3，得到对应的波动电价购电费用和策略差异。",
            ),
        ]
        model_results = {
            "schema_version": "1.0",
            "generated_by": "paper_output/code/modeling/run_modeling.py",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "status": "computed",
            "questions": results,
        }
        metrics = {
            "schema_version": "1.0",
            "generated_by": "paper_output/code/modeling/run_modeling.py",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "status": "computed",
            "items": metrics_items,
        }
        conclusions = {
            "schema_version": "1.0",
            "generated_by": "paper_output/code/modeling/run_modeling.py",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "status": "computed",
            "items": conclusions_items,
        }
        table_index = {
            "schema_version": "1.0",
            "generated_by": "paper_output/code/modeling/run_modeling.py",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "status": "computed",
            "tables": tables,
        }
        write_json(RESULT_DIR / "model_results.json", model_results)
        write_json(RESULT_DIR / "metrics.json", metrics)
        write_json(RESULT_DIR / "conclusions.json", conclusions)
        write_json(TABLE_DIR / "table_index.json", table_index)

        output_paths = [
            result1_path,
            result2_path,
            result3_path,
            result4_2_path,
            result4_3_path,
            RESULT_DIR / "model_results.json",
            RESULT_DIR / "metrics.json",
            RESULT_DIR / "conclusions.json",
            TABLE_DIR / "table_index.json",
            figure_index_path,
            visualization_plan_path,
        ] + [ROOT / item["path"] for item in tables]
        output_paths += [ROOT / item["path"] for item in figure_records]
        code_paths = [
            source_path,
            ROOT / "paper_output" / "code" / "modeling" / "common_storage_lp.py",
            ROOT / "paper_output" / "code" / "modeling" / "result_contract_io.py",
            ROOT / "paper_output" / "code" / "modeling" / "q1_model.py",
            ROOT / "paper_output" / "code" / "modeling" / "q2_model.py",
            ROOT / "paper_output" / "code" / "modeling" / "q3_model.py",
            ROOT / "paper_output" / "code" / "modeling" / "q4_model.py",
            ROOT / "paper_output" / "code" / "visualization" / "generate_model_figures.py",
        ]
        finished_at = datetime.now().isoformat(timespec="seconds")
        manifest = build_run_manifest(
            status="PASS",
            question_ids=["Q1", "Q2", "Q3", "Q4"],
            code_paths=code_paths,
            input_paths=INPUT_PATHS,
            output_paths=output_paths,
            run_command=run_command,
            started_at=started_at,
            finished_at=finished_at,
            notes=[
                "Q4 block-bootstrap VaR/CVaR risk test was {}.".format(
                    "enabled" if not args.skip_stochastic else "disabled"
                )
            ],
        )
        write_json(RESULT_DIR / "run_manifest.json", manifest)
        print("modeling run PASS")
        return 0
    except Exception:
        traceback.print_exc()
        failed_manifest = {
            "schema_version": "1.0",
            "generated_by": "paper_output/code/modeling/run_modeling.py",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "status": "FAIL",
            "runs": [
                {
                    "script": source_path.relative_to(ROOT).as_posix(),
                    "script_sha256": sha256_file(source_path),
                    "returncode": 1,
                    "question_ids": ["Q1", "Q2", "Q3", "Q4"],
                    "started_at": started_at,
                    "finished_at": datetime.now().isoformat(timespec="seconds"),
                }
            ],
            "error": traceback.format_exc(),
        }
        write_json(RESULT_DIR / "run_manifest.json", failed_manifest)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STEP1_FILE = ROOT / "paper_output" / "step1" / "problem_analysis.json"
PLAN_DIR = ROOT / "paper_output" / "plan"


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def figure(qid, number, title, purpose):
    return {
        "figure_id": "fig_{}_{}".format(qid.lower(), number),
        "title": title,
        "purpose": purpose,
        "expected_path": "paper_output/figures/fig_{}_{}.png".format(qid.lower(), number),
    }


def build_model_route(analysis):
    return {
        "schema_version": "1.1",
        "stage": "S2",
        "status": "complete",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_by": "paper_output/code/data_processing/build_s2_plan.py",
        "source": {
            "problem_analysis": "paper_output/step1/problem_analysis.json",
            "s1_status": analysis.get("status"),
            "question_count": len(analysis.get("questions", [])),
        },
        "selection_principles": [
            "先满足题目直接要求的确定性结果，再增加滚动优化和随机风险分析。",
            "所有问题复用同一套 144 时段功率能量换算、储能动态和边界约束。",
            "每一问必须有可执行基线、一个主模型和至少一项验证或对照实验。",
            "主结果必须能写入附件 5 的结果模板，并可由代码和运行账本复现。",
            "创新模型不得替代题目要求的 result*.xlsx，只能作为增强结果和策略对比。",
        ],
        "common_framework": {
            "time_grid": "每天 144 个 10 分钟时段，Delta t = 1/6 h。",
            "energy_conversion": "功率 kW 乘 1/6 转为时段能量 kWh。",
            "state_variable": "E_t 为第 t 个时段结束后的储电量。",
            "storage_dynamics": "E_t = E_(t-1) + eta_c*c_t - d_t/eta_d，主口径 eta_c=eta_d=0.9。",
            "storage_bounds": "1200 <= E_t <= 10800 kWh。",
            "charge_discharge_bounds": "0 <= c_t,d_t <= 5000/6 kWh。",
            "load_requirement": "微网供给不可低于负载；富余光伏允许弃光，不倒送外网。",
            "main_cost_terms": "计划购电费、紧急购电费、问题 3 的调整偏差费用。",
            "official_output_period": "2025-02-01 至 2025-12-31，共 334 天。",
        },
        "question_routes": [
            {
                "question_id": "Q1",
                "title": "问题一：单日确定性购电与储能调度",
                "task_type": "确定性线性规划/调度",
                "core_goal": "在单日电价、负载和光伏预测已知条件下，确定 144 个时段的购电和储能计划，最小化全天购电费。",
                "baseline_model": {
                    "name": "无储能购电基线",
                    "description": "每个时段直接用外网补齐负载与光伏的差额，不进行储能充放电。",
                    "purpose": "提供费用上界并量化储能套利的价值。",
                },
                "main_model": {
                    "name": "144 时段单日储能调度线性规划",
                    "objective": "min sum_t rho_t*q_t",
                    "decision_variables": ["q_t 计划购电量", "c_t 充电量", "d_t 放电量", "E_t 期末储电量", "u_t 弃光量"],
                    "constraints": [
                        "q_t + pv_forecast_t/6 + d_t = load_t/6 + c_t + u_t",
                        "E_t = E_(t-1) + 0.9*c_t - d_t/0.9",
                        "1200 <= E_t <= 10800",
                        "0 <= c_t,d_t <= 5000/6",
                        "E_0 = E_144 = 6000",
                    ],
                    "solver": "优先 scipy.optimize.linprog；若需要更清晰的约束表达可使用 PuLP 或 OR-Tools。",
                    "why_this_model": "题意中的目标、储能动态和边界条件均可线性表达，LP 能得到全局最优解且便于解释。",
                },
                "backup_model": "规则型峰谷充电策略；若 LP 求解异常，用于诊断可行性和给出保守方案。",
                "experiment_design": [
                    "无储能对照：计算同一日期的购电费上界。",
                    "储能容量扰动：对最大容量或初始 SOC 做小幅变化。",
                    "效率口径对照：单边 90% 与往返 90% 两种解释。",
                ],
                "validation": [
                    "逐时段功率平衡残差不超过 1e-6。",
                    "储能上下界、充放电功率上限满足率 100%。",
                    "E_0 与 E_144 差值不超过 1e-6。",
                    "全天购电量与 144 时段购电量求和不矛盾。",
                    "购电费可由分时电价和购电量逐项复算。",
                ],
                "risk_controls": [
                    "把弃光作为显式变量，避免光伏富余时模型不可行。",
                    "检查充放电是否同时发生；若出现则增加互补约束或说明由损耗自然抑制。",
                ],
                "required_result_files": ["result1.xlsx"],
                "figures": [
                    figure("Q1", 1, "电价-负载-光伏日曲线", "解释问题一的输入特征和峰谷结构。"),
                    figure("Q1", 2, "购电量与储能充放电量叠加图", "展示最优调度行为。"),
                    figure("Q1", 3, "储能 SOC 轨迹与上下界", "证明储能边界约束和首末状态一致。"),
                ],
                "implementation_module": "paper_output/code/modeling/q1_model.py",
                "paper_sections": ["问题一模型建立", "问题一求解与结果", "问题一模型检验"],
            },
            {
                "question_id": "Q2",
                "title": "问题二：全年逐日计划购电",
                "task_type": "逐日滚动确定性线性规划",
                "core_goal": "在日电价固定、全年负载与光伏实际功率变化时，每天 0:00 制定计划，并计算紧急购电和全年费用。",
                "baseline_model": {
                    "name": "逐日无储能或固定阈值规则策略",
                    "description": "按固定规则在低价时段充电、高价时段放电。",
                    "purpose": "验证优化模型是否比简单规则产生更低费用。",
                },
                "main_model": {
                    "name": "全年逐日 LP + 跨日储能状态传递",
                    "objective": "min sum_day sum_t [rho_t*q_(day,t) + 5*rho_t*e_(day,t)]",
                    "decision_variables": ["每日 q_t、c_t、d_t、E_t", "结算量 e_t"],
                    "constraints": [
                        "每天使用附件 2 的负载和光伏实际功率。",
                        "每天首储电量等于前一天末储电量。",
                        "2025 年 1 月用于初始化，2 月 1 日至 12 月 31 日形成正式结果。",
                        "每日内部满足功率平衡、储能边界和充放电功率约束。",
                    ],
                    "solver": "逐日调用 LP 求解器；保存每日求解状态、目标值和约束残差。",
                    "why_this_model": "题目要求每天 0:00 制定计划，逐日 LP 能直接对应决策时点和跨日储能连续性。",
                },
                "backup_model": "全年统一 LP。它不严格对应每天制定计划的题意，但可作为理论下界和计算对照。",
                "experiment_design": [
                    "主确定性口径：0:00 已知当天实际负载和实际光伏，紧急购电量为 0。",
                    "预报对照：使用附件 3 的 0:00 光伏预报制定计划，以附件 2 实际值结算，得到非零紧急购电。",
                    "与无储能和规则策略对比全年购电费。",
                    "四个指定日期逐时段展示调度差异。",
                ],
                "validation": [
                    "检查 334 天日期和 144 时段均完整。",
                    "检查日间储能状态连续，无跳变。",
                    "紧急购电量与供能缺口一致，价格按 5 倍计算。",
                    "全年总购电费等于每日费用求和。",
                    "解释主结果紧急购电为 0 是完美信息假设的结果，而非机制遗漏。",
                ],
                "risk_controls": [
                    "严格区分实际功率与预报功率，结果文件使用统一的结算口径。",
                    "若任务时间不足，至少保留预报对照的四个指定日期结果。",
                ],
                "required_result_files": ["result2.xlsx"],
                "figures": [
                    figure("Q2", 1, "逐日购电费时间序列", "识别季节性费用变化和异常日。"),
                    figure("Q2", 2, "四个指定日期调度曲线", "满足论文指定日期结果展示。"),
                    figure("Q2", 3, "储能 SOC 全年轨迹", "验证跨日连续性和 SOC 边界。"),
                ],
                "implementation_module": "paper_output/code/modeling/q2_model.py",
                "paper_sections": ["问题二模型建立", "问题二全年结果", "问题二模型检验"],
            },
            {
                "question_id": "Q3",
                "title": "问题三：多时刻光伏预报滚动调整",
                "task_type": "滚动时域线性规划/模型预测控制",
                "core_goal": "利用 0:00、6:00、12:00、18:00 的四次预报滚动修正剩余时段购电计划，并评估新增预报时点的价值。",
                "baseline_model": {
                    "name": "仅使用 0:00 预报的静态计划",
                    "description": "全天只优化一次，后续不根据新预报调整。",
                    "purpose": "作为滚动优化策略的低信息基线。",
                },
                "main_model": {
                    "name": "四预报时刻滚动时域 LP",
                    "objective": "min 计划购电费 + 紧急购电费 + 调整偏差费用",
                    "decision_variables": ["q_bar_t 初始计划量", "q_t 最终执行或调整量", "c_t、d_t、E_t", "e_t"],
                    "adjustment_cost": "q_t < q_bar_t 时，超额计划减少部分按 0.5*rho_t 计费；q_t > q_bar_t 时，超出部分按 1.5*rho_t 计费。",
                    "rolling_rule": "每次预报只更新尚未发生的时段；最终 q_t 取时段开始前最近一次预报得到的计划。",
                    "constraints": [
                        "历史时段决策锁定。",
                        "预报时点之后仍满足储能连续性和功率平衡。",
                        "紧急供能缺口按 5 倍价格补足。",
                    ],
                    "solver": "在每个预报时点构造剩余时段 LP，保存版本化决策和最终执行量。",
                    "why_this_model": "题目明确允许根据新预报调整，滚动 LP 最直接地体现信息更新和决策因果顺序。",
                },
                "backup_model": "基于 0:00、6:00、12:00、18:00 的场景树近似。",
                "experiment_design": [
                    "策略 A：仅 0:00。",
                    "策略 B：0:00 + 6:00。",
                    "策略 C：0:00 + 6:00 + 12:00。",
                    "策略 D：0:00 + 6:00 + 12:00 + 18:00。",
                    "扩展比较：若数据支持，增加 3 小时间隔或 1 小时间隔预报情景。",
                    "分析预报误差大小与调整幅度、调整费用的关系。",
                ],
                "validation": [
                    "检查每项最终决策只使用决策时点之前可用的信息。",
                    "初始计划量与最终调整量定义一致，费用可按公式复算。",
                    "四组策略使用相同储能初值和边界条件。",
                    "比较总费用、调整费用、紧急购电量和调峰效果。",
                ],
                "risk_controls": [
                    "避免把未来预报泄漏到已经执行的时段。",
                    "调整费用主口径固定为相对 0:00 初始计划量，并做另一种解释的敏感性分析。",
                ],
                "required_result_files": ["result3.xlsx"],
                "figures": [
                    figure("Q3", 1, "初始计划与调整计划对比图", "展示预报更新前后的决策变化。"),
                    figure("Q3", 2, "预报时点消融实验柱状图", "定量回答是否需要其他时刻预报。"),
                    figure("Q3", 3, "调整费用与预报误差关系图", "解释滚动调整的收益来源。"),
                ],
                "implementation_module": "paper_output/code/modeling/q3_model.py",
                "paper_sections": ["问题三模型建立", "问题三滚动结果", "问题三预报价值分析"],
            },
            {
                "question_id": "Q4",
                "title": "问题四：波动电价下的问题二和问题三重算",
                "task_type": "确定性完美信息基准 + 随机优化与 CVaR 风险扩展",
                "core_goal": "使用附件 4 的波动电价重算问题 2 和问题 3，并进一步分析未来电价不确定时的期望费用和尾部风险。",
                "baseline_model": {
                    "name": "使用附件 4 实际电价的确定性 LP",
                    "description": "将附件 4 的电价代入 Q2/Q3 的确定性框架，得到可复现的完美信息基准。",
                    "purpose": "直接完成题目要求的 result4-2.xlsx 和 result4-3.xlsx。",
                },
                "main_model": {
                    "name": "实际电价确定性结果 + 块 bootstrap 场景随机 LP + CVaR",
                    "objective": "min (1/|S|)*sum_s C_s + lambda*CVaR_alpha(C_s)",
                    "decision_variables": ["各时段购电量、储能充放电量", "各电价情景下的费用 C_s"],
                    "scenario_generation": "按时刻和季节估计均值，对残差采用块 bootstrap，主块长 6 或 12 个 10 分钟时段。",
                    "risk_parameters": "默认 alpha=95%；对 lambda、场景数、块长做敏感性分析。",
                    "rolling_extension": "Q4-3 在每个预报时刻重新生成或更新价格场景，执行当前决策后滚动到下一时点。",
                    "solver": "场景平均近似 SAA；对每个优化问题保存场景种子、规模、训练目标和样本外指标。",
                    "why_this_model": "附件 4 给出实际波动价格，必须先完成确定性重算；场景随机 LP 进一步处理现实中未来价格未知的风险。",
                },
                "backup_model": "价格扰动鲁棒优化或仅用前一日同时刻价格作为朴素预测策略。",
                "experiment_design": [
                    "将附件 4 实际价格代入 Q2 和 Q3，生成题目要求的两个结果文件。",
                    "固定价与波动价费用对比。",
                    "确定性完美信息基准、随机期望费用策略、CVaR 风险厌恶策略对比。",
                    "比较期望费用、标准差、VaR、CVaR和最坏情景费用。",
                    "对全天价格施加 +/-5%、+/-10%、+/-20% 扰动。",
                    "使用前一日同时段价格作为朴素预测基准。",
                    "场景训练集与样本外评价集分离，固定随机种子。",
                ],
                "validation": [
                    "检查附件 4 的 334 个输出日与 144 时段完整性。",
                    "确定性基准结果与 Q2/Q3 使用同一套储能和费用约束。",
                    "随机策略不能在优化时读取未来实际价格。",
                    "报告训练场景与样本外场景的期望费用和尾部指标。",
                    "场景数增加后指标应趋于稳定，否则说明采样或缩减不稳定。",
                ],
                "risk_controls": [
                    "题目要求的 result4-2 和 result4-3 必须存在，不能只交随机模型分析。",
                    "CVaR 是增强证据，不作为替代确定性结果的借口。",
                    "若计算时间受限，优先完成确定性结果，再逐步增加 200～500 个优化场景。",
                ],
                "required_result_files": ["result4-2.xlsx", "result4-3.xlsx"],
                "figures": [
                    figure("Q4", 1, "电价场景扇形图", "展示价格不确定性和典型分位路径。"),
                    figure("Q4", 2, "费用分布与 CVaR 尾部", "解释风险目标和尾部损失。"),
                    figure("Q4", 3, "风险权重敏感性曲线", "说明期望费用与风险的权衡。"),
                    figure("Q4", 4, "固定价、波动价与多策略费用对比", "回答波动电价对策略的影响。"),
                ],
                "implementation_module": "paper_output/code/modeling/q4_model.py",
                "paper_sections": ["问题四模型建立", "问题四波动电价结果", "问题四风险与敏感性分析"],
            },
        ],
        "cross_question_experiments": [
            {
                "id": "EXP01",
                "name": "无储能基准",
                "purpose": "量化储能在 Q1、Q2、Q4-2 中的套利和削峰价值。",
                "evidence": ["各问总费用", "费用下降率", "购电负荷峰值变化"],
            },
            {
                "id": "EXP02",
                "name": "预报时点消融",
                "purpose": "回答 Q3 是否需要增加其他预报时刻。",
                "evidence": ["策略 A/B/C/D 总费用", "调整费用", "紧急购电费用"],
            },
            {
                "id": "EXP03",
                "name": "固定价与波动价对比",
                "purpose": "说明电价波动对购电策略和费用的影响。",
                "evidence": ["Q2 与 Q4-2 费用差", "Q3 与 Q4-3 费用差", "充放电时段变化"],
            },
            {
                "id": "EXP04",
                "name": "确定性完美信息与随机策略对比",
                "purpose": "区分事后最优和可执行的随机策略，避免高估模型效果。",
                "evidence": ["完美信息费用", "期望费用", "CVaR", "样本外费用差"],
            },
            {
                "id": "EXP05",
                "name": "关键参数敏感性",
                "purpose": "检验时间标签、储能效率、调整费用口径和场景参数对结论的影响。",
                "evidence": ["参数扰动表", "费用变化曲线", "策略稳定性结论"],
            },
        ],
        "downstream_handoff": {
            "S3_required_fields": [
                "date、interval_id、start_time、end_time",
                "load_kw、pv_actual_kw、price_fixed、price_actual",
                "pv_forecast_00、pv_forecast_06、pv_forecast_12、pv_forecast_18",
                "prediction_target_time、forecast_horizon",
            ],
            "S3_required_checks": [
                "附件 3 日期向下填充和 4 次预报完整性。",
                "附件 1、2、4 的 144 个时段位置一致性。",
                "0:00、24:00 边界与储能首末状态映射。",
                "整点预报到 10 分钟时段的分段常数展开。",
            ],
            "S4_model_modules": [
                "q1_model.py、q2_model.py、q3_model.py、q4_model.py",
                "common_storage_lp.py、forecast_mapping.py、result_writer.py",
            ],
            "S5_required_artifacts": [
                "result1.xlsx、result2.xlsx、result3.xlsx、result4-2.xlsx、result4-3.xlsx",
                "metrics.json、conclusions.json、run_manifest.json",
                "table_index.json、figure_index.json",
            ],
        },
    }


def build_rubric_alignment(model_route):
    items = [
        {
            "rubric_point": "题意理解准确",
            "question_id": "ALL",
            "priority": 1,
            "evidence_required": ["四问可计算任务定义", "输入输出映射", "参数与单位"],
            "artifact_contract": ["paper_output/step1/problem_analysis.json", "paper_output/plan/model_route.json"],
            "paper_location": ["问题重述", "问题分析", "符号说明"],
            "qa_rule": "正文不得把优化调度题改写成单纯光伏预测题。",
            "pass_condition": "四问均包含目标、决策变量、约束和指定输出。",
        },
        {
            "rubric_point": "数据与时间轴可靠",
            "question_id": "ALL",
            "priority": 1,
            "evidence_required": ["统一 144 点索引", "单位换算", "预报展开", "日期完整性"],
            "artifact_contract": ["paper_output/data_cleaned/*.csv", "paper_output/data_cleaned/load_report.json"],
            "paper_location": ["数据说明与预处理", "附录"],
            "qa_rule": "所有模型必须使用同一日期和时段索引，禁止功率与能量直接混算。",
            "pass_condition": "334 个输出日、144 时段、四个预报源和单位检查均 PASS。",
        },
        {
            "rubric_point": "统一储能模型正确",
            "question_id": "ALL",
            "priority": 1,
            "evidence_required": ["SOC 动态公式", "边界约束", "功率约束", "首末状态传递"],
            "artifact_contract": ["模型公式", "constraint_checks.csv"],
            "paper_location": ["模型假设", "各问模型建立", "模型检验"],
            "qa_rule": "所有问题必须复用同一 SOC 动态和边界条件。",
            "pass_condition": "SOC 边界满足率 100%，跨日状态连续。",
        },
        {
            "rubric_point": "Q1 模型与结果正确",
            "question_id": "Q1",
            "priority": 1,
            "evidence_required": ["单日 LP", "表 1、表 2", "result1.xlsx", "无储能对照"],
            "artifact_contract": ["result1.xlsx", "paper_output/results/model_results.json"],
            "paper_location": ["问题一模型", "问题一结果", "问题一检验"],
            "qa_rule": "正文表 1、表 2 必须与 result1.xlsx 对应。",
            "pass_condition": "目标值、全时段时间和储能边界均可复算。",
        },
        {
            "rubric_point": "Q2 全年计算完整",
            "question_id": "Q2",
            "priority": 1,
            "evidence_required": ["334 天逐日 LP", "跨日 SOC 连续", "四个指定日期", "result2.xlsx"],
            "artifact_contract": ["result2.xlsx", "results/model_results.json"],
            "paper_location": ["问题二模型", "全年结果", "模型检验"],
            "qa_rule": "输出日期不得从 1 月开始，2025 年 1 月只作为初始化。",
            "pass_condition": "334 天完整，日间储能无跳变，指定日期结果齐全。",
        },
        {
            "rubric_point": "Q2 紧急购电机制解释充分",
            "question_id": "Q2",
            "priority": 2,
            "evidence_required": ["5 倍紧急电价公式", "主结果 e=0 的原因", "预报对照的紧急购电"],
            "artifact_contract": ["result2.xlsx", "metrics.json", "对照结果表"],
            "paper_location": ["问题二模型", "完美信息讨论", "敏感性分析"],
            "qa_rule": "不能只给空结果，必须解释为什么主口径没有紧急购电。",
            "pass_condition": "主口径和预报对照均有结果和结论。",
        },
        {
            "rubric_point": "Q3 滚动因果顺序正确",
            "question_id": "Q3",
            "priority": 1,
            "evidence_required": ["版本化决策", "历史时段锁定", "最终执行量规则"],
            "artifact_contract": ["result3.xlsx", "decision_versions.csv"],
            "paper_location": ["问题三模型", "滚动调整结果"],
            "qa_rule": "不得使用未来预报反向修改已执行决策。",
            "pass_condition": "每个时段决策只使用该时点及以前的数据。",
        },
        {
            "rubric_point": "Q3 回答预报时点问题",
            "question_id": "Q3",
            "priority": 1,
            "evidence_required": ["A/B/C/D 四策略", "总费用与调整费用", "结论"],
            "artifact_contract": ["forecast_ablation.csv", "fig_q3_2.png"],
            "paper_location": ["问题三模型检验", "结论"],
            "qa_rule": "必须明确回答是否值得引入其他时刻预报。",
            "pass_condition": "给出费用差、边际收益和适用条件，不止列数字。",
        },
        {
            "rubric_point": "Q4 题目要求完整交付",
            "question_id": "Q4",
            "priority": 1,
            "evidence_required": ["附件 4 实际价重算", "result4-2.xlsx", "result4-3.xlsx"],
            "artifact_contract": ["result4-2.xlsx", "result4-3.xlsx"],
            "paper_location": ["问题四模型", "问题四结果"],
            "qa_rule": "随机模型不能替代题目明确要求的两个结果文件。",
            "pass_condition": "两个文件均存在，工作表结构与附件 5 一致。",
        },
        {
            "rubric_point": "Q4 风险分析充分",
            "question_id": "Q4",
            "priority": 2,
            "evidence_required": ["价格场景", "期望费用", "VaR", "CVaR", "最坏情景", "样本外评价"],
            "artifact_contract": ["scenario_metrics.csv", "fig_q4_2.png", "fig_q4_3.png"],
            "paper_location": ["问题四随机模型", "风险与敏感性分析"],
            "qa_rule": "未来实际电价不得直接用于随机优化。",
            "pass_condition": "训练与评价场景分离，尾部风险结论可复现。",
        },
        {
            "rubric_point": "基线对照充分",
            "question_id": "ALL",
            "priority": 1,
            "evidence_required": ["无储能", "规则策略", "仅 0:00 预报", "固定价/波动价"],
            "artifact_contract": ["comparison_metrics.csv", "费用对比图"],
            "paper_location": ["各问结果", "模型评价"],
            "qa_rule": "至少一个可执行基线证明主策略的相对优势。",
            "pass_condition": "所有对照使用相同数据期、单位和储能边界。",
        },
        {
            "rubric_point": "敏感性分析完整",
            "question_id": "ALL",
            "priority": 2,
            "evidence_required": ["时间标签", "储能效率", "调整费用口径", "价格扰动", "场景参数"],
            "artifact_contract": ["sensitivity_metrics.csv", "敏感性图"],
            "paper_location": ["模型检验", "不足与展望"],
            "qa_rule": "敏感性项目必须对应前文关键假设。",
            "pass_condition": "报告参数变化方向和结论稳定性。",
        },
        {
            "rubric_point": "结果文件与论文数值一致",
            "question_id": "ALL",
            "priority": 1,
            "evidence_required": ["result*.xlsx", "表格索引", "数值追溯记录"],
            "artifact_contract": ["table_index.json", "run_manifest.json", "evidence_gate_report.json"],
            "paper_location": ["各问结果表", "摘要", "附录"],
            "qa_rule": "任何论文数字都必须能回溯到机器可读结果。",
            "pass_condition": "证据门禁 PASS，正文表与结果文件逐项匹配。",
        },
        {
            "rubric_point": "创新性有实际收益",
            "question_id": "Q3-Q4",
            "priority": 2,
            "evidence_required": ["预报消融", "随机优化", "CVaR 对比", "边际收益"],
            "artifact_contract": ["forecast_ablation.csv", "scenario_metrics.csv"],
            "paper_location": ["问题三检验", "问题四风险分析", "模型评价"],
            "qa_rule": "创新模型必须说明相对于基线的改进，不堆砌算法名称。",
            "pass_condition": "每个创新点至少对应一项对照指标或风险指标。",
        },
        {
            "rubric_point": "可复现与可审计",
            "question_id": "ALL",
            "priority": 1,
            "evidence_required": ["输入哈希", "代码", "随机种子", "运行命令", "输出哈希"],
            "artifact_contract": ["run_manifest.json", "modeling code", "config JSON"],
            "paper_location": ["算法实现", "附录"],
            "qa_rule": "结果现场必须记录代码版本、参数和退出码。",
            "pass_condition": "从原始附件到结果文件可由脚本一键复现。",
        },
        {
            "rubric_point": "表达清晰且逐问闭环",
            "question_id": "ALL",
            "priority": 2,
            "evidence_required": ["摘要关键数字", "图表自解释", "逐问结论"],
            "artifact_contract": ["final_paper_source.md", "figure_index.json"],
            "paper_location": ["摘要", "问题分析", "结论"],
            "qa_rule": "每个结果图必须在正文引用并给出解释。",
            "pass_condition": "问题、模型、结果、验证、结论五段闭环完整。",
        },
    ]
    return {
        "schema_version": "1.1",
        "stage": "S2",
        "status": "complete",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "paper_output/plan/model_route.json",
        "items": items,
        "summary": {
            "item_count": len(items),
            "priority_1_count": sum(1 for item in items if item["priority"] == 1),
            "question_ids": ["Q1", "Q2", "Q3", "Q4"],
        },
    }


def build_scoring_strategy(model_route, rubric):
    lines = [
        "# S2 模型路线与评分闭环策略",
        "",
        "## 一、结论",
        "",
        "本题是统一的微网储能调度优化问题。问题 1、2 使用确定性 LP，问题 3 使用滚动时域 LP，问题 4 先完成附件 4 实际波动电价下的确定性重算，再用场景随机 LP 和 CVaR 做风险扩展。",
        "",
        "主结果必须写入附件 5 的五个结果模板；创新模型只作为增强证据，不能替代题目明确要求的结果文件。",
        "",
        "## 二、逐问路线",
        "",
        "| 问题 | 基线 | 主模型 | 关键验证 |",
        "|---|---|---|---|",
        "| Q1 | 无储能购电 | 144 时段单日 LP | E0=E144、SOC 边界、无储能对照 |",
        "| Q2 | 规则充放电 | 逐日 LP + 跨日 SOC 传递 | 334 天完整、紧急购电解释、预报对照 |",
        "| Q3 | 仅 0:00 预报 | 四预报时刻滚动 LP | A/B/C/D 消融、因果顺序、调整费用 |",
        "| Q4 | 附件 4 实际价确定性 LP | 确定性重算 + 场景随机 LP + CVaR | 样本外评价、尾部风险、固定价对比 |",
        "",
        "## 三、评分优先级",
        "",
        "1. 先保证题意、单位、储能约束和五个结果文件完全正确。",
        "2. 再保证每问有基线对照和约束满足验证。",
        "3. 然后完成 Q3 的预报时点消融和 Q4 的波动价风险分析。",
        "4. 最后加强敏感性和创新性表达，不能以复杂算法掩盖结果缺口。",
        "",
        "## 四、证据闭环",
        "",
        "### 4.1 数据证据",
        "",
        "- 统一日期和 144 时段索引。",
        "- 附件 2、4 的功率和价格转成模型可用表。",
        "- 附件 3 的四个预报时刻展开到 10 分钟粒度。",
        "- 输出数据加载报告，记录缺失、范围、异常和映射规则。",
        "",
        "### 4.2 模型证据",
        "",
        "- 每个模型写出决策变量、目标函数和全部约束。",
        "- 共享 SOC 动态和费用公式，问题之间不得偷换口径。",
        "- 滚动优化必须保存每个决策时点的版本，证明没有未来信息泄漏。",
        "",
        "### 4.3 结果证据",
        "",
        "- result1 至 result4-3 五个文件必须真实生成。",
        "- 每个论文数字追溯到结果 JSON、CSV 或 Excel。",
        "- 表格、图形、摘要和结论中的统数字一致。",
        "",
        "### 4.4 验证证据",
        "",
        "- 基础检查：功率平衡、SOC 上下界、充放电功率上限、首末状态。",
        "- 对照检查：无储能、规则策略、静态预报、滚动预报、固定价、波动价。",
        "- 稳健检查：时间标签、储能效率、调整费用、场景数、块长、lambda 和 alpha。",
        "",
        "## 五、必须避免的问题",
        "",
        "1. 把本题误判为光伏预测题，直接使用预测误差指标代替调度结果。",
        "2. 直接混用 kW 和 kWh，或把 10 分钟功率当作时段能量。",
        "3. 全年结果从 2025 年 1 月开始输出，破坏 334 天口径。",
        "4. Q2 主结果紧急购电为 0，却不解释这是完美信息假设造成的。",
        "5. Q3 使用未来预报修改已执行时段，导致信息泄漏。",
        "6. Q4 只给随机模型，不生成题目要求的 result4-2 和 result4-3。",
        "7. 把附件 4 实际电价直接当成未来已知价格，混淆完美信息基准和可执行策略。",
        "",
        "## 六、后续交接",
        "",
        "- S3 按 `downstream_handoff.S3_required_fields` 建立统一数据表，并专项检查时间标签和预报展开。",
        "- S4 按 `implementation_module` 生成 q1～q4 模型模块和通用 LP/结果写入模块。",
        "- S5 实际运行代码，生成五个 result 文件、metrics、conclusions、figure_index 和 run_manifest。",
        "- S6 使用评分点映射和证据门禁逐条检查，不得用文字代替缺失结果。",
        "",
        "## 七、S2 完成标准",
        "",
        "- 四问均有基线、主模型、备选模型、验证和风险控制。",
        "- 每个评分点都有证据形式和论文落点。",
        "- 后续 S3、S4、S5 的输入输出契约明确。",
        "- 工作流守卫确认 S2 PASS，并指向 S3。",
    ]
    return "\n".join(lines)


def main():
    analysis = load_json(STEP1_FILE)
    if len(analysis.get("questions", [])) != 4:
        raise SystemExit("S1 problem_analysis.json does not contain four questions")
    model_route = build_model_route(analysis)
    # The orchestrator guard uses the standard "questions" key; keep the
    # detailed "question_routes" key for downstream model-specific workflows.
    model_route["questions"] = model_route["question_routes"]
    rubric = build_rubric_alignment(model_route)
    write_json(PLAN_DIR / "model_route.json", model_route)
    write_json(PLAN_DIR / "rubric_alignment.json", rubric)
    write_text(PLAN_DIR / "scoring_strategy.md", build_scoring_strategy(model_route, rubric))
    print("S2 outputs written to: {}".format(PLAN_DIR))


if __name__ == "__main__":
    main()

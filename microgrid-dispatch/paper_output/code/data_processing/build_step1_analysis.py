from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STEP1_DIR = ROOT / "paper_output" / "step1"
MANIFEST_PATH = ROOT / "paper_output" / "input_manifest.json"


def load_json(path):
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def manifest_hashes():
    manifest = load_json(MANIFEST_PATH)
    result = {}
    for item in manifest.get("entries", []):
        path = str(item.get("path", "")).replace("\\", "/")
        if path:
            result[path] = item.get("sha256", "")
    return result


def build_analysis():
    hashes = manifest_hashes()
    analysis = {
        "schema_version": "1.1",
        "stage": "S1",
        "status": "complete",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_by": "problem-doc-model-selector with Codex structured correction",
        "source": {
            "problem_statement": "problem_files/C题.pdf",
            "reference_plan": "reference/C题_建模思路.md",
            "input_manifest": "paper_output/input_manifest.json",
            "preflight_report": "paper_output/preflight_report.json",
            "problem_statement_sha256": hashes.get("problem_files/C题.pdf", ""),
        },
        "problem": {
            "title": "微网与外部电网电力调控策略",
            "objective": "在满足小区负载、储能边界和跨日边界条件的前提下，确定购电量及储能充放电量，使购电费用尽可能低。",
            "planning_horizon": "每天 0:00 制定计划；问题 3 和问题 4-3 在 6:00、12:00、18:00 根据新预报滚动调整。",
            "core_question_type": "优化/调度；问题 3、4-3 为滚动时域优化；问题 4 包含价格不确定性建模。",
            "external_data_required": False,
        },
        "attachments": [
            {
                "id": "附件1",
                "path": "problem_files/附件1.xlsx",
                "sha256": hashes.get("problem_files/附件1.xlsx", ""),
                "role": "单日固定电价、负载和光伏预测功率",
                "structure": "Sheet1；1 行表头 + 144 行数据；4 列；无缺失。",
                "fields": [
                    {"name": "时间", "unit": "time", "meaning": "10 分钟时间标识，首个为 00:10，末个为 0:00+1。"},
                    {"name": "电价", "unit": "元/kWh", "meaning": "问题 1、2、3 使用的固定日价格曲线。"},
                    {"name": "小区负载", "unit": "kW", "meaning": "对应 10 分钟时段的小区负载功率。"},
                    {"name": "光伏发电预测功率", "unit": "kW", "meaning": "对应 10 分钟时段的光伏预测功率。"},
                ],
                "used_by": ["Q1", "Q2", "Q3"],
            },
            {
                "id": "附件2",
                "path": "problem_files/附件2.xlsx",
                "sha256": hashes.get("problem_files/附件2.xlsx", ""),
                "role": "全年负载与光伏实际功率",
                "structure": "2 个工作表：小区负载、光伏发电实际功率；每表 1 行表头 + 365 行日数据；每行 144 个 10 分钟值；无缺失。",
                "fields": [
                    {"name": "日期\\时间", "unit": "date", "meaning": "2025-01-01 至 2025-12-31。"},
                    {"name": "00:10 至 0:00+1", "unit": "kW", "meaning": "144 个 10 分钟负载或光伏实际功率。"},
                ],
                "used_by": ["Q2", "Q3", "Q4-2", "Q4-3"],
            },
            {
                "id": "附件3",
                "path": "problem_files/附件3.xlsx",
                "sha256": hashes.get("problem_files/附件3.xlsx", ""),
                "role": "四个预报时刻发布的未来 24 小时整点光伏预报",
                "structure": "Sheet1；1 行表头 + 1460 行；26 列；每天 4 个预报时刻，每个时刻 24 个整点预报值。日期列仅在每日首行出现，读取时需向下填充。",
                "fields": [
                    {"name": "日期", "unit": "date", "meaning": "预报发布日期；合并单元格导致后续行显示为空。"},
                    {"name": "预报时刻", "unit": "time", "meaning": "0:00、6:00、12:00、18:00。"},
                    {"name": "预报1小时至预报24小时", "unit": "kW", "meaning": "从预报时刻起未来第 1 至第 24 个整点的光伏功率预报。"},
                ],
                "used_by": ["Q3", "Q4-3"],
            },
            {
                "id": "附件4",
                "path": "problem_files/附件4.xlsx",
                "sha256": hashes.get("problem_files/附件4.xlsx", ""),
                "role": "全年逐 10 分钟电价",
                "structure": "Sheet1；1 行表头 + 365 行日数据；每行 144 个 10 分钟电价；无缺失。",
                "fields": [
                    {"name": "日期\\时间", "unit": "date", "meaning": "2025-01-01 至 2025-12-31。"},
                    {"name": "00:10 至 0:00+1", "unit": "元/kWh", "meaning": "144 个 10 分钟交易电价。"},
                ],
                "used_by": ["Q4-2", "Q4-3"],
            },
            {
                "id": "附件5",
                "path": "problem_files/附件5",
                "sha256": "",
                "role": "五个空结果提交模板",
                "structure": "result1.xlsx、result2.xlsx、result3.xlsx、result4-2.xlsx、result4-3.xlsx。",
                "used_by": ["Q1", "Q2", "Q3", "Q4-2", "Q4-3"],
            },
        ],
        "global_parameters": {
            "delta_t_hours": 1 / 6,
            "periods_per_day": 144,
            "storage_max_capacity_kwh": 12000,
            "storage_min_soc_kwh": 1200,
            "storage_max_soc_kwh": 10800,
            "storage_initial_kwh": 6000,
            "storage_initial_time": "2025-01-01 00:00",
            "max_charge_power_kw": 5000,
            "max_discharge_power_kw": 5000,
            "max_charge_energy_per_period_kwh": 5000 / 6,
            "max_discharge_energy_per_period_kwh": 5000 / 6,
            "charge_efficiency_default": 0.9,
            "discharge_efficiency_default": 0.9,
            "round_trip_efficiency_implied": 0.81,
            "emergency_price_multiplier": 5,
            "adjustment_deficit_price_multiplier": 0.5,
            "adjustment_excess_price_multiplier": 1.5,
            "official_output_start": "2025-02-01",
            "official_output_end": "2025-12-31",
            "official_output_days": 334,
            "initialization_period": "2025-01",
            "specified_report_dates": ["2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"],
        },
        "data_contract": {
            "time_axis": {
                "internal_index": "day t=1..144，按附件列从左到右编号。",
                "energy_conversion": "功率单位为 kW，时段长度为 1/6 h；能量 kWh = 功率 kW × 1/6。",
                "default_mapping": "附件 1、2、4 的 144 个数据位置与对应结果模板的 144 个时段位置一一对应，不因模板文字标签差异而移动数值。",
                "known_conflict": "附件时间标签为 00:10 至 0:00+1，result1 时段标签为 0:10-0:20 至 0:00-0:10+1；两套标签存在 10 分钟语义差。S1 暂采用位置映射，S3 必须用边界校验和敏感性分析复核。",
            },
            "forecast_alignment": {
                "origin_times": ["00:00", "06:00", "12:00", "18:00"],
                "horizon": "未来 24 个整点。",
                "to_10_min": "主口径采用小时内分段常数；将整点预报展开到 6 个 10 分钟槽。",
                "sensitivity": "可用前一小时与后一小时线性插值作为复核口径。",
            },
            "storage_model": {
                "energy_unit": "kWh",
                "state_transition": "E_t = E_(t-1) + eta_c * c_t - d_t / eta_d。",
                "default_interpretation": "90% 为充电和放电的单向效率，隐含往返效率 81%。",
                "sensitivity": "另做 90% 为往返效率的对照，检查费用和调度结论是否稳健。",
                "boundary": "q1 要求 E_0=E_144；全年模型逐日传递储能状态。",
            },
            "cost_model": {
                "planned_purchase": "rho_t * q_t。",
                "adjustment_below_plan": "rho_t * q_t + 0.5 * rho_t * (q_bar_t - q_t)，当 q_t < q_bar_t。",
                "adjustment_above_plan": "rho_t * q_bar_t + 1.5 * rho_t * (q_t - q_bar_t)，当 q_t > q_bar_t。",
                "emergency": "5 * rho_t * e_t。",
                "interpretation": "调整费用以最终调整购电量与 0:00 初始计划购电量比较；该解释需在论文中明确。",
            },
            "default_assumptions": [
                "负载必须被满足；光伏剩余量可在储能无法继续吸收时弃光，不允许向外部电网倒送电。",
                "购电量和储能充放电量均以 10 分钟时段内累计能量 kWh 表示。",
                "问题 2 主口径使用附件 2 当天实际负载和实际光伏制定计划，因此紧急购电量为 0；另用 0:00 光伏预报结算实际功率作为对照。",
                "问题 3 的最终执行量由时段开始前最近一次可用预报决定；已发生时段不再重优化。",
                "问题 4 使用附件 4 历史电价构造价格分布；实际电价仅用于样本外结算和基准评价，不用于声称未来电价完全已知。",
            ],
        },
        "questions": [
            {
                "id": "Q1",
                "title": "问题一：单日确定性购电与储能调度",
                "summary": "在一天电价、负载和光伏预测已知时，制定 144 个 10 分钟时段的购电和储能充放电计划。",
                "task_type": "确定性线性规划/调度",
                "inputs": ["附件1", "附录1 储能参数"],
                "decision_variables": [
                    "g_t：计划购电量，kWh。",
                    "c_t：储能充电量，kWh。",
                    "d_t：储能放电量，kWh。",
                    "E_t：期末储电量，kWh。",
                    "u_t：弃光量，kWh，作为可行性和物理口径显式变量。",
                ],
                "objective": "min sum_t rho_t * g_t。",
                "constraints": [
                    "g_t + pv_forecast_t * delta_t + d_t = load_t * delta_t + c_t + u_t。",
                    "0 <= g_t；0 <= c_t,d_t <= 5000 * delta_t；0 <= u_t。",
                    "E_t = E_(t-1) + 0.9*c_t - d_t/0.9。",
                    "1200 <= E_t <= 10800。",
                    "E_0 = E_144 = 6000 kWh。",
                ],
                "required_results": [
                    "论文表 1：10:00-10:10、12:00-12:10、14:00-14:10、16:00-16:10、18:00-18:10、20:00-20:10 的购电量、全天购电量和购电费。",
                    "论文表 2：六个四小时区间的充电量、放电量，以及 0:00、24:00 储电量。",
                    "result1.xlsx：计划购电量和充放电量工作表完整 144 时段结果。",
                ],
                "result_files": ["result1.xlsx"],
                "baseline_model": "无储能规则基线或日前 LP 基线。",
                "recommended_model": "144 时段确定性 LP；以 scipy.optimize.linprog、PuLP 或 OR-Tools 求解。",
                "validation": [
                    "逐时段功率平衡残差 <= 1e-6。",
                    "储能上下界和功率上限满足率 100%。",
                    "E_0 与 E_144 差值 <= 1e-6。",
                    "与无储能基准比较全天购电费下降幅度。",
                ],
                "figure_suggestions": ["电价-负载-光伏曲线", "购电量与储能充放电堆叠图", "储能 SOC 轨迹图"],
            },
            {
                "id": "Q2",
                "title": "问题二：全年逐日计划购电",
                "summary": "在日价格固定、全年负载和实际光伏变化时，每天 0:00 制定计划，并处理紧急购电机制。",
                "task_type": "逐日滚动确定性线性规划",
                "inputs": ["附件1 电价", "附件2 全年负载与光伏实际功率", "附录1 储能参数"],
                "decision_variables": [
                    "q_(day,t)：当天 10 分钟计划购电量。",
                    "c_(day,t)、d_(day,t)、E_(day,t)：当天储能充放电量和储电量。",
                    "e_(day,t)：实际结算时的紧急购电量，主确定性口径下为 0。",
                ],
                "objective": "min sum_day sum_t [rho_t * q_(day,t) + 5 * rho_t * e_(day,t)]。",
                "constraints": [
                    "q + pv + d + e = load + c + u，所有功率量在平衡式中先转为 kWh。",
                    "储能状态从 2025 年 1 月初始化，逐日连续传递至 12 月 31 日。",
                    "E 范围、充放电效率和功率上限与问题 1 相同。",
                    "每天使用当天 0:00 计划，不跨日重新优化已经执行的时段。",
                ],
                "required_results": [
                    "2025-03-20、2025-06-21、2025-09-23、2025-12-21 的表 1、表 2 和紧急购电表。",
                    "全年购电量、购电费、紧急购电量和紧急购电费用。",
                    "result2.xlsx：计划购电量、充放电量、紧急购电量。",
                ],
                "result_files": ["result2.xlsx"],
                "baseline_model": "无储能或纯规则充放电策略。",
                "recommended_model": "逐日 144 时段 LP；2025 年 1 月用于初始化，2 月 1 日至 12 月 31 日输出。",
                "validation": [
                    "确认每天储能首末状态连续。",
                    "确认 334 天日期和 144 时段完整。",
                    "主确定性口径紧急购电量为 0，并解释完美信息假设。",
                    "增加 0:00 光伏预报与实际光伏的对照，量化紧急购电费用损失。",
                ],
                "figure_suggestions": ["逐日购电费时间序列", "四个指定日期调度曲线", "储能 SOC 全年轨迹"],
            },
            {
                "id": "Q3",
                "title": "问题三：基于多时刻光伏预报的滚动调整",
                "summary": "使用 0:00、6:00、12:00、18:00 的预报滚动调整未来购电计划，并评估新增预报时刻的价值。",
                "task_type": "滚动时域线性规划/模型预测控制",
                "inputs": ["附件1 电价", "附件2 负载与实际光伏", "附件3 四时刻光伏预报", "附录1 储能参数"],
                "decision_variables": [
                    "q_bar_t：0:00 初始计划购电量。",
                    "q_t：最终调整购电量或实际执行的计划量。",
                    "c_t、d_t、E_t：最终储能充放电量和储电量。",
                    "e_t：紧急购电量。",
                ],
                "objective": "min 计划购电费 + 紧急购电费 + 调整偏差费用，其中偏差费用以 q_t 与 q_bar_t 的差计算。",
                "constraints": [
                    "每个预报时刻仅重新优化尚未发生时段的决策。",
                    "历史时段决策锁定；最终 q_t 取该时段开始前最后一次有效决策。",
                    "低于计划量部分按 0.5 rho 计违约电价；高于计划量部分按 1.5 rho 计调整电价。",
                    "功率平衡、储能边界、首末状态和紧急购电约束沿用问题 2。",
                ],
                "required_results": [
                    "四个指定日期的初始计划、最终调整、储能充放电、紧急购电结果。",
                    "比较仅 0:00、0:00+6:00、0:00+6:00+12:00、四个时刻全用四种策略的费用。",
                    "明确回答是否值得引入其他时刻预报。",
                    "result3.xlsx：计划购电量、调整购电量、充放电量、紧急购电量。",
                ],
                "result_files": ["result3.xlsx"],
                "baseline_model": "仅使用 0:00 预报的静态计划。",
                "recommended_model": "滚动时域 LP；按预报时刻重优化剩余时段，进行预报增量的消融实验。",
                "validation": [
                    "对比四种预报时点策略的总成本和调整费用。",
                    "检查调整费用解释是否与初始计划量一致。",
                    "将预报误差与调整幅度关联，说明新增预报的边际收益。",
                    "必要时增加 3 小时间隔或 1 小时间隔情景，回答是否需要更多预报。",
                ],
                "figure_suggestions": ["初始计划与调整计划对比图", "预报时点消融实验柱状图", "调整费用与预报误差关系图"],
            },
            {
                "id": "Q4",
                "title": "问题四：波动电价下重算问题二和问题三",
                "summary": "用附件 4 的波动电价替代固定电价，分别构建问题 4-2 和问题 4-3，并刻画价格不确定性。",
                "task_type": "随机优化；确定性完美信息基准 + 场景随机规划/CVaR",
                "inputs": ["附件2 负载与光伏实际功率", "附件3 光伏预报", "附件4 逐 10 分钟电价", "附录1 储能参数"],
                "decision_variables": [
                    "问题 4-2：逐日计划购电量、储能充放电量和储电量。",
                    "问题 4-3：滚动初始计划、调整购电量、最终储能充放电量和紧急购电量。",
                    "随机模型：每个电价情景下的购电和储能决策。",
                ],
                "objective": "min 期望购电费用 + lambda * CVaR_alpha(购电费用)。",
                "constraints": [
                    "波动电价下的功率平衡、储能和购电约束与问题 2、3 相同。",
                    "电价场景只能由当日以前可获得的历史数据生成，实际电价用于样本外评价。",
                    "问题 4-3 在 0:00、6:00、12:00、18:00 重新生成场景并更新剩余时段决策。",
                ],
                "required_results": [
                    "问题 4-2 和问题 4-3 的完整购电、调整、储能和紧急购电结果。",
                    "固定电价与波动电价费用差异。",
                    "确定性完美信息基准、随机期望费用策略和风险厌恶策略对照。",
                    "期望费用、标准差、VaR、CVaR和最坏场景费用。",
                    "result4-2.xlsx 和 result4-3.xlsx。",
                ],
                "result_files": ["result4-2.xlsx", "result4-3.xlsx"],
                "baseline_model": "使用实际电价的确定性 LP，仅作为事后完美信息基准。",
                "recommended_model": "日内周期加残差块 bootstrap 生成价格场景；SAA 随机 LP；目标加入 CVaR；问题 4-3 使用滚动蒙特卡洛 MPC。",
                "validation": [
                    "固定随机种子，优化场景和样本外评价场景分离。",
                    "比较期望费用、尾部风险和最坏情景。",
                    "对 lambda、场景数、块长和 alpha 做敏感性分析。",
                    "进行 +/-5%、+/-10%、+/-20% 电价扰动以及前一日电价朴素预测对照。",
                ],
                "figure_suggestions": ["电价场景扇形图", "目标函数-风险权重曲线", "费用分布与 CVaR 尾部图", "三种策略费用对比"],
            },
        ],
        "output_contract": {
            "result1.xlsx": {
                "计划购电量": "1 行表头 + 144 行；时间段、购电量。",
                "充放电量": "六个四小时区间及 0:00、24:00 储电量。",
            },
            "result2.xlsx": {
                "计划购电量": "2025-02-01 至 2025-12-31 每日 144 个 10 分钟计划购电量，附全天购电量和购电费。",
                "充放电量": "每日六个四小时区间充电量、放电量及 0:00、24:00 储电量。",
                "紧急购电量": "日期、购电时间段、购电量；主确定性口径可为空。",
            },
            "result3.xlsx": {
                "计划购电量": "0:00 预报制定的计划购电量。",
                "调整购电量": "其他预报时刻调整后的最终购电量。",
                "充放电量": "最终充放电量和储电量。",
                "紧急购电量": "最终紧急购电时间段与购电量。",
            },
            "result4-2.xlsx": "保存波动电价下问题 2 的全部结果，工作表同 result2.xlsx。",
            "result4-3.xlsx": "保存波动电价下问题 3 的全部结果，工作表同 result3.xlsx。",
        },
        "critical_decisions": [
            {
                "id": "A01",
                "topic": "时间标签偏移",
                "default": "按附件列位置与结果模板时段位置一一映射，数值不做平移。",
                "risk": "附件的 00:10 到 0:00+1 与 result1 的 0:10-0:20 到 0:00-0:10+1 存在语义差。",
                "validation": "在 S3 生成 144 点统一索引，检查首末时段、日总量和 0:00/24:00 边界；若题目评审预期另一口径，做标签平移敏感性分析。",
            },
            {
                "id": "A02",
                "topic": "储能效率",
                "default": "90% 为单边充、放电效率，往返效率 81%。",
                "risk": "题目可能把 90% 理解为往返效率。",
                "validation": "S5 比较单边效率和往返效率两种模型，报告费用和调度差异。",
            },
            {
                "id": "A03",
                "topic": "光伏富余量处置",
                "default": "允许弃光，不允许倒送外网。",
                "risk": "若不允许弃光，部分时段可能不可行。",
                "validation": "统计弃光量，并说明仅在储能无法吸收时发生。",
            },
            {
                "id": "A04",
                "topic": "问题 2 紧急购电为 0",
                "default": "主口径使用当天实际负载和实际光伏制定计划，因此最优计划不会制造可控缺口。",
                "risk": "结果看似未使用紧急购电机制。",
                "validation": "增加 0:00 光伏预报结算对照，得到非零紧急购电量和费用损失。",
            },
            {
                "id": "A05",
                "topic": "问题 3 调整费用基准",
                "default": "最终调整购电量与 0:00 初始计划购电量比较。",
                "risk": "也可能解释为与上一次调整量比较。",
                "validation": "在敏感性分析中测试另一种解释，论文明确主口径。",
            },
            {
                "id": "A06",
                "topic": "价格可知性",
                "default": "确定性附件 4 模型仅作为完美信息基准；随机模型不从未来实际价直接优化。",
                "risk": "把事后实际价格当作日前已知会高估策略表现。",
                "validation": "严格划分训练历史、优化场景和样本外评价路径。",
            },
        ],
        "recommended_models": [
            {
                "question_id": "Q1",
                "task_type": "确定性 LP",
                "baseline": "无储能购电基线",
                "primary": "144 时段单日储能调度 LP",
                "backup": "规则充电/放电策略",
            },
            {
                "question_id": "Q2",
                "task_type": "逐日滚动 LP",
                "baseline": "每日无储能或固定 SOC 规则",
                "primary": "逐日 144 时段 LP，跨日传递储电量",
                "backup": "全年统一 LP 作为理论基准",
            },
            {
                "question_id": "Q3",
                "task_type": "滚动时域 LP",
                "baseline": "仅 0:00 预报",
                "primary": "四预报时刻滚动重优化",
                "backup": "情景树或确定性等价近似",
            },
            {
                "question_id": "Q4",
                "task_type": "随机优化",
                "baseline": "附件 4 实际价确定性完美信息 LP",
                "primary": "块 bootstrap 场景 + SAA 随机 LP + CVaR；Q4-3 使用滚动蒙特卡洛 MPC",
                "backup": "鲁棒优化或仅价格扰动敏感性分析",
            },
        ],
        "validation_plan": [
            "数据层：日期完整性、144 时段完整性、单位一致性、合并单元格日期回填。",
            "模型层：功率平衡、储能上下界、充放电功率上限、首末储电量一致性。",
            "结果层：论文表与 result*.xlsx 数值一致，全天购电量与分时段求和不矛盾，费用分解可复核。",
            "对照层：无储能、规则策略、仅 0:00 预报、多时刻预报、固定价与波动价、确定性基准与随机策略。",
            "稳健层：时间标签、储能效率、调整费用口径、场景数、块长、CVaR 参数和价格扰动。",
        ],
        "figure_suggestions": [
            "电价、负荷、光伏预测与实际功率日曲线。",
            "购电量和储能充放电量堆叠图。",
            "储能 SOC 轨迹与上下界图。",
            "全年逐日购电费和紧急购电费用时间序列。",
            "预报时点消融实验对比图。",
            "电价场景扇形图与 CVaR 费用分布图。",
            "技术路线图和各问模型输入输出关系图。",
        ],
        "data_requirements": [],
        "next_outputs": {
            "model_route": "paper_output/plan/model_route.json",
            "rubric_alignment": "paper_output/plan/rubric_alignment.json",
            "scoring_strategy": "paper_output/plan/scoring_strategy.md",
            "data_plan": "paper_output/plan/data_plan.json",
            "visualization_plan": "paper_output/plan/visualization_plan.json",
        },
    }
    return analysis


def build_a(analysis):
    return """# A 题意对齐

## 一、总体任务

题目为**微网与外部电网电力调控策略**，核心是在满足小区负载、储能容量与跨日边界条件下，优化外网购电量和储能充放电量，降低购电费用。四问均为调度优化问题，问题 3 和问题 4-3 增加滚动预报更新，问题 4 进一步引入实时波动电价。

## 二、逐问对齐

| 问题 | 输入 | 决策 | 目标 | 关键约束 | 必须输出 | 验证方式 |
|---|---|---|---|---|---|---|
| Q1 | 附件 1、储能参数 | 144 时段购电量、充放电量、储电量 | 最小化全天购电费 | 供能不低于负载；E0=E144；SOC 与功率边界 | 表 1、表 2、result1.xlsx | 功率平衡、SOC 边界、首末电量、无储能对照 |
| Q2 | 附件 1 电价、附件 2 全年负载与实际光伏 | 每日计划购电量、储能状态；紧急购电结算量 | 最小化计划购电费和紧急购电费 | 每天 0:00 制定；储能逐日连续；2 月 1 日至 12 月 31 日 | 四个指定日期结果、全年费用、result2.xlsx | 334 天完整性、储能连续性、完美信息说明、预报误差对照 |
| Q3 | 附件 1 电价、附件 2 实际值、附件 3 四时刻预报 | 初始计划量、滚动调整量、最终储能状态 | 最小化计划费、调整偏差费和紧急购电费 | 仅重优化未发生时段；调整费用以初始计划为基准 | 指定日期结果、预报时刻价值分析、result3.xlsx | 四种预报时点对照、调整费用分解、预报误差关联 |
| Q4 | 附件 2、附件 3、附件 4 波动电价 | Q4-2 逐日决策；Q4-3 滚动决策；随机场景决策 | 最小化期望费用并控制尾部风险 CVaR | 保留功率与储能约束；未来价格不可直接预知 | Q4-2、Q4-3 完整结果、风险指标和策略对比 | 场景外评价、固定价/波动价对比、CVaR 与参数敏感性 |

## 三、全局参数

- 时间粒度：10 分钟，每天 144 个时段，`Delta t = 1/6 h`。
- 能量换算：`kWh = kW × 1/6`。
- 储能容量：12000 kWh；SOC 范围 1200～10800 kWh；初始 SOC 为 2025-01-01 00:00 的 6000 kWh。
- 充放电功率：均不超过 5000 kW，即每个 10 分钟时段最多 833.3333 kWh。
- 储能效率：默认充电、放电单边效率均为 90%，隐含往返效率 81%，另做往返效率口径敏感性分析。
- 正常购电价：问题 1～3 使用附件 1；问题 4 使用附件 4。
- 紧急购电价：交易时刻电价的 5 倍。
- 调整价格：低于初始计划量部分按 0.5 倍价格，高于初始计划量部分按 1.5 倍价格。
- 正式输出期：2025-02-01 至 2025-12-31，共 334 天；2025 年 1 月用于储能初始化。

## 四、附件与结果模板映射

| 附件 | 内容 | 使用问题 | 关键读取规则 |
|---|---|---|---|
| 附件 1 | 单日电价、负载、光伏预测 | Q1、Q2、Q3 | 144 个 10 分钟位置；功率字段乘 1/6 转能量 |
| 附件 2 | 全年负载和光伏实际功率 | Q2、Q3、Q4 | 两个工作表；365 天 × 144 时段；逐日传递储能 |
| 附件 3 | 四时刻未来 24 小时整点预报 | Q3、Q4-3 | 日期列向下填充；整点预报映射到 10 分钟时段 |
| 附件 4 | 全年逐 10 分钟电价 | Q4-2、Q4-3 | 历史价格用于场景建模，实际路径用于样本外评价 |
| 附件 5 | 五个结果模板 | 全部 | 只作为输出结构，禁止当作原始建模数据 |

## 五、必须冻结的口径

1. **时间轴**：按附件列位置与结果模板时段位置一一映射，数值不平移。附件时间 `00:10～0:00+1` 与 result1 的 `0:10-0:20～0:00-0:10+1` 存在标签语义差，S3 必须专项校验。
2. **储能效率**：主口径为单边 90%，往返 81%。
3. **光伏剩余量**：允许弃光，不允许反向售电。
4. **问题 2 紧急购电**：使用实际负载和实际光伏制定计划时，主结果紧急购电量为 0；另设预报对照。
5. **问题 3 调整费用**：最终调整量与 0:00 初始计划量比较。
6. **问题 4 电价可知性**：实际电价不能作为日前已知输入；确定性模型只作为完美信息基准。

## 六、S1 结论

数据完整，不需要外部公开数据。四问均可建立在统一的 144 时段储能调度框架上，主要风险集中在时间标签、储能效率、问题 2 紧急购电机制和问题 4 价格可知性。上述口径已写入 `problem_analysis.json`，供 S2 模型路线继续使用。
"""


def build_b():
    return """# B 论文大纲

## 摘要

- 问题背景、四问任务。
- 统一 LP/滚动优化主模型和 Q4 随机 CVaR 扩展。
- 给出全天购电量、购电费、全年费用、调整节省、波动电价风险指标等关键数字。
- 结论回答“是否值得增加预报时刻”和“波动电价下策略如何变化”。

## 1. 问题重述

### 1.1 问题背景

### 1.2 已知条件与待求任务

### 1.3 四个子问题的联系

## 2. 模型假设与符号说明

### 2.1 模型假设

覆盖时间区间、功率转能量、储能效率、弃光、完美信息、调整费用和价格可知性。

### 2.2 符号表

统一列出 `g_t、c_t、d_t、E_t、e_t、q_t、q_bar_t、u_t、rho_t、eta_c、eta_d`。

## 3. 数据说明与预处理

### 3.1 附件字段和时间轴

### 3.2 合并单元格处理

### 3.3 整点预报到 10 分钟粒度映射

### 3.4 数据质量检查

## 4. 问题一：单日确定性购电与储能调度模型

### 4.1 模型建立

### 4.2 约束与目标函数

### 4.3 求解方法

### 4.4 指定时段结果与全天结果

### 4.5 储能充放电和 SOC 分析

### 4.6 模型检验

## 5. 问题二：全年逐日计划购电模型

### 5.1 逐日 LP 和跨日储能状态传递

### 5.2 紧急购电机制

### 5.3 2025 年 1 月初始化与 334 天输出口径

### 5.4 四个指定日期结果

### 5.5 全年费用与紧急购电分析

### 5.6 完美信息假设和预报对照

## 6. 问题三：多时刻光伏预报滚动调整模型

### 6.1 滚动时域决策框架

### 6.2 计划量、调整量和偏差费用

### 6.3 预报到 10 分钟的映射

### 6.4 四预报时刻策略求解

### 6.5 预报时点消融实验

### 6.6 是否需要更多预报时刻

## 7. 问题四：波动电价下的随机购电策略

### 7.1 确定性完美信息基准

### 7.2 电价统计特征、日内周期和残差

### 7.3 块 bootstrap 场景生成

### 7.4 SAA 随机线性规划

### 7.5 期望费用与 CVaR 风险目标

### 7.6 问题 4-2 结果

### 7.7 问题 4-3 滚动蒙特卡洛 MPC

### 7.8 固定价与波动价、确定性与随机策略对比

## 8. 模型检验与敏感性分析

### 8.1 时间标签口径

### 8.2 储能效率口径

### 8.3 调整费用基准

### 8.4 场景数、块长、CVaR 参数

### 8.5 电价扰动和前一日价格基准

## 9. 模型评价与推广

### 9.1 优点

### 9.2 不足与适用范围

### 9.3 推广方向

## 10. 结论

按 Q1～Q4 逐项给出数值结论，并明确回答 Q3 的预报时刻选择问题。

## 参考文献

## 附录

### 附录 A 模型公式

### 附录 B 关键代码说明

### 附录 C 结果文件说明
"""


def build_c():
    return """# C 评分点对齐表

| 评分点 | 对应证据 | 论文位置 | 验收标准 |
|---|---|---|---|
| 问题重述准确 | 四问目标、输入、输出和约束；`problem_analysis.json` | 第 1 章 | 不遗漏购电、储能、紧急购电、调整费用和波动电价 |
| 数据说明完整 | 附件字段表、时间轴、单位、缺失与合并单元格处理 | 第 3 章 | 每个字段可追溯到附件和用途 |
| 模型假设合理 | 时间、效率、弃光、完美信息、调整费用、价格可知性假设 | 第 2 章 | 每个关键假设说明依据和影响 |
| 符号统一 | 统一符号表、单位表、上下标规则 | 第 2 章 | 四问共用符号不冲突，功率与能量单位不混用 |
| Q1 模型正确 | 单日 LP、功率平衡、SOC 动态、边界条件 | 第 4 章 | result1 与正文表 1、表 2 一致 |
| Q1 求解可信 | 约束满足率、E0=E144、无储能对照 | 第 4.6 节 | 约束残差达到数值精度，结果可复现 |
| Q2 模型正确 | 逐日 LP、跨日储能传递、334 天输出 | 第 5 章 | 日期完整、SOC 连续、result2 可回算 |
| Q2 机制说明 | 紧急购电公式、完美信息说明、预报对照 | 第 5.2、5.6 节 | 解释主结果紧急购电为 0 的原因，并给出对照结果 |
| Q3 模型正确 | 滚动时域、锁定历史决策、最终执行量规则 | 第 6 章 | result3 的初始计划和调整计划字段完整 |
| Q3 回答原问 | 四种预报时点策略的消融实验 | 第 6.5、6.6 节 | 用总费用和调整费用定量回答是否需要新增预报 |
| Q4 模型正确 | 场景生成、SAA、CVaR、滚动 MPC | 第 7 章 | 训练场景与样本外评价严格分离 |
| Q4 风险刻画 | 期望、标准差、VaR、CVaR、最坏情景 | 第 7.5、7.8 节 | 不仅比较平均值，还展示尾部风险 |
| 对照实验充分 | 无储能、规则策略、固定价/波动价、确定性/随机、预报时点 | 第 4～8 章 | 对照对象、指标和结论一一对应 |
| 敏感性分析 | 时间、效率、费用口径、场景参数、价格扰动 | 第 8 章 | 结论不因合理口径变化而失效 |
| 结果文件一致 | `result1` 至 `result4-3` 与论文表格、图形、摘要数字一致 | 各结果章、附录 | 机器校验报告 PASS，数值逐项匹配 |
| 创新性表达 | 滚动预报消融、随机 CVaR、完美信息与可执行策略分离 | 摘要、第 6～7 章、模型评价 | 创新点服务于题意，不堆砌无关模型 |
| 论文可读性 | 摘要数字、图表顺序、公式编号、结论闭环 | 全文 | 图表自解释，结论直接回答四问 |
"""


def build_d(analysis):
    routes = analysis["recommended_models"]
    detailed = []
    questions = {item["id"]: item for item in analysis["questions"]}
    for route in routes:
        question = questions[route["question_id"]]
        detailed.append(
            {
                "question_id": route["question_id"],
                "title": question["title"],
                "task_type": route["task_type"],
                "baseline_model": route["baseline"],
                "primary_model": route["primary"],
                "backup_model": route["backup"],
                "input_attachments": question["inputs"],
                "decision_variables": question["decision_variables"],
                "objective": question["objective"],
                "constraints": question["constraints"],
                "required_results": question["required_results"],
                "result_files": question["result_files"],
                "validation_plan": question["validation"],
                "figure_suggestions": question["figure_suggestions"],
            }
        )
    return detailed


def build_e(analysis):
    return """# E 数据与输出契约

## 一、统一时间索引

| 项目 | 约定 |
|---|---|
| 日期间隔 | 10 分钟 |
| 每日时段数 | 144 |
| 时段长度 | `Delta t = 1/6 h` |
| 正式输出期 | 2025-02-01 至 2025-12-31，共 334 天 |
| 初始化期 | 2025-01-01 至 2025-01-31 |
| 附件 2、4 | 365 天 × 144 个位置 |
| 附件 3 | 每天 4 个预报时刻 × 24 个整点预报 |

附件 1、2、4 的第 k 个数据位置与结果模板第 k 个 10 分钟时段位置一一对应。附件 1 的 `00:10～0:00+1` 和 result1 的 `0:10-0:20～0:00-0:10+1` 存在标签偏移，S3 必须用首末时段、全天总量和储能边界做专项校验。

## 二、单位与转换

| 数据 | 原始单位 | 模型单位 | 转换 |
|---|---|---|---|
| 负载 | kW | kWh | `× 1/6` |
| 光伏功率 | kW | kWh | `× 1/6` |
| 电价 | 元/kWh | 元/kWh | 不变 |
| 充放电功率上限 | kW | kWh/时段 | `5000 × 1/6` |
| 储电量 | kWh | kWh | 不变 |

## 三、储能公式

默认采用单边效率：

```text
E[t] = E[t-1] + eta_c * c[t] - d[t] / eta_d
eta_c = eta_d = 0.9
1200 <= E[t] <= 10800
0 <= c[t], d[t] <= 5000 / 6
```

问题 1 要求 `E[0] = E[144]`。全年模型每天把当日末储电量传给次日初储电量。

## 四、费用公式

正常计划购电：

```text
C_plan[t] = rho[t] * q_plan[t]
```

最终调整量与 0:00 初始计划量比较：

```text
C_adjust[t] =
rho[t] * q_final[t] + 0.5 * rho[t] * max(q_initial[t] - q_final[t], 0)
if q_final[t] < q_initial[t]

C_adjust[t] =
rho[t] * q_initial[t] + 1.5 * rho[t] * max(q_final[t] - q_initial[t], 0)
if q_final[t] > q_initial[t]
```

紧急购电：

```text
C_emergency[t] = 5 * rho[t] * e[t]
```

## 五、输出文件

| 文件 | 工作表 | 口径 |
|---|---|---|
| result1.xlsx | 计划购电量 | 单日 144 个 10 分钟购电量 |
| result1.xlsx | 充放电量 | 六段充电量、放电量及 0:00、24:00 储电量 |
| result2.xlsx | 计划购电量 | 2025-02-01 至 2025-12-31 每日 144 个计划量 |
| result2.xlsx | 充放电量 | 每日六段充放电量及边界储电量 |
| result2.xlsx | 紧急购电量 | 日期、时间段、购电量 |
| result3.xlsx | 计划购电量 | 0:00 初始计划 |
| result3.xlsx | 调整购电量 | 其他预报时刻调整后的最终量 |
| result3.xlsx | 充放电量 | 最终储能计划 |
| result3.xlsx | 紧急购电量 | 最终紧急购电记录 |
| result4-2.xlsx | 同 result2 | 波动电价下问题 2 结果 |
| result4-3.xlsx | 同 result3 | 波动电价下问题 3 结果 |

## 六、关键风险

1. 时间标签偏移可能影响指定时段结果，S3 必须专项校验。
2. 90% 是单边效率还是往返效率会影响费用，S5 要做双口径。
3. 光伏富余量若不能弃光，部分时段可能不可行。
4. 问题 2 使用完美信息时紧急购电量为 0，需要用预报对照解释机制。
5. 问题 4 的实际电价只能用于样本外评价，不能当作日前已知信息。
"""


def main():
    STEP1_DIR.mkdir(parents=True, exist_ok=True)
    analysis = build_analysis()
    write_text(
        STEP1_DIR / "problem_analysis.json",
        json.dumps(analysis, ensure_ascii=False, indent=2),
    )
    write_text(STEP1_DIR / "A_题意对齐.md", build_a(analysis))
    write_text(STEP1_DIR / "B_论文大纲.md", build_b())
    write_text(STEP1_DIR / "C_评分点对齐表.md", build_c())
    write_text(
        STEP1_DIR / "D_模型路线.json",
        json.dumps(build_d(analysis), ensure_ascii=False, indent=2),
    )
    write_text(STEP1_DIR / "E_数据与输出契约.md", build_e(analysis))
    print("S1 structured outputs written to: {}".format(STEP1_DIR))


if __name__ == "__main__":
    main()

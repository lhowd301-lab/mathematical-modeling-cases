# C 题建模代码

## 运行

```powershell
py -3.12 paper_output/code/modeling/run_modeling.py
```

可选的波动电价情景压力测试：

```powershell
py -3.12 paper_output/code/modeling/run_modeling.py --enable-stochastic
```

## 模块

- `common_storage_lp.py`：统一 144 时段储能 LP、单位换算和调度约束。
- `q1_model.py`：单日确定性调度，强制首末储电量均为 6000 kWh。
- `q2_model.py`：2025 全年逐日 LP，1 月初始化，2 月 1 日至 12 月 31 日输出。
- `q3_model.py`：0:00、6:00、12:00、18:00 滚动调整，包含 A/B/C/D 预报时点消融。
- `q4_model.py`：使用附件 4 实际波动电价重算问题 2 和问题 3；可选块 bootstrap 压力测试。
- `result_contract_io.py`：写入五个结果模板、结果 JSON、指标、结论和运行账本。
- `run_modeling.py`：统一入口和运行哈希记录。

## 输出

- `paper_output/results/result1.xlsx`
- `paper_output/results/result2.xlsx`
- `paper_output/results/result3.xlsx`
- `paper_output/results/result4-2.xlsx`
- `paper_output/results/result4-3.xlsx`
- `paper_output/results/model_results.json`
- `paper_output/results/metrics.json`
- `paper_output/results/conclusions.json`
- `paper_output/results/run_manifest.json`
- `paper_output/tables/table_index.json`

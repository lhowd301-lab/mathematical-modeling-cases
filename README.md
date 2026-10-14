# 数学建模案例集

生产过程决策与微电网购售储协同调度的 Python 求解案例。

## 案例

| 目录 | 内容 |
| --- | --- |
| `production-decision/` | 2024 全国大学生数学建模竞赛 B 题，抽样检测、生产决策、多工序优化与抽样不确定性。 |
| `microgrid-dispatch/` | 微电网购售储协同调度，四问模型、线性优化、预测与策略对照。 |

每个案例保留算法、数据说明、数值结果和图表。赛题及原始附件请从官方竞赛发布渠道取得。团队论文、承诺书、第三方文献全文和个人识别信息不分发。

```bash
python -m pip install -r requirements.txt
cd production-decision
python 求解/问题一/问题一_抽样检测方案.py
python 求解/问题二/问题二_生产决策优化.py
python 求解/问题三/问题三_多工序决策优化.py
python 求解/问题四/问题四_抽样不确定重新决策.py
```

Python 3.10+。微电网入口为 `microgrid-dispatch/paper_output/code/modeling/run_modeling.py`，模型就绪数据使用 gzip 无损压缩保存，先在 `microgrid-dispatch/` 执行 `python prepare_data.py`，再运行模型入口。生产决策四问已在整理时重新运行通过；微电网原历史结果另行标注。

## 项目说明

维护者：[lhowd301-lab](https://github.com/lhowd301-lab)。本仓库整理自既有课程、研究或工具项目，开发与文档整理使用了 AI 辅助。代码可运行性与研究结论有效性分别说明，不将历史模拟结果视为实盘业绩。

# 微电网输入数据

保留原赛题附件的模型就绪序列，使用 gzip 无损压缩。文件包含负荷、光伏、电价和预测字段，不含个人或账户资料。来源及 SHA-256 见 `../../dataset_manifest.json`。

在 `microgrid-dispatch/` 执行 `python prepare_data.py` 后，原求解脚本可直接读取 CSV。原始赛题 PDF、未处理 Excel、团队论文和第三方全文未上传。

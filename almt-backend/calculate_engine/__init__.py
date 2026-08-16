"""
经营计划模拟系统 - 计算引擎（Python 重写版）

4 个引擎：
- ENGINE A 业务分摊（业务计划分摊到账户册树）
- ENGINE B 定价策略分摊（BP 叠加 + FTP 收入）
- ENGINE C 现金流计量（动态现金流生成）
- ENGINE D 指标计量（23 组指标计算）

入口：runner.run_full_calculate(task_id, data_date)
"""
__version__ = "0.1.0"
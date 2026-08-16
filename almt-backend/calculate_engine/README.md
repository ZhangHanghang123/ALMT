# 经营计划模拟系统 - 计算引擎 (Python 重写版)

> 用 Python 完整重写原系统的 4 个 Excel 计算引擎（ENGINE A/B/C/D），实现业务分摊、定价策略分摊、现金流计量、指标计量。

## 快速开始

### 1. 测试基础架构

```bash
cd almt-backend
python -m calculate_engine.tests.test_loader        # 数据加载
python -m calculate_engine.tests.test_coa_tree      # 账户册树
python -m calculate_engine.tests.test_engine_a      # ENGINE A 业务分摊
python -m calculate_engine.tests.test_engine_b      # ENGINE B 定价策略
python -m calculate_engine.tests.test_engine_c      # ENGINE C 现金流
python -m calculate_engine.tests.test_engine_d      # ENGINE D 指标计量
```

### 2. 加载数据并查看

```python
from calculate_engine.core import load_all_params, build_coa_tree
from calculate_engine.engines import (
    allocate_business_plan,      # ENGINE A
    get_bp_with_baseline
)
from calculate_engine.engines.engine_b_pricing import run_engine_b    # ENGINE B
from calculate_engine.engines.engine_c_cashflow import run_engine_c   # ENGINE C
from calculate_engine.engines.engine_d_indicators import run_engine_d # ENGINE D

data = load_all_params()
result_a = allocate_business_plan(data.coa_info, data.business_plan)
result_b = run_engine_b(data.coa_info, data.coa_attribute, data.custom_strategy, ...)
result_c = run_engine_c(data.coa_info, data.coa_attribute, data.business_plan, data.current_position, ...)
result_d = run_engine_d(data, engine_c_result=result_c)  # ENGINE D 依赖 ENGINE C
```

## 目录结构

```
calculate_engine/
├── core/                       # 核心数据模型
│   ├── loader.py               # MySQL → DataFrame ✅
│   ├── coa_tree.py             # 账户册树 + 聚合算法 ✅
│   ├── period.py               # 24 期数据结构 ⏳
│   └── saver.py                # 写回 MySQL ⏳
├── engines/                    # 4 个引擎实现
│   ├── engine_a_allocate.py    # 业务分摊（直接在 __init__.py 里） ✅
│   ├── engine_b_pricing.py     # 定价策略分摊 ✅
│   ├── engine_c_cashflow.py    # 现金流计量 ✅
│   └── engine_d_indicator.py   # 指标计量 ⏳
├── tests/                      # 测试用例（全部通过）
│   ├── test_loader.py          # ✅
│   ├── test_coa_tree.py        # ✅
│   ├── test_engine_a.py        # ✅
│   ├── test_engine_b.py        # ✅
│   └── test_engine_c.py        # ✅
├── MEASUREMENT_MANUAL.md       # 计量手册（数据源 + 计算过程 + 结果表）
├── PLAN.md                     # 8 周开发计划
└── README.md                   # 本文档
```

## 进度

| 阶段 | 状态 | 完成时间 |
|---|---|---|
| 阶段 1：基础架构（loader + coa_tree） | ✅ | 2026-08-15 |
| 阶段 2：ENGINE A 业务分摊（v2：按比例） | ✅ | 2026-08-15 |
| 阶段 3：ENGINE B 定价策略 | ✅ | 2026-08-15 |
| 阶段 4：ENGINE C 现金流计量（含 schedule 支持） | ✅ | 2026-08-16 |
| 阶段 5：ENGINE D 指标计量 | ✅ | 2026-08-15 |
| 阶段 6：主流程 runner.py + API 集成 | ✅ | 2026-08-16 |
| 阶段 7：数据对账（Excel ↔ MySQL） | ✅ | 2026-08-16 |

**总测试**：37 个，全部通过 |

## 一键运行完整 4 引擎

```bash
cd almt-backend
python -m calculate_engine.runner  # 冒烟测试，约 11s 完成
```

## 一键对账（原 Excel vs MySQL）

```bash
python reconcile_with_excel.py    # 输出 reports/reconcile_<TIMESTAMP>.json
```

## ENGINE C 完全对标（可选）

```bash
python migrate_add_cashflow_schedule.py   # 新增表（如果未创建）
# 然后从原 xlsm 的"标准化剩余本金表"导入数据到 almt_param_cashflow_schedule
```

## 当前输出规模

| 引擎 | 行数 | 列数 | 关键列 |
|---|---:|---:|---|
| ENGINE A | 774 | 99 | `bp_balance_1~24`, `bp_average_1~24`, `cum_balance_1~24`, `cum_average_1~24`, `m0_balance`, `m0_average`, `m0_rate` |
| ENGINE B | 774 | 96 | `base_rate_1~24`, `pricing_rate_1~24`, `ftp_income_1~24`, `delta_ftp_1~24` |
| ENGINE C | 774 | 75 | `principal_0~24`, `interest_0~24`, `total_0~24` |

## 关键设计决策

详见 `MEASUREMENT_MANUAL.md` 各章节
1. **ENGINE A**：简化设计，不做树形分摊（数据已按层级挂在账户册上）
2. **ENGINE B**：BP 叠加 → 小数（× 0.0001），FTP 月化（× / 12）
3. **ENGINE C**：模式 sum 标准化（不超额还本），还本基于上期余额
4. **数据精度**：Decimal → float（在 loader 中转换），容许 ±0.01 元浮点误差
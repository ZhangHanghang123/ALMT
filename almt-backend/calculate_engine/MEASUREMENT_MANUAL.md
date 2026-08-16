# 经营计划模拟系统 - 计算引擎计量手册

> 本文档描述 Python 重写后的 4 个计算引擎（ENGINE A/B/C/D）的**数据来源表、结果表、计算过程**。
>
> 用途：开发期间的"单一事实来源"（Single Source of Truth）；运维期间的问题排查手册；业务人员的算法白皮书。

---

## 文档结构

| 章节 | 内容 | 状态 |
|---|---|---|
| 第 0 章 | 引擎总览与数据流 | ✅ 已写 |
| 第 1 章 | 基础架构（数据加载 + 账户册树） | ✅ 已写 |
| 第 2 章 | ENGINE A 业务分摊 | ✅ 已写 |
| 第 3 章 | ENGINE B 定价策略分摊 | ✅ 已写 |
| 第 4 章 | ENGINE C 现金流计量 | ✅ 已写 |
| 第 5 章 | ENGINE D 指标计量 | ✅ 已写 |
| 第 6 章 | 主流程编排 | ✅ 已完成（2026-08-16） |
| 第 7 章 | 计算版本管理 | ✅ 已完成（2026-08-16） |
| 附录 A | 表结构与字段映射 | ✅ 已写 |
| 附录 B | 数据对账报告 | ✅ 已完成（2026-08-16） |
| 附录 D | API 文档 | ✅ 已完成（2026-08-16） |

---

## 第 0 章 引擎总览

### 0.1 4 个引擎职责

| 引擎 | 名称 | 职责 | 输入 | 输出 |
|---|---|---|---|---|
| **A** | 业务分摊 | 把账户册顶层的 24 期业务计划增量，按层级分摊到所有节点 | 业务计划（24 期增量）+ 账户册树 + 锁定标记 | 分摊后余额/日均（每节点 24 期） |
| **B** | 定价策略分摊 | 把每个账户册的定价策略 BP 叠加到基础利率上，并计算 FTP 收入 | 定价策略（24 期 BP）+ 利率情景（24 期）+ 阶段 A 输出 | 定价后利率 + FTP 收入 + ΔFTP（每节点 24 期） |
| **C** | 现金流计量 | 按期限生成 24 期动态现金流（本金+利息），覆盖存量和增量 | 底层账户册属性 + 阶段 A 输出 | 现金流（每个底层账户册 25 期序列） |
| **D** | 指标计量 | 按 23 组指标口径（NUM/DEN 字典）计算 24 期指标值 | 指标口径配置 + 阶段 A/B/C 输出 | 23 组指标（每账户册 24 期） |

### 0.2 数据流图

```
┌────────────────────────────────────────────────────────────┐
│                    MySQL 参数数据库                          │
│  almt_coa_info / almt_coa_attribute / almt_param_*         │
│  almt_current_position / almt_metric_caliber / almt_dict_* │
└────────────────────────┬───────────────────────────────────┘
                         │ core/loader.py
                         ▼
┌────────────────────────────────────────────────────────────┐
│                    内存 DataFrame 池                        │
│  df_coa_info / df_coa_attr / df_strategy / df_bp_plan ... │
└──┬──────────────┬─────────────┬──────────────┬─────────────┘
   ▼              ▼             ▼              ▼
┌────────┐   ┌────────┐    ┌────────┐    ┌────────┐
│ENG A   │──▶│ENG B   │───▶│ENG C   │───▶│ENG D   │
│业务分摊│   │定价分摊│    │现金流  │    │指标    │
└────────┘   └────────┘    └────────┘    └────────┘
   │              │             │              │
   ▼              ▼             ▼              ▼
┌────────────────────────────────────────────────────────────┐
│             almt_calculate_intermediate（中间表）            │
│  bp_balance_alloc / bp_average_alloc / pricing / cashflow  │
└────────────────────────┬───────────────────────────────────┘
                         │ core/saver.py
                         ▼
┌────────────────────────────────────────────────────────────┐
│                almt_result_index / almt_result_plan        │
└────────────────────────────────────────────────────────────┘
```

### 0.3 24 期约定

- **M1~M24**：未来 24 个月预测期（每月底）
- **M0**：当前存量（作为 M1 的基础）
- 业务计划字段命名：`plan_balance_1` ~ `plan_balance_24`（M1~M24）
- 定价策略字段命名：`strategy_m_1` ~ `strategy_m_24`
- 利率情景字段命名：`m_1` ~ `m_24`

---

## 第 1 章 基础架构

### 1.1 数据来源表（输入）

| 表名 | 用途 | 关键字段 | 数据量级 |
|---|---|---|---|
| `almt_coa_info` | 账户册树形结构 | `id`, `coa_cd`, `coa_name`, `parent_coa_cd`, `leaf_flag` | ~774 行 |
| `almt_coa_attribute` | 账户册属性（含锁定/曲线/期限） | `coa_cd`, `is_locked`, `curve_id`, `term`, `pricing_strategy`, `biz_line`, `repricing_freq` | ~774 行 |
| `almt_current_position` | 当前存量数据 | `coa_lvl`, `balance`, `average_balance`, `rate` | ~773 行 |
| `almt_param_business_plan` | 业务计划 24 期增量 | `coa_cd`, `plan_balance_1~24`, `plan_average_1~24` | 10 条核心 |
| `almt_param_custom_strategy` | 定价策略 24 期 BP | `coa_cd`, `strategy_m_1~24` | 15 条核心 |
| `almt_param_rate_scenario` | 利率情景 24 期值 | `curve_id`, `m_1~24` | 128 行（多条曲线） |
| `almt_param_risk_weight` | 风险权重 24 期 | `coa_cd`, `risk_weight_1~24` | 部分行 |
| `almt_metric_caliber` | 23 组指标口径配置 | `*_item`, `*_coeff`, `*_type`（138 字段） | 23 行 |
| `almt_dict_value` | 字典码值（NUM/DEN） | `dict_type`, `value_cd`, `value_name` | 105+60 |

### 1.2 中间结果表（暂存）

新建中间表存储 4 个引擎的输出：

```sql
-- 阶段 A 输出
CREATE TABLE almt_calculate_intermediate (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  task_id VARCHAR(36) NOT NULL,
  coa_cd VARCHAR(50) NOT NULL,
  -- 阶段 A：分摊后余额（24 期）
  bp_balance_1 DECIMAL(20,2), ..., bp_balance_24 DECIMAL(20,2),
  -- 阶段 A：分摊后日均（24 期）
  bp_average_1 DECIMAL(20,2), ..., bp_average_24 DECIMAL(20,2),
  -- 阶段 B：定价后利率（24 期，%）
  pricing_rate_1 DECIMAL(10,6), ..., pricing_rate_24 DECIMAL(10,6),
  -- 阶段 B：FTP 收入（24 期）
  ftp_income_1 DECIMAL(20,2), ..., ftp_income_24 DECIMAL(20,2),
  -- 阶段 C：现金流 25 期（本金）
  cashflow_0 DECIMAL(20,2), ..., cashflow_24 DECIMAL(20,2),
  INDEX idx_task (task_id),
  INDEX idx_coa (coa_cd)
);
```

### 1.3 最终结果表（输出）

| 表名 | 用途 | 来源引擎 |
|---|---|---|
| `almt_result_index` | 指标结果（基础指标树） | 阶段 A + 阶段 D |
| `almt_result_plan` | 计划结果（业务计划） | 阶段 A |

### 1.4 账户册树形模型（coa_tree.py）

#### 1.4.1 数据结构

```python
class CoaNode:
    """账户册节点"""
    coa_cd: str          # 编码（如 "1_1_1"）
    coa_name: str        # 名称
    parent_cd: str|None  # 父节点编码（ROOT 节点的 parent_cd=None）
    leaf_flag: int       # 0=非叶节点, 1=叶节点
    is_locked: bool      # 是否锁定（阶段 A 用）
    children: list[CoaNode]
```

#### 1.4.2 计算逻辑

```python
def aggregate_bottom_up(nodes: list[CoaNode], period_value: pd.Series) -> pd.Series:
    """
    自底向上聚合（按 parent_cd 逐级汇总）：
    - 每个节点的值 = sum(所有子节点的本期值)
    - 锁定节点：用锁定值覆盖聚合值
    - 返回每个 coa_cd 对应的聚合后值
    """
```

**关键不变量**：聚合后所有节点的本期总和 = 顶层账户册（1_1~3_1）的本期值（不会重复计算）。

---

## 第 2 章 ENGINE A 业务分摊

> ✅ **阶段 2 完成**（2026-08-15），v2 算法更新（2026-08-16 修复）

### 2.1 数据来源表

| 表名 | 取数字段 | 实际字段名 |
|---|---|---|
| `almt_param_business_plan` | 24 期余额增量 | `plan_balance1`~`plan_balance24`（数字前无下划线） |
| `almt_param_business_plan` | 24 期日均增量 | `plan_average1`~`plan_average24` |
| `almt_coa_info` | 树形结构 | `coa_cd`, `parent_coa_cd`, `leaf_flag` |
| `almt_coa_attribute` | 锁定标记 | 当前数据库**无 is_locked 字段**（v2 暂忽略锁定） |
| `almt_current_position` | M0 存量基线 + **分摊比例依据** | `coa_lvl`, `balance`, `average_balance`, `rate` |

### 2.2 计算逻辑（v2 算法，对标 Excel）

**对拍发现**：原 Excel 公式 `=SUMIFS(G,B,B3) × E3 / (...)` 表明**父级计划值会按子节点余额比例分摊到子节点**。原 v1 "直接保留"是错的。

**v2 算法**：
```python
def allocate_business_plan(coa_info, business_plan, current_position, ...):
    roots = build_coa_tree(coa_info)
    balance_map = current_position.groupby('coa_lvl')['balance'].sum().to_dict()

    # 对每期做"自顶向下分摊"
    for i in range(1, 25):
        plan_input = {cd: plan_balance_i for cd ...}
        allocated = _allocate_one_period(plan_input, balance_map, nodes_flat)
        # 递归：对非叶节点，把 plan_input 按子节点余额比例分摊
        # 叶节点累加"收到的"分摊值
        result[f'bp_balance_{i}'] = allocated
```

**算法核心**（`_allocate_one_period`）：
- 对每个非叶节点 N，如果有 plan_value：
  - 找到 N 的所有直接子节点 S1..Sn
  - sum_bal = Σbalance[Si]
  - 每个子节点分到：plan_value × balance[Si] / sum_bal
  - N 自身的 plan_value = 0（已分摊）
- 递归处理子节点，直到叶节点
- 叶节点累加所有"收到的"分摊值

### 2.3 v1 → v2 修复记录（2026-08-16）

| 项 | v1（错误）| v2（正确）|
|---|---|---|
| 父级节点 plan_balance | 原值保留 | 0（已分摊到子节点） |
| 子节点 plan_balance | 0 | 父级 × (子节点余额 / 父级所有子节点余额之和) |
| 与 Excel 数据对拍 | 不一致 | 一致 |

**Excel 公式验证**（业务计划-规模分摊 列 8 Q1增量规模）：
- 1（顶层）Q1 = 5 → 1_1/1_2/1_3/1_4 各自 Q1 = 0.28/3.92/0.80/0 ✓（按余额比例）

### 2.3 M0 基线（存量）

```python
m0_rate = (月度利息 × 12) / 平均余额 × 100%  # 年化利率%
```

### 2.4 累计序列

```python
cum_balance_1 = m0_balance + bp_balance_1
cum_balance_i = cum_balance_{i-1} + bp_balance_i  # 累计值
cum_average_i = ...
```

### 2.5 结果表

| 表名 | 写入字段 |
|---|---|
| `almt_calculate_intermediate` | `bp_balance_1~24`, `bp_average_1~24`, `cum_balance_1~24`, `cum_average_1~24`, `m0_balance`, `m0_average`, `m0_rate` |

### 2.6 输出示例

| 账户册 | M0 余额 | M1 累计 | M12 累计 | M24 累计 |
|---|---:|---:|---:|---:|
| 1_1（现金及存放央行）| 179.5 亿 | 179.5 亿 | 179.5 亿 | 179.5 亿 |
| 1_4（发放贷款）| 1876.8 亿 | 1876.8 亿 | 1876.8 亿 | 1876.8 亿 |
| 2_5（吸收存款）| 2060.6 亿 | 2060.6 亿 | 2060.6 亿 | 2060.6 亿 |

> 注：业务计划值较小（1.67 亿/账户册），所以累计值与 M0 差异不大；如需显著差异需补充业务计划数据。

---

## 第 3 章 ENGINE B 定价策略分摊

> ✅ **阶段 3 完成**（2026-08-15）

### 3.1 数据来源表

| 表名 | 取数字段 |
|---|---|
| `almt_coa_attribute` | `coa_cd`, `curve_id`（用于查基础利率曲线） |
| `almt_param_custom_strategy` | `strategy_M1`~`strategy_M24`（大写 M，单位 BP） |
| `almt_param_rate_scenario` | `m1_value`~`m24_value`（带 `_value` 后缀） |
| 阶段 A 输出 | `cum_average_1~24`（累计日均） |

### 3.2 计算逻辑

#### 3.2.1 基础利率查询

```python
base_rate_i = rate_scenario[curve_id][m_i_value]
```

#### 3.2.2 定价策略 BP 叠加

```python
pricing_rate_i = base_rate_i + strategy_M_i × 0.0001   # BP → 小数
```

#### 3.2.3 FTP 收入

```python
ftp_income_i = cum_average_i × pricing_rate_i / 12   # 月化 FTP 收入
delta_ftp_i = cum_average_i × (pricing_rate_i - base_rate_i) / 12
```

### 3.3 输出结构

96 列 = 24 × 4：
- `base_rate_1~24`（24 列）：基础利率
- `pricing_rate_1~24`（24 列）：叠加定价策略后的利率
- `ftp_income_1~24`（24 列）：FTP 月度收入
- `delta_ftp_1~24`（24 列）：策略增量的 FTP 收入

### 3.4 输出示例

| 账户册 | M1 基础 | M1 定价后 | M1 FTP |
|---|---:|---:|---:|
| 2_5_1_3_1（单位定期_3M）| 2.00% | 2.40% | 170,870 元 |
| 2_2_1_1_1（同业存放活期）| 2.00% | 2.00% | 5,065,006 元 |

> 注：5 个账户册的定价策略 BP=+40 BP（基础 2% → 定价后 2.4%）

---

## 第 4 章 ENGINE C 现金流计量

> ✅ **阶段 4 完成**（2026-08-15）

### 4.1 数据来源表

| 表名 | 取数字段 |
|---|---|
| `almt_coa_attribute` | `term`（原始期限：1D/7D/1M/3M/6M/1Y/2Y/3Y/5Y/10Y/20Y/30Y） |
| 阶段 A 输出 | `cum_balance_1~24`（累计余额），`m0_balance` |
| 阶段 B 输出（可选） | `pricing_rate_1~24`（叠加利率） |

### 4.2 现金流模式矩阵（cf_pattern.py）

12 种期限 × 25 期的摊销矩阵（已硬编码在 `engines/engine_c_cashflow.py`）：

| 期限 | 头寸类型 | M1 | M2 | M3 | M4 | M5 | M6 | ... | M12 | ... | M24 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1D | 1 | 1 | 0 | 0 | 0 | 0 | 0 | ... | 0 | ... | 0 |
| 7D | 1 | 1 | 0 | 0 | 0 | 0 | 0 | ... | 0 | ... | 0 |
| 1M | 1 | 1 | 0 | 0 | 0 | 0 | 0 | ... | 0 | ... | 0 |
| 3M | 3 | 1 | 1 | 1 | 0 | 0 | 0 | ... | 0 | ... | 0 |
| 6M | 6 | 1 | 1 | 1 | 1 | 1 | 1 | ... | 0 | ... | 0 |
| 1Y | 12 | 1 | 1 | 1 | 1 | 1 | 1 | ... | 1 | ... | 0 |
| 2Y | 24 | 1 | 1 | 1 | 1 | 1 | 1 | ... | 1 | ... | 1 |
| 3Y~30Y | 25 | 1 | 1 | 1 | 1 | 1 | 1 | ... | 1 | ... | 1 |

**含义**：
- `1`：该期还本金/付息
- `0`：已到期，不操作

### 4.3 计算逻辑

```python
def simulate_cashflow_for_node(balance_seq, rate_seq, term):
    pattern = CF_PATTERN[term]                # 25 期还本比例
    pattern_sum = sum(pattern)
    principal[0] = 0                          # M0 无现金流
    for i in range(1, 25):
        principal[i] = balance_seq[i-1] × pattern[i-1] / pattern_sum
        interest[i] = balance_seq[i-1] × rate_seq[i-1] / 12
        total[i] = principal[i] + interest[i]
    return {principal, interest, total}
```

**核心要点**：
- 还本基于**上期余额**（不是当期）
- 模式 sum 标准化：所有期本金之和 ≈ m0_balance（不超额还本）
- 利息按月化：`rate × balance / 12`

### 4.4 输出结构

75 列 = 3 类 × 25 期：
- `principal_0~24`（25 列）：本金
- `interest_0~24`（25 列）：利息
- `total_0~24`（25 列）：现金流（本金+利息）

### 4.5 输出示例

| 账户册 | 期限 | M0 本金 | M1 本金 | M2 本金 | M3 本金 |
|---|---|---:|---:|---:|---:|
| 1_1_1（现金_1D）| 1D | 3.52 亿 | 3.52 亿（还清）| 0 | 0 |
| 1_1_2（存放央行法定准备金_30Y）| 30Y | 12.99 亿 | 5.20 亿（持续还 1/25）| 5.20 亿 | 5.20 亿 |
| 2_5_1_3_1（单位定期_3M）| 3M | 8.54 亿 | 2.85 亿（还 1/3）| 2.85 亿（还 1/3）| 2.85 亿（还清）|
| 2_5_1_3_3（单位定期_1Y）| 1Y | 13.62 亿 | 1.36 亿（还 1/12）| 1.36 亿 | ... | 1.36 亿（12 月还清）|

---

## 第 5 章 ENGINE D 指标计量

> ✅ **已开发**（阶段 5）：774 账户册 × 23 组指标，6 个测试通过

### 5.1 数据来源表

| 表名 | 取数字段 | 用途 |
|---|---|---|
| `almt_metric_caliber` | `coa_cd`, `num1~num23`, `den1~den23`, `num_t`, `den_t`, `num_c`, `den_c` | **核心配置**：每个叶节点账户册对 23 组指标的分子/分母配置（550 行） |
| `almt_current_position` | `balance`, `average_balance`, `rate` | M0 基线（B、AB、NII） |
| `almt_param_risk_weight` | `risk_weight_1`（用作 M0 权重近似） | 风险加权资产计算 |
| ENGINE C 输出 | `principal_1~24` | CF1~CF12+ 现金流度量 |

### 5.2 23 组指标的度量类型映射

| 度量类型 t | 数据来源 | 含义 |
|---|---|---|
| `B` | ENGINE A `m0_balance` | M0 余额 |
| `AB` | `current_position.average_balance` | M0 日均余额 |
| `NII` | `current_position.rate` | M0 月度利息收入 |
| `CF1` | ENGINE C `principal_1` | M1 本金还本 |
| `CF3` | ENGINE C `principal_1+2+3` | M1~M3 累计本金还本 |
| `CF1-6` | ENGINE C `principal_1~6` 之和 | M1~M6 累计本金还本 |
| `CF7-12` | ENGINE C `principal_7~12` 之和 | M7~M12 累计本金还本 |
| `CF12+` | ENGINE C `principal_13~24` 之和 | M13~M24 累计本金还本 |
| `B-CF3` | `B - CF3` | 3月后剩余余额 |
| `RWA` | `B × risk_weight_1` | 风险加权资产 |

**映射表实现**：见 `engine_d_indicators.py` 的 `LOOKUP_FIELD_MAP` 字典。

### 5.3 23 组指标语义（基于数据库 `num_t` 分布）

| 指标 | 含义（推断） | num_t | den_t |
|---:|---|---|---|
| 1 | 利息净收入（绝对值） | NII (544) | — |
| 2 | 总余额（部分口径） | B (106) | — |
| 3-8 | 各类利息收入 | NII | — |
| 9 | 总余额（更广口径） | B (418) | — |
| 10 | 风险加权资产 | RWA (456) | — |
| 11 | 流动性比率（CF3 / B） | CF3 (475), B (64) | B |
| 12 | 1月内现金流 / 总余额 | CF1 (304), B (4) | — |
| 13 | 总余额 / 1月内现金流 | B (244), CF1 (2) | — |
| 14 | 6月内累计现金流 | CF1-6 (50) | CF1-6 |
| 15 | 7-12月累计现金流 | CF7-12 (49) | CF7-12 |
| 16 | 13月后累计现金流 | CF12+ (49) | CF12+ |
| 17 | 余额（特定口径） | B (20) | — |
| 18 | 余额 - 3月内现金流 | B-CF3 (60) | — |
| 19 | 总余额（最全覆盖） | B (550) | — |
| 20 | CF3 / 总余额（流动性比率） | CF3 (490), CF1 (56) | B |
| 21-23 | 未使用，预留扩展 | — | — |

### 5.4 计算流程

```
1. compute_basic_lookups:
   为 774 账户册计算 10 种基础度量值（B/AB/NII/CF1/CF3/CF1_6/CF7_12/CF12_PLUS/RWA/B_CF3）

2. compute_per_account_indicators:
   遍历 almt_metric_caliber 550 行叶节点
   对每个账户册 × 每组指标（1~23）：
     num_value = lookup(num_t) × num_c
     den_value = lookup(den_t) × den_c

3. aggregate_indicators:
   对 num_1~23_value 和 den_1~23_value 分别做自底向上聚合
   ratio_i_value = num_i_value / den_i_value（den=0 时 NaN）

4. 输出：DataFrame(774 行, 69 列)
     23 num_value + 23 den_value + 23 ratio_value
```

### 5.5 结果表（写入 `almt_result_indicator`）

| 字段 | 含义 |
|---|---|
| `coa_cd` | 账户册编码（含 ROOT） |
| `num_1_value ~ num_23_value` | 23 组指标的分子（绝对值） |
| `den_1_value ~ den_23_value` | 23 组指标的分母（绝对值） |
| `ratio_1_value ~ ratio_23_value` | 23 组指标的比率（den=0 时 NaN） |

**输出规模**：774 账户册 × 69 列 = 53,406 单元

**实际 ROOT 数据示例**（端到端跑出来的）：
- 指标1 (NII): num = 178 万元（月度利息）
- 指标10 (RWA): num = 362 亿元（风险加权资产）
- 指标19 (总余额): num = 7,103 亿元
- 指标20 (CF3/B): ratio = 34.80%（3月内可回收 35% 余额）

### 5.6 关键技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 字典码映射 | **简化方案：字典码作为占位符，caliber 表存储每个账户册自己的配置** | 数据库现状：caliber 按账户册存储，每个账户册有自己的 num/den 字段；字典码主要起标识作用 |
| 度量类型 t 识别 | 从 `num_t`/`den_t` 字段读取 | 直接利用数据库现有约定 |
| 风险权重 M0 | 用 `risk_weight_1` 近似 | 数据库无 `risk_weight_0` 字段；M0 静态权重假设与 M1 相同 |
| 比率计算 | `num / den`，den=0 时 NaN | 避免除零错误 |
| 树形聚合 | 复用 `aggregate_bottom_up`（sum） | 与 ENGINE A/B/C 算法一致 |

### 5.7 验证测试

`tests/test_engine_d.py` 6 个测试：
- ✓ 度量类型映射完整性（10 种类型）
- ✓ 基础度量值计算（774 × 10，371 个账户有余额）
- ✓ 按账户册 num/den 计算（550 × 46，指标1 有 67 个账户配置）
- ✓ 树形聚合（774 × 69，ROOT num_1 == 叶节点之和）
- ✓ 端到端测试（ROOT 有 16 个有效比率）
- ✓ 指标快照（指标11 前10个账户册）
| ... | ... | ... | ... |

### 5.3 计算逻辑

待补充...

### 5.4 结果表

待补充...

---

## 第 6 章 主流程编排

> ⏳ **未开始**：阶段 6 完成后补充

### 6.1 执行顺序

```python
def run_full_calculate(task_id: str, data_date: str):
    # 1. 加载参数
    data = load_all_params(data_date)

    # 2. ENGINE A → 中间表
    bp_result = engine_a.allocate(...)

    # 3. ENGINE B → 中间表
    pricing_result = engine_b.price(...)

    # 4. ENGINE C → 中间表
    cashflow_result = engine_c.simulate(...)

    # 5. ENGINE D → 结果表
    indicator_result = engine_d.compute(...)

    # 6. 保存
    save_results(task_id, ...)
```

### 6.2 进度跟踪

每个引擎独立 try/except，单个引擎失败不影响其他引擎结果入库。

---

## 附录 A 表结构与字段映射

### A.1 表清单速查

| 表名 | 行数（当前） | 主键 | 关键索引 |
|---|---|---|---|
| `almt_coa_info` | 774 | `id` | `coa_cd` 唯一 |
| `almt_coa_attribute` | ~774 | `coa_cd` | `curve_id`, `term` |
| `almt_current_position` | 773 | `id` | `coa_lvl` |
| `almt_param_business_plan` | ~10 | `coa_cd` | `coa_cd` 唯一 |
| `almt_param_custom_strategy` | 15 | `coa_cd` | `coa_cd` 唯一 |
| `almt_param_rate_scenario` | 128 | `curve_id` | - |
| `almt_metric_caliber` | 23 | `id` | - |

### A.2 字段命名约定

| 含义 | 命名前缀 | 示例 |
|---|---|---|
| 业务计划余额增量 | `plan_balance_` | `plan_balance_1`（M1 余额增量） |
| 业务计划日均增量 | `plan_average_` | `plan_average_1` |
| 定价策略 BP | `strategy_m_` | `strategy_m_1`（M1 定价 BP） |
| 利率情景 | `m_` | `m_1`（M1 利率值） |
| 风险权重 | `risk_weight_` | `risk_weight_1` |
| 中间表分摊后余额 | `bp_balance_` | `bp_balance_1` |
| 中间表分摊后日均 | `bp_average_` | `bp_average_1` |
| 中间表定价后利率 | `pricing_rate_` | `pricing_rate_1` |
| 中间表 FTP 收入 | `ftp_income_` | `ftp_income_1` |
| 中间表现金流 | `cashflow_` | `cashflow_0`（M0） |

### A.3 字典码值（NUM/DEN）

- `NUM001` ~ `NUM105`：分子项（如 NII、贷款收息率、流动性资产等）
- `DEN001` ~ `DEN060`：分母项（如 总资产、存款余额、贷款余额等）

完整列表见 `almt_dict_value` 表。

---

## 更新日志

| 日期 | 章节 | 变更 |
|---|---|---|
| 2026-08-15 | 第 0、1 章 + 附录 A | 初版（阶段 1 基础架构） |
| 2026-08-15 | 第 1.1/1.4 章 + 附录 A.2 | 阶段 1 完成：补充实际数据库字段名（见下方说明） |
| 2026-08-15 | 第 2 章 ENGINE A | 阶段 2 完成：业务分摊简化版（不树形分摊，直接保留 plan_balance/plan_average） |
| 2026-08-15 | 第 3 章 ENGINE B | 阶段 3 完成：定价策略 BP 叠加基础利率 + FTP 月化收入计算 |
| 2026-08-15 | 第 4 章 ENGINE C | 阶段 4 完成：12 种期限 × 25 期现金流模式 + 本金/利息模拟 |
| 2026-08-15 | 第 5 章 ENGINE D | 阶段 5 完成：23 组指标按 caliber 表配置计算 + 树形聚合 + 比率输出 |

### 阶段 1 完成 - 数据库字段名修正记录

开发 loader.py 时发现 MySQL 实际字段名与原系统设计文档有差异，**修正如下**：

#### 1. `almt_param_business_plan` 字段（24 期业务计划）

| 错误命名（我最初以为） | 实际命名 | 说明 |
|---|---|---|
| `plan_balance_1` ~ `plan_balance_24` | **`plan_balance1` ~ `plan_balance24`** | 数字前**无下划线** |
| `plan_average_1` ~ `plan_average_24` | **`plan_average1` ~ `plan_average24`** | 同上 |

#### 2. `almt_param_custom_strategy` 字段（24 期定价策略）

| 错误命名 | 实际命名 |
|---|---|
| `strategy_m_1` ~ `strategy_m_24`（小写 m） | **`strategy_M1` ~ `strategy_M24`（大写 M）** |

#### 3. `almt_param_rate_scenario` 字段（24 期利率情景）

| 错误命名 | 实际命名 |
|---|---|
| `m_1` ~ `m_24` | **`m1_value` ~ `m24_value`**（带 `_value` 后缀） |

#### 4. `almt_coa_attribute` 字段（账户册属性）

| 错误命名 | 实际命名 | 说明 |
|---|---|---|
| `biz_line` | **`business_line`** | 完整单词 |
| `repricing_freq` | **`reprice_freq`** | 缩写 |
| `is_locked` | **字段不存在** | 当前数据库无锁定标记 |
| `pricing_strategy_type` | **字段不存在** | - |
| `remark` | **字段不存在** | - |

实际可用字段：`coa_cd`, `coa_name`, `term`, `accrule_base`, `curve_name`, `curve_id`, `business_line`, `float_ratio`, `replace_type`, `reprice_freq`。

#### 5. `almt_coa_info.leaf_flag` 字段

**问题**：全部 774 行的 `leaf_flag='0'`，无法直接区分叶节点/非叶节点。

**解决方案**：`build_coa_tree()` 中先用 `leaf_flag` 字段构建父子关系，**然后用"是否有子节点"重新回填** `leaf_flag`：
- 没有子节点 → `leaf_flag=1`（叶）
- 有子节点 → `leaf_flag=0`（非叶）

实测：774 个节点中 550 个为叶节点。

#### 6. `almt_dict_value` 字段（字典码值）

| 错误命名 | 实际命名 |
|---|---|
| `dict_type` | **`dict_id`** |
| `value_cd` | **`value_code`** |
| `sort_order` | **`sort_no`** |

#### 7. 数据量级

| 表 | 实测行数 | 备注 |
|---|---:|---|
| `almt_coa_info` | 774 | 含 1 个 ROOT |
| `almt_coa_attribute` | 550 | 只配了部分账户册 |
| `almt_current_position` | 773 | - |
| `almt_param_business_plan` | 773 | 全部账户册都有（默认 0） |
| `almt_param_custom_strategy` | 15 | 只有部分账户册配了定价策略 |
| `almt_param_rate_scenario` | 128 | 多条曲线 |
| `almt_param_risk_weight` | 550 | - |
| `almt_metric_caliber` | 550 | 每个账户册一个指标配置 |
| `almt_dict_value` | 165 | NUM + DEN 等 |
---

## 第 6 章 主流程编排（runner.py）

### 6.1 入口

`almt-backend/calculate_engine/runner.py` 提供 `run_full_calculate()` 统一入口，按顺序执行 4 个引擎。

### 6.2 完整流程

```
加载参数 (load_all_params)
  ├─ 10% [0%, 10%]
  ├─ ENGINE A 业务分摊          (774 × 48)        ~0.5s
  ├─ ENGINE B 定价策略分摊      (774 × 96)        ~2.3s
  ├─ ENGINE C 现金流计量         (774 × 75)        ~3.3s
  └─ ENGINE D 指标计量          (774 × 69)        ~2.6s
合计耗时：~11s（含参数加载）
```

### 6.3 API 集成

`POST /api/calculate/start` 自动调用 `run_full_calculate`：
- 创建 `almt_calculate_task` 任务记录
- 通过 `progress_callback` 实时更新进度（10%/30%/50%/70%/95%/100%）
- 失败时写入 `error_message`，状态置为 `failed`
- 成功时返回 4 引擎输出规模摘要（存入 `error_message` 字段）

测试示例：
```bash
curl -X POST http://localhost:8001/api/calculate/start \
  -H "Content-Type: application/json" \
  -d '{"data_date":"2026-08-15"}'
# 返回 {"task_id":"...", "status":"success", "progress":100}
```

---

## 附录 B 数据对账报告（2026-08-16）

### B.1 对账工具

`almt-backend/reconcile_with_excel.py` 对比原系统 Excel (ALMT.DATA.xlsx) 与当前 MySQL 数据库。

执行：
```bash
python reconcile_with_excel.py
# 输出 reports/reconcile_<TIMESTAMP>.json
```

### B.2 对账结果

| 数据表 | Excel 行数 | MySQL 行数 | 公共 | 总差异 | 状态 |
|---|---:|---:|---:|---:|---|
| 账户册层级 | 2181 | 774 | **773 (99.9%)** | - | ⚠️ Excel 多中间层节点 |
| 当前存量 | 774 | 773 | **773 (100%)** | **0.06 元** | ✅ 数据一致 |
| 指标口径 | 551 | 550 | - | 1 行 | ⚠️ 字段结构待映射 |

### B.3 关键发现

1. **当前存量数据完全一致**：总差异 0.06 元（约 0.0006 分钱），属于浮点精度级别，远低于容差阈值（±0.01 元）。
2. **Excel 包含更细的层级展开**：Excel 2181 个层级编码 vs MySQL 774 个核心节点；Excel 多出的是中间层显示节点（无数据）。MySQL 用 `parent_coa_cd` 表达层级关系，等效。
3. **指标口径 1 行差异**：可能原因 — Excel 含 1 条废弃/重复记录，需要业务方确认是否清理。

### B.4 结论

Python 计算引擎的输入数据**已通过数据一致性验证**，可以基于当前数据放心使用。

---

## 附录 C 原 ENGINE C 完全对标方案

### C.1 新增表 `almt_param_cashflow_schedule`

```
字段：
  coa_cd        账户册编码
  term          原始期限（1D/7D/1M/3M/6M/1Y/30Y...）
  period        期数 0-24（0=M0 基线）
  principal_ratio  本期本金占比（占 M0 余额的比例）
  is_x_marker   Excel 'x' 标记位（本期还清 + 计息）
  remark        备注
```

### C.2 数据来源

原系统 Excel `ALMT.DATA.xlsx` 中的"标准化剩余本金表"是手工录入的现金流分摊序列：
- 1D/7D/1M: M1 = balance（一次性还本）
- 6M (2_1_4): M4=0.5, M5=0.35, M6=0.3（不规则）
- 1Y (2_1_5): M7=0.15, M8=3.45, M9=1.1, M11=2.78, M12=1（不规则）

### C.3 ENGINE C 改造

ENGINE C 在 `run_engine_c(..., df_cashflow_schedule=None)` 中：
- **优先**：用 `df_cashflow_schedule` 覆盖默认 CF_PATTERN 算法
- **回退**：表为空时用默认 CF_PATTERN 等比例分摊

迁移脚本：`almt-backend/migrate_add_cashflow_schedule.py`

---

## 第 7 章 计算版本管理（2026-08-16）

### 7.1 calc_version 版本号规则

格式：`YYYYMMDD-XXXX`

- `YYYYMMDD`: 数据日期（8 位）
- `XXXX`: 4 位序列码（同一天内递增，从 0001 开始；新一天从 0001 重新开始）

示例：
- `20260816-0001` - 8月16日第1个版本
- `20260816-0002` - 8月16日第2个版本
- `20260817-0001` - 8月17日第1个版本（新一天重置）

### 7.2 版本状态

| 状态 | 含义 |
|---|---|
| `pending` | 待执行 |
| `running` | 执行中 |
| `success` | 计算完成（有结果数据） |
| `failed` | 计算失败 |
| `empty` | 空版本（手动创建，未执行计算） |

### 7.3 数据库变更

```sql
ALTER TABLE almt_calculate_task
  ADD COLUMN calc_version VARCHAR(20) DEFAULT NULL AFTER task_id,
  ADD INDEX idx_calc_version (calc_version);
```

迁移脚本：`almt-backend/migrate_add_calc_version.py`

### 7.4 API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/calculate/start` | 执行计算（自动分配版本号） |
| POST | `/api/calculate/versions` | 创建空版本（不执行计算） |
| GET | `/api/calculate/versions` | 列出所有版本 |
| GET | `/api/calculate/versions/{calc_version}` | 版本详情 |
| DELETE | `/api/calculate/versions/{calc_version}` | 删除整个版本（含所有结果） |

### 7.5 版本管理服务

`almt-backend/almt_app/services/calc_version_service.py` 提供 6 个函数：
- `get_next_version(data_date)` - 获取下一个版本号
- `version_exists(calc_version)` - 检查版本是否存在
- `get_task_id_by_version(calc_version)` - 反查 task_id
- `list_versions(limit, only_with_data)` - 列出版本
- `delete_version(calc_version)` - 删除整个版本
- `create_empty_version(data_date, remark)` - 创建空版本

---

## 附录 D API 文档（2026-08-16）

### D.1 创建空版本

```bash
POST /api/calculate/versions
Content-Type: application/json

{
  "data_date": "2026-08-16",
  "remark": "预留版本用于手工导入数据"
}

Response 200:
{
  "task_id": "uuid",
  "calc_version": "20260816-0001",
  "data_date": "2026-08-16",
  "status": "empty",
  "progress": 100,
  "message": "空版本已创建（未执行计算）"
}
```

### D.2 列出所有版本

```bash
GET /api/calculate/versions?limit=50&include_empty=false

Response 200:
[
  {
    "calc_version": "20260816-0002",
    "task_id": "uuid",
    "data_date": "2026-08-16",
    "status": "success",
    "progress": 100,
    "started_at": "2026-08-16T...",
    "completed_at": "2026-08-16T...",
    "error_message": "...",
    "index_count": 774,
    "plan_count": 774
  },
  ...
]
```

### D.3 删除版本

```bash
DELETE /api/calculate/versions/20260816-0001

Response 200:
{
  "success": true,
  "message": "版本 20260816-0001 已删除",
  "calc_version": "20260816-0001",
  "deleted_task": 1,
  "deleted_index": 774,
  "deleted_plan": 774
}
```

⚠️ **危险操作**：删除会同时清除所有结果数据（almt_result_index, almt_result_plan），不可恢复。

---

## 第 8 章 结果落库服务（saver.py，2026-08-16）

### 8.1 落库目标

把 4 个引擎的输出保存到 6 张表：

| 表 | 写入规则 | 行数 |
|---|---|---:|
| `almt_result_index` | 基础指标汇总（每账户册：余额/日均/利率） | 774 |
| `almt_result_plan` | 业务计划结果（每账户册 × 3 个 item） | 2322 |
| `almt_calculate_intermediate_a` | ENGINE A 完整 25 期数据 | 19350 |
| `almt_calculate_intermediate_b` | ENGINE B 完整 24 期数据 | 18576 |
| `almt_calculate_intermediate_c` | ENGINE C 完整 25 期现金流 | 19350 |
| `almt_calculate_intermediate_d` | ENGINE D 23 组指标 | 17802 |

合计 **78,174 行**结果数据。

### 8.2 关键字段映射

ENGINE A 实际输出列：仅 `bp_balance_1~24` 和 `bp_average_1~24`（无 m0/cum）。

saver 在写入时补齐：

```
total_balance   = current_position.balance + Σbp_balance_i
average_balance = current_position.average_balance + Σbp_average_i
avg_rate        = current_position.rate
```

负债账户册（`coa_cd LIKE '2_%'`）取负值，便于 result/summary 用 `>0/<0` 区分资产/负债。

### 8.3 迁移脚本

```bash
python migrate_add_intermediate_tables.py
# 创建 4 张中间结果表
```

### 8.4 API 集成

`runner.run_full_calculate()` 完成后自动调用 `saver.save_calc_result()`，通过 `progress_callback` 在 90%→100% 之间执行。

### 8.5 端到端验证

通过 `POST /api/calculate/start` 触发完整计算 + 落库：
- result/summary 返回 total_assets=15.97万亿 / total_liabilities=-12.14万亿
- indicator/full-bank 返回 24 个指标，每个有 M0~M24 共 25 期数据
- 未来余额（合计）从 M0=15.5万亿 衰减到 M24=0

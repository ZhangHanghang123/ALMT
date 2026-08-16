# 经营计划模拟系统 - 计算引擎实施方案

> 目标：用 Python 完全替代原系统的 4 个 Excel 引擎（ENGINE A/B/C/D），实现业务分摊、定价策略分摊、现金流计量、指标计量

---

## 一、引擎算法简化分析

经过对 `ALMTCalculateEngine.xlsm`（51 sheet、约 170 万公式）的抽样分析，**实际逻辑模式只有 15-20 种**，每个 sheet 都是这几种模式的重复：

| 模式 | 占比 | Python 实现 |
|---|---|---|
| VLOOKUP 查找（维度、利率情景、现金流模式） | ~40% | `dict` 字典映射 / `pandas.merge` |
| SUMIFS 条件汇总（树形子节点求和） | ~25% | `pandas.groupby` |
| IF/IFERROR 条件分支（锁定判断） | ~15% | 逻辑判断 |
| 期限→摊销矩阵乘法 | ~10% | 矩阵运算 |
| 字典码值查询（NUM/DEN） | ~5% | `dict` 查询 |
| 其他（SUM、PRODUCT、IFERROR 包装） | ~5% | 直接翻译 |

**结论**：170 万公式 ≈ 15-20 个 Python 函数 × 1000 行循环。代码量预计 2000-3000 行 Python。

---

## 二、项目结构

```
almt-backend/calculate_engine/
├── __init__.py
├── core/                       # 核心数据模型与工具
│   ├── __init__.py
│   ├── coa_tree.py             # 账户册树形模型 + DFS 聚合
│   ├── period.py               # 24 期（M1~M24）+ 25 期（M0~M24）数据结构
│   ├── loader.py               # 从 MySQL 加载参数到内存 DataFrame
│   └── saver.py                # 计算结果写回 MySQL
├── engines/                    # 4 个引擎实现
│   ├── __init__.py
│   ├── engine_a_allocate.py    # 业务计划分摊（ENGINE A）
│   ├── engine_b_pricing.py     # 定价策略分摊（ENGINE B）
│   ├── engine_c_cashflow.py    # 现金流计量（ENGINE C）
│   └── engine_d_indicator.py   # 指标计量（ENGINE D）
├── cf_pattern.py               # 现金流模式（12种期限 × 25期 摊销矩阵）
├── indicators.py               # 23组指标公式（利息净收入/净息差/资本充足率等）
├── runner.py                   # 主流程编排（按顺序执行 4 个引擎）
├── validator.py                # 对拍验证（与 Excel 结果对比）
├── tests/                      # 单元测试 + 对拍测试
│   ├── test_coa_tree.py
│   ├── test_engine_a.py
│   ├── test_indicators.py
│   └── fixtures/
│       └── sample_data.json
├── PLAN.md                     # 本文档
└── README.md                   # 使用说明
```

---

## 三、阶段划分（8 周交付）

### 阶段 1：基础架构（第 1 周）

**目标**：搭好骨架，把数据从 MySQL 加载进来，账户册树形结构能正确遍历。

| 任务 | 产出 | 验证 |
|---|---|---|
| 1.1 建表 schema 文档 | `core/schema.sql` | 与 MySQL 实际表结构一致 |
| 1.2 `loader.py`：从 MySQL 加载 8 张表到 DataFrame | `loader.py` | DataFrame 行数 = MySQL 行数 |
| 1.3 `coa_tree.py`：账户册树形模型 | `coa_tree.py` | 测试树深度、节点数 |
| 1.4 `period.py`：24期数据结构 | `period.py` | 测试初始化 |
| 1.5 单元测试框架（pytest） | `tests/` | 跑通测试 |

### 阶段 2：业务分摊 ENGINE A（第 2-3 周）

**目标**：把 `业务计划-规模分摊`（17K 公式）和 `业务计划-日均分摊`（29K 公式）翻译成 Python。

**核心算法**（伪代码）：
```python
def engine_a_allocate(df_business_plan: DataFrame, df_coa_tree: DataFrame) -> DataFrame:
    """
    输入：业务计划 24期增量（plan_balance_1~24, plan_average_1~24）
    输出：每个账户册节点的 24 期分摊后余额/日均
    规则：
      - 状态=锁定：直接取自身值
      - 状态=默认：累加所有子节点的本期增量 - 自身本期增量（避免重复）
    """
    # 1. 给每行加一个"是否锁定"标记（来自 almt_coa_attribute.is_locked）
    # 2. 对每个 M_i，按 coa_cd 分组 SUM
    # 3. 自底向上做树形聚合
    # 4. 锁定节点用锁定值覆盖聚合值
    pass
```

**输入表**：
- `almt_param_business_plan`（24期 plan_balance_i/plan_average_i）
- `almt_coa_info`（树形 parent_coa_cd）
- `almt_coa_attribute`（is_locked 标记）

**输出表**：
- `almt_calculate_intermediate.bp_balance_allocated`（每个账户册的 24 期分摊后余额）
- `almt_calculate_intermediate.bp_average_allocated`（每个账户册的 24 期分摊后日均）

**验证**：
- 抽样 10 个账户册，与原 Excel `业务计划-规模分摊` 的 G/H/I 列对比
- 容差 < 0.01 元

### 阶段 3：定价策略分摊 ENGINE B（第 4 周）

**目标**：把 `账户册收益率曲线变动`（30K 公式）+ `利差不变FTPNII`/`重定价的ΔFTPNII`（各 28K 公式）翻译。

**核心算法**：
```python
def engine_b_pricing(df_strategy: DataFrame, df_rate_scenario: DataFrame,
                     df_bp_balance: DataFrame, df_bp_average: DataFrame) -> DataFrame:
    """
    输入：定价策略 24 期 BP、利率情景 24 期值、业务分摊余额/日均
    输出：每个账户册的 24 期"定价后利率" + "FTP收入"
    """
    # 1. 对每个账户册，根据 curve_id 查到利率情景的 24 期值
    # 2. 累加定价策略 BP：new_rate = curve_value + sum(strategy_bp)
    # 3. FTP = (利差不变 FTP_NII 基础) + 重定价 ΔFTP_NII
    #    利差不变：ftpi = avg_balance_i * curve_value_i
    #    重定价：delta_ftpi = avg_balance_i * strategy_bp_i
    pass
```

**输入表**：
- `almt_param_custom_strategy`（24 期 strategy_m_i）
- `almt_param_rate_scenario`（24 期 M1~M24 利率值）
- 阶段 2 的输出（分摊后余额/日均）
- `almt_coa_attribute`（curve_id 字段）

**输出表**：
- `almt_calculate_intermediate.pricing_result`（24期定价后利率、FTP收入、ΔFTP）

**验证**：与 Excel `账户册收益率曲线变动` / `利差不变FTPNII` 对比。

### 阶段 4：现金流计量 ENGINE C（第 5-6 周）

**目标**：把 `动态现金流`（**279K 公式，最大的一张表**）+ 5 个相关 sheet 翻译。

**核心算法**：
```python
def engine_c_cashflow(df_coa_attribute: DataFrame, df_bp_balance: DataFrame,
                      cf_pattern: dict) -> DataFrame:
    """
    输入：底层账户册 + 业务分摊余额 + 现金流模式表
    输出：每个账户册的 24 期动态现金流（本金+利息）
    """
    # 1. 准备现金流模式矩阵（12种期限 × 25期）：
    #    1D→[1,0,0,...]   6M→[1,1,1,1,1,x,0,...]
    #    1Y→[1,1,...,x,0]  30Y→[1,1,...,1,x]
    cf_pattern = {
        '1D':  [1] + [0]*24,
        '1M':  [1] + [0]*24,
        '3M':  [1,1,1] + [0]*22,
        '6M':  [1,1,1,1,1] + [0]*20,
        '1Y':  [1]*12 + [0]*13,
        '2Y':  [1]*24 + [0],
        '30Y': [1]*25,  # 30Y 期限 > 24 期，全期还本
        # ...
    }
    
    # 2. 对每个底层账户册，根据其原始期限 term 取摊销模式
    # 3. cashflow[i] = balance_i * pattern[i]   # 本金
    # 4. interest[i] = balance_{i-1} * rate    # 利息（基于上期余额）
    # 5. 累加 M0~M24 共 25 期
    pass
```

**简化机会**：`动态现金流`虽然有 279K 公式，但**每个公式都是同一模式**：`IF(VLOOKUP(pattern, period_marker)=1, balance, IF(='x', SUMIFS, 0))`，翻译成 Python 后就是一个**矩阵乘法**（pandas `DataFrame.dot(cf_pattern_matrix)`）。

**输入表**：
- `almt_coa_attribute`（term 字段、curve_id 字段）
- 阶段 2 的输出（业务分摊余额）

**输出表**：
- `almt_calculate_intermediate.cashflow`（每个底层账户册 25 期现金流序列）

**验证**：与 Excel `动态现金流` sheet 对比，**抽样 5% 行**（避免逐行 1000×283=28万 cell 对比太慢）。

### 阶段 5：指标计量 ENGINE D（第 7 周）

**目标**：把 23 组指标（利息净收入、净息差、资本充足率等）翻译成 Python。

**核心算法**：
```python
def engine_d_indicator(df_metrics_caliber: DataFrame, ...all_prev_outputs) -> DataFrame:
    """
    输入：almt_metric_caliber（23组 × 138字段配置）+ 各阶段输出
    输出：23组指标的 24 期值
    """
    # 1. 从字典（NUM001~NUM105 / DEN001~DEN060）查询分子分母项的值
    # 2. 通用公式：indicator = sum(分子项 × 系数 × 取数类型)
    #                     / sum(分母项 × 系数 × 取数类型)
    # 3. 每组指标一个独立函数（interest_nii / nim / lcr / ...）
    pass
```

**取数类型**（共 10 种）：
- NII：利息净收入（来自阶段 3 输出）
- RWA：风险加权资产（来自 almt_param_risk_weight）
- B：余额（来自阶段 2 输出）
- AB：平均余额（来自阶段 2 输出）
- CF1~CF12：现金流第 1~12 期（来自阶段 4 输出）

**输入表**：
- `almt_metric_caliber`（138字段已字典化）
- `almt_dict_value`（NUM/DEN 字典）
- 阶段 2/3/4 的全部输出

**输出表**：
- `almt_calculate_intermediate.indicator_24m`（每账户册 × 23指标 × 24期）

**验证**：与 Excel `基础指标汇总` / `应用&基础指标汇总` 对比。

### 阶段 6：主流程编排 + 对拍验证（第 8 周）

**目标**：把 4 个引擎串起来，提供统一入口；建立完整的对拍测试。

```python
# runner.py 主入口
def run_full_calculate(task_id: str, data_date: str):
    """执行完整 4 引擎计算，返回 (task_id, status, metrics)"""
    
    # 1. 加载参数
    data = load_all_params(data_date)
    
    # 2. ENGINE A
    bp_balance, bp_average = engine_a_allocate(...)
    
    # 3. ENGINE B
    pricing = engine_b_pricing(...bp_balance, bp_average)
    
    # 4. ENGINE C
    cashflow = engine_c_cashflow(...bp_balance)
    
    # 5. ENGINE D
    indicators = engine_d_indicator(...pricing, cashflow)
    
    # 6. 保存到 almt_result_index / almt_result_plan / almt_calculate_intermediate
    save_results(task_id, ...)
```

**集成到新系统**：
- 把 `/api/calculate/start` 改为调用 `runner.run_full_calculate()`
- 前端 `Calculate.tsx` 的 5 个简单步骤改为 8 步骤展示（参数加载 → ENG A → ENG B → ENG C → ENG D → 结果保存 → 对拍验证 → 完成）

---

## 四、关键技术决策

### 决策 1：数据结构

**选项 A**：全部用 pandas DataFrame（推荐）
- 优点：API 丰富、group by 强大、易调试
- 缺点：内存占用略高（774 节点 × 24 期 × 4 引擎约 100MB，可接受）

**选项 B**：用 numpy 数组
- 优点：性能最好
- 缺点：可读性差、调试难

**选项 C**：混合（DataFrame 装载 + numpy 计算）
- 优点：兼顾性能与可读性
- 缺点：复杂度增加

**推荐**：选 A，按需引入 numpy 做矩阵乘法（阶段 4 现金流模式）。

### 决策 2：树形聚合算法

**选项 A**：手写递归 DFS
- 优点：代码直观、易调试
- 缺点：深度大时性能下降

**选项 B**：自底向上用 `networkx.DiGraph`
- 优点：图论算法现成
- 缺点：依赖重

**选项 C**：在 DataFrame 上用 `groupby + transform` 模拟树形聚合
- 优点：性能最好、向量化
- 缺点：需要构造特殊索引

**推荐**：选 C，对于 774 节点规模，自底向上 transform 性能足够。

### 决策 3：精度与容差

**容差标准**：金融场景默认 ±0.01 元（精度到分）。

**浮点处理**：
- 内部计算用 `Decimal` 或 `float64`
- 比较时统一用 `math.isclose(a, b, rel_tol=1e-9, abs_tol=0.01)`
- 利率用 `float64`（精度足够）

### 决策 4：增量 vs 全量重算

**推荐**：全量重算
- 数据量小（774 节点 × 24 期 = 18K cell），全量重算 < 1 秒
- 全量比增量简单，避免状态同步 bug

---

## 五、验证策略（对拍）

每个阶段完成后必须做的对拍测试：

```python
# validator.py
class ExcelComparator:
    """与原 Excel 引擎结果对拍"""
    
    def __init__(self, engine_xlsm_path: str):
        # 用 LibreOffice headless 或 pywin32 加载 engine.xlsm
        # 跑一次 calcuteResult 宏，拿到所有 cell 的"标准答案"
        self.reference = self._load_reference()
    
    def assert_close(self, sheet_name: str, python_df: DataFrame,
                     cell_map: dict, tolerance: float = 0.01):
        """
        cell_map: {(row_key, col_key) -> Excel cell coordinate}
        比较 python_df 的值与 Excel cell 值是否在容差内
        """
        diffs = []
        for (rk, ck), coord in cell_map.items():
            excel_val = self.reference[sheet_name][coord]
            py_val = python_df.loc[rk, ck]
            if abs(excel_val - py_val) > tolerance:
                diffs.append((coord, excel_val, py_val))
        if diffs:
            raise AssertionError(f"{sheet_name}: {len(diffs)} cells differ")
```

**对拍覆盖率目标**：
| 阶段 | 抽样率 | 通过率 |
|---|---|---|
| ENGINE A | 100% 节点 × 100% 期间 = 18K cell | 100% 通过 |
| ENGINE B | 100% 节点 × 100% 期间 = 18K cell | 100% 通过 |
| ENGINE C | 5% 节点 × 100% 期间 = ~3K cell | 99% 通过 |
| ENGINE D | 100% 指标 × 100% 期间 = 5K cell | 100% 通过 |

---

## 六、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| Excel VBA 中有隐藏的 Sub 函数 | 中 | 中 | 抽样所有 VBA Sub 函数，分类：被公式调用/纯交互，被调用的优先翻译 |
| 浮点精度差异（Python vs Excel） | 高 | 低 | 容差放宽到 ±0.01 元；利率用 Decimal |
| 现金流模式表有特殊逻辑（"x" vs 1） | 中 | 中 | 单独测试"x"位置 cell（x 表示该期还清 + 付息） |
| 业务计划"锁定"逻辑有多版本 | 低 | 中 | 与产品经理确认锁定规则；用单测覆盖 0/1/混合三种 |
| 阶段 4 现金流 279K 公式对拍太慢 | 中 | 低 | 抽样 5%（约 14K cell）；剩余用统计指标对比 |

---

## 七、时间估算

| 阶段 | 工时 | 累计 |
|---|---|---|
| 阶段 1：基础架构 | 1 周 | 1 周 |
| 阶段 2：ENGINE A 业务分摊 | 2 周 | 3 周 |
| 阶段 3：ENGINE B 定价策略 | 1 周 | 4 周 |
| 阶段 4：ENGINE C 现金流计量 | 2 周 | 6 周 |
| 阶段 5：ENGINE D 指标计量 | 1 周 | 7 周 |
| 阶段 6：主流程 + 对拍 | 1 周 | 8 周 |
| **合计** | **8 周** | |

**前提**：
- 1 名有经验的 Python 工程师
- 数据库 schema 已稳定（已稳定）
- 原 Excel 引擎可运行（可借 LibreOffice 跑出标准答案）

---

## 八、下一步行动

请确认这个方案，我将从**阶段 1（基础架构）**开始动手：
1. 创建 `almt-backend/calculate_engine/` 目录结构
2. 实现 `loader.py` 从 MySQL 加载数据
3. 实现 `coa_tree.py` 账户册树形模型
4. 写 5-10 个单元测试

如果你想调整优先级，可以告诉我（比如先把阶段 2 的 ENGINE A 做出来，因为它是其他 3 个引擎的输入基础）。
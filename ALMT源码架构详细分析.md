# ALMT 源码架构详细分析报告

## 一、项目结构概览

```
资产负债模拟分析工具/
├── ALMT/                          # 主应用程序
│   ├── Calculate/                  # 计算执行模块
│   │   ├── ExecuteProcessPage.cs      # 计算执行主页面
│   │   ├── ResultIndexPage.cs         # 指标结果查看
│   │   ├── ResultPlanPage.cs          # 计划结果查看
│   │   └── SystemLogPage.cs           # 系统日志查看
│   ├── Controls/                   # 业务控制层（页面）
│   │   ├── BaseParameterPage.cs        # 基础参数配置
│   │   ├── COAPage.cs                 # 账户册管理
│   │   ├── COAAttributePage.cs       # 账户册属性
│   │   ├── COATexPage.cs             # 税率假设
│   │   ├── ReportRulePage.cs          # 报表规则/指标口径
│   │   ├── EditCurrentDataPage.cs     # 存量数据编辑
│   │   ├── EditRateScenarioPage.cs    # 利率情景假设
│   │   ├── EditCustomStretagyPage.cs  # 对客定价策略
│   │   ├── EditRiskWeightPage.cs      # 风险权重
│   │   ├── EditFTPMarginPage.cs       # FTP利差假设
│   │   └── EditBusinessPlanPage.cs    # 业务计划编辑
│   ├── Database/                    # 数据访问层
│   │   ├── entity/                  # 实体类（ORM映射）
│   │   │   ├── coa_info.cs             # 账户册信息
│   │   │   ├── coa_attribute.cs        # 账户册属性
│   │   │   ├── coa_tex_info.cs        # 税率信息
│   │   │   ├── current_position.cs      # 当前持仓/存量
│   │   │   ├── curve_define.cs         # 曲线定义
│   │   │   ├── param_buckets.cs        # 业务桶参数
│   │   │   ├── param_business_plan.cs  # 业务计划
│   │   │   ├── param_custom_stretagy.cs # 对客定价策略
│   │   │   ├── param_ftp_margin.cs     # FTP利差
│   │   │   ├── param_rate_scenario.cs   # 利率情景
│   │   │   ├── param_risk_weight.cs    # 风险权重
│   │   │   ├── report_rule_info.cs      # 报表规则
│   │   │   ├── result_index.cs         # 指标结果
│   │   │   ├── result_plan.cs          # 计划结果
│   │   │   ├── system_config.cs        # 系统配置
│   │   │   └── ALMTLog.cs              # 系统日志
│   │   ├── SugarDao.cs                 # 数据库连接管理
│   │   ├── ExcelHelper.cs             # Excel导入导出
│   │   ├── ExcelHelper2.cs            # Excel辅助工具
│   │   ├── DataTableToExcel.cs        # 数据表转Excel
│   │   ├── DataGridTools.cs           # DataGrid工具
│   │   ├── FileHelper.cs              # 文件操作
│   │   ├── IniHelper.cs               # INI配置
│   │   └── LogHelper.cs               # 日志辅助
│   ├── Tools/                       # 工具类
│   │   ├── ConvertObject.cs           # 对象转换
│   │   ├── ExcelMacroHelper.cs       # Excel宏执行
│   │   ├── LicenseTools.cs           # 授权工具
│   │   ├── MicrosoftExcel.cs         # Excel COM操作
│   │   ├── SM4.cs                    # SM4加密算法
│   │   ├── SM4Utils.cs               # SM4工具
│   │   ├── SM4_Context.cs            # SM4上下文
│   │   └── StreamTools.cs            # 流操作
│   ├── UI/                          # 界面组件
│   │   ├── AddLicense.cs             # 添加授权
│   │   ├── FormatUI.cs               # 格式化UI
│   │   ├── FrmSplash.cs             # 启动画面
│   │   ├── Splasher.cs              # 启动器
│   │   ├── VpRiskStyle.cs           # 风控样式
│   │   └── test.cs                  # 测试
│   ├── Properties/                  # 程序集属性
│   ├── ALMT.csproj                 # 项目文件
│   ├── App.config                  # 配置文件
│   ├── MainForm.cs                  # 主窗体
│   └── Program.cs                   # 入口程序
├── ALMTLicenseTools/               # 授权工具项目
└── packages/                       # NuGet包
```

---

## 二、技术架构详解

### 2.1 技术栈

| 层级 | 技术选型 | 版本 |
|------|----------|------|
| **框架** | .NET Framework | 4.5.2 |
| **UI框架** | SunnyUI | 3.0.2 |
| **ORM** | SqlSugar | 5.0.2.6 |
| **数据库** | SQLite | System.Data.SQLite |
| **Excel处理** | NPOI | 2.5.2 |
| **日志** | log4net | 2.0.12 |
| **加密** | BouncyCastle | 1.8.6 |
| **压缩** | DotNetZip | 1.15.0 |

### 2.2 架构分层

```
┌─────────────────────────────────────────────────────────┐
│                    表现层 (UI Layer)                    │
│     SunnyUI 窗体 + 各个功能页面 (Controls/)             │
├─────────────────────────────────────────────────────────┤
│                    业务逻辑层 (BLL)                    │
│     ExecuteProcessPage (计算引擎调度)                   │
│     各EditPage (参数编辑业务逻辑)                        │
├─────────────────────────────────────────────────────────┤
│                    数据访问层 (DAL)                    │
│     SugarDao (SqlSugar ORM) + ExcelHelper              │
├─────────────────────────────────────────────────────────┤
│                    实体模型层 (Entity)                 │
│     Database/entity/*.cs (数据实体类)                  │
├─────────────────────────────────────────────────────────┤
│                    工具层 (Tools)                      │
│     Excel宏 / 加密 / 授权 / 流操作                     │
└─────────────────────────────────────────────────────────┘
```

---

## 三、核心计算流程

### 3.1 计算引擎工作流

核心计算流程在 `ExecuteProcessPage.cs` 中实现：

```
┌──────────────────────────────────────────────────────────────────┐
│                        计算流程总览                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │ 1.加载参数  │ -> │ 2.加载存量  │ -> │ 3.加载配置  │          │
│  │   数据      │    │    数据     │    │    数据     │          │
│  └─────────────┘    └─────────────┘    └─────────────┘          │
│        │                  │                  │                      │
│        └──────────────────┼──────────────────┘                      │
│                           ▼                                        │
│                    ┌─────────────┐                                  │
│                    │ 4.执行计算  │                                  │
│                    │ Excel宏计算 │                                  │
│                    └─────────────┘                                  │
│                           │                                        │
│                           ▼                                        │
│                    ┌─────────────┐                                  │
│                    │ 5.提取结果  │                                  │
│                    │ 到数据库    │                                  │
│                    └─────────────┘                                  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Excel宏计算引擎

ALMT的核心计算逻辑实际上是通过**Excel宏**实现的：

```csharp
// ExecuteProcessPage.cs - CalcutingExcel 方法
private void CalcutingExcel(CancellationToken ct)
{
    ExcelMacroHelper macroHelper = new ExcelMacroHelper();
    object objRtn = new object();
    string fileName = sysPath + @"\ALMTCalculateEngine.dat";
    // 调用Excel宏: calcuteResult
    macroHelper.RunExcelMacro(fileName, "calcuteResult", new Object[]{}, out objRtn, false);
}
```

**计算流程说明：**

1. **参数数据加载** (`LoadParamDataFromDB`):
   - 从数据库读取账户册层级、属性、税率、报表口径等
   - 写入 `ALMTCalculate.dat` Excel模板

2. **存量数据加载** (`LoadCurrentDataFromDB`):
   - 从数据库读取当前持仓数据
   - 写入Excel "存量数据表" sheet

3. **配置数据加载** (`LoadConfigDataFromDB`):
   - 读取利率情景、对客定价策略、风险权重、FTP利差、业务计划等
   - 写入对应sheet页

4. **执行Excel计算** (`CalcutingExcel`):
   - 调用 `ALMTCalculateEngine.dat` 中的VBA宏 `calcuteResult`
   - 核心计算逻辑在Excel中实现

5. **结果提取** (`GetResultFromExcel`):
   - 读取 "指标看板" 和 "策略看板" sheet
   - 解析并保存到 `result_index` 和 `result_plan` 表

---

## 四、核心实体模型

### 4.1 账户册体系

| 实体类 | 表名 | 说明 |
|--------|------|------|
| `coa_info` | coa_info | 账户册层级结构 |
| `coa_attribute` | coa_attribute | 账户册属性（重定价、收益率曲线等）|
| `coa_tex_info` | coa_tex_info | 税率假设 |

### 4.2 业务参数

| 实体类 | 表名 | 说明 |
|--------|------|------|
| `param_rate_scenario` | param_rate_scenario | 利率情景假设（24个月）|
| `param_custom_stretagy` | param_custom_stretagy | 对客定价策略 |
| `param_risk_weight` | param_risk_weight | 风险权重 |
| `param_ftp_margin` | param_ftp_margin | FTP利差假设 |
| `param_business_plan` | param_business_plan | 业务计划（余额/日均）|
| `param_buckets` | param_buckets | 业务存续期/时间桶 |

### 4.3 数据存储

| 实体类 | 表名 | 说明 |
|--------|------|------|
| `current_position` | current_position | 存量数据（余额、日均、利率）|
| `result_index` | result_index | 指标计算结果 |
| `result_plan` | result_plan | 计划执行结果 |
| `report_rule_info` | report_rule_info | 报表规则/指标口径 |
| `system_config` | system_config | 系统配置 |
| `ALMTLog` | Log | 系统运行日志 |

---

## 五、界面模块导航

基于 `MainForm.cs` 的页面注册：

```
资产负债管理系统
│
├── A. 基础参数配置
│   ├── BaseParameterPage (基础参数)
│   ├── COAPage (账户册管理)
│   ├── COAAttributePage (账户册属性)
│   ├── COATexPage (税率假设)
│   └── ReportRulePage (报表规则/指标口径)
│
├── B. 存量数据管理
│   └── EditCurrentDataPage (存量数据编辑)
│
├── C. 业务参数配置
│   ├── EditRateScenarioPage (利率情景假设)
│   ├── EditCustomStretagyPage (对客定价策略)
│   ├── EditRiskWeightPage (风险权重)
│   ├── EditFTPMarginPage (FTP利差假设)
│   └── EditBusinessPlanPage (业务计划)
│
├── D. 计算执行
│   ├── ExecuteProcessPage (执行计算)
│   └── SystemLogPage (系统日志)
│
└── E. 结果查看
    ├── ResultIndexPage (指标看板)
    └── ResultPlanPage (策略看板)
```

---

## 六、关键技术实现

### 6.1 数据库连接 (SugarDao.cs)

```csharp
public static SqlSugarClient GetInstance()
{
    string workDir = Directory.GetCurrentDirectory();
    string dbdir = workDir + @"\ALMT.db";

    SqlSugarClient db = new SqlSugarClient(new ConnectionConfig()
    {
        ConnectionString = @"DataSource=" + dbdir,
        DbType = DbType.Sqlite,
        IsAutoCloseConnection = true,
        InitKeyType = InitKeyType.Attribute
    });

    // SQL日志输出
    db.Aop.OnLogExecuting = (sql, pars) => { ... };
    return db;
}
```

### 6.2 Excel数据导出

```csharp
// 使用NPOI导出DataTable到Excel
DataTable COATable = db.Queryable<coa_info>().ToDataTable();
ExcelHelper.ExportDataToWorkbook(COATable, sheetCOA, cellStyle);
```

### 6.3 Excel宏调用

```csharp
// 使用COM调用Excel VBA宏
ExcelMacroHelper macroHelper = new ExcelMacroHelper();
macroHelper.RunExcelMacro(fileName, "calcuteResult", new Object[]{}, out objRtn, false);
```

### 6.4 授权验证

```csharp
// SM4加密验证
DateTime date = Convert.ToDateTime("2022-01-01");
string lic = "mantiandoushixiaoxingxing" + date;
var a = LicenseTools.LicenseStatus(lic);
```

---

## 七、关键文件说明

| 文件 | 作用 |
|------|------|
| `ALMT.csproj` | 项目文件，定义依赖和编译选项 |
| `ALMTCalculate.dat` | 计算模板Excel（含数据sheet）|
| `ALMTCalculateEngine.dat` | 计算引擎Excel（含VBA宏）|
| `ALMT.db` | SQLite本地数据库 |
| `ALMT.exe.config` | 应用程序配置 |

---

## 八、总结

ALMT是一个典型的**混合计算架构**桌面应用：

- **C#负责UI和流程控制**：使用SunnyUI构建界面，管理数据流转
- **Excel负责核心计算**：复杂的ALM计算逻辑通过VBA宏实现
- **SQLite负责数据存储**：轻量级本地数据库

这种架构的优势：
1. 降低开发复杂度 - 复杂计算逻辑借助Excel
2. 便于业务人员理解 - 公式可在Excel中调试
3. 部署简单 - 单文件+数据库即可运行

---

*报告生成时间：2026年8月*
*基于源码目录：`C:\中电金信\产品资料\ALMT\资债效率工具\源码\资产负债模拟分析工具`*

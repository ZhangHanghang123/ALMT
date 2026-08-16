# 经营计划模拟系统（ALMT）

> ALMT（Asset Liability Management Tool）的 Python 重写版。
> 完整覆盖原 Excel/VBA 系统的 4 个计算引擎：业务分摊、定价策略、现金流、指标。

---

## 一、项目位置

**新工作空间目录**：`C:\银行经营\ALMT\`

原工作空间目录 `C:\中电金信\产品资料\ALMT\` 已停止更新，仅作为历史参考。

---

## 二、目录结构

```
C:\银行经营\ALMT\
├── almt-backend/             # Python 后端（FastAPI + MySQL）
│   ├── almt_app/            # 应用层（API + 模型 + 服务）
│   ├── calculate_engine/    # 4 个计算引擎 + saver + runner
│   ├── docs/                # MEASUREMENT_MANUAL.md 等
│   ├── reports/             # 对账报告（自动生成）
│   ├── *.py                 # 各种工具脚本（init_db / import_ / migrate_）
│   └── requirements.txt
│
├── almt-frontend/            # React 前端（Vite + Ant Design）
│   ├── src/pages/           # 21 个页面（数据/计算/指标/结果）
│   ├── src/components/      # 共享组件（VersionSelector 等）
│   ├── package.json
│   └── vite.config.ts
│
├── docs/                     # 项目文档
│   └── compare_with_original.md   # 新旧系统对比报告
│
├── 技术架构说明.md            # 整体技术架构
├── 项目重构-技术架构与产品功能架构.md
├── ALMT产品分析报告.md
├── ALMT源码架构详细分析.md
├── ALMT重构可行性分析.md
├── Python调用Excel重构流程.md
└── 报表口径.xlsx              # 业务报表口径定义
```

---

## 三、开发指南

### 3.1 启动后端

```bash
cd "C:\银行经营\ALMT\almt-backend"

# 第一次：创建虚拟环境
"C:\Users\zhanghh\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m venv venv
venv\Scripts\python -m pip install -r requirements.txt

# 启动服务
"C:\Users\zhanghh\.workbuddy\binaries\python\versions\3.13.12\python.exe" -m uvicorn almt_app.main:app --host 0.0.0.0 --port 8001 --reload
```

后端地址：http://localhost:8001
API 文档：http://localhost:8001/docs

### 3.2 启动前端

```bash
cd "C:\银行经营\ALMT\almt-frontend"

# 第一次：安装依赖
"C:\Users\zhanghh\.workbuddy\binaries\node\versions\22.22.2\npm.cmd" install

# 启动开发服务器
"C:\Users\zhanghh\.workbuddy\binaries\node\versions\22.22.2\npm.cmd" run dev
```

前端地址：http://localhost:5174

### 3.3 数据库

- **MySQL**：localhost:3306，库名 `almt_db`，账号 `almt/almt`
- **SQLite 演示库**：`C:\中电金信\产品资料\ALMT\ALMT\ALMT.db`（原 VBA 系统导出，用于导入数据）

---

## 四、迁移记录

| 日期 | 操作 | 说明 |
|---|---|---|
| 2026-08-16 | 从 `C:\中电金信\产品资料\ALMT` 迁移到 `C:\银行经营\ALMT` | 完整复制源代码、文档、配置 |

### 迁移内容

- ✅ 7 个根目录文档（技术架构、分析报告、报表口径等）
- ✅ docs/ 目录（含 compare_with_original.md）
- ✅ almt-backend/ 完整源代码（70 个文件，过滤缓存）
- ✅ almt-frontend/ 源代码 + 配置（37 个文件，不含 node_modules）

### 未迁移内容

- ❌ `ALMT/` 原始 Excel 数据（100MB，仅作历史参考，保留在原位置）
- ❌ `ALMT.zip` 压缩包
- ❌ `资债效率工具/` C# 历史代码（用户确认不需要）
- ❌ `almt_app/`（与 almt-backend/almt_app 重复）
- ❌ `node_modules/` 依赖包（在新位置运行 `npm install` 重新安装）
- ❌ `__pycache__/` Python 缓存
- ❌ `.workbuddy/memory/` 用户私人记忆

---

## 五、注意事项

1. **Vite dev 自动 HMR**：修改前端代码会自动热更新
2. **后端无 --reload**：修改后端代码需要手动重启 uvicorn
3. **数据库独立**：MySQL 数据库在 localhost，不随项目移动
4. **路径引用**：脚本里所有引用 `C:\中电金信\产品资料\ALMT` 的硬编码路径需要更新为 `C:\银行经营\ALMT`
5. **Python 版本**：使用 Python 3.13.12（managed 版本），路径见上方

---

## 六、核心文档清单

| 文档 | 路径 | 内容 |
|---|---|---|
| 计量手册 | `almt-backend/calculate_engine/MEASUREMENT_MANUAL.md` | 8 章：架构/4 个引擎/saver/runner/版本管理/对账报告 |
| 项目 README | `almt-frontend/README.md` | 前端开发指南 |
| 新旧系统对比 | `docs/compare_with_original.md` | 模块清单/算法/数据一致性 |
| 架构说明 | `技术架构说明.md` | 整体技术架构图 |
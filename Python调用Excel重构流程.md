# Python调用Excel模型重构流程

## 一、现有调用方式分析

### C# 原有实现
```csharp
// 使用 COM 调用 Excel VBA 宏
Application oExcel = new Application();
Excel._Workbook oBook = oBooks.Open(excelFilePath);
// 调用宏: calcuteResult
rtnValue = this.RunMacro(oExcel, paraObjects);
oBook.Save();
oBook.Close();
```

### Python 可选方案

| 方案 | 优点 | 缺点 | 推荐场景 |
|------|------|------|----------|
| **xlwings** | 与Excel深度集成，支持VBA调用 | 需要安装Excel | ✅ 推荐 |
| **pywin32** | 功能最全，可完全替代COM | 代码复杂 | 不推荐 |
| **openpyxl + formulas** | 纯Python，无需Excel | 部分公式不支持 | 长期目标 |
| **Excel REST API** | 跨平台 | 需要Excel Server | 企业部署 |

---

## 二、重构流程设计

### 阶段一：环境准备（1周）

#### 1.1 技术选型确认

```
推荐技术栈：
├── Python 3.11
├── xlwings (调用Excel VBA)
├── openpyxl (读写Excel)
├── pandas (数据处理)
└── FastAPI (后端框架)
```

#### 1.2 服务架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         后端服务                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │  FastAPI    │───▶│  计算服务    │───▶│  Excel引擎  │       │
│  │  Web服务    │    │  (Celery)   │    │  (xlwings) │       │
│  └─────────────┘    └─────────────┘    └─────────────┘       │
│         │                                        │              │
│         ▼                                        ▼              │
│  ┌─────────────┐                       ┌─────────────┐       │
│  │  MySQL/     │                       │  Excel模型  │       │
│  │  Redis      │                       │  (VBA宏)    │       │
│  └─────────────┘                       └─────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 阶段二：Excel引擎封装（2周）

#### 2.1 创建Excel调用基础类

```python
# excel_engine.py
import xlwings as xw
from pathlib import Path
from typing import Any, Optional
import logging

class ExcelEngine:
    """Excel计算引擎封装"""

    def __init__(self, template_path: str):
        self.template_path = Path(template_path)
        self.app = None
        self.book = None

    def open(self, visible: bool = False):
        """打开Excel工作簿"""
        self.app = xw.App(visible=visible, add_book=False)
        self.book = self.app.books.open(str(self.template_path))

    def run_macro(self, macro_name: str, *args) -> Any:
        """执行VBA宏"""
        return self.book.macro(macro_name)(*args)

    def save_as(self, output_path: str):
        """另存为"""
        self.book.save(str(output_path))

    def close(self):
        """关闭工作簿和Excel"""
        if self.book:
            self.book.close()
        if self.app:
            self.app.quit()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

#### 2.2 创建ALMT计算封装

```python
# almt_calculator.py
from excel_engine import ExcelEngine
from pathlib import Path
import logging

class ALMTCalculator:
    """ALMT计算器"""

    def __init__(self, model_path: str, data_dir: str):
        self.model_path = model_path
        self.data_dir = Path(data_dir)
        self.logger = logging.getLogger(__name__)

    def calculate(self, data_date: str) -> dict:
        """执行完整计算流程"""

        # 1. 准备输出路径
        output_file = self.data_dir / "ALMTCalculate.dat"

        # 2. 调用计算引擎
        with ExcelEngine(self.model_path) as engine:
            # 调用VBA宏
            result = engine.run_macro("calcuteResult")

            # 保存结果
            engine.save_as(str(output_file))

        # 3. 返回结果
        return {
            "status": "success",
            "output_file": str(output_file),
            "result": result
        }

    def load_param_to_excel(self, db_data: dict) -> str:
        """将参数数据加载到Excel"""
        output_file = self.data_dir / "ALMTCalculate.dat"

        with ExcelEngine(self.model_path) as engine:
            # 获取Sheet
            sheet_coa = engine.book.sheets["账户册层级"]

            # 写入数据
            sheet_coa.range("A2").value = db_data["coa_info"]

            engine.save_as(str(output_file))

        return str(output_file)

    def extract_result(self, result_file: str) -> dict:
        """从结果Excel提取数据"""
        with ExcelEngine(result_file) as engine:
            # 读取指标看板
            sheet_index = engine.book.sheets["指标看板"]
            index_data = sheet_index.used_range.value

            # 读取策略看板
            sheet_plan = engine.book.sheets["策略看板"]
            plan_data = sheet_plan.used_range.value

        return {
            "index_data": index_data,
            "plan_data": plan_data
        }
```

### 阶段三：计算服务集成（2周）

#### 3.1 创建Celery任务

```python
# tasks/calculate_tasks.py
from celery import Celery
from almt_calculator import ALMTCalculator
import logging

app = Celery('almt')

@app.task(bind=True)
def calculate_task(self, data_date: str, param_ids: list):
    """ALMT计算异步任务"""

    try:
        # 更新进度
        self.update_state(state='PROGRESS', meta={'step': 'loading_param'})

        # 1. 加载参数到Excel
        calculator = ALMTCalculator(
            model_path="models/ALMTCalculateEngine.xlsm",
            data_dir="data/temp"
        )

        # 获取参数
        param_data = fetch_params_from_db(param_ids)
        calculator.load_param_to_excel(param_data)

        self.update_state(state='PROGRESS', meta={'step': 'calculating'})

        # 2. 执行计算
        result = calculator.calculate(data_date)

        self.update_state(state='PROGRESS', meta={'step': 'extracting'})

        # 3. 提取结果
        result_data = calculator.extract_result(result["output_file"])

        # 4. 保存到数据库
        save_results_to_db(result_data)

        return {
            "status": "success",
            "result": result_data
        }

    except Exception as e:
        logging.error(f"计算失败: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
```

#### 3.2 FastAPI集成

```python
# routers/calculate.py
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from tasks.calculate_tasks import calculate_task

router = APIRouter()

class CalculateRequest(BaseModel):
    data_date: str
    param_ids: list

@router.post("/calculate")
async def start_calculate(
    request: CalculateRequest,
    background_tasks: BackgroundTasks
):
    """启动计算任务"""
    task = calculate_task.delay(request.data_date, request.param_ids)

    return {
        "task_id": task.id,
        "status": "started"
    }

@router.get("/calculate/{task_id}")
async def get_calculate_result(task_id: str):
    """获取计算结果"""
    from tasks.calculate_tasks import app

    task = app.AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {"status": "pending"}
    elif task.state == 'PROGRESS':
        response = {
            "status": "processing",
            "step": task.info.get("step", "unknown")
        }
    elif task.state == 'SUCCESS':
        response = {
            "status": "success",
            "result": task.result
        }
    else:
        response = {
            "status": "error",
            "message": str(task.info)
        }

    return response
```

### 阶段四：数据流转改造（2周）

#### 4.1 数据流转设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                          新版数据流转                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  数据库(MySQL)                                                      │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       │
│  │ 参数API  │───▶│ Python  │───▶│ Excel   │───▶│ 提取    │       │
│  │ 写入    │    │ 计算服务 │    │ VBA宏   │    │ 结果   │       │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘       │
│       │                                              │              │
│       │                                              ▼              │
│       │                                      ┌─────────────┐       │
│       └─────────────────────────────────────▶│  结果API    │       │
│                                              │ 返回前端    │       │
│                                              └─────────────┘       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2 批量数据写入优化

```python
# services/excel_writer.py
import xlwings as xw
import pandas as pd

class ExcelDataWriter:
    """Excel数据批量写入"""

    def __init__(self, workbook_path: str):
        self.workbook_path = workbook_path

    def write_dataframe(self, sheet_name: str, df: pd.DataFrame, start_cell: str = "A2"):
        """使用pandas快速写入DataFrame"""
        with xw.Book(self.workbook_path) as book:
            sheet = book.sheets[sheet_name]
            sheet.range(start_cell).value = df.values

            # 写入表头
            if start_cell == "A2":
                sheet.range("A1").value = [df.columns]

    def batch_write_params(self, coa_data, attr_data, rate_data):
        """批量写入参数"""
        with xw.Book(self.workbook_path) as book:
            # 账户册层级
            book.sheets["账户册层级"].range("A2").value = coa_data

            # 账户册属性
            book.sheets["底层账户册及属性配置"].range("A2").value = attr_data

            # 利率情景
            book.sheets["利率情景假设"].range("A2").value = rate_data

            book.save()
```

### 阶段五：部署与运维（1周）

#### 5.1 Windows服务器部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Windows Excel服务 (需在Windows宿主运行)
  excel-engine:
    image: windows/servercore:ltsc2022
    volumes:
      - ./models:/models
      - ./data:/data
    command: python excel_engine_service.py

  # FastAPI服务
  api:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - excel-engine
      - redis
    environment:
      - REDIS_URL=redis://redis:6379

  # Celery Worker
  worker:
    build: ./backend
    command: celery -A tasks worker --loglevel=info
    depends_on:
      - redis
      - excel-engine

  redis:
    image: redis:7-alpine
```

#### 5.2 Excel服务独立部署

```python
# excel_engine_service.py
# 独立Excel计算服务 (使用Flask + xlwings)
from flask import Flask, request, jsonify
import xlwings as xw
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/run_macro', methods=['POST'])
def run_macro():
    data = request.json
    macro_name = data.get('macro_name')
    workbook_path = data.get('workbook_path')

    try:
        # 打开Excel执行宏
        with xw.App(visible=False, add_book=False) as app:
            book = app.books.open(workbook_path)
            result = book.macro(macro_name)()
            book.save()
            book.close()

        return jsonify({"status": "success", "result": result})

    except Exception as e:
        logging.error(f"宏执行失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

## 三、迁移检查清单

### 环境检查
- [ ] Windows Server（xlwings需要Windows）
- [ ] 安装Microsoft Excel
- [ ] Python 3.11+
- [ ] xlwings已安装

### 代码检查
- [ ] Excel模型文件（.xlsm）可访问
- [ ] VBA宏名称已记录
- [ ] 参数表与Sheet对应关系已整理

### 功能检查
- [ ] 参数写入正确
- [ ] 宏执行成功
- [ ] 结果提取正确
- [ ] 错误处理完善

---

## 四、预期效果

| 指标 | 旧架构 | 新架构 |
|------|--------|--------|
| 并发能力 | 单用户 | 多用户 |
| 响应方式 | 同步阻塞 | 异步+进度推送 |
| 部署方式 | 桌面安装 | Web服务 |
| 维护性 | 困难 | 易于维护 |

---

*文档版本: V1.0*
*生成时间: 2026年8月*

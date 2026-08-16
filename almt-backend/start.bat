@echo off
REM ALMT Backend 启动脚本

echo ========================================
echo ALMT Backend 启动中...
echo ========================================

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.11+
    pause
    exit /b 1
)

REM 创建虚拟环境(如果不存在)
if not exist "venv" (
    echo [1/4] 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖
echo [2/4] 安装依赖...
pip install -r requirements.txt

REM 创建数据目录
if not exist "data" mkdir data
if not exist "models" mkdir models
if not exist "logs" mkdir logs

REM 启动应用
echo [3/4] 启动应用...
python -m uvicorn almt_app.main:app --host 0.0.0.0 --port 8001 --reload

pause

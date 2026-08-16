"""
计算执行 API（接入 Python 引擎版本 + 版本管理）

改造点（2026-08-16）：
  - run_calculate 改为调用 calculate_engine.runner.run_full_calculate
  - 自动分配 calc_version（YYYYMMDD-XXXX）
  - 新增 4 个版本管理接口：
      POST   /api/calculate/versions            创建空版本
      GET    /api/calculate/versions            列出所有版本
      DELETE /api/calculate/versions/{version}  删除整个版本
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import pymysql
import uuid

router = APIRouter(prefix="/api/calculate", tags=["计算执行"])


def get_db_conn():
    return pymysql.connect(
        host='localhost', user='almt', password='almt',
        database='almt_db', port=3306, cursorclass=pymysql.cursors.DictCursor
    )


# ============================================================
# 基础请求模型
# ============================================================

class CalculateRequest(BaseModel):
    """计算请求"""
    data_date: str


class CreateVersionRequest(BaseModel):
    """创建空版本请求"""
    data_date: str
    remark: Optional[str] = None


# ============================================================
# 内部辅助
# ============================================================

def _update_progress(conn, task_id: str, progress: int, status: str = None, error: str = None):
    """更新任务进度"""
    with conn.cursor() as cursor:
        sets = ['progress = %s']
        params = [progress]
        if status:
            sets.append('status = %s')
            params.append(status)
        if error is not None:
            sets.append('error_message = %s')
            params.append(error[:500])
        if progress >= 100 or status in ('success', 'failed'):
            sets.append('completed_at = NOW()')
        params.append(task_id)
        cursor.execute(
            f"UPDATE almt_calculate_task SET {', '.join(sets)} WHERE task_id = %s",
            tuple(params)
        )
    conn.commit()


# ============================================================
# 计算执行
# ============================================================

@router.post("/start")
def start_calculate(request: CalculateRequest):
    """启动计算任务（调用 4 引擎 Python 实现，自动分配 calc_version）"""
    task_id = str(uuid.uuid4())
    data_date = request.data_date

    # 延迟导入避免循环
    from almt_app.services.calc_version_service import get_next_version

    calc_version = get_next_version(data_date)

    conn = get_db_conn()
    try:
        # 1. 创建任务记录（含 calc_version）
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO almt_calculate_task
                (task_id, calc_version, data_date, status, progress, started_at, created_by)
                VALUES (%s, %s, %s, 'running', 0, NOW(), 1)""",
                (task_id, calc_version, data_date)
            )
        conn.commit()

        # 2. 调用 4 引擎计算
        run_calculate(task_id, data_date, conn)

        # 3. 查最终状态
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT status, progress, calc_version FROM almt_calculate_task WHERE task_id = %s",
                (task_id,)
            )
            row = cursor.fetchone()

        return {
            "task_id": task_id,
            "calc_version": row['calc_version'] if row else calc_version,
            "status": row['status'] if row else 'unknown',
            "progress": row['progress'] if row else 0,
            "message": "计算完成" if (row and row['status'] == 'success') else "计算失败"
        }
    except Exception as e:
        _update_progress(conn, task_id, 0, status='failed', error=str(e))
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")
    finally:
        conn.close()


def run_calculate(task_id: str, data_date: str, conn):
    """调度 4 引擎计算"""
    def _progress(p: int, msg: str):
        if p < 0:
            _update_progress(conn, task_id, 0, status='failed', error=msg)
        else:
            _update_progress(conn, task_id, p)

    from calculate_engine.runner import run_full_calculate

    result = run_full_calculate(
        task_id=task_id,
        data_date=data_date,
        progress_callback=_progress
    )

    if result.error:
        raise RuntimeError(result.error)

    _update_progress(conn, task_id, 100, status='success')

    # 写摘要
    import json
    summary = json.dumps(result.summary(), ensure_ascii=False, default=str)
    if len(summary) > 500:
        summary = summary[:497] + '...'
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE almt_calculate_task SET error_message = %s WHERE task_id = %s",
            (summary, task_id)
        )
    conn.commit()

    return result


# ============================================================
# 任务查询（兼容旧 API）
# ============================================================

@router.get("/task/{task_id}")
def get_task_status(task_id: str):
    """获取任务状态"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM almt_calculate_task WHERE task_id=%s",
                (task_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="任务不存在")
            for k, v in row.items():
                if isinstance(v, datetime):
                    row[k] = v.isoformat()
            return row
    finally:
        conn.close()


@router.get("/tasks")
def get_task_list(skip: int = 0, limit: int = 20):
    """获取任务列表"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM almt_calculate_task
                ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                (limit, skip)
            )
            rows = cursor.fetchall()
            for row in rows:
                for k, v in row.items():
                    if isinstance(v, datetime):
                        row[k] = v.isoformat()
            return rows
    finally:
        conn.close()


# ============================================================
# 版本管理（新功能 2026-08-16）
# ============================================================

@router.post("/versions")
def create_version(request: CreateVersionRequest):
    """
    创建空版本（不执行计算）。

    用于业务场景：先占位版本号，后续手动导入数据或调整参数。
    """
    from almt_app.services.calc_version_service import create_empty_version
    try:
        task_id, calc_version = create_empty_version(request.data_date, request.remark)
        return {
            "task_id": task_id,
            "calc_version": calc_version,
            "data_date": request.data_date,
            "status": "empty",
            "progress": 100,
            "message": "空版本已创建（未执行计算）"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建版本失败: {str(e)}")


@router.get("/versions")
def list_versions(limit: int = Query(50, ge=1, le=200), include_empty: bool = False):
    """
    获取计算版本列表（按版本号倒序）。

    Args:
        limit: 返回条数（1-200）
        include_empty: 是否包含"空版本"（仅 status='success' 时不返回空版本）
    """
    from almt_app.services.calc_version_service import list_versions as _list
    return _list(limit=limit, only_with_data=not include_empty)


@router.delete("/versions/{calc_version}")
def delete_version(calc_version: str):
    """
    删除整个计算版本（含所有结果数据：almt_result_index, almt_result_plan）。

    ⚠️ 危险操作：不可恢复！
    """
    from almt_app.services.calc_version_service import delete_version as _del
    result = _del(calc_version)
    if result['deleted_task'] == 0:
        raise HTTPException(status_code=404, detail=f"版本不存在: {calc_version}")
    return {
        "success": True,
        "message": f"版本 {calc_version} 已删除",
        **result
    }


@router.get("/versions/{calc_version}")
def get_version_detail(calc_version: str):
    """获取单个版本的详细信息"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT t.*,
                       (SELECT COUNT(*) FROM almt_result_index WHERE task_id=t.task_id) AS index_count,
                       (SELECT COUNT(*) FROM almt_result_plan WHERE task_id=t.task_id) AS plan_count
                FROM almt_calculate_task t
                WHERE t.calc_version = %s
                ORDER BY t.id DESC LIMIT 1""",
                (calc_version,)
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"版本不存在: {calc_version}")
            for k, v in row.items():
                if isinstance(v, datetime):
                    row[k] = v.isoformat()
            return row
    finally:
        conn.close()


# ============================================================
# 演示接口
# ============================================================

@router.post("/simulate")
def simulate_calculate():
    """快速模拟计算（演示用，不查数据库）"""
    return {
        "success": True,
        "message": "模拟计算成功",
        "indicators": {
            "total_assets": 321_589_800_000,
            "total_liabilities": -298_456_300_000,
            "net_position": 23_133_500_000,
            "avg_rate": 0.0325,
            "duration_days": 184,
            "duration_years": 0.504
        },
        "strategy": {
            "ftp_total": 8_456_700_000,
            "nii": 6_234_500_000,
            "nim": 0.0194,
            "var_99": 12_345_000_000
        }
    }
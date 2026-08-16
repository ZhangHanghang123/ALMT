"""
计算版本号管理服务

calc_version 格式：YYYYMMDD-XXXX
  - YYYYMMDD: 计算数据日期（8 位数字）
  - XXXX: 4 位序列码（同一天内递增，从 0001 开始）

示例：
  - 20260816-0001   第一天第一个版本
  - 20260816-0002   第一天第二个版本
  - 20260817-0001   第二天第一个版本
"""
import pymysql
from datetime import datetime, date
from typing import Optional, Tuple


def _to_yyyymmdd(d) -> str:
    """把日期转成 YYYYMMDD 字符串"""
    if isinstance(d, str):
        return d.replace('-', '').replace('/', '')[:8]
    if isinstance(d, datetime):
        return d.strftime('%Y%m%d')
    if isinstance(d, date):
        return d.strftime('%Y%m%d')
    raise ValueError(f"无法识别日期类型: {type(d)}")


def _db_conn():
    return pymysql.connect(
        host='localhost', user='almt', password='almt',
        database='almt_db', port=3306, cursorclass=pymysql.cursors.DictCursor
    )


def get_next_version(data_date) -> str:
    """
    获取下一个可用的版本号（同一天内递增）。

    规则：
      1. date_prefix = YYYYMMDD(data_date)
      2. 查询同日已有的 calc_version
      3. 取最大序列码 +1，没有则从 0001 开始

    Args:
        data_date: str(YYYY-MM-DD) / datetime / date

    Returns:
        str: YYYYMMDD-XXXX（如 20260816-0001）
    """
    date_prefix = _to_yyyymmdd(data_date)
    conn = _db_conn()
    try:
        with conn.cursor() as cursor:
            # 找同日最大的序列码
            cursor.execute(
                """SELECT MAX(CAST(SUBSTRING(calc_version, 10, 4) AS UNSIGNED)) AS max_seq
                FROM almt_calculate_task
                WHERE calc_version LIKE %s""",
                (f'{date_prefix}-%',)
            )
            row = cursor.fetchone()
            max_seq = (row['max_seq'] or 0) if row else 0
            next_seq = max_seq + 1
            return f'{date_prefix}-{next_seq:04d}'
    finally:
        conn.close()


def version_exists(calc_version: str) -> bool:
    """判断版本号是否已存在"""
    conn = _db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM almt_calculate_task WHERE calc_version=%s",
                (calc_version,)
            )
            return cursor.fetchone()['cnt'] > 0
    finally:
        conn.close()


def get_task_id_by_version(calc_version: str) -> Optional[str]:
    """通过 calc_version 反查 task_id（取最新一条）"""
    conn = _db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT task_id FROM almt_calculate_task
                WHERE calc_version=%s ORDER BY id DESC LIMIT 1""",
                (calc_version,)
            )
            row = cursor.fetchone()
            return row['task_id'] if row else None
    finally:
        conn.close()


def list_versions(limit: int = 50, only_with_data: bool = True) -> list:
    """
    列出所有计算版本（按版本号倒序）。

    Args:
        limit: 返回条数
        only_with_data: True 仅返回有数据的版本（status='success'）

    Returns:
        列表，每项含 calc_version, task_id, data_date, status, progress,
             created_at, completed_at, index_count, plan_count
    """
    conn = _db_conn()
    try:
        with conn.cursor() as cursor:
            where = "WHERE t.status = 'success'" if only_with_data else ""
            sql = f"""
                SELECT t.calc_version, t.task_id, t.data_date, t.status, t.progress,
                       t.started_at, t.completed_at, t.error_message,
                       (SELECT COUNT(*) FROM almt_result_index WHERE task_id=t.task_id) AS index_count,
                       (SELECT COUNT(*) FROM almt_result_plan WHERE task_id=t.task_id) AS plan_count
                FROM almt_calculate_task t
                {where}
                ORDER BY t.calc_version DESC, t.id DESC
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            rows = cursor.fetchall()
            for r in rows:
                for k, v in r.items():
                    if isinstance(v, datetime):
                        r[k] = v.isoformat()
                    elif isinstance(v, date):
                        r[k] = v.isoformat()
            return rows
    finally:
        conn.close()


def delete_version(calc_version: str) -> dict:
    """
    删除整个计算版本（任务记录 + 所有结果数据）。

    Returns:
        dict: {calc_version, deleted_task, deleted_index, deleted_plan}
    """
    conn = _db_conn()
    try:
        with conn.cursor() as cursor:
            # 1. 查 task_id
            cursor.execute(
                "SELECT task_id FROM almt_calculate_task WHERE calc_version=%s",
                (calc_version,)
            )
            rows = cursor.fetchall()
            if not rows:
                return {'calc_version': calc_version, 'deleted_task': 0, 'deleted_index': 0, 'deleted_plan': 0}

            task_ids = [r['task_id'] for r in rows]
            placeholders = ','.join(['%s'] * len(task_ids))

            # 2. 删除结果表
            cursor.execute(
                f"DELETE FROM almt_result_index WHERE task_id IN ({placeholders})",
                tuple(task_ids)
            )
            deleted_index = cursor.rowcount

            cursor.execute(
                f"DELETE FROM almt_result_plan WHERE task_id IN ({placeholders})",
                tuple(task_ids)
            )
            deleted_plan = cursor.rowcount

            # 3. 删除任务记录
            cursor.execute(
                "DELETE FROM almt_calculate_task WHERE calc_version=%s",
                (calc_version,)
            )
            deleted_task = cursor.rowcount

        conn.commit()
        return {
            'calc_version': calc_version,
            'deleted_task': deleted_task,
            'deleted_index': deleted_index,
            'deleted_plan': deleted_plan,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_empty_version(data_date: str, remark: str = None) -> Tuple[str, str]:
    """
    创建空版本（不执行计算）。

    Returns:
        (task_id, calc_version)
    """
    import uuid
    calc_version = get_next_version(data_date)
    task_id = str(uuid.uuid4())

    conn = _db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO almt_calculate_task
                (task_id, calc_version, data_date, status, progress, started_at, completed_at, error_message, created_by)
                VALUES (%s, %s, %s, 'empty', 100, NOW(), NOW(), %s, 1)""",
                (task_id, calc_version, data_date, remark or '空版本（未执行计算）')
            )
        conn.commit()
        return task_id, calc_version
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
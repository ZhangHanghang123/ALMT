"""
结果查询API（简化版，直接SQL操作）

支持 calc_version 参数（向后兼容）：
  - 不指定 calc_version 时，按 task_id 取最近一个 success 任务的结果
  - 指定 calc_version 时，按 calc_version 反查 task_id 取该版本结果
"""
from fastapi import APIRouter, Query
from typing import Optional
import pymysql
from datetime import datetime

router = APIRouter(prefix="/api/result", tags=["结果查询"])


def get_db_conn():
    return pymysql.connect(
        host='localhost', user='almt', password='almt',
        database='almt_db', port=3306, cursorclass=pymysql.cursors.DictCursor
    )


def _resolve_task_id(calc_version: Optional[str]) -> Optional[str]:
    """calc_version → task_id 反查"""
    if not calc_version:
        return None
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT task_id FROM almt_calculate_task WHERE calc_version=%s ORDER BY id DESC LIMIT 1",
                (calc_version,),
            )
            row = cursor.fetchone()
            return row['task_id'] if row else None
    finally:
        conn.close()


@router.get("/tasks")
def get_tasks():
    """获取已完成的任务列表（用于结果查看选择）"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT task_id, calc_version, data_date, status, progress, started_at, completed_at
                FROM almt_calculate_task
                WHERE status = 'success'
                ORDER BY completed_at DESC
                LIMIT 20
            """)
            rows = cursor.fetchall()
            for r in rows:
                for k, v in r.items():
                    if isinstance(v, datetime):
                        r[k] = v.isoformat()
            return rows
    finally:
        conn.close()


@router.get("/index")
def get_index_list(
    task_id: Optional[str] = None,
    calc_version: Optional[str] = Query(None, description="计算版本号（优先级高于 task_id）"),
):
    """获取基础指标结果（按账户册层级汇总）

    优先级：calc_version > task_id > 最近 success 任务
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # 优先级：calc_version > task_id > 最近 success
            cv_task_id = _resolve_task_id(calc_version) if calc_version else None
            if cv_task_id:
                task_id = cv_task_id
            elif not task_id:
                cursor.execute("""
                    SELECT task_id FROM almt_calculate_task
                    WHERE status = 'success'
                    ORDER BY completed_at DESC LIMIT 1
                """)
                row = cursor.fetchone()
                task_id = row['task_id'] if row else None

            if not task_id:
                return {"task_id": None, "calc_version": calc_version, "items": []}

            cursor.execute("""
                SELECT id, task_id, data_date, coa_cd, coa_name,
                       total_balance, average_balance, avg_rate
                FROM almt_result_index
                WHERE task_id = %s
                ORDER BY coa_cd
            """, (task_id,))
            items = cursor.fetchall()
            return {"task_id": task_id, "calc_version": calc_version, "items": items}
    finally:
        conn.close()


@router.get("/index/tree")
def get_index_tree(
    task_id: Optional[str] = None,
    calc_version: Optional[str] = Query(None, description="计算版本号（优先级高于 task_id）"),
):
    """按账户册树形展示基础指标结果

    优先级：calc_version > task_id > 最近 success 任务
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cv_task_id = _resolve_task_id(calc_version) if calc_version else None
            if cv_task_id:
                task_id = cv_task_id
            elif not task_id:
                cursor.execute("""
                    SELECT task_id FROM almt_calculate_task
                    WHERE status = 'success'
                    ORDER BY completed_at DESC LIMIT 1
                """)
                row = cursor.fetchone()
                task_id = row['task_id'] if row else None

            if not task_id:
                return {"task_id": None, "calc_version": calc_version, "items": []}

            cursor.execute("SELECT id, coa_cd, coa_name, leaf_flag, parent_coa_cd FROM almt_coa_info")
            all_coa = cursor.fetchall()

            cursor.execute("""
                SELECT coa_cd, total_balance, average_balance, avg_rate
                FROM almt_result_index WHERE task_id = %s
            """, (task_id,))
            value_map = {}
            for r in cursor.fetchall():
                value_map[r['coa_cd']] = r

            # 构建节点
            coa_map = {}
            roots = []
            for coa in all_coa:
                node = {
                    "id": coa['id'],
                    "coa_cd": coa['coa_cd'],
                    "coa_name": coa['coa_name'],
                    "leaf_flag": coa['leaf_flag'],
                    "total_balance": None,
                    "average_balance": None,
                    "avg_rate": None,
                    "has_data": False,
                    "children": []
                }
                if coa['coa_cd'] in value_map:
                    v = value_map[coa['coa_cd']]
                    node['total_balance'] = float(v['total_balance'] or 0)
                    node['average_balance'] = float(v['average_balance'] or 0)
                    node['avg_rate'] = float(v['avg_rate'] or 0)
                    node['has_data'] = True
                coa_map[coa['coa_cd']] = node

            # 父子挂载
            for coa in all_coa:
                node = coa_map[coa['coa_cd']]
                parent_cd = coa['parent_coa_cd']
                if not parent_cd or parent_cd not in coa_map:
                    roots.append(node)
                else:
                    coa_map[parent_cd]['children'].append(node)

            # 自底向上汇总
            def calc_sum(node):
                for c in node['children']:
                    calc_sum(c)
                if not node['children']:
                    return
                total_bal = 0
                total_avg = 0
                rate_sum = 0
                rate_cnt = 0
                any_data = False
                for c in node['children']:
                    if c['total_balance'] is not None:
                        total_bal += c['total_balance']
                        any_data = True
                    if c['average_balance'] is not None:
                        total_avg += c['average_balance']
                    if c['avg_rate'] is not None and c['avg_rate'] > 0:
                        rate_sum += c['avg_rate']
                        rate_cnt += 1
                if any_data:
                    node['total_balance'] = total_bal
                    node['average_balance'] = total_avg
                    if rate_cnt > 0:
                        node['avg_rate'] = rate_sum / rate_cnt
                    node['has_data'] = True

            for root in roots:
                calc_sum(root)

            return {"task_id": task_id, "calc_version": calc_version, "items": roots}
    finally:
        conn.close()


@router.get("/plan")
def get_plan_list(
    task_id: Optional[str] = None,
    calc_version: Optional[str] = Query(None, description="计算版本号"),
):
    """获取策略结果（业务计划汇总）"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cv_task_id = _resolve_task_id(calc_version) if calc_version else None
            if cv_task_id:
                task_id = cv_task_id
            elif not task_id:
                cursor.execute("""
                    SELECT task_id FROM almt_calculate_task
                    WHERE status = 'success'
                    ORDER BY completed_at DESC LIMIT 1
                """)
                row = cursor.fetchone()
                task_id = row['task_id'] if row else None

            if not task_id:
                return {"task_id": None, "calc_version": calc_version, "items": []}

            cursor.execute("""
                SELECT id, task_id, data_date, coa_cd, coa_name, item_name, item_value
                FROM almt_result_plan
                WHERE task_id = %s
                ORDER BY coa_cd
            """, (task_id,))
            items = cursor.fetchall()
            return {"task_id": task_id, "calc_version": calc_version, "items": items}
    finally:
        conn.close()


@router.get("/plan/tree")
def get_plan_tree(
    task_id: Optional[str] = None,
    calc_version: Optional[str] = Query(None, description="计算版本号"),
):
    """按账户册树形展示策略结果（业务计划）"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cv_task_id = _resolve_task_id(calc_version) if calc_version else None
            if cv_task_id:
                task_id = cv_task_id
            elif not task_id:
                cursor.execute("""
                    SELECT task_id FROM almt_calculate_task
                    WHERE status = 'success'
                    ORDER BY completed_at DESC LIMIT 1
                """)
                row = cursor.fetchone()
                task_id = row['task_id'] if row else None

            if not task_id:
                return {"task_id": None, "calc_version": calc_version, "items": []}

            cursor.execute("SELECT id, coa_cd, coa_name, leaf_flag, parent_coa_cd FROM almt_coa_info")
            all_coa = cursor.fetchall()

            cursor.execute("""
                SELECT coa_cd, item_value FROM almt_result_plan WHERE task_id = %s
            """, (task_id,))
            value_map = {r['coa_cd']: float(r['item_value'] or 0) for r in cursor.fetchall()}

            coa_map = {}
            roots = []
            for coa in all_coa:
                node = {
                    "id": coa['id'],
                    "coa_cd": coa['coa_cd'],
                    "coa_name": coa['coa_name'],
                    "leaf_flag": coa['leaf_flag'],
                    "item_value": None,
                    "has_data": False,
                    "children": []
                }
                if coa['coa_cd'] in value_map:
                    node['item_value'] = value_map[coa['coa_cd']]
                    node['has_data'] = True
                coa_map[coa['coa_cd']] = node

            for coa in all_coa:
                node = coa_map[coa['coa_cd']]
                parent_cd = coa['parent_coa_cd']
                if not parent_cd or parent_cd not in coa_map:
                    roots.append(node)
                else:
                    coa_map[parent_cd]['children'].append(node)

            def calc_sum(node):
                for c in node['children']:
                    calc_sum(c)
                if not node['children']:
                    return
                total = 0
                any_data = False
                for c in node['children']:
                    if c['item_value'] is not None:
                        total += c['item_value']
                        any_data = True
                if any_data:
                    node['item_value'] = total
                    node['has_data'] = True

            for root in roots:
                calc_sum(root)

            return {"task_id": task_id, "calc_version": calc_version, "items": roots}
    finally:
        conn.close()


@router.get("/summary")
def get_summary(
    task_id: Optional[str] = None,
    calc_version: Optional[str] = Query(None, description="计算版本号"),
):
    """获取结果汇总统计"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cv_task_id = _resolve_task_id(calc_version) if calc_version else None
            if cv_task_id:
                task_id = cv_task_id
                cursor.execute("SELECT data_date FROM almt_calculate_task WHERE task_id=%s", (task_id,))
                row = cursor.fetchone()
                data_date = row['data_date'] if row else None
            elif not task_id:
                cursor.execute("""
                    SELECT task_id, data_date FROM almt_calculate_task
                    WHERE status = 'success'
                    ORDER BY completed_at DESC LIMIT 1
                """)
                row = cursor.fetchone()
                if not row:
                    return {"task_id": None}
                task_id = row['task_id']
                data_date = row['data_date']
            else:
                cursor.execute("SELECT data_date FROM almt_calculate_task WHERE task_id=%s", (task_id,))
                row = cursor.fetchone()
                data_date = row['data_date'] if row else None

            cursor.execute("""
                SELECT
                    SUM(total_balance) AS sum_total,
                    SUM(CASE WHEN total_balance > 0 THEN total_balance ELSE 0 END) AS total_assets,
                    SUM(CASE WHEN total_balance < 0 THEN total_balance ELSE 0 END) AS total_liabilities,
                    AVG(avg_rate) AS avg_rate,
                    COUNT(*) AS cnt
                FROM almt_result_index
                WHERE task_id = %s
            """, (task_id,))
            stats = cursor.fetchone()

            return {
                "task_id": task_id,
                "calc_version": calc_version,
                "data_date": str(data_date) if data_date else None,
                "total_assets": float(stats['total_assets'] or 0),
                "total_liabilities": float(stats['total_liabilities'] or 0),
                "net_position": float(stats['sum_total'] or 0),
                "avg_rate": float(stats['avg_rate'] or 0),
                "index_count": int(stats['cnt'] or 0)
            }
    finally:
        conn.close()
"""
账户册管理API
"""
from fastapi import APIRouter
from typing import List
import pymysql

router = APIRouter(prefix="/api/coa", tags=["账户册管理"])


def get_db_conn():
    return pymysql.connect(
        host='localhost', user='almt', password='almt',
        database='almt_db', port=3306, cursorclass=pymysql.cursors.DictCursor
    )


@router.get("")
def get_coa_list():
    """获取账户册列表"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, uuid, order_number, parent_coa_cd, coa_cd, coa_name, leaf_desc, leaf_flag FROM almt_coa_info ORDER BY order_number LIMIT 1000")
            return cursor.fetchall()
    finally:
        conn.close()


@router.get("/tree")
def get_coa_tree():
    """获取账户册树形结构"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, uuid, parent_coa_cd, coa_cd, coa_name, leaf_flag FROM almt_coa_info")
            items = cursor.fetchall()

        tree_map = {}
        roots = []

        for item in items:
            node = {
                "id": item['id'],
                "uuid": item['uuid'],
                "coa_cd": item['coa_cd'],
                "coa_name": item['coa_name'],
                "leaf_flag": item['leaf_flag'],
                "title": f"{item['coa_cd']} - {item['coa_name'] or ''}",
                "key": str(item['id']),
                "children": []
            }
            tree_map[item['coa_cd']] = node

        for item in items:
            parent = item['parent_coa_cd']
            node = tree_map[item['coa_cd']]
            if not parent or parent not in tree_map:
                roots.append(node)
            else:
                tree_map[parent]['children'].append(node)

        return roots
    finally:
        conn.close()


@router.post("")
def create_coa(item: dict):
    """创建账户册"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            uuid_val = item.get('uuid') or str(__import__('uuid').uuid4())
            cursor.execute(
                """INSERT INTO almt_coa_info (uuid, order_number, parent_coa_cd, coa_cd, coa_name, leaf_desc, leaf_flag) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (uuid_val, item.get('order_number'), item.get('parent_coa_cd'),
                 item.get('coa_cd'), item.get('coa_name'), item.get('leaf_desc'), item.get('leaf_flag'))
            )
        conn.commit()
        return {"message": "创建成功", "uuid": uuid_val}
    finally:
        conn.close()


@router.put("/{coa_id}")
def update_coa(coa_id: int, item: dict):
    """更新账户册"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE almt_coa_info SET coa_name=%s, leaf_desc=%s WHERE id=%s""",
                (item.get('coa_name'), item.get('leaf_desc'), coa_id)
            )
        conn.commit()
        return {"message": "更新成功"}
    finally:
        conn.close()


@router.delete("/{coa_id}")
def delete_coa(coa_id: int):
    """删除账户册"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM almt_coa_info WHERE id=%s", (coa_id,))
        conn.commit()
        return {"message": "删除成功"}
    finally:
        conn.close()

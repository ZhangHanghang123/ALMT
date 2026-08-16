"""
基础参数API（时间步设置、账户册属性、报表口径）
"""
from fastapi import APIRouter
from typing import Optional
import pymysql
import uuid

router = APIRouter(prefix="/api/basic-param", tags=["基础参数"])


def get_db_conn():
    return pymysql.connect(
        host='localhost', user='almt', password='almt',
        database='almt_db', port=3306, cursorclass=pymysql.cursors.DictCursor
    )


# ============ 时间步设置 ============
@router.get("/time-step")
def list_time_step():
    """获取时间步列表"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT step_no, month_label, month_end_date, month_days, year_days FROM almt_time_step ORDER BY step_no")
            rows = cursor.fetchall()
            from datetime import date
            for r in rows:
                if isinstance(r.get('month_end_date'), date):
                    r['month_end_date'] = r['month_end_date'].isoformat()
            return rows
    finally:
        conn.close()


@router.post("/time-step")
def create_time_step(item: dict):
    """创建时间步"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO almt_time_step (step_no, month_label, month_end_date, month_days, year_days)
                VALUES (%s, %s, %s, %s, %s)""",
                (item.get('step_no'), item.get('month_label', ''),
                 item.get('month_end_date'), item.get('month_days', 30), item.get('year_days', 365))
            )
        conn.commit()
        return {"message": "创建成功"}
    finally:
        conn.close()


@router.put("/time-step/{step_no}")
def update_time_step(step_no: int, item: dict):
    """更新时间步"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE almt_time_step SET month_label=%s, month_end_date=%s, month_days=%s, year_days=%s WHERE step_no=%s""",
                (item.get('month_label', ''), item.get('month_end_date'),
                 item.get('month_days', 30), item.get('year_days', 365), step_no)
            )
        conn.commit()
        return {"message": "更新成功"}
    finally:
        conn.close()


@router.delete("/time-step/{step_no}")
def delete_time_step(step_no: int):
    """删除时间步"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM almt_time_step WHERE step_no=%s", (step_no,))
        conn.commit()
        return {"message": "删除成功"}
    finally:
        conn.close()


@router.post("/time-step/regenerate")
def regenerate_time_step(item: dict):
    """根据指定起始年月重新生成24个月时间步

    入参: { year: int, start_month: int (1-12) }
    输出: 自动生成24个月的月末日、当月天数、当年天数
    """
    import calendar
    from datetime import date

    year = int(item.get('year', 2024))
    start_month = int(item.get('start_month', 1))

    conn = get_db_conn()
    try:
        # 先清空
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM almt_time_step")

            generated = []
            y, m = year, start_month
            for i in range(24):
                step_no = i + 1
                month_label = f'M{step_no}'
                # 当月最后一天
                last_day = calendar.monthrange(y, m)[1]
                end_date = date(y, m, last_day)
                # 当月天数
                month_days = last_day
                # 当年天数
                year_days = 366 if calendar.isleap(y) else 365

                cursor.execute(
                    """INSERT INTO almt_time_step
                    (step_no, month_label, month_end_date, month_days, year_days)
                    VALUES (%s, %s, %s, %s, %s)""",
                    (step_no, month_label, end_date, month_days, year_days)
                )
                generated.append({
                    'step_no': step_no,
                    'month_label': month_label,
                    'month_end_date': end_date.isoformat(),
                    'month_days': month_days,
                    'year_days': year_days
                })

                # 下个月
                m += 1
                if m > 12:
                    m = 1
                    y += 1

        conn.commit()
        return {"message": f"已生成 {len(generated)} 个月时间步", "items": generated}
    finally:
        conn.close()


# ============ 账户册属性 ============
@router.get("/coa-attribute")
def list_coa_attribute(skip: int = 0, limit: int = 100, search: str = ''):
    """获取账户册属性列表（带 has_data 标记）"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            base_sql = """SELECT a.id, a.uuid, a.coa_cd, a.coa_name, a.term, a.accrule_base,
                          a.curve_name, a.curve_id, a.business_line, a.float_ratio,
                          a.replace_type, a.reprice_freq,
                          (SELECT c.coa_name FROM almt_coa_info c WHERE c.coa_cd = a.coa_cd LIMIT 1) AS coa_name_ref
                          FROM almt_coa_attribute a"""
            if search:
                cursor.execute(
                    base_sql + " WHERE a.coa_cd LIKE %s OR a.coa_name LIKE %s ORDER BY a.coa_cd LIMIT %s OFFSET %s",
                    (f'%{search}%', f'%{search}%', limit, skip)
                )
            else:
                cursor.execute(base_sql + " ORDER BY a.coa_cd LIMIT %s OFFSET %s", (limit, skip))
            rows = cursor.fetchall()
            for r in rows:
                r['has_data'] = True
            return rows
    finally:
        conn.close()


@router.get("/coa-attribute/tree")
def get_coa_attribute_tree():
    """按账户册树形结构组织属性（含所有账户册节点）"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # 所有账户册节点
            cursor.execute("SELECT id, coa_cd, coa_name FROM almt_coa_info ORDER BY coa_cd")
            all_coa = cursor.fetchall()

            # 所有账户册属性（按 coa_cd 索引）
            cursor.execute("""SELECT coa_cd, coa_name, term, accrule_base, curve_name, curve_id,
                              business_line, float_ratio, replace_type, reprice_freq
                              FROM almt_coa_attribute""")
            attr_map = {}
            for r in cursor.fetchall():
                attr_map[r['coa_cd']] = r

        # 构建账户册节点，挂载属性
        coa_map = {}
        roots = []
        for coa in all_coa:
            attr = attr_map.get(coa['coa_cd'])
            has_data = attr is not None
            node = {
                'id': coa['id'],
                'coa_cd': coa['coa_cd'],
                'coa_name': coa['coa_name'],
                'has_data': has_data,
                'children': []
            }
            if attr:
                node.update({
                    'term': attr.get('term'),
                    'accrule_base': attr.get('accrule_base'),
                    'curve_name': attr.get('curve_name'),
                    'curve_id': attr.get('curve_id'),
                    'business_line': attr.get('business_line'),
                    'float_ratio': attr.get('float_ratio'),
                    'replace_type': attr.get('replace_type'),
                    'reprice_freq': attr.get('reprice_freq')
                })
            coa_map[coa['coa_cd']] = node

        # 挂载父子关系
        for coa in all_coa:
            node = coa_map[coa['coa_cd']]
            parent_cd = None
            # 根据 parent_coa_cd 查找
            cursor2 = conn.cursor()
            try:
                cursor2.execute("SELECT parent_coa_cd FROM almt_coa_info WHERE coa_cd=%s", (coa['coa_cd'],))
                row = cursor2.fetchone()
                if row and row['parent_coa_cd']:
                    parent_cd = row['parent_coa_cd']
            finally:
                cursor2.close()

            if parent_cd and parent_cd in coa_map:
                coa_map[parent_cd]['children'].append(node)
            else:
                roots.append(node)

        return roots
    finally:
        conn.close()


@router.post("/coa-attribute/save")
def save_coa_attribute(item: dict):
    """按 coa_cd upsert 账户册属性"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            coa_cd = item.get('coa_cd', '')
            coa_name = item.get('coa_name', '')
            cursor.execute("SELECT id FROM almt_coa_attribute WHERE coa_cd=%s", (coa_cd,))
            existing = cursor.fetchone()
            fields = ['coa_cd', 'coa_name', 'term', 'accrule_base', 'curve_name', 'curve_id',
                      'business_line', 'float_ratio', 'replace_type', 'reprice_freq']
            values = [coa_cd, coa_name,
                      item.get('term', ''), item.get('accrule_base', ''),
                      item.get('curve_name', ''), item.get('curve_id'),
                      item.get('business_line', ''),
                      item.get('float_ratio'),
                      item.get('replace_type', ''), item.get('reprice_freq', '')]
            if existing:
                set_clause = ','.join([f + '=%s' for f in fields])
                sql = f'UPDATE almt_coa_attribute SET {set_clause} WHERE id=%s'
                values.append(existing['id'])
                cursor.execute(sql, values)
            else:
                fields.insert(0, 'uuid')
                values.insert(0, str(uuid.uuid4()))
                placeholders = ','.join(['%s'] * len(fields))
                sql = f'INSERT INTO almt_coa_attribute ({",".join(fields)}) VALUES ({placeholders})'
                cursor.execute(sql, values)
        conn.commit()
        return {"message": "保存成功"}
    finally:
        conn.close()


@router.delete("/coa-attribute/{item_id}")
def delete_coa_attribute(item_id: int):
    """删除账户册属性"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM almt_coa_attribute WHERE id=%s", (item_id,))
        conn.commit()
        return {"message": "删除成功"}
    finally:
        conn.close()





# ============ 字典管理 ============
@router.get("/dict")
def list_dict(dict_type: str = ''):
    """获取字典列表"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            if dict_type:
                cursor.execute("SELECT id, dict_id, dict_name, dict_type, description FROM almt_dict WHERE dict_type=%s ORDER BY dict_id", (dict_type,))
            else:
                cursor.execute("SELECT id, dict_id, dict_name, dict_type, description FROM almt_dict ORDER BY dict_id")
            return cursor.fetchall()
    finally:
        conn.close()


@router.get("/dict/{dict_id}/values")
def list_dict_values(dict_id: str):
    """获取字典码值列表"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, value_code, value_name, sort_no FROM almt_dict_value WHERE dict_id=%s ORDER BY sort_no, value_code", (dict_id,))
            return cursor.fetchall()
    finally:
        conn.close()


@router.post("/dict/{dict_id}/values")
def create_dict_value(dict_id: str, item: dict):
    """新增字典码值"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO almt_dict_value (dict_id, value_code, value_name, sort_no) VALUES (%s, %s, %s, %s)",
                (dict_id, item.get('value_code', ''), item.get('value_name', ''), item.get('sort_no', 0))
            )
        conn.commit()
        return {"message": "创建成功"}
    finally:
        conn.close()


@router.put("/dict/value/{value_id}")
def update_dict_value(value_id: int, item: dict):
    """更新字典码值"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE almt_dict_value SET value_code=%s, value_name=%s, sort_no=%s WHERE id=%s",
                (item.get('value_code', ''), item.get('value_name', ''), item.get('sort_no', 0), value_id)
            )
        conn.commit()
        return {"message": "更新成功"}
    finally:
        conn.close()


@router.delete("/dict/value/{value_id}")
def delete_dict_value(value_id: int):
    """删除字典码值"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM almt_dict_value WHERE id=%s", (value_id,))
        conn.commit()
        return {"message": "删除成功"}
    finally:
        conn.close()


# ============ 报表口径（使用字典码值） ============
CALIBER_FIELDS = ['coa_cd', 'coa_name']
for i in range(1, 24):
    CALIBER_FIELDS.extend([f'num{i}', f'num{i}_c', f'num{i}_t', f'den{i}', f'den{i}_c', f'den{i}_t'])
CALIBER_FIELDS.append('remark')

CALIBER_SELECT_FIELDS = ['id'] + CALIBER_FIELDS


def _load_dict_map(cursor, dict_id):
    """加载字典码值映射 code->name"""
    cursor.execute("SELECT value_code, value_name FROM almt_dict_value WHERE dict_id=%s", (dict_id,))
    return {r['value_code']: r['value_name'] for r in cursor.fetchall()}


def _resolve_caliber_row(row, num_map, den_map):
    """把行数据中的字典码值转换为名称"""
    resolved = dict(row)
    for i in range(1, 24):
        # 分子
        num_code = row.get(f'num{i}')
        if num_code and num_code in num_map:
            resolved[f'num{i}_name'] = num_map[num_code]
        else:
            resolved[f'num{i}_name'] = ''
        # 分母
        den_code = row.get(f'den{i}')
        if den_code and den_code in den_map:
            resolved[f'den{i}_name'] = den_map[den_code]
        else:
            resolved[f'den{i}_name'] = ''
    return resolved


@router.get("/metric-caliber")
def list_metric_caliber(skip: int = 0, limit: int = 100, search: str = ''):
    """获取报表口径列表（自动将字典码值转换为名称）"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            num_map = _load_dict_map(cursor, 'NUM')
            den_map = _load_dict_map(cursor, 'DEN')

            fields_str = ','.join(CALIBER_SELECT_FIELDS)
            if search:
                sql = f"""SELECT {fields_str} FROM almt_metric_caliber
                          WHERE coa_cd LIKE %s OR coa_name LIKE %s
                          ORDER BY coa_cd LIMIT %s OFFSET %s"""
                cursor.execute(sql, (f'%{search}%', f'%{search}%', limit, skip))
            else:
                sql = f"""SELECT {fields_str} FROM almt_metric_caliber
                          ORDER BY coa_cd LIMIT %s OFFSET %s"""
                cursor.execute(sql, (limit, skip))
            rows = cursor.fetchall()
            return [_resolve_caliber_row(r, num_map, den_map) for r in rows]
    finally:
        conn.close()


@router.post("/metric-caliber")
def create_metric_caliber(item: dict):
    """创建报表口径（前端传字典码值）"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            values = []
            for f in CALIBER_FIELDS:
                v = item.get(f)
                if v == '':
                    v = None
                values.append(v)
            placeholders = ','.join(['%s'] * len(CALIBER_FIELDS))
            sql = f'INSERT INTO almt_metric_caliber ({",".join(CALIBER_FIELDS)}) VALUES ({placeholders})'
            cursor.execute(sql, values)
        conn.commit()
        return {"message": "创建成功"}
    finally:
        conn.close()


@router.put("/metric-caliber/{item_id}")
def update_metric_caliber(item_id: int, item: dict):
    """更新报表口径"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            set_clause = ','.join([f + '=%s' for f in CALIBER_FIELDS])
            values = []
            for f in CALIBER_FIELDS:
                v = item.get(f)
                if v == '':
                    v = None
                values.append(v)
            values.append(item_id)
            sql = f'UPDATE almt_metric_caliber SET {set_clause} WHERE id=%s'
            cursor.execute(sql, values)
        conn.commit()
        return {"message": "更新成功"}
    finally:
        conn.close()


@router.delete("/metric-caliber/{item_id}")
def delete_metric_caliber(item_id: int):
    """删除报表口径"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM almt_metric_caliber WHERE id=%s", (item_id,))
        conn.commit()
        return {"message": "删除成功"}
    finally:
        conn.close()


# ============ 账户册下拉选项（供报表口径使用） ============
@router.get("/coa-options")
def get_coa_options():
    """获取账户册编码-名称下拉选项（从 coa_attribute 加载，无数据时从 coa_info 补充）"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # 优先账户册属性表
            cursor.execute("""
                SELECT coa_cd, coa_name FROM almt_coa_attribute
                WHERE coa_cd IS NOT NULL AND coa_cd != ''
                ORDER BY coa_cd
            """)
            attr_list = cursor.fetchall()
            attr_keys = {r['coa_cd'] for r in attr_list}

            # 补充 coa_info 中的账户册
            cursor.execute("""
                SELECT coa_cd, coa_name FROM almt_coa_info
                WHERE coa_cd IS NOT NULL AND coa_cd != ''
                ORDER BY coa_cd
            """)
            info_list = cursor.fetchall()

        options = []
        for r in attr_list:
            options.append({
                'value': r['coa_cd'],
                'label': f"{r['coa_cd']} - {r['coa_name'] or ''}"
            })
        for r in info_list:
            if r['coa_cd'] not in attr_keys:
                options.append({
                    'value': r['coa_cd'],
                    'label': f"{r['coa_cd']} - {r['coa_name'] or ''}"
                })
        return options
    finally:
        conn.close()
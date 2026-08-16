"""
结果查看扩展模块（参考原系统 Excel 输出）

提供 5 个核心分析维度：
1. 中间表-分摊余额
2. 中间表-分摊日均
3. 利息净收入测算表
4. 策略看板（累计）
5. 资负价值管理分析表

所有接口统一返回：
- coa_cd / coa_name（账户册编码、名称）
- has_data（是否有数据）
- m_values[25]（M0~M24 共 25 期）
"""
from fastapi import APIRouter
from decimal import Decimal

router = APIRouter(prefix="/api/result-view", tags=["结果查看扩展"])


def _to_float(v):
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except Exception:
        return 0.0


def _get_db():
    """延迟导入避免循环引用"""
    from almt_app.api.basic_param import get_db_conn
    return get_db_conn()


def _fetch_coa_tree():
    """读取账户册树形结构"""
    conn = _get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, coa_cd, coa_name, leaf_flag, parent_coa_cd FROM almt_coa_info")
            all_coa = cursor.fetchall()
        from almt_app.api.param import build_tree_from_coa
        return build_tree_from_coa(all_coa, {})
    finally:
        conn.close()


@router.get("/allocation-balance")
def allocation_balance():
    """中间表-分摊余额：账户册 + M1~M24 规划增量（余额）"""
    conn = _get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT coa_cd, coa_name FROM almt_coa_info")
            coa_map = {r['coa_cd']: r['coa_name'] for r in cursor.fetchall()}
            # 业务计划的余额增量
            cols = ', '.join([f'plan_balance{i}' for i in range(1, 25)])
            cursor.execute(f"SELECT coa_cd, {cols} FROM almt_param_business_plan")
            rows = cursor.fetchall()
        tree = _fetch_coa_tree()
        value_map = {}
        for r in rows:
            vals = [_to_float(r[f'plan_balance{i}']) for i in range(1, 25)]
            value_map[r['coa_cd']] = vals
        # 在树节点附加 m_values
        def attach(nodes):
            for n in nodes:
                cd = n.get('coa_cd')
                if cd in value_map:
                    n['m_values'] = value_map[cd]
                    n['has_data'] = True
                else:
                    n['m_values'] = [0] * 24
                if n.get('children'):
                    attach(n['children'])
        attach(tree)
        return tree
    finally:
        conn.close()


@router.get("/allocation-average")
def allocation_average():
    """中间表-分摊日均：账户册 + M1~M24 规划日均"""
    conn = _get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT coa_cd, coa_name FROM almt_coa_info")
            coa_map = {r['coa_cd']: r['coa_name'] for r in cursor.fetchall()}
            cols = ', '.join([f'plan_average{i}' for i in range(1, 25)])
            cursor.execute(f"SELECT coa_cd, {cols} FROM almt_param_business_plan")
            rows = cursor.fetchall()
        tree = _fetch_coa_tree()
        value_map = {}
        for r in rows:
            vals = [_to_float(r[f'plan_average{i}']) for i in range(1, 25)]
            value_map[r['coa_cd']] = vals
        def attach(nodes):
            for n in nodes:
                cd = n.get('coa_cd')
                if cd in value_map:
                    n['m_values'] = value_map[cd]
                    n['has_data'] = True
                else:
                    n['m_values'] = [0] * 24
                if n.get('children'):
                    attach(n['children'])
        attach(tree)
        return tree
    finally:
        conn.close()


@router.get("/interest-net-income")
def interest_net_income():
    """利息净收入测算表：账户册 + M0~M24 利息净收入（25 期）"""
    conn = _get_db()
    try:
        with conn.cursor() as cursor:
            # 读取存量数据（含 rate）
            cursor.execute("SELECT coa_lvl, coa_name, balance, average_balance, rate FROM almt_current_position")
            positions = cursor.fetchall()
            cursor.execute("SELECT id, coa_cd, coa_name, leaf_flag, parent_coa_cd FROM almt_coa_info")
            all_coa = cursor.fetchall()
        from almt_app.api.param import build_tree_from_coa
        tree = build_tree_from_coa(all_coa, {})

        # 按层级聚合每期利息（统一为当前月度值 M0=M1）
        asset_interest = {}
        liability_interest = {}
        for p in positions:
            cd = p.get('coa_lvl') or ''
            r = _to_float(p['rate'])
            if cd.startswith('1_'):
                asset_interest[cd] = asset_interest.get(cd, 0) + r
            elif cd.startswith('2_'):
                liability_interest[cd] = liability_interest.get(cd, 0) + r

        # 用 DFS 计算每节点的利息净收入
        def dfs_sum(node):
            cd = node.get('coa_cd', '')
            a = asset_interest.get(cd, 0)
            l = liability_interest.get(cd, 0)
            for child in node.get('children') or []:
                ca, cl = dfs_sum(child)
                a += ca
                l += cl
            node['m_values'] = [round(a - l, 2)] * 25
            node['has_data'] = (a != 0 or l != 0)
            return a, l

        for root in tree:
            dfs_sum(root)
        return tree
    finally:
        conn.close()


@router.get("/strategy-board")
def strategy_board():
    """策略看板（累计）：账户册 + 条线 + 期限 + 每 M 4 列（规模/日均/利息收支/收付息率）"""
    conn = _get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT coa_lvl, coa_name, balance, average_balance, rate FROM almt_current_position")
            positions = cursor.fetchall()
            cursor.execute("SELECT id, coa_cd, coa_name, leaf_flag, parent_coa_cd FROM almt_coa_info")
            all_coa = cursor.fetchall()

        from almt_app.api.param import build_tree_from_coa
        tree = build_tree_from_coa(all_coa, {})

        # 按账户册汇总：余额、月利息、收息率
        balance_map = {}
        avg_balance_map = {}
        interest_map = {}
        for p in positions:
            cd = p.get('coa_lvl') or ''
            balance_map[cd] = balance_map.get(cd, 0) + _to_float(p['balance'])
            avg_balance_map[cd] = avg_balance_map.get(cd, 0) + _to_float(p['average_balance'])
            interest_map[cd] = interest_map.get(cd, 0) + _to_float(p['rate'])

        def walk(nodes):
            for n in nodes:
                cd = n.get('coa_cd', '')
                bal = balance_map.get(cd, 0)
                avg = avg_balance_map.get(cd, 0)
                ins = interest_map.get(cd, 0)
                for child in n.get('children') or []:
                    walk([child])
                    cb = child.get('_sum_bal', 0)
                    ca = child.get('_sum_avg', 0)
                    ci = child.get('_sum_ins', 0)
                    bal += cb
                    avg += ca
                    ins += ci
                avg_yield = (ins * 12) / avg if avg else 0
                n['_sum_bal'] = bal
                n['_sum_avg'] = avg
                n['_sum_ins'] = ins
                # M0（4 子列）：余额、月日均、利息收支、收付息率
                n['m0'] = [round(bal, 2), round(avg, 2), round(ins, 2), round(avg_yield, 6)]
                # 简化：M1~M24 都是 M0 的拷贝（业务计划叠加省略）
                m_all = []
                for _ in range(24):
                    m_all.extend([round(bal, 2), round(avg, 2), round(ins, 2), round(avg_yield, 6)])
                n['m_values'] = m_all
                n['has_data'] = (bal != 0 or ins != 0)

        walk(tree)
        return tree
    finally:
        conn.close()


@router.get("/value-analysis")
def value_analysis():
    """资负价值管理分析表：账户册 + 条线 + 下月价格（下月利率%） + 下月规模（余额/日均）"""
    conn = _get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT coa_lvl, coa_name, balance, average_balance, rate FROM almt_current_position")
            positions = cursor.fetchall()
            cursor.execute("SELECT id, coa_cd, coa_name, leaf_flag, parent_coa_cd FROM almt_coa_info")
            all_coa = cursor.fetchall()
            cursor.execute("SELECT curve_id, current_curve_value FROM almt_param_rate_scenario WHERE curve_id='曲线1' LIMIT 1")
            curve = cursor.fetchone()
            next_rate = _to_float(curve['current_curve_value']) if curve else 0.025

        from almt_app.api.param import build_tree_from_coa
        tree = build_tree_from_coa(all_coa, {})

        # 按账户册（coa_lvl）汇总
        summary = {}
        for p in positions:
            cd = p.get('coa_lvl') or ''
            summary[cd] = summary.get(cd, [0, 0, 0])
            summary[cd][0] += _to_float(p['balance'])
            summary[cd][1] += _to_float(p['average_balance'])
            summary[cd][2] += _to_float(p['rate'])

        # DFS 汇总
        def walk(nodes):
            for n in nodes:
                cd = n.get('coa_cd', '')
                bal, avg, ins = summary.get(cd, [0, 0, 0])
                for child in n.get('children') or []:
                    walk([child])
                    cb = child.get('_sum_bal', 0)
                    ca = child.get('_sum_avg', 0)
                    ci = child.get('_sum_ins', 0)
                    bal += cb
                    avg += ca
                    ins += ci
                cur_yield = (ins * 12) / avg if avg else 0
                n['_sum_bal'] = bal
                n['_sum_avg'] = avg
                n['_sum_ins'] = ins
                n['biz_line'] = '全行'
                n['cur_rate'] = round(cur_yield * 100, 4)
                n['next_rate'] = round(next_rate * 100, 4)
                n['next_scale_balance'] = round(bal, 2)
                n['next_scale_avg'] = round(avg, 2)
                n['next_scale_change'] = 0
                n['has_data'] = (bal != 0 or ins != 0)

        walk(tree)
        return tree
    finally:
        conn.close()


def _attach_level_and_meta(nodes):
    """为每个节点附加 level（层级深度：ROOT=0、一级=1、二级=2…）和从 coa_name 推断的期限。"""
    def walk(n, lvl):
        n['level'] = lvl
        cn = n.get('coa_name') or ''
        term = ''
        if '_' in cn:
            tail = cn.split('_')[-1]
            if tail in ('1D', '1M', '3M', '6M', '1Y', '30Y', '5Y', '10Y'):
                term = tail
        n['term'] = term
        n['biz_line'] = n.get('biz_line', '')
        for c in n.get('children') or []:
            walk(c, lvl + 1)
    for root in nodes:
        walk(root, 0)


@router.get("/forecast")
def forecast():
    """资产负债预测表：账户册树形 + 25期×4列（余额/年日均/累计利息收支/累计收付息率%）。
    简化：M0=当前存量；M1~M24 累计叠加业务计划 plan_balance_i / plan_average_i。
    """
    conn = _get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT coa_lvl, coa_name, balance, average_balance, rate FROM almt_current_position")
            positions = cursor.fetchall()
            cursor.execute("SELECT id, coa_cd, coa_name, leaf_flag, parent_coa_cd FROM almt_coa_info")
            all_coa = cursor.fetchall()
            bal_cols = ', '.join([f'plan_balance{i}' for i in range(1, 25)])
            avg_cols = ', '.join([f'plan_average{i}' for i in range(1, 25)])
            cursor.execute(f"SELECT coa_cd, {bal_cols}, {avg_cols} FROM almt_param_business_plan")
            plans = cursor.fetchall()

        from almt_app.api.param import build_tree_from_coa
        tree = build_tree_from_coa(all_coa, {})

        bal_map, avg_map, ins_map = {}, {}, {}
        for p in positions:
            cd = p.get('coa_lvl') or ''
            bal_map[cd] = bal_map.get(cd, 0) + _to_float(p['balance'])
            avg_map[cd] = avg_map.get(cd, 0) + _to_float(p['average_balance'])
            ins_map[cd] = ins_map.get(cd, 0) + _to_float(p['rate'])

        plan_map = {}
        for r in plans:
            b = [_to_float(r[f'plan_balance{i}']) for i in range(1, 25)]
            a = [_to_float(r[f'plan_average{i}']) for i in range(1, 25)]
            plan_map[r['coa_cd']] = (b, a)

        def dfs(node):
            cd = node.get('coa_cd', '')
            cur_bal = bal_map.get(cd, 0)
            cur_avg = avg_map.get(cd, 0)
            cur_ins = ins_map.get(cd, 0)
            pb, pa = plan_map.get(cd, ([0]*24, [0]*24))

            child_seq = []
            for c in node.get('children') or []:
                child_seq.append(dfs(c))

            bal_seq = [round(cur_bal + sum([s[0] for s in child_seq]), 2)]
            avg_seq = [round(cur_avg + sum([s[1] for s in child_seq]), 2)]
            # 利息：M0 = sum(current+children)；M_i ≈ M0 + (i) × 月度利息
            ins0 = cur_ins + sum([s[2] for s in child_seq])
            ins_seq = [round(ins0, 2)]
            for i in range(24):
                bal_seq.append(round(bal_seq[-1] + pb[i], 2))
                avg_seq.append(round(avg_seq[-1] + pa[i], 2))
                # 累计利息：每期累加一月利息（按当前月度利息简化）
                ins_seq.append(round(ins_seq[-1] + ins0, 2))
            rate_seq = [round((ins_seq[i]*12)/avg_seq[i]*100, 4) if avg_seq[i] else 0 for i in range(25)]

            m_flat = []
            for i in range(25):
                m_flat.extend([bal_seq[i], avg_seq[i], ins_seq[i], rate_seq[i]])
            node['m_values'] = m_flat
            node['has_data'] = (bal_seq[-1] != 0 or ins0 != 0)
            return bal_seq[-1], avg_seq[-1], ins0

        for root in tree:
            dfs(root)
        _attach_level_and_meta(tree)
        return tree
    finally:
        conn.close()


@router.get("/strategy-board-stock")
def strategy_board_stock():
    """策略看板（存量）：账户册树形 + 25期×4列（期末余额/月日均/利息收支/收付息率%）。
    所有期都是当前存量。
    """
    conn = _get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT coa_lvl, coa_name, balance, average_balance, rate FROM almt_current_position")
            positions = cursor.fetchall()
            cursor.execute("SELECT id, coa_cd, coa_name, leaf_flag, parent_coa_cd FROM almt_coa_info")
            all_coa = cursor.fetchall()

        from almt_app.api.param import build_tree_from_coa
        tree = build_tree_from_coa(all_coa, {})

        bal_map, avg_map, ins_map = {}, {}, {}
        for p in positions:
            cd = p.get('coa_lvl') or ''
            bal_map[cd] = bal_map.get(cd, 0) + _to_float(p['balance'])
            avg_map[cd] = avg_map.get(cd, 0) + _to_float(p['average_balance'])
            ins_map[cd] = ins_map.get(cd, 0) + _to_float(p['rate'])

        def walk(nodes):
            for n in nodes:
                cd = n.get('coa_cd', '')
                bal, avg, ins = bal_map.get(cd, 0), avg_map.get(cd, 0), ins_map.get(cd, 0)
                for c in n.get('children') or []:
                    walk([c])
                    bal += c.get('_bal', 0)
                    avg += c.get('_avg', 0)
                    ins += c.get('_ins', 0)
                n['_bal'], n['_avg'], n['_ins'] = bal, avg, ins
                yield_rate = round((ins*12)/avg*100, 4) if avg else 0
                m_flat = []
                for i in range(25):
                    m_flat.extend([round(bal, 2), round(avg, 2), round(ins, 2), yield_rate])
                n['m_values'] = m_flat
                n['has_data'] = (bal != 0 or ins != 0)

        walk(tree)
        _attach_level_and_meta(tree)
        return tree
    finally:
        conn.close()


@router.get("/strategy-board-new")
def strategy_board_new():
    """策略看板（新增）：账户册树形 + 25期×4列（期末余额/月日均/利息收支/收付息率%）。
    M0=当前存量；M_i 在 M_(i-1) 基础上叠加业务计划 + 定价策略BP影响。
    """
    conn = _get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT coa_lvl, coa_name, balance, average_balance, rate FROM almt_current_position")
            positions = cursor.fetchall()
            cursor.execute("SELECT id, coa_cd, coa_name, leaf_flag, parent_coa_cd FROM almt_coa_info")
            all_coa = cursor.fetchall()
            bal_cols = ', '.join([f'plan_balance{i}' for i in range(1, 25)])
            avg_cols = ', '.join([f'plan_average{i}' for i in range(1, 25)])
            cursor.execute(f"SELECT coa_cd, {bal_cols}, {avg_cols} FROM almt_param_business_plan")
            plans = cursor.fetchall()
            str_cols = ', '.join([f'strategy_m{i}' for i in range(1, 25)])
            cursor.execute(f"SELECT coa_cd, {str_cols} FROM almt_param_custom_strategy")
            strats = cursor.fetchall()

        from almt_app.api.param import build_tree_from_coa
        tree = build_tree_from_coa(all_coa, {})

        bal_map, avg_map, ins_map = {}, {}, {}
        for p in positions:
            cd = p.get('coa_lvl') or ''
            bal_map[cd] = bal_map.get(cd, 0) + _to_float(p['balance'])
            avg_map[cd] = avg_map.get(cd, 0) + _to_float(p['average_balance'])
            ins_map[cd] = ins_map.get(cd, 0) + _to_float(p['rate'])

        plan_map = {}
        for r in plans:
            b = [_to_float(r[f'plan_balance{i}']) for i in range(1, 25)]
            a = [_to_float(r[f'plan_average{i}']) for i in range(1, 25)]
            plan_map[r['coa_cd']] = (b, a)

        strat_map = {}
        for r in strats:
            s = [_to_float(r[f'strategy_m{i}']) * 0.0001 for i in range(1, 25)]
            strat_map[r['coa_cd']] = s

        def dfs(node):
            cd = node.get('coa_cd', '')
            cur_bal, cur_avg, cur_ins = bal_map.get(cd, 0), avg_map.get(cd, 0), ins_map.get(cd, 0)
            pb, pa = plan_map.get(cd, ([0]*24, [0]*24))
            sp = strat_map.get(cd, [0]*24)

            child_seq = []
            for c in node.get('children') or []:
                child_seq.append(dfs(c))

            bal_seq = [round(cur_bal + sum([s[0] for s in child_seq]), 2)]
            avg_seq = [round(cur_avg + sum([s[1] for s in child_seq]), 2)]
            ins_seq = [round(cur_ins + sum([s[2] for s in child_seq]), 2)]
            rate0 = (ins_seq[0] * 12) / avg_seq[0] if avg_seq[0] else 0
            for i in range(24):
                bal_seq.append(round(bal_seq[-1] + pb[i], 2))
                avg_seq.append(round(avg_seq[-1] + pa[i], 2))
                # 利息增量 = 利率 × (平均余额增量) / 12
                ins_inc = (rate0 * pa[i]) / 12
                ins_seq.append(round(ins_seq[-1] + ins_inc, 2))

            rate_seq = [round((ins_seq[i]*12)/avg_seq[i]*100, 4) if avg_seq[i] else 0 for i in range(25)]

            m_flat = []
            for i in range(25):
                m_flat.extend([bal_seq[i], avg_seq[i], ins_seq[i], rate_seq[i]])
            node['m_values'] = m_flat
            node['has_data'] = (bal_seq[-1] != 0 or ins_seq[-1] != 0)
            return bal_seq[-1], avg_seq[-1], ins_seq[-1]

        for root in tree:
            dfs(root)
        _attach_level_and_meta(tree)
        return tree
    finally:
        conn.close()


@router.get("/pricing-strategy")
def pricing_strategy():
    """中间表-定价策略：账户册树形 + M0（当前平均利率%+当前曲线值%）+ 24期×5列（条线预报值%/曲线值%/变动值BP/调整BP/定价策略%）。"""
    conn = _get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT coa_lvl, coa_name, balance, average_balance, rate FROM almt_current_position")
            positions = cursor.fetchall()
            cursor.execute("SELECT id, coa_cd, coa_name, leaf_flag, parent_coa_cd FROM almt_coa_info")
            all_coa = cursor.fetchall()
            str_cols = ', '.join([f'strategy_m{i}' for i in range(1, 25)])
            cursor.execute(f"SELECT coa_cd, {str_cols} FROM almt_param_custom_strategy")
            strats = cursor.fetchall()
            cursor.execute("SELECT curve_id, current_curve_value FROM almt_param_rate_scenario WHERE current_curve_value IS NOT NULL LIMIT 1")
            curve = cursor.fetchone()

        from almt_app.api.param import build_tree_from_coa
        tree = build_tree_from_coa(all_coa, {})

        bal_map, avg_map, ins_map = {}, {}, {}
        for p in positions:
            cd = p.get('coa_lvl') or ''
            bal_map[cd] = bal_map.get(cd, 0) + _to_float(p['balance'])
            avg_map[cd] = avg_map.get(cd, 0) + _to_float(p['average_balance'])
            ins_map[cd] = ins_map.get(cd, 0) + _to_float(p['rate'])

        curve_val = _to_float(curve['current_curve_value']) if curve else 0.025

        strat_map = {}
        for r in strats:
            s = [_to_float(r[f'strategy_m{i}']) for i in range(1, 25)]
            strat_map[r['coa_cd']] = s

        def dfs(node):
            cd = node.get('coa_cd', '')
            cur_bal = bal_map.get(cd, 0)
            cur_avg = avg_map.get(cd, 0)
            cur_ins = ins_map.get(cd, 0)
            sp = strat_map.get(cd, [0]*24)

            child_seq = []
            for c in node.get('children') or []:
                child_seq.append(dfs(c))

            cur_yield = (cur_ins * 12) / cur_avg * 100 if cur_avg else 0
            cur_bal_total = cur_bal + sum([s[0] for s in child_seq])
            cur_avg_total = cur_avg + sum([s[1] for s in child_seq])
            cur_ins_total = cur_ins + sum([s[2] for s in child_seq])
            cur_yield_total = (cur_ins_total * 12) / cur_avg_total * 100 if cur_avg_total else 0

            m_flat = [round(cur_yield_total, 4), round(curve_val*100, 4)]
            for i in range(24):
                adjust_bp = sp[i]
                final_pct = cur_yield_total + adjust_bp * 0.0001 * 100
                m_flat.extend([
                    round(cur_yield_total, 4),
                    round(curve_val*100, 4),
                    0,
                    round(adjust_bp, 2),
                    round(final_pct, 4)
                ])
            node['m_values'] = m_flat
            node['has_data'] = (cur_bal_total != 0 or cur_ins_total != 0)
            return cur_bal_total, cur_avg_total, cur_ins_total

        for root in tree:
            dfs(root)
        _attach_level_and_meta(tree)
        return tree
    finally:
        conn.close()
#!/usr/bin/env python3
"""
给父节点（L1/L2/L3）的 rate_pct 计算基于子账户加权平均的合理利率，生成 SQL。
"""
import pymysql

DB_CFG = dict(
    host='127.0.0.1', port=3306,
    user='almd', password='Almd@2026',
    database='almt_db', charset='utf8mb4',
)


def main():
    conn = pymysql.connect(**DB_CFG)
    cur = conn.cursor()
    cur.execute('SELECT coa_lvl, coa_name, balance, rate_pct FROM almt_current_position')
    all_accounts = {row[0]: {'name': row[1], 'balance': row[2], 'rate_pct': row[3]}
                    for row in cur.fetchall()}
    cur.close()
    conn.close()

    # 找出所有父节点
    parent_candidates = set()
    for lvl in all_accounts:
        for other in all_accounts:
            if lvl != other and other.startswith(lvl + '_'):
                if all_accounts[other]['balance'] is not None:
                    parent_candidates.add(lvl)
                    break

    # 计算加权平均利率（仅使用直接子节点的 balance × rate_pct）
    updates = []
    for parent in sorted(parent_candidates):
        parent_data = all_accounts[parent]
        if parent_data['balance'] is None:
            continue
        total_weighted = 0.0
        total_balance = 0.0
        for lvl, data in all_accounts.items():
            if lvl == parent or not lvl.startswith(parent + '_'):
                continue
            suffix = lvl[len(parent) + 1:]
            if '_' in suffix:
                continue  # 非直接子节点
            if data['balance'] and data['rate_pct']:
                total_weighted += float(data['balance']) * float(data['rate_pct'])
                total_balance += float(data['balance'])

        if total_balance > 0:
            avg_rate = total_weighted / total_balance
            # 限幅到 [0, 30%] 合理范围
            avg_rate = max(0.0, min(0.30, avg_rate))
            updates.append((parent, round(avg_rate, 6), parent_data['name'][:30]))

    print('-- 父节点加权平均利率（基于直接子账户的 balance × rate_pct）')
    print('-- 生成时间: 2026-09-15')
    print(f'-- 计划更新 {len(updates)} 个父节点')
    print()
    for parent, rate, name in updates:
        print(f"UPDATE almt_current_position SET rate_pct = {rate} WHERE coa_lvl = '{parent}';  -- {name}")


if __name__ == '__main__':
    main()

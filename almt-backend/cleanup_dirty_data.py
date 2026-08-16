"""
结果集脏数据清理脚本

清理对象：
  1. calc_version=NULL 的旧任务（schema 升级前生成的，不属于新版本管理体系）
  2. 孤儿结果数据（task_id 在 result 表但不在 task 表）

执行：
    python cleanup_dirty_data.py              # 默认 dry-run 模式（只显示不执行）
    python cleanup_dirty_data.py --execute    # 实际清理

清理前会自动备份 task_id 列表到 cleanup_<TIMESTAMP>_backup.csv
"""
import argparse
import csv
import os
import sys
from datetime import datetime

import pymysql

DB_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'almt', 'password': 'almt',
    'database': 'almt_db', 'charset': 'utf8mb4', 'cursorclass': pymysql.cursors.DictCursor
}


def scan():
    """扫描脏数据"""
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # 1. 旧任务（无版本号）
            cursor.execute(
                "SELECT task_id, data_date, status, started_at FROM almt_calculate_task WHERE calc_version IS NULL"
            )
            old_tasks = cursor.fetchall()

            # 2. 孤儿指标
            cursor.execute(
                "SELECT task_id, COUNT(*) AS cnt FROM almt_result_index "
                "WHERE task_id NOT IN (SELECT task_id FROM almt_calculate_task) "
                "GROUP BY task_id"
            )
            orphan_index = cursor.fetchall()

            # 3. 孤儿计划
            cursor.execute(
                "SELECT task_id, COUNT(*) AS cnt FROM almt_result_plan "
                "WHERE task_id NOT IN (SELECT task_id FROM almt_calculate_task) "
                "GROUP BY task_id"
            )
            orphan_plan = cursor.fetchall()

            # 4. 每个旧任务的结果统计
            task_stats = {}
            for t in old_tasks:
                cursor.execute("SELECT COUNT(*) AS c FROM almt_result_index WHERE task_id=%s", (t['task_id'],))
                task_stats[t['task_id']] = {'idx': cursor.fetchone()['c'], 'plan': 0}
                cursor.execute("SELECT COUNT(*) AS c FROM almt_result_plan WHERE task_id=%s", (t['task_id'],))
                task_stats[t['task_id']]['plan'] = cursor.fetchone()['c']

        return {
            'old_tasks': old_tasks,
            'task_stats': task_stats,
            'orphan_index': orphan_index,
            'orphan_plan': orphan_plan,
        }
    finally:
        conn.close()


def cleanup(dry_run=True, backup_dir='reports'):
    """执行清理"""
    scan_result = scan()

    old_tasks = scan_result['old_tasks']
    task_stats = scan_result['task_stats']
    orphan_index = scan_result['orphan_index']
    orphan_plan = scan_result['orphan_plan']

    old_task_ids = [t['task_id'] for t in old_tasks]
    orphan_task_ids = list({r['task_id'] for r in orphan_index} | {r['task_id'] for r in orphan_plan})
    all_to_delete = list(set(old_task_ids + orphan_task_ids))

    total_idx = sum(task_stats[tid]['idx'] for tid in old_task_ids if tid in task_stats)
    total_plan = sum(task_stats[tid]['plan'] for tid in old_task_ids if tid in task_stats)
    total_idx += sum(r['cnt'] for r in orphan_index)
    total_plan += sum(r['cnt'] for r in orphan_plan)

    print('=' * 70)
    print(f' 脏数据清理 {"（预览模式）" if dry_run else "（执行模式）"}')
    print(f' 时间: {datetime.now().isoformat(timespec="seconds")}')
    print('=' * 70)
    print()
    print(f' 旧任务（calc_version=NULL）: {len(old_tasks)} 个')
    print(f' 孤儿任务（task_id 孤儿）: {len(orphan_task_ids)} 个')
    print(f' 将删除任务总数: {len(all_to_delete)}')
    print(f' 将删除指标记录: {total_idx} 条')
    print(f' 将删除计划记录: {total_plan} 条')
    print()

    if not all_to_delete:
        print('✅ 没有脏数据，无需清理')
        return

    print('--- 待删除的旧任务 ---')
    for t in old_tasks:
        stats = task_stats.get(t['task_id'], {'idx': 0, 'plan': 0})
        print(f'  {t["task_id"][:13]}...  {t["data_date"]}  {t["status"]:8s}  指标={stats["idx"]:4d}  计划={stats["plan"]:4d}')
    if orphan_task_ids:
        print('--- 待删除的孤儿 ---')
        for tid in orphan_task_ids:
            print(f'  {tid}')

    if dry_run:
        print()
        print('⚠️ 这是预览模式，没有实际删除。执行：python cleanup_dirty_data.py --execute')
        return

    # 备份
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'cleanup_{ts}_backup.csv')
    with open(backup_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['task_id', 'data_date', 'status', 'started_at'])
        for t in old_tasks:
            writer.writerow([t['task_id'], t['data_date'], t['status'], t['started_at']])
    print(f'\n📄 备份已保存: {backup_path}')

    # 执行删除
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # 1. 删除结果表
            placeholders = ','.join(['%s'] * len(all_to_delete))
            cursor.execute(
                f"DELETE FROM almt_result_index WHERE task_id IN ({placeholders})",
                tuple(all_to_delete)
            )
            deleted_idx = cursor.rowcount
            cursor.execute(
                f"DELETE FROM almt_result_plan WHERE task_id IN ({placeholders})",
                tuple(all_to_delete)
            )
            deleted_plan = cursor.rowcount

            # 2. 删除任务记录
            cursor.execute(
                "DELETE FROM almt_calculate_task WHERE calc_version IS NULL OR task_id IN ({})".format(placeholders),
                tuple(all_to_delete)
            )
            deleted_task = cursor.rowcount

        conn.commit()

        print()
        print('=' * 70)
        print(' ✅ 清理完成！')
        print('=' * 70)
        print(f'   删除任务记录: {deleted_task} 条')
        print(f'   删除指标记录: {deleted_idx} 条')
        print(f'   删除计划记录: {deleted_plan} 条')
    except Exception as e:
        conn.rollback()
        print(f'\n[FAIL] {e}')
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='清理结果集脏数据')
    parser.add_argument('--execute', action='store_true', help='实际执行清理（默认预览）')
    parser.add_argument('--backup-dir', default='reports', help='备份目录')
    args = parser.parse_args()

    cleanup(dry_run=not args.execute, backup_dir=args.backup_dir)
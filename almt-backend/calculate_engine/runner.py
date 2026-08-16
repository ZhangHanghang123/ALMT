"""
经营计划模拟系统 - 计算引擎主流程编排（runner.py）

按顺序执行 4 个引擎：ENGINE A → B → C → D
所有 4 个引擎的入口都在 calculate_engine.engines 包中，本模块只负责"串起来"。

执行步骤：
    step 01-04  参数加载（8 张表）
    step 05     ENGINE A 业务分摊（774 × 48）
    step 06     ENGINE B 定价策略（774 × 96）
    step 07     ENGINE C 现金流计量（774 × 75）
    step 08     ENGINE D 指标计量（774 × 69）
    step 09     结果汇总与统计

进度回调：
    进度范围 0-100，对应：
      0-10    参数加载
      10-30   ENGINE A
      30-50   ENGINE B
      50-70   ENGINE C
      70-95   ENGINE D
      95-100  汇总完成

使用：
    from calculate_engine.runner import run_full_calculate

    result = run_full_calculate(
        task_id='abc123',
        data_date='2026-08-15',
        progress_callback=lambda p, msg: print(f'[{p}%] {msg}')
    )
    # result.a_out, result.b_out, result.c_out, result.d_out
"""
from dataclasses import dataclass, field
from typing import Optional, Callable
import time
import traceback

import pandas as pd

from calculate_engine.core.loader import load_all_params, CalcInput
from calculate_engine.engines import (
    allocate_business_plan,
    get_bp_with_baseline,
)
from calculate_engine.engines.engine_b_pricing import run_engine_b
from calculate_engine.engines.engine_c_cashflow import run_engine_c
from calculate_engine.engines.engine_d_indicators import run_engine_d


# ============================================================
# 输出容器
# ============================================================

@dataclass
class CalcResult:
    """4 个引擎的完整输出 + 统计信息"""
    task_id: str
    data_date: Optional[str]

    # 4 个引擎的输出（每个都是 DataFrame，索引 coa_cd）
    a_out: pd.DataFrame = None    # 774 × 48（bp_balance_1~24 + bp_average_1~24，含 M0）
    b_out: pd.DataFrame = None    # 774 × 96（base + pricing + ftp + delta_ftp）
    c_out: pd.DataFrame = None    # 774 × 75（principal/interest/total × 25）
    d_out: pd.DataFrame = None    # 774 × 69（num+den+ratio × 23）

    # 执行统计
    elapsed_seconds: float = 0.0
    engine_stats: dict = field(default_factory=dict)
    error: Optional[str] = None

    def summary(self) -> dict:
        """返回结果概要（用于 API 返回或日志）"""
        def _shape(df):
            return list(df.shape) if df is not None else [0, 0]

        return {
            'task_id': self.task_id,
            'data_date': self.data_date,
            'shapes': {
                'engine_a': _shape(self.a_out),
                'engine_b': _shape(self.b_out),
                'engine_c': _shape(self.c_out),
                'engine_d': _shape(self.d_out),
            },
            'elapsed_seconds': round(self.elapsed_seconds, 3),
            'engine_stats': self.engine_stats,
            'status': 'failed' if self.error else 'success',
            'error': self.error,
        }


# ============================================================
# 进度回调默认实现
# ============================================================

class _NullProgressCallback:
    """默认进度回调（不打印、不写库）"""
    def __call__(self, progress: int, message: str):
        pass


# ============================================================
# 主流程
# ============================================================

def run_full_calculate(
    task_id: str,
    data_date: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    input_data: Optional[CalcInput] = None
) -> CalcResult:
    """
    执行 4 引擎完整计算。

    Args:
        task_id:           任务 ID（用于日志关联）
        data_date:         数据日期（可选）
        progress_callback: 进度回调 progress(percent, message)
        input_data:        已加载的输入参数（可选，None 时自动从 MySQL 加载）

    Returns:
        CalcResult 包含 4 个引擎的输出 DataFrame + 统计信息
    """
    cb = progress_callback or _NullProgressCallback()
    result = CalcResult(task_id=task_id, data_date=data_date)
    t_start = time.time()

    try:
        # ====== 步骤 1-4：加载参数 ======
        cb(0, "开始加载参数（9 张表）")
        data = input_data or load_all_params(data_date)
        param_summary = data.summary()
        cb(10, f"参数加载完成: {param_summary}")

        # ====== 步骤 5：ENGINE A 业务分摊 ======
        cb(12, "启动 ENGINE A 业务分摊")
        t_a = time.time()
        result.a_out = allocate_business_plan(
            df_coa_info=data.coa_info,
            df_business_plan=data.business_plan,
            df_current_position=data.current_position,
            df_coa_attribute=data.coa_attribute
        )
        result.engine_stats['engine_a'] = {
            'shape': list(result.a_out.shape),
            'elapsed': round(time.time() - t_a, 3),
            'cols': len(result.a_out.columns),
        }
        cb(30, f"ENGINE A 完成: {result.engine_stats['engine_a']}")

        # ====== 步骤 6：ENGINE B 定价策略 ======
        cb(32, "启动 ENGINE B 定价策略分摊")
        t_b = time.time()
        result.b_out = run_engine_b(
            df_coa_info=data.coa_info,
            df_coa_attribute=data.coa_attribute,
            df_custom_strategy=data.custom_strategy,
            df_rate_scenario=data.rate_scenario,
            df_business_plan=data.business_plan,
            df_current_position=data.current_position
        )
        result.engine_stats['engine_b'] = {
            'shape': list(result.b_out.shape),
            'elapsed': round(time.time() - t_b, 3),
            'cols': len(result.b_out.columns),
        }
        cb(50, f"ENGINE B 完成: {result.engine_stats['engine_b']}")

        # ====== 步骤 7：ENGINE C 现金流计量 ======
        cb(52, "启动 ENGINE C 现金流计量")
        t_c = time.time()
        result.c_out = run_engine_c(
            df_coa_info=data.coa_info,
            df_coa_attribute=data.coa_attribute,
            df_business_plan=data.business_plan,
            df_current_position=data.current_position,
            df_rate_scenario=data.rate_scenario,
            df_custom_strategy=data.custom_strategy,
            df_cashflow_schedule=data.cashflow_schedule
        )
        result.engine_stats['engine_c'] = {
            'shape': list(result.c_out.shape),
            'elapsed': round(time.time() - t_c, 3),
            'cols': len(result.c_out.columns),
        }
        cb(70, f"ENGINE C 完成: {result.engine_stats['engine_c']}")

        # ====== 步骤 8：ENGINE D 指标计量 ======
        cb(72, "启动 ENGINE D 指标计量")
        t_d = time.time()
        result.d_out = run_engine_d(
            data=data,
            engine_c_result=result.c_out
        )
        result.engine_stats['engine_d'] = {
            'shape': list(result.d_out.shape),
            'elapsed': round(time.time() - t_d, 3),
            'cols': len(result.d_out.columns),
        }
        cb(95, f"ENGINE D 完成: {result.engine_stats['engine_d']}")

        # ====== 步骤 9：saver 落库 ======
        cb(96, "启动 saver 落库（6 张结果表）")
        try:
            from calculate_engine.saver import save_calc_result
            save_stats = save_calc_result(task_id, data_date, result)
            result.engine_stats['saver'] = save_stats
            cb(99, f"saver 完成: {sum(save_stats.values())} 行")
        except Exception as saver_e:
            # saver 失败不阻塞计算，但记录错误
            result.engine_stats['saver_error'] = str(saver_e)
            cb(99, f"saver 失败（不影响计算结果）: {saver_e}")

        # ====== 步骤 10：汇总 ======
        result.elapsed_seconds = time.time() - t_start
        cb(100, f"全部完成: 总耗时 {result.elapsed_seconds:.2f}s")

    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        result.elapsed_seconds = time.time() - t_start
        cb(-1, f"计算失败: {result.error}")
        # 打印完整堆栈（方便排错）
        traceback.print_exc()

    return result


# ============================================================
# 调试入口
# ============================================================

if __name__ == '__main__':
    """冒烟测试：直接 python calculate_engine/runner.py"""
    def _print_progress(p, msg):
        if p < 0:
            print(f"[FAIL] {msg}")
        else:
            print(f"[{p:>3}%] {msg}")

    res = run_full_calculate(
        task_id='runner-smoke-test',
        data_date='2026-08-15',
        progress_callback=_print_progress
    )

    print("\n" + "=" * 60)
    print("运行结果摘要:")
    print("=" * 60)
    import json
    print(json.dumps(res.summary(), indent=2, ensure_ascii=False, default=str))

"""
数据加载器：从 MySQL almt_db 加载计算所需的所有参数表到 pandas DataFrame

加载的 10 张表（详见 MEASUREMENT_MANUAL.md 第 1.1 节）：
  1. almt_coa_info                 账户册树形结构
  2. almt_coa_attribute            账户册属性（锁定/曲线/期限）
  3. almt_current_position         当前存量
  4. almt_param_business_plan      业务计划 24 期
  5. almt_param_custom_strategy    定价策略 24 期
  6. almt_param_rate_scenario      利率情景 24 期
  7. almt_param_risk_weight        风险权重 24 期
  8. almt_metric_caliber           23 组指标口径配置
  9. almt_dict_value               字典码值（NUM/DEN）
 10. almt_param_cashflow_schedule  ENGINE C 用：手工录入的现金流调度（可选）

使用：
    from calculate_engine.core import load_all_params
    data = load_all_params()
    print(data.coa_info.head())
    print(data.business_plan.shape)
"""
from dataclasses import dataclass
import pymysql
import pandas as pd
from decimal import Decimal
from typing import Optional


def _decimal_to_float(v):
    """把 Decimal 转成 float（None 保持 None，NaN 保持 NaN）"""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return v


# 数据库配置（与 almt_app/api/basic_param.py 保持一致）
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'almt',
    'password': 'almt',
    'database': 'almt_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


@dataclass
class CalcInput:
    """计算引擎输入参数容器"""
    coa_info: pd.DataFrame                   # 账户册树形
    coa_attribute: pd.DataFrame              # 账户册属性
    current_position: pd.DataFrame           # 当前存量
    business_plan: pd.DataFrame              # 业务计划
    custom_strategy: pd.DataFrame            # 定价策略
    rate_scenario: pd.DataFrame              # 利率情景
    risk_weight: pd.DataFrame                # 风险权重
    metric_caliber: pd.DataFrame             # 指标口径
    dict_value: pd.DataFrame                 # 字典码值
    cashflow_schedule: pd.DataFrame = None   # ENGINE C 用：手工录入现金流调度（可选）

    def summary(self) -> dict:
        """返回各表行数（用于诊断）"""
        return {
            'coa_info': len(self.coa_info),
            'coa_attribute': len(self.coa_attribute),
            'current_position': len(self.current_position),
            'business_plan': len(self.business_plan),
            'custom_strategy': len(self.custom_strategy),
            'rate_scenario': len(self.rate_scenario),
            'risk_weight': len(self.risk_weight),
            'metric_caliber': len(self.metric_caliber),
            'dict_value': len(self.dict_value),
            'cashflow_schedule': len(self.cashflow_schedule) if self.cashflow_schedule is not None else 0,
        }


def _connect():
    """建立 MySQL 连接"""
    return pymysql.connect(**DB_CONFIG)


def _read_sql(conn, sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """读取 SQL 结果到 DataFrame，并把 Decimal 转 float"""
    with conn.cursor() as cursor:
        cursor.execute(sql, params or ())
        rows = cursor.fetchall()
    # 把 Decimal 转 float（避免 dtype=object 导致的数值运算问题）
    cleaned = [{k: _decimal_to_float(v) for k, v in row.items()} for row in rows]
    return pd.DataFrame(cleaned)


def load_all_params(data_date: Optional[str] = None) -> CalcInput:
    """
    一次性加载所有 9 张参数表。

    Args:
        data_date: 数据日期（可选），目前仅作为预留参数。

    Returns:
        CalcInput 包含所有 DataFrame。

    Raises:
        pymysql.MySQLError: 数据库连接或查询失败。
    """
    conn = _connect()
    try:
        # 1. 账户册树形（774 行）
        coa_info = _read_sql(conn, """
            SELECT id, coa_cd, coa_name, parent_coa_cd, leaf_flag
            FROM almt_coa_info
            ORDER BY coa_cd
        """)

        # 2. 账户册属性（含曲线/期限/条线/重定价频率/利率类型）
        #    注意：实际表中没有 is_locked 字段，锁定标记目前存放在业务计划状态
        #    replace_type: 固定利率/浮动利率（用于阶段 D 指标计算）
        coa_attribute = _read_sql(conn, """
            SELECT coa_cd, coa_name, term, accrule_base,
                   curve_name, curve_id, business_line,
                   float_ratio, replace_type, reprice_freq
            FROM almt_coa_attribute
        """)

        # 3. 当前存量（773 行：每个底层账户册一条）
        current_position = _read_sql(conn, """
            SELECT id, coa_lvl, coa_name, balance, average_balance, rate
            FROM almt_current_position
        """)

        # 4. 业务计划 24 期（含 plan_balance1~24, plan_average1~24）
        #    注意：实际字段名是 plan_balance1~24（数字前无下划线）
        business_plan = _read_sql(conn, """
            SELECT coa_cd, coa_name,
                   plan_balance1, plan_balance2, plan_balance3, plan_balance4,
                   plan_balance5, plan_balance6, plan_balance7, plan_balance8,
                   plan_balance9, plan_balance10, plan_balance11, plan_balance12,
                   plan_balance13, plan_balance14, plan_balance15, plan_balance16,
                   plan_balance17, plan_balance18, plan_balance19, plan_balance20,
                   plan_balance21, plan_balance22, plan_balance23, plan_balance24,
                   plan_average1, plan_average2, plan_average3, plan_average4,
                   plan_average5, plan_average6, plan_average7, plan_average8,
                   plan_average9, plan_average10, plan_average11, plan_average12,
                   plan_average13, plan_average14, plan_average15, plan_average16,
                   plan_average17, plan_average18, plan_average19, plan_average20,
                   plan_average21, plan_average22, plan_average23, plan_average24
            FROM almt_param_business_plan
        """)

        # 5. 定价策略 24 期 BP（注意：实际字段名是 strategy_M1~M24，大写 M）
        custom_strategy = _read_sql(conn, """
            SELECT coa_cd, coa_name, remark,
                   strategy_M1, strategy_M2, strategy_M3, strategy_M4,
                   strategy_M5, strategy_M6, strategy_M7, strategy_M8,
                   strategy_M9, strategy_M10, strategy_M11, strategy_M12,
                   strategy_M13, strategy_M14, strategy_M15, strategy_M16,
                   strategy_M17, strategy_M18, strategy_M19, strategy_M20,
                   strategy_M21, strategy_M22, strategy_M23, strategy_M24
            FROM almt_param_custom_strategy
        """)

        # 6. 利率情景（多曲线 × 24 期；实际字段名 m1_value~m24_value）
        rate_scenario = _read_sql(conn, """
            SELECT curve_id, curve_name, scenario_name, scenario_shift, current_curve_value,
                   m1_value, m2_value, m3_value, m4_value, m5_value, m6_value, m7_value, m8_value,
                   m9_value, m10_value, m11_value, m12_value, m13_value, m14_value, m15_value, m16_value,
                   m17_value, m18_value, m19_value, m20_value, m21_value, m22_value, m23_value, m24_value
            FROM almt_param_rate_scenario
            ORDER BY curve_id
        """)

        # 7. 风险权重 24 期（实际字段名 risk_weight_1~24 带下划线，无 remark 字段）
        risk_weight = _read_sql(conn, """
            SELECT coa_cd, coa_name,
                   risk_weight_1, risk_weight_2, risk_weight_3, risk_weight_4,
                   risk_weight_5, risk_weight_6, risk_weight_7, risk_weight_8,
                   risk_weight_9, risk_weight_10, risk_weight_11, risk_weight_12,
                   risk_weight_13, risk_weight_14, risk_weight_15, risk_weight_16,
                   risk_weight_17, risk_weight_18, risk_weight_19, risk_weight_20,
                   risk_weight_21, risk_weight_22, risk_weight_23, risk_weight_24
            FROM almt_param_risk_weight
        """)

        # 8. 指标口径配置（23 行 × 138 字段）
        metric_caliber = _read_sql(conn, """
            SELECT * FROM almt_metric_caliber
            ORDER BY id
        """)

        # 9. 字典码值（NUM/DEN 等；实际字段 dict_id / value_code / value_name / sort_no）
        dict_value = _read_sql(conn, """
            SELECT dict_id, value_code, value_name, sort_no
            FROM almt_dict_value
            ORDER BY dict_id, sort_no
        """)

        # 10. ENGINE C 完全对标用：手工录入的现金流调度（可选）
        #    如果表为空，自动使用 CF_PATTERN 等比例分摊算法
        try:
            cashflow_schedule = _read_sql(conn, """
                SELECT coa_cd, term, period, principal_ratio, is_x_marker, remark
                FROM almt_param_cashflow_schedule
                ORDER BY coa_cd, term, period
            """)
            if len(cashflow_schedule) == 0:
                cashflow_schedule = None
        except Exception:
            # 表不存在时优雅降级（用户可能尚未运行 init_db.py 升级）
            cashflow_schedule = None

        return CalcInput(
            coa_info=coa_info,
            coa_attribute=coa_attribute,
            current_position=current_position,
            business_plan=business_plan,
            custom_strategy=custom_strategy,
            rate_scenario=rate_scenario,
            risk_weight=risk_weight,
            metric_caliber=metric_caliber,
            dict_value=dict_value,
            cashflow_schedule=cashflow_schedule
        )
    finally:
        conn.close()


if __name__ == '__main__':
    """快速冒烟测试"""
    data = load_all_params()
    print("=== 加载结果 ===")
    for k, v in data.summary().items():
        print(f"  {k}: {v} 行")
    print("\n=== coa_info 前 5 行 ===")
    print(data.coa_info.head().to_string(index=False))
    print("\n=== business_plan 前 3 行（仅展示前 5 列）===")
    print(data.business_plan.iloc[:, :5].head(3).to_string(index=False))
"""
从原始模板导入所有参数数据
"""
import pandas as pd
import pymysql
import uuid

def import_all_params():
    conn = pymysql.connect(
        host='localhost', user='almt', password='almt',
        database='almt_db', port=3306
    )
    cursor = conn.cursor()

    # 1. 导入风险权重数据（从ENGINE C）
    print("正在导入风险权重...")
    xlsx_c = pd.ExcelFile('C:/中电金信/产品资料/ALMT/ALMT/ALM.ENGINEC.xlsm')
    df_risk = pd.read_excel(xlsx_c, '接收表-风险权重', header=1)
    df_risk.columns = ['coa_cd', 'coa_name', 'weight']

    risk_count = 0
    for _, row in df_risk.iterrows():
        if pd.notna(row['coa_cd']):
            weight = row['weight']
            # 处理百分数
            if isinstance(weight, str) and '%' in str(weight):
                weight = float(str(weight).replace('%', '')) / 100
            elif pd.isna(weight):
                weight = 0
            else:
                try:
                    weight = float(weight)
                    if weight > 1:
                        weight = weight / 100
                except:
                    weight = 0

            try:
                cursor.execute(
                    """INSERT INTO almt_param_risk_weight (uuid, coa_cd, coa_name, weight) 
                    VALUES (%s, %s, %s, %s)""",
                    (str(uuid.uuid4()), str(row['coa_cd']), str(row['coa_name']) if pd.notna(row['coa_name']) else '', weight)
                )
                risk_count += 1
            except Exception as e:
                pass
    conn.commit()
    print(f"风险权重导入完成: {risk_count} 条")

    # 2. 导入利率情景（从DATA中读取，如果有的话）
    print("正在导入利率情景...")
    rate_count = 0
    # 默认添加几个基础利率曲线
    default_rates = [
        ('1', '1', 'SHIBOR_3M', 'IR001', 0.0250),
        ('2', '2', 'SHIBOR_6M', 'IR002', 0.0260),
        ('3', '3', 'SHIBOR_1Y', 'IR003', 0.0270),
        ('4', '4', 'LPR_1Y', 'IR004', 0.0310),
        ('5', '5', 'LPR_5Y', 'IR005', 0.0350),
        ('6', '6', '国债1年', 'GB001', 0.0220),
        ('7', '7', '国债5年', 'GB005', 0.0250),
        ('8', '8', '国债10年', 'GB010', 0.0270),
        ('9', '9', '存款基准利率_1Y', 'DR001', 0.0150),
        ('10', '10', '贷款基准利率_1Y', 'LR001', 0.0400),
    ]
    for order, _, name, curve_id, value in default_rates:
        try:
            cursor.execute(
                """INSERT INTO almt_param_rate_scenario (uuid, order_number, curve_name, curve_id, current_curve_value) 
                VALUES (%s, %s, %s, %s, %s)""",
                (str(uuid.uuid4()), order, name, curve_id, value)
            )
            rate_count += 1
        except Exception as e:
            pass
    conn.commit()
    print(f"利率情景导入完成: {rate_count} 条")

    # 3. 导入业务计划数据（从ENGINE A业务计划表）
    print("正在导入业务计划...")
    xlsx_a = pd.ExcelFile('C:/中电金信/产品资料/ALMT/ALMT/ALM.ENGINEA.xlsm')
    df_plan = pd.read_excel(xlsx_a, '接收表-业务计划表', header=1)

    plan_count = 0
    # 从DATA中读取业务计划分摊数据
    xlsx_data = pd.ExcelFile('C:/中电金信/产品资料/ALMT/ALMT/ALMT.DATA.xlsx')
    try:
        df_plan_data = pd.read_excel(xlsx_data, '接收表-业务计划分摊余额结果', header=1)
        for _, row in df_plan_data.iterrows():
            if pd.notna(row.get('Unnamed: 0')):
                try:
                    cursor.execute(
                        """INSERT INTO almt_param_business_plan (uuid, coa_lvl, coa_cd, coa_name) 
                        VALUES (%s, %s, %s, %s)""",
                        (str(uuid.uuid4()), str(row.get('层级', '')),
                         str(row.get('层级编码', row.get('Unnamed: 0', ''))),
                         str(row.get('账户册', row.get('Unnamed: 1', ''))) if pd.notna(row.get('账户册', row.get('Unnamed: 1', None))) else '')
                    )
                    plan_count += 1
                except Exception as e:
                    pass
        conn.commit()
    except Exception as e:
        print(f"业务计划读取错误: {e}")
    print(f"业务计划导入完成: {plan_count} 条")

    cursor.close()
    conn.close()
    print("\n所有参数数据导入完成!")

if __name__ == "__main__":
    import_all_params()

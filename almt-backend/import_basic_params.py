import pymysql
import pandas as pd
import uuid
from datetime import datetime

conn = pymysql.connect(host='localhost', user='almt', password='almt', database='almt_db', port=3306)
cursor = conn.cursor()

# 1. 时间步数据
xlsx = pd.ExcelFile('C:/中电金信/产品资料/ALMT/ALMT/ALMT.DATA.xlsx')
df_step = pd.read_excel(xlsx, '接收表-业务存续期', header=1)
print('时间步sheet形状:', df_step.shape)

cursor.execute('DELETE FROM almt_time_step')
months_end = df_step.iloc[0, 1:25].tolist()
month_days = df_step.iloc[1, 1:25].tolist()
year_days = df_step.iloc[2, 1:25].tolist()

for i in range(24):
    step_no = i + 1
    month_label = 'M' + str(i+1)
    month_end = months_end[i]
    md = month_days[i]
    yd = year_days[i]
    if pd.notna(month_end):
        if isinstance(month_end, str):
            end_date = month_end
        else:
            end_date = month_end.strftime('%Y-%m-%d')
        cursor.execute(
            'INSERT INTO almt_time_step (step_no, month_label, month_end_date, month_days, year_days) VALUES (%s, %s, %s, %s, %s)',
            (step_no, month_label, end_date, int(md) if pd.notna(md) else 30, int(yd) if pd.notna(yd) else 365)
        )

conn.commit()
print('[OK] 时间步导入完成')

# 2. 账户册属性
df_attr = pd.read_excel(xlsx, '接收表-底层账户册及属性配置', header=1)
print('账户册属性sheet形状:', df_attr.shape)

cursor.execute('DELETE FROM almt_coa_attribute')
attr_count = 0
for _, row in df_attr.iterrows():
    coa_cd = str(row['Unnamed: 1']) if pd.notna(row['Unnamed: 1']) else ''
    coa_name = str(row['Unnamed: 2']) if pd.notna(row['Unnamed: 2']) else ''
    term = str(row['Unnamed: 3']) if pd.notna(row['Unnamed: 3']) else ''
    accrual = str(row['Unnamed: 4']) if pd.notna(row['Unnamed: 4']) else ''
    curve_name = str(row['Unnamed: 5']) if pd.notna(row['Unnamed: 5']) else ''
    curve_id = str(row['Unnamed: 6']) if pd.notna(row['Unnamed: 6']) else ''
    biz_line = str(row['Unnamed: 7']) if pd.notna(row['Unnamed: 7']) else ''
    float_ratio = row['Unnamed: 8']
    reprice_type = str(row['Unnamed: 9']) if pd.notna(row['Unnamed: 9']) else ''
    reprice_freq = str(row['Unnamed: 10']) if pd.notna(row['Unnamed: 10']) else ''

    if not coa_cd or coa_cd == 'nan':
        continue

    try:
        cursor.execute('''
            INSERT INTO almt_coa_attribute
            (uuid, coa_cd, coa_name, term, accrule_base, curve_name, curve_id, business_line, float_ratio, replace_type, reprice_freq)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (str(uuid.uuid4()), coa_cd, coa_name, term, accrual, curve_name, curve_id, biz_line,
              float(float_ratio) if pd.notna(float_ratio) else None, reprice_type, reprice_freq))
        attr_count += 1
    except Exception as e:
        pass

conn.commit()
print('[OK] 账户册属性导入完成: ' + str(attr_count) + ' 条')

# 3. 报表口径
df_cal = pd.read_excel(xlsx, '接收表-指标口径配置', header=1)
print('指标口径sheet形状:', df_cal.shape)

cursor.execute('DELETE FROM almt_metric_caliber')
cal_count = 0
for _, row in df_cal.iterrows():
    coa_cd = str(row['Unnamed: 0']) if pd.notna(row['Unnamed: 0']) else ''
    coa_name = str(row['Unnamed: 1']) if pd.notna(row['Unnamed: 1']) else ''
    numerator = str(row['分子项目名称']) if pd.notna(row['分子项目名称']) else ''
    numerator_coef = row['系数']
    numerator_type = str(row['取数类型']) if pd.notna(row['取数类型']) else ''
    denominator = str(row['分母项目名称']) if pd.notna(row['分母项目名称']) else ''
    denominator_coef = row['系数.1']
    denominator_type = str(row['取数类型.1']) if pd.notna(row['取数类型.1']) else ''

    if not coa_cd or coa_cd == 'nan':
        continue

    try:
        cursor.execute('''
            INSERT INTO almt_metric_caliber
            (coa_cd, coa_name, numerator, numerator_coef, numerator_type, denominator, denominator_coef, denominator_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (coa_cd, coa_name, numerator,
              float(numerator_coef) if pd.notna(numerator_coef) else None,
              numerator_type,
              denominator,
              float(denominator_coef) if pd.notna(denominator_coef) else None,
              denominator_type))
        cal_count += 1
    except Exception as e:
        pass

conn.commit()
print('[OK] 报表口径导入完成: ' + str(cal_count) + ' 条')

cursor.close()
conn.close()
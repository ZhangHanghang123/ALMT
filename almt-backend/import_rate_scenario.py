import pymysql
import pandas as pd
import uuid

conn = pymysql.connect(host='localhost', user='almt', password='almt', database='almt_db', port=3306)
cursor = conn.cursor()

xlsx = pd.ExcelFile('C:/中电金信/产品资料/ALMT/ALMT/ALM.ENGINEB.xlsm')
df = pd.read_excel(xlsx, '接收表-利率情景假设', header=1)

cursor.execute('DELETE FROM almt_param_rate_scenario')
count = 0

for _, row in df.iterrows():
    order_no = int(row['Unnamed: 0']) if pd.notna(row['Unnamed: 0']) else None
    curve_name = str(row['Unnamed: 1']) if pd.notna(row['Unnamed: 1']) else ''
    curve_id = str(row['Unnamed: 2']) if pd.notna(row['Unnamed: 2']) else ''
    shift = row['Unnamed: 3']

    if not curve_name or curve_name == 'nan':
        continue

    # 根据shift值定义情景名称
    if pd.isna(shift):
        scenario_name = '基准'
        shift_val = 0.0
    elif shift >= 0.02:
        scenario_name = '上行' + str(int(shift * 10000)) + 'BP'
        shift_val = float(shift)
    elif shift <= -0.01:
        scenario_name = '下行' + str(abs(int(shift * 10000))) + 'BP'
        shift_val = float(shift)
    else:
        scenario_name = '情景' + str(int(shift * 10000)) + 'BP'
        shift_val = float(shift)

    # 当前曲线值（M1的值）
    current_val = row['M1'] if pd.notna(row['M1']) else None

    # 提取24个月利率值
    m_values = []
    for i in range(1, 25):
        v = row['M' + str(i)]
        m_values.append(float(v) if pd.notna(v) else None)

    try:
        cursor.execute('''
            INSERT INTO almt_param_rate_scenario
            (uuid, order_number, curve_name, curve_id, scenario_name, scenario_shift, current_curve_value,
             m1_value, m2_value, m3_value, m4_value, m5_value, m6_value, m7_value, m8_value,
             m9_value, m10_value, m11_value, m12_value, m13_value, m14_value, m15_value, m16_value,
             m17_value, m18_value, m19_value, m20_value, m21_value, m22_value, m23_value, m24_value)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', [str(uuid.uuid4()), order_no, curve_name, curve_id, scenario_name, shift_val, current_val] + m_values)
        count += 1
    except Exception as e:
        print('err ' + curve_name + ': ' + str(e))

conn.commit()
print('[OK] 利率情景导入完成: ' + str(count) + ' 条')

cursor.execute('SELECT scenario_name, COUNT(*) FROM almt_param_rate_scenario GROUP BY scenario_name')
print('\\n按情景分布:')
for r in cursor.fetchall():
    print('  ' + r[0] + ': ' + str(r[1]))

cursor.close()
conn.close()
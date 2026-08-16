"""
从原始Excel模板导入数据到数据库
"""
import pandas as pd
import pymysql
import uuid
from datetime import datetime

def import_data():
    # 连接数据库
    conn = pymysql.connect(
        host='localhost',
        user='almt',
        password='almt',
        database='almt_db',
        port=3306
    )
    cursor = conn.cursor()

    # 读取Excel文件
    xlsx = pd.ExcelFile('C:/中电金信/产品资料/ALMT/ALMT/ALMT.DATA.xlsx')

    # 1. 导入账户册层级
    print("正在导入账户册层级...")
    df_coa = pd.read_excel(xlsx, '接收表-账户册层级', header=1)
    df_coa.columns = ['order_number', 'lvl', 'parent_coa_cd', 'coa_cd', 'coa_name', 'leaf_desc', 'leaf_flag']
    
    coa_count = 0
    for _, row in df_coa.iterrows():
        if pd.notna(row['coa_cd']):
            uuid_val = str(uuid.uuid4())
            leaf = '1' if str(row['leaf_flag']) == '末级账户册' else '0'
            try:
                cursor.execute(
                    """INSERT INTO almt_coa_info (uuid, order_number, parent_coa_cd, coa_cd, coa_name, leaf_desc, leaf_flag) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (uuid_val, str(row['order_number']), str(row['parent_coa_cd']) if pd.notna(row['parent_coa_cd']) else None,
                     str(row['coa_cd']), str(row['coa_name']) if pd.notna(row['coa_name']) else None,
                     str(row['leaf_desc']) if pd.notna(row['leaf_desc']) else None, leaf)
                )
                coa_count += 1
            except Exception as e:
                pass
    conn.commit()
    print(f"账户册导入完成: {coa_count} 条")

    # 2. 导入存量数据
    print("正在导入存量数据...")
    df_position = pd.read_excel(xlsx, '接收表-存量数据情况表', header=1)
    
    pos_count = 0
    for _, row in df_position.iterrows():
        if pd.notna(row['Unnamed: 0']):
            uuid_val = str(uuid.uuid4())
            try:
                balance = float(row['Unnamed: 2']) if pd.notna(row['Unnamed: 2']) else 0
                cursor.execute(
                    """INSERT INTO almt_current_position (uuid, coa_lvl, coa_name, balance, average_balance, rate) 
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                    (uuid_val, str(row['Unnamed: 0']), str(row['Unnamed: 1']) if pd.notna(row['Unnamed: 1']) else None,
                     balance, 0, 0)
                )
                pos_count += 1
            except Exception as e:
                pass
    conn.commit()
    print(f"存量数据导入完成: {pos_count} 条")

    cursor.close()
    conn.close()
    print("\n数据导入完成!")

if __name__ == "__main__":
    import_data()

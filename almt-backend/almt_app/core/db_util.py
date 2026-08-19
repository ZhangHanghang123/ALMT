"""
ALMT 数据库连接工具（统一管理）

注意：所有 API 模块使用此工具创建连接，避免硬编码
"""
from urllib.parse import urlparse, unquote

import pymysql
from pymysql.cursors import DictCursor

from almt_app.core.config import settings


def get_db_conn():
    """获取 MySQL 数据库连接（读取 settings）

    优先用 DATABASE_URL_OVERRIDE（pymysql 兼容格式），否则从 MYSQL_* 字段构建
    """
    override = settings.DATABASE_URL_OVERRIDE
    if override:
        # 解析 mysql+pymysql://user:pass@host:port/db?charset=utf8mb4
        url = override.replace('mysql+pymysql://', 'mysql://')
        parsed = urlparse(url)
        conn_kwargs = {
            'host': parsed.hostname or '127.0.0.1',
            'port': parsed.port or 3306,
            'user': unquote(parsed.username or 'almd'),
            'password': unquote(parsed.password or ''),
            'database': (parsed.path or '/almt_db').lstrip('/').split('?')[0],
            'charset': 'utf8mb4',
            'cursorclass': DictCursor,
        }
    else:
        conn_kwargs = {
            'host': settings.MYSQL_HOST,
            'port': settings.MYSQL_PORT,
            'user': settings.MYSQL_USER,
            'password': settings.MYSQL_PASSWORD,
            'database': settings.MYSQL_DATABASE,
            'charset': 'utf8mb4',
            'cursorclass': DictCursor,
        }
    return pymysql.connect(**conn_kwargs)

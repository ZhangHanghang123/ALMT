"""
经营计划模拟系统 应用配置
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置"""

    # 应用配置
    APP_NAME: str = "经营计划模拟系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库连接 URL（支持环境变量直接配置，比 MYSQL_* 字段更灵活）
    DATABASE_URL_OVERRIDE: Optional[str] = None

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # 数据库配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "almt"
    MYSQL_PASSWORD: str = "almt"
    MYSQL_DATABASE: str = "almt_db"

    @property
    def DATABASE_URL(self) -> str:
        """数据库连接URL（优先用显式 DATABASE_URL_OVERRIDE，否则从 MYSQL_* 字段构建）"""
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    @property
    def REDIS_URL(self) -> str:
        """Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # JWT配置
    SECRET_KEY: str = "almt-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # Excel模型路径
    EXCEL_MODEL_PATH: str = "./models/ALMTCalculateEngine.xlsm"
    EXCEL_DATA_PATH: str = "./data"

    # Celery配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()

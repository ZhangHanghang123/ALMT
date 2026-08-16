"""
计算任务实体

版本管理：
  - calc_version：YYYYMMDD-XXXX 格式（如 20260816-0001）
    - 创建空版本时生成（不执行计算）
    - 执行计算时自动分配
    - 用户查询结果时按 calc_version 过滤
"""
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.sql import func
from almt_app.models.database import Base


class CalculateTask(Base):
    """计算任务表"""
    __tablename__ = "almt_calculate_task"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String(36), unique=True, nullable=False, index=True)
    calc_version = Column(String(20), nullable=True, index=True, comment="YYYYMMDD-XXXX")
    data_date = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending/running/completed/failed/success/empty
    progress = Column(Integer, nullable=True, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CalculateTask(task_id={self.task_id}, version={self.calc_version}, status={self.status})>"
"""
曲线定义实体
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Text
from sqlalchemy.sql import func
from almt_app.models.database import Base


class CurveDefinition(Base):
    """曲线定义表"""
    __tablename__ = "almt_curve_definition"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    curve_code = Column(String(50), nullable=False, index=True, comment="曲线代码")
    curve_name = Column(String(100), nullable=False, comment="曲线名称")
    curve_type = Column(String(50), nullable=True, comment="曲线类型: SHIBOR/国债/存贷/FTP等")
    currency = Column(String(10), nullable=True, default="CNY", comment="币种")
    description = Column(String(500), nullable=True, comment="曲线描述")
    is_active = Column(Integer, nullable=True, default=1, comment="是否启用: 0-禁用 1-启用")
    remark = Column(Text, nullable=True, comment="备注")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CurveDefinition(curve_code={self.curve_code}, curve_name={self.curve_name})>"

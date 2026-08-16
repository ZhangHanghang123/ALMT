"""
风险权重实体
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime
from sqlalchemy.sql import func
from almt_app.models.database import Base


class ParamRiskWeight(Base):
    """风险权重表"""
    __tablename__ = "almt_param_risk_weight"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    order_number = Column(String(50), nullable=True)
    coa_cd = Column(String(50), nullable=True)
    coa_name = Column(String(200), nullable=True)
    weight = Column(Numeric(10, 6), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ParamRiskWeight(coa_cd={self.coa_cd}, weight={self.weight})>"

"""
账户册属性实体
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Text
from sqlalchemy.sql import func
from almt_app.models.database import Base


class CoaAttribute(Base):
    """账户册属性表"""
    __tablename__ = "almt_coa_attribute"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    order_number = Column(String(50), nullable=True)
    coa_cd = Column(String(50), nullable=False, index=True)
    coa_name = Column(String(200), nullable=True)
    term = Column(String(50), nullable=True)
    accrule_base = Column(String(50), nullable=True)
    curve_name = Column(String(100), nullable=True)
    curve_id = Column(String(50), nullable=True)
    business_line = Column(String(100), nullable=True)
    float_ratio = Column(Numeric(10, 4), nullable=True)
    replace_type = Column(String(50), nullable=True)
    reprice_freq = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CoaAttribute(coa_cd={self.coa_cd}, coa_name={self.coa_name})>"

"""
账户册信息实体
"""
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from almt_app.models.database import Base


class CoaInfo(Base):
    """账户册信息表"""
    __tablename__ = "almt_coa_info"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    order_number = Column(String(50), nullable=True)
    parent_coa_cd = Column(String(50), nullable=True)
    coa_cd = Column(String(50), nullable=False)
    coa_name = Column(String(200), nullable=True)
    leaf_desc = Column(String(200), nullable=True)
    leaf_flag = Column(String(1), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CoaInfo(coa_cd={self.coa_cd}, coa_name={self.coa_name})>"

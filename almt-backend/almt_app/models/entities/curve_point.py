"""
曲线点定义实体
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from almt_app.models.database import Base


class CurvePoint(Base):
    """曲线点定义表"""
    __tablename__ = "almt_curve_point"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    curve_uuid = Column(String(36), ForeignKey('almt_curve_definition.uuid'), nullable=False, index=True, comment="曲线UUID")
    term = Column(String(20), nullable=False, comment="期限: 1D/7D/1M/3M/6M/1Y/2Y/3Y/5Y/7Y/10Y等")
    term_days = Column(Integer, nullable=True, comment="期限天数(用于排序)")
    rate_value = Column(Numeric(12, 6), nullable=True, comment="利率值(小数形式,如0.0325表示3.25%)")
    spread = Column(Numeric(12, 6), nullable=True, comment="利差(基点)")
    is_active = Column(Integer, nullable=True, default=1, comment="是否启用: 0-禁用 1-启用")
    remark = Column(String(500), nullable=True, comment="备注")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CurvePoint(curve_uuid={self.curve_uuid}, term={self.term}, rate_value={self.rate_value})>"

"""
现金流调度参数实体（ENGINE C 完全对标 Excel "标准化剩余本金表"）

每行代表某个账户册在某期限下、某期 period 的：
  - principal_ratio: 本金占比（占 M0 余额的比例）
  - is_x_marker: Excel 的 'x' 标记位（本期还清 + 计息）

注：手工录入数据，允许不规则的还本模式（如 6M: M4=0.5/M5=0.35/M6=0.3）。
"""
from sqlalchemy import Column, String, Integer, SmallInteger, Numeric, DateTime
from sqlalchemy.sql import func
from almt_app.models.database import Base


class ParamCashflowSchedule(Base):
    """现金流调度表（参数）"""
    __tablename__ = "almt_param_cashflow_schedule"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    coa_cd = Column(String(50), nullable=False, index=True)
    term = Column(String(20), nullable=False, index=True)
    period = Column(SmallInteger, nullable=False, comment="期数 0-24，0=M0 基线")
    principal_ratio = Column(Numeric(10, 6), nullable=True, comment="本期本金占比")
    is_x_marker = Column(SmallInteger, default=0, nullable=True, comment="Excel x 标记")
    remark = Column(String(200), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ParamCashflowSchedule(coa_cd={self.coa_cd}, term={self.term}, period={self.period})>"

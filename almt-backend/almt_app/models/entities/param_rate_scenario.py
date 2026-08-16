"""
利率情景假设实体
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime
from sqlalchemy.sql import func
from almt_app.models.database import Base


class ParamRateScenario(Base):
    """利率情景假设表"""
    __tablename__ = "almt_param_rate_scenario"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    order_number = Column(String(50), nullable=True)
    curve_name = Column(String(100), nullable=True)
    curve_id = Column(String(50), nullable=True)
    current_curve_value = Column(Numeric(10, 6), nullable=True)

    # 24个月的情景数据
    scenario_M1 = Column(Numeric(10, 6), nullable=True)
    scenario_M2 = Column(Numeric(10, 6), nullable=True)
    scenario_M3 = Column(Numeric(10, 6), nullable=True)
    scenario_M4 = Column(Numeric(10, 6), nullable=True)
    scenario_M5 = Column(Numeric(10, 6), nullable=True)
    scenario_M6 = Column(Numeric(10, 6), nullable=True)
    scenario_M7 = Column(Numeric(10, 6), nullable=True)
    scenario_M8 = Column(Numeric(10, 6), nullable=True)
    scenario_M9 = Column(Numeric(10, 6), nullable=True)
    scenario_M10 = Column(Numeric(10, 6), nullable=True)
    scenario_M11 = Column(Numeric(10, 6), nullable=True)
    scenario_M12 = Column(Numeric(10, 6), nullable=True)
    scenario_M13 = Column(Numeric(10, 6), nullable=True)
    scenario_M14 = Column(Numeric(10, 6), nullable=True)
    scenario_M15 = Column(Numeric(10, 6), nullable=True)
    scenario_M16 = Column(Numeric(10, 6), nullable=True)
    scenario_M17 = Column(Numeric(10, 6), nullable=True)
    scenario_M18 = Column(Numeric(10, 6), nullable=True)
    scenario_M19 = Column(Numeric(10, 6), nullable=True)
    scenario_M20 = Column(Numeric(10, 6), nullable=True)
    scenario_M21 = Column(Numeric(10, 6), nullable=True)
    scenario_M22 = Column(Numeric(10, 6), nullable=True)
    scenario_M23 = Column(Numeric(10, 6), nullable=True)
    scenario_M24 = Column(Numeric(10, 6), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ParamRateScenario(curve_name={self.curve_name}, curve_id={self.curve_id})>"

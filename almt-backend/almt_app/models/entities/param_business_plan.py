"""
业务计划实体
"""
from sqlalchemy import Column, String, Integer, Numeric, DateTime
from sqlalchemy.sql import func
from almt_app.models.database import Base


class ParamBusinessPlan(Base):
    """业务计划表"""
    __tablename__ = "almt_param_business_plan"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    coa_lvl = Column(String(50), nullable=True)
    coa_cd = Column(String(50), nullable=True)
    coa_name = Column(String(200), nullable=True)

    # 24个月的余额计划
    plan_balance1 = Column(Numeric(20, 2), nullable=True)
    plan_balance2 = Column(Numeric(20, 2), nullable=True)
    plan_balance3 = Column(Numeric(20, 2), nullable=True)
    plan_balance4 = Column(Numeric(20, 2), nullable=True)
    plan_balance5 = Column(Numeric(20, 2), nullable=True)
    plan_balance6 = Column(Numeric(20, 2), nullable=True)
    plan_balance7 = Column(Numeric(20, 2), nullable=True)
    plan_balance8 = Column(Numeric(20, 2), nullable=True)
    plan_balance9 = Column(Numeric(20, 2), nullable=True)
    plan_balance10 = Column(Numeric(20, 2), nullable=True)
    plan_balance11 = Column(Numeric(20, 2), nullable=True)
    plan_balance12 = Column(Numeric(20, 2), nullable=True)
    plan_balance13 = Column(Numeric(20, 2), nullable=True)
    plan_balance14 = Column(Numeric(20, 2), nullable=True)
    plan_balance15 = Column(Numeric(20, 2), nullable=True)
    plan_balance16 = Column(Numeric(20, 2), nullable=True)
    plan_balance17 = Column(Numeric(20, 2), nullable=True)
    plan_balance18 = Column(Numeric(20, 2), nullable=True)
    plan_balance19 = Column(Numeric(20, 2), nullable=True)
    plan_balance20 = Column(Numeric(20, 2), nullable=True)
    plan_balance21 = Column(Numeric(20, 2), nullable=True)
    plan_balance22 = Column(Numeric(20, 2), nullable=True)
    plan_balance23 = Column(Numeric(20, 2), nullable=True)
    plan_balance24 = Column(Numeric(20, 2), nullable=True)

    # 24个月的日均计划
    plan_average1 = Column(Numeric(20, 2), nullable=True)
    plan_average2 = Column(Numeric(20, 2), nullable=True)
    plan_average3 = Column(Numeric(20, 2), nullable=True)
    plan_average4 = Column(Numeric(20, 2), nullable=True)
    plan_average5 = Column(Numeric(20, 2), nullable=True)
    plan_average6 = Column(Numeric(20, 2), nullable=True)
    plan_average7 = Column(Numeric(20, 2), nullable=True)
    plan_average8 = Column(Numeric(20, 2), nullable=True)
    plan_average9 = Column(Numeric(20, 2), nullable=True)
    plan_average10 = Column(Numeric(20, 2), nullable=True)
    plan_average11 = Column(Numeric(20, 2), nullable=True)
    plan_average12 = Column(Numeric(20, 2), nullable=True)
    plan_average13 = Column(Numeric(20, 2), nullable=True)
    plan_average14 = Column(Numeric(20, 2), nullable=True)
    plan_average15 = Column(Numeric(20, 2), nullable=True)
    plan_average16 = Column(Numeric(20, 2), nullable=True)
    plan_average17 = Column(Numeric(20, 2), nullable=True)
    plan_average18 = Column(Numeric(20, 2), nullable=True)
    plan_average19 = Column(Numeric(20, 2), nullable=True)
    plan_average20 = Column(Numeric(20, 2), nullable=True)
    plan_average21 = Column(Numeric(20, 2), nullable=True)
    plan_average22 = Column(Numeric(20, 2), nullable=True)
    plan_average23 = Column(Numeric(20, 2), nullable=True)
    plan_average24 = Column(Numeric(20, 2), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ParamBusinessPlan(coa_cd={self.coa_cd}, coa_name={self.coa_name})>"

"""
Pydantic Schemas
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


# 账户册信息
class CoaInfoBase(BaseModel):
    uuid: str
    order_number: Optional[str] = None
    parent_coa_cd: Optional[str] = None
    coa_cd: str
    coa_name: Optional[str] = None
    leaf_desc: Optional[str] = None
    leaf_flag: Optional[str] = None


class CoaInfoCreate(CoaInfoBase):
    pass


class CoaInfoUpdate(BaseModel):
    order_number: Optional[str] = None
    parent_coa_cd: Optional[str] = None
    coa_cd: Optional[str] = None
    coa_name: Optional[str] = None
    leaf_desc: Optional[str] = None
    leaf_flag: Optional[str] = None


class CoaInfoResponse(CoaInfoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 账户册属性
class CoaAttributeBase(BaseModel):
    uuid: str
    order_number: Optional[str] = None
    coa_cd: str
    coa_name: Optional[str] = None
    term: Optional[str] = None
    accrule_base: Optional[str] = None
    curve_name: Optional[str] = None
    curve_id: Optional[str] = None
    business_line: Optional[str] = None
    float_ratio: Optional[float] = None
    replace_type: Optional[str] = None
    reprice_freq: Optional[str] = None


class CoaAttributeCreate(CoaAttributeBase):
    pass


class CoaAttributeResponse(CoaAttributeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 存量数据
class CurrentPositionBase(BaseModel):
    uuid: str
    coa_lvl: Optional[str] = None
    coa_name: Optional[str] = None
    balance: Optional[float] = None
    average: Optional[float] = None
    rate: Optional[float] = None


class CurrentPositionCreate(CurrentPositionBase):
    pass


class CurrentPositionResponse(CurrentPositionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 利率情景
class ParamRateScenarioBase(BaseModel):
    uuid: str
    order_number: Optional[str] = None
    curve_name: Optional[str] = None
    curve_id: Optional[str] = None
    current_curve_value: Optional[float] = None


class ParamRateScenarioCreate(ParamRateScenarioBase):
    scenario_M1: Optional[float] = None
    scenario_M2: Optional[float] = None
    scenario_M3: Optional[float] = None
    scenario_M4: Optional[float] = None
    scenario_M5: Optional[float] = None
    scenario_M6: Optional[float] = None
    scenario_M7: Optional[float] = None
    scenario_M8: Optional[float] = None
    scenario_M9: Optional[float] = None
    scenario_M10: Optional[float] = None
    scenario_M11: Optional[float] = None
    scenario_M12: Optional[float] = None
    scenario_M13: Optional[float] = None
    scenario_M14: Optional[float] = None
    scenario_M15: Optional[float] = None
    scenario_M16: Optional[float] = None
    scenario_M17: Optional[float] = None
    scenario_M18: Optional[float] = None
    scenario_M19: Optional[float] = None
    scenario_M20: Optional[float] = None
    scenario_M21: Optional[float] = None
    scenario_M22: Optional[float] = None
    scenario_M23: Optional[float] = None
    scenario_M24: Optional[float] = None


class ParamRateScenarioResponse(ParamRateScenarioBase):
    id: int
    scenario_M1: Optional[float] = None
    scenario_M2: Optional[float] = None
    scenario_M3: Optional[float] = None
    scenario_M4: Optional[float] = None
    scenario_M5: Optional[float] = None
    scenario_M6: Optional[float] = None
    scenario_M7: Optional[float] = None
    scenario_M8: Optional[float] = None
    scenario_M9: Optional[float] = None
    scenario_M10: Optional[float] = None
    scenario_M11: Optional[float] = None
    scenario_M12: Optional[float] = None
    scenario_M13: Optional[float] = None
    scenario_M14: Optional[float] = None
    scenario_M15: Optional[float] = None
    scenario_M16: Optional[float] = None
    scenario_M17: Optional[float] = None
    scenario_M18: Optional[float] = None
    scenario_M19: Optional[float] = None
    scenario_M20: Optional[float] = None
    scenario_M21: Optional[float] = None
    scenario_M22: Optional[float] = None
    scenario_M23: Optional[float] = None
    scenario_M24: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# 风险权重
class ParamRiskWeightBase(BaseModel):
    uuid: str
    order_number: Optional[str] = None
    coa_cd: Optional[str] = None
    coa_name: Optional[str] = None
    weight: Optional[float] = None


class ParamRiskWeightCreate(ParamRiskWeightBase):
    pass


class ParamRiskWeightResponse(ParamRiskWeightBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# 业务计划
class ParamBusinessPlanBase(BaseModel):
    uuid: str
    coa_lvl: Optional[str] = None
    coa_cd: Optional[str] = None
    coa_name: Optional[str] = None


class ParamBusinessPlanCreate(ParamBusinessPlanBase):
    plan_balance1: Optional[float] = None
    plan_balance2: Optional[float] = None
    plan_balance3: Optional[float] = None
    plan_balance4: Optional[float] = None
    plan_balance5: Optional[float] = None
    plan_balance6: Optional[float] = None
    plan_balance7: Optional[float] = None
    plan_balance8: Optional[float] = None
    plan_balance9: Optional[float] = None
    plan_balance10: Optional[float] = None
    plan_balance11: Optional[float] = None
    plan_balance12: Optional[float] = None
    plan_balance13: Optional[float] = None
    plan_balance14: Optional[float] = None
    plan_balance15: Optional[float] = None
    plan_balance16: Optional[float] = None
    plan_balance17: Optional[float] = None
    plan_balance18: Optional[float] = None
    plan_balance19: Optional[float] = None
    plan_balance20: Optional[float] = None
    plan_balance21: Optional[float] = None
    plan_balance22: Optional[float] = None
    plan_balance23: Optional[float] = None
    plan_balance24: Optional[float] = None


class ParamBusinessPlanResponse(ParamBusinessPlanBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# 计算任务
class CalculateTaskCreate(BaseModel):
    data_date: Optional[datetime] = None


class CalculateTaskResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

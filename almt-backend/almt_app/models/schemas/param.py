from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ParamRateScenarioBase(BaseModel):
    uuid: Optional[str] = None
    order_number: Optional[str] = None
    curve_name: Optional[str] = None
    curve_id: Optional[str] = None
    current_curve_value: Optional[float] = None


class ParamRateScenarioCreate(ParamRateScenarioBase):
    pass


class ParamRateScenarioUpdate(ParamRateScenarioBase):
    pass


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

    class Config:
        from_attributes = True


class ParamRiskWeightBase(BaseModel):
    uuid: Optional[str] = None
    coa_cd: Optional[str] = None
    coa_name: Optional[str] = None
    weight: Optional[float] = None


class ParamRiskWeightCreate(ParamRiskWeightBase):
    pass


class ParamRiskWeightUpdate(ParamRiskWeightBase):
    pass


class ParamRiskWeightResponse(ParamRiskWeightBase):
    id: int

    class Config:
        from_attributes = True

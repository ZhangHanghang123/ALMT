from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CurveDefinitionBase(BaseModel):
    uuid: Optional[str] = None
    curve_code: Optional[str] = None
    curve_name: Optional[str] = None
    curve_type: Optional[str] = None
    currency: Optional[str] = "CNY"
    description: Optional[str] = None
    is_active: Optional[int] = 1
    remark: Optional[str] = None


class CurveDefinitionCreate(CurveDefinitionBase):
    pass


class CurveDefinitionUpdate(CurveDefinitionBase):
    pass


class CurveDefinitionResponse(CurveDefinitionBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CurvePointBase(BaseModel):
    uuid: Optional[str] = None
    curve_uuid: Optional[str] = None
    term: Optional[str] = None
    term_days: Optional[int] = None
    rate_value: Optional[float] = None
    spread: Optional[float] = None
    is_active: Optional[int] = 1
    remark: Optional[str] = None


class CurvePointCreate(CurvePointBase):
    pass


class CurvePointUpdate(CurvePointBase):
    pass


class CurvePointResponse(CurvePointBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CurveWithPointsResponse(CurveDefinitionResponse):
    """曲线定义包含曲线点"""
    points: List[CurvePointResponse] = []

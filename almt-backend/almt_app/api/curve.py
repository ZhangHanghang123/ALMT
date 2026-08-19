"""
曲线定义管理API
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from almt_app.models.database import get_db
from almt_app.models.entities.curve_definition import CurveDefinition
from almt_app.models.entities.curve_point import CurvePoint
from almt_app.models.schemas.curve import (
    CurveDefinitionCreate, CurveDefinitionUpdate, CurveDefinitionResponse,
    CurvePointCreate, CurvePointUpdate, CurvePointResponse,
    CurveWithPointsResponse
)

router = APIRouter(prefix="/api/curve", tags=["曲线定义管理"])

# 期限天数映射
TERM_DAYS_MAP = {
    "1D": 1, "2D": 2, "3D": 3, "5D": 5, "7D": 7,
    "1W": 7, "2W": 14,
    "1M": 30, "2M": 60, "3M": 90, "4M": 120, "5M": 150, "6M": 180,
    "7M": 210, "8M": 240, "9M": 270, "10M": 300, "11M": 330, "12M": 365,
    "1Y": 365, "2Y": 730, "3Y": 1095, "4Y": 1460, "5Y": 1825,
    "7Y": 2555, "10Y": 3650, "15Y": 5475, "20Y": 7300, "30Y": 10950
}


# ===== 曲线定义API =====

@router.get("/definitions", response_model=List[CurveDefinitionResponse])
def get_curve_definitions(db: Session = Depends(get_db)):
    """获取所有曲线定义"""
    return db.query(CurveDefinition).filter(CurveDefinition.is_active == 1).order_by(CurveDefinition.curve_code).all()


@router.get("/definitions/{uuid}", response_model=CurveWithPointsResponse)
def get_curve_definition(uuid: str, db: Session = Depends(get_db)):
    """获取曲线定义(含曲线点)"""
    curve = db.query(CurveDefinition).filter(CurveDefinition.uuid == uuid).first()
    if not curve:
        raise HTTPException(status_code=404, detail="曲线定义不存在")

    points = db.query(CurvePoint).filter(
        CurvePoint.curve_uuid == uuid,
        CurvePoint.is_active == 1
    ).order_by(CurvePoint.term_days).all()

    result = CurveWithPointsResponse.model_validate(curve)
    result.points = points
    return result


@router.post("/definitions", response_model=CurveDefinitionResponse)
def create_curve_definition(item: CurveDefinitionCreate, db: Session = Depends(get_db)):
    """创建曲线定义"""
    # 检查曲线代码是否已存在
    existing = db.query(CurveDefinition).filter(CurveDefinition.curve_code == item.curve_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"曲线代码 {item.curve_code} 已存在")

    db_item = CurveDefinition(
        uuid=str(uuid.uuid4()),
        curve_code=item.curve_code,
        curve_name=item.curve_name,
        curve_type=item.curve_type,
        currency=item.currency or "CNY",
        description=item.description,
        is_active=item.is_active if item.is_active is not None else 1,
        remark=item.remark
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/definitions/{uuid}", response_model=CurveDefinitionResponse)
def update_curve_definition(uuid: str, item: CurveDefinitionUpdate, db: Session = Depends(get_db)):
    """更新曲线定义"""
    db_item = db.query(CurveDefinition).filter(CurveDefinition.uuid == uuid).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="曲线定义不存在")

    # 检查曲线代码是否与其他记录重复
    if item.curve_code and item.curve_code != db_item.curve_code:
        existing = db.query(CurveDefinition).filter(
            CurveDefinition.curve_code == item.curve_code,
            CurveDefinition.uuid != uuid
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"曲线代码 {item.curve_code} 已存在")

    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/definitions/{uuid}")
def delete_curve_definition(uuid: str, db: Session = Depends(get_db)):
    """删除曲线定义(软删除)"""
    db_item = db.query(CurveDefinition).filter(CurveDefinition.uuid == uuid).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="曲线定义不存在")

    # 软删除：禁用曲线定义和所有关联的曲线点
    db_item.is_active = 0
    db.query(CurvePoint).filter(CurvePoint.curve_uuid == uuid).update({"is_active": 0})
    db.commit()
    return {"message": "删除成功"}


# ===== 曲线点API =====

@router.get("/points", response_model=List[CurvePointResponse])
def get_curve_points(curve_uuid: str, db: Session = Depends(get_db)):
    """获取指定曲线的所有曲线点"""
    return db.query(CurvePoint).filter(
        CurvePoint.curve_uuid == curve_uuid,
        CurvePoint.is_active == 1
    ).order_by(CurvePoint.term_days).all()


@router.post("/points", response_model=CurvePointResponse)
def create_curve_point(item: CurvePointCreate, db: Session = Depends(get_db)):
    """创建曲线点"""
    # 验证曲线是否存在
    curve = db.query(CurveDefinition).filter(CurveDefinition.uuid == item.curve_uuid).first()
    if not curve:
        raise HTTPException(status_code=404, detail="曲线定义不存在")

    # 转换期限为天数
    term_days = TERM_DAYS_MAP.get(item.term, 0)

    db_item = CurvePoint(
        uuid=str(uuid.uuid4()),
        curve_uuid=item.curve_uuid,
        term=item.term,
        term_days=term_days,
        rate_value=item.rate_value,
        spread=item.spread,
        is_active=item.is_active if item.is_active is not None else 1,
        remark=item.remark
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/points/{uuid}", response_model=CurvePointResponse)
def update_curve_point(uuid: str, item: CurvePointUpdate, db: Session = Depends(get_db)):
    """更新曲线点"""
    db_item = db.query(CurvePoint).filter(CurvePoint.uuid == uuid).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="曲线点不存在")

    for key, value in item.model_dump(exclude_unset=True).items():
        if key == "term":
            # 更新期限时同步更新天数
            setattr(db_item, key, value)
            setattr(db_item, "term_days", TERM_DAYS_MAP.get(value, 0))
        else:
            setattr(db_item, key, value)

    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/points/{uuid}")
def delete_curve_point(uuid: str, db: Session = Depends(get_db)):
    """删除曲线点(软删除)"""
    db_item = db.query(CurvePoint).filter(CurvePoint.uuid == uuid).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="曲线点不存在")

    db_item.is_active = 0
    db.commit()
    return {"message": "删除成功"}


@router.post("/points/batch")
def batch_save_curve_points(curve_uuid: str, points: List[CurvePointCreate], db: Session = Depends(get_db)):
    """批量保存曲线点"""
    # 验证曲线是否存在
    curve = db.query(CurveDefinition).filter(CurveDefinition.uuid == curve_uuid).first()
    if not curve:
        raise HTTPException(status_code=404, detail="曲线定义不存在")

    # 删除现有曲线点(软删除)
    db.query(CurvePoint).filter(CurvePoint.curve_uuid == curve_uuid).update({"is_active": 0})

    # 批量新增
    for pt in points:
        term_days = TERM_DAYS_MAP.get(pt.term, 0)
        db_item = CurvePoint(
            uuid=str(uuid.uuid4()),
            curve_uuid=curve_uuid,
            term=pt.term,
            term_days=term_days,
            rate_value=pt.rate_value,
            spread=pt.spread,
            is_active=1,
            remark=pt.remark
        )
        db.add(db_item)

    db.commit()
    return {"message": f"保存成功，共 {len(points)} 个曲线点"}

"""
认证API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import hashlib

from almt_app.core.database import get_db
from almt_app.core.security import (
    create_access_token,
    get_current_user
)
from almt_app.core.config import settings

router = APIRouter(prefix="/api/auth", tags=["认证"])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password


# 模拟用户数据（生产环境应从数据库读取）
# 密码: admin123 的SHA256哈希
MOCK_USER = {
    "username": "admin",
    "password_hash": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"
}


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录"""
    # 简化版本：使用模拟用户验证
    # 生产环境应从数据库查询用户
    if form_data.username != MOCK_USER["username"] or \
       not verify_password(form_data.password, MOCK_USER["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建访问令牌
    access_token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": form_data.username
    }


@router.get("/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "username": current_user.get("sub"),
        "status": "active"
    }


@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    """用户登出"""
    # JWT是无状态的，登出只需前端删除token
    return {"message": "登出成功"}

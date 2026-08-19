"""
经营计划模拟系统 后端应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from almt_app.core.config import settings
from almt_app.models.database import engine, Base
from almt_app.api import auth, coa, param, calculate, position, result, basic_param, indicator, result_views, curve

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="经营计划模拟系统",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 初始化数据库
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"正在启动 {settings.APP_NAME} v{settings.APP_VERSION}")

    # 创建数据库表
    from almt_app.models.database import engine as db_engine
    Base.metadata.create_all(bind=db_engine)
    logger.info("数据库表已创建/更新")

    # 检查Excel引擎
    from almt_app.services.excel_engine import ExcelEngine
    excel_engine = ExcelEngine()
    if excel_engine.is_available():
        logger.info("Excel引擎可用")
    else:
        logger.warning("Excel引擎不可用，将使用模拟计算")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("应用正在关闭...")


# 注册路由
app.include_router(auth.router)
app.include_router(coa.router)
app.include_router(param.router)
app.include_router(calculate.router)
app.include_router(position.router)
app.include_router(result.router)
app.include_router(basic_param.router)
app.include_router(indicator.router)
app.include_router(result_views.router)
app.include_router(curve.router)


# 根路径
@app.get("/")
def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


# 健康检查
@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

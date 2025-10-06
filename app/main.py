# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import spiders, monitoring
from app.core.config import settings
from app.core.resources import resource_manager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化资源
    logger.info("正在初始化全局资源...")
    try:
        await resource_manager.init_resources({
            'redis_url': settings.REDIS_URL,
            'database_url': settings.DATABASE_URL,
        })
        logger.info("全局资源初始化成功")
    except Exception as e:
        logger.error(f"资源初始化失败: {e}")
        raise

    yield  # 应用运行期间

    # 关闭时清理资源
    logger.info("正在关闭全局资源...")
    await resource_manager.close_resources()
    logger.info("全局资源关闭完成")


# 创建FastAPI应用
app = FastAPI(
    title="Scrapy FastAPI 集成",
    description="异步Scrapy爬虫管理与API服务",
    version="1.0.0",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(spiders.router, prefix="/api/v1/spiders", tags=["spiders"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])


@app.get("/")
async def root():
    return {"message": "Scrapy FastAPI 集成服务", "status": "running"}


@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查Redis连接
        await resource_manager.redis.ping()

        # 检查数据库连接
        async with resource_manager.get_db_connection() as conn:
            await conn.execute("SELECT 1")

        return {
            "status": "healthy",
            "redis": "connected",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=503, detail="服务不可用")
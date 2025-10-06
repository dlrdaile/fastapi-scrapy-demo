# app/api/dependencies.py

from fastapi import Depends, HTTPException
from redis import Redis

from app.core.resources import resource_manager
from app.models.schemas import ErrorResponse


def get_redis_client():
    """获取Redis客户端依赖"""
    try:
        yield resource_manager.redis
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error="RedisUnavailable",
                message="Redis服务不可用",
                detail=str(e)
            ).dict()
        )


async def get_database_connection():
    """获取数据库连接依赖"""
    try:
        async with resource_manager.get_db_connection() as connection:
            yield connection
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error="DatabaseUnavailable",
                message="数据库服务不可用",
                detail=str(e)
            ).dict()
        )


async def validate_spider_name(spider_name: str) -> str:
    """验证爬虫名称依赖"""
    # 这里可以添加爬虫名称的白名单验证
    allowed_spiders = ['example_spider', 'news_spider', 'product_spider']

    if spider_name not in allowed_spiders:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="InvalidSpiderName",
                message=f"无效的爬虫名称: {spider_name}",
                detail=f"允许的爬虫: {', '.join(allowed_spiders)}"
            ).dict()
        )

    return spider_name



class RateLimiter:
    """速率限制器依赖"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute

    async def __call__(
            self,
            client_ip: str,
            redis=Depends(get_redis_client)
    ):
        redis_key = f"rate_limit:{client_ip}"

        # 获取当前计数
        current = await redis.get(redis_key)
        if current is None:
            # 第一次请求，设置过期时间
            await redis.setex(redis_key, 60, 1)
            return

        current_count = int(current)
        if current_count >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail=ErrorResponse(
                    error="RateLimitExceeded",
                    message="请求频率超限",
                    detail=f"每分钟最多 {self.requests_per_minute} 次请求"
                ).dict()
            )

        # 增加计数
        await redis.incr(redis_key)
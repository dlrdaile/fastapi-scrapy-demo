# app/core/resources.py
import asyncio
import aiohttp
import redis.asyncio as redis
import asyncpg
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AsyncResourceManager:
    """异步全局资源管理器"""

    def __init__(self):
        self._redis_pool: Optional[redis.Redis] = None
        self._db_pool: Optional[asyncpg.Pool] = None
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._initialized = False

    async def init_resources(self, config: Dict[str, Any]):
        """初始化所有资源"""
        if self._initialized:
            return

        try:
            # 初始化Redis连接池
            self._redis_pool = redis.from_url(
                config['redis_url'],
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )

            # 初始化PostgreSQL连接池
            self._db_pool = await asyncpg.create_pool(
                config['database_url'],
                min_size=5,
                max_size=20
            )

            # 初始化aiohttp会话
            timeout = aiohttp.ClientTimeout(total=30)
            self._http_session = aiohttp.ClientSession(timeout=timeout)

            self._initialized = True
            logger.info("异步全局资源初始化完成")

        except Exception as e:
            logger.error(f"资源初始化失败: {e}")
            await self.close_resources()
            raise

    async def close_resources(self):
        """关闭所有资源"""
        tasks = []

        if self._http_session:
            tasks.append(self._http_session.close())

        if self._redis_pool:
            tasks.append(self._redis_pool.aclose())

        if self._db_pool:
            tasks.append(self._db_pool.close())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._initialized = False
        logger.info("异步全局资源已关闭")

    @property
    def redis(self) -> redis.Redis:
        if not self._redis_pool:
            raise RuntimeError("Redis连接池未初始化")
        return self._redis_pool

    @property
    def database(self) -> asyncpg.Pool:
        if not self._db_pool:
            raise RuntimeError("数据库连接池未初始化")
        return self._db_pool

    @property
    def http_session(self) -> aiohttp.ClientSession:
        if not self._http_session:
            raise RuntimeError("HTTP会话未初始化")
        return self._http_session

    @asynccontextmanager
    async def get_db_connection(self):
        """获取数据库连接的上下文管理器"""
        if not self._db_pool:
            raise RuntimeError("数据库连接池未初始化")

        async with self._db_pool.acquire() as connection:
            yield connection


# 全局资源管理器实例
resource_manager = AsyncResourceManager()

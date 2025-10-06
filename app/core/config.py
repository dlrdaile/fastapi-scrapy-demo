# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
from pydantic import validator, RedisDsn, PostgresDsn
import os


class Settings(BaseSettings):
    """应用配置"""

    # API配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Scrapy FastAPI Integration"
    VERSION: str = "1.0.0"

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False

    # 数据库配置
    DATABASE_URL: str = "postgresql://postgres:dl201127@localhost:5432/scrapy_db"
    DB_POOL_MIN_SIZE: int = 5
    DB_POOL_MAX_SIZE: int = 20

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/1"
    REDIS_MAX_CONNECTIONS: int = 20

    # CORS配置
    ALLOWED_HOSTS: List[str] = ["*"]

    # Scrapy配置
    SCRAPY_SETTINGS_MODULE: str = "fastapi-scrapy-demo.app.settings"

    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 爬虫配置
    MAX_CONCURRENT_SPIDERS: int = 5
    SPIDER_TIMEOUT: int = 3600  # 1小时

    # 存储配置
    ITEMS_STORAGE_BACKEND: str = "redis"  # redis, database, file
    ITEMS_EXPIRE_TIME: int = 86400  # 24小时

    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if v and not str(v).startswith("postgresql://"):
            raise ValueError("DATABASE_URL must use asyncpg driver")
        return v

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 开发环境配置
class DevelopmentSettings(Settings):
    RELOAD: bool = True
    LOG_LEVEL: str = "DEBUG"


# 生产环境配置
class ProductionSettings(Settings):
    RELOAD: bool = False
    LOG_LEVEL: str = "WARNING"


# 测试环境配置
class TestingSettings(Settings):
    DATABASE_URL: str = "postgresql://test:test@localhost/test_db"
    REDIS_URL: str = "redis://localhost:6379/1"
    RELOAD: bool = False


def get_settings() -> Settings:
    """根据环境获取配置"""
    env = os.getenv("ENV", "development")

    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


settings = get_settings()
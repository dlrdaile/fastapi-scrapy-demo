# app/models/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum


class SpiderStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class SpiderRunRequest(BaseModel):
    """启动爬虫请求模型"""
    spider_name: str = Field(..., description="爬虫名称")
    spider_kwargs: Dict[str, Any] = Field(default_factory=dict, description="爬虫参数")
    priority: int = Field(default=1, ge=1, le=10, description="任务优先级")
    timeout: int = Field(default=3600, ge=60, description="超时时间（秒）")

    @validator('spider_name')
    def validate_spider_name(cls, v):
        if not v or not v.strip():
            raise ValueError("爬虫名称不能为空")
        return v.strip()


class SpiderTaskResponse(BaseModel):
    """爬虫任务响应模型"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="响应消息")
    spider_name: Optional[str] = Field(None, description="爬虫名称")
    created_at: Optional[datetime] = Field(None, description="创建时间")


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str = Field(..., description="任务ID")
    spider_name: str = Field(..., description="爬虫名称")
    status: SpiderStatus = Field(..., description="任务状态")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    items_count: int = Field(0, description="抓取项目数量")
    error_message: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")

    @validator('execution_time', always=True)
    def calculate_execution_time(cls, v, values):
        start_time = values.get('start_time')
        end_time = values.get('end_time')

        if start_time and end_time:
            return (end_time - start_time).total_seconds()
        return v


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: List[Dict[str, Any]] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    redis: str = Field(..., description="Redis状态")
    database: str = Field(..., description="数据库状态")
    timestamp: datetime = Field(..., description="检查时间")
    version: str = Field(..., description="服务版本")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    detail: Optional[Any] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间")


class SpiderInfo(BaseModel):
    """爬虫信息模型"""
    name: str = Field(..., description="爬虫名称")
    description: Optional[str] = Field(None, description="爬虫描述")
    allowed_domains: List[str] = Field(default_factory=list, description="允许的域名")
    start_urls: List[str] = Field(default_factory=list, description="起始URL")
    custom_settings: Dict[str, Any] = Field(default_factory=dict, description="自定义设置")
    is_active: bool = Field(True, description="是否激活")
# app/api/endpoints/monitoring.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
import psutil
import time
from datetime import datetime, timedelta

from app.core.resources import resource_manager
from app.models.schemas import HealthCheckResponse, ErrorResponse
from app.spiders.spider_runner import spider_runner

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """系统健康检查"""
    try:
        # 检查Redis连接
        redis_start = time.time()
        await resource_manager.redis.ping()
        redis_latency = time.time() - redis_start

        # 检查数据库连接
        db_start = time.time()
        async with resource_manager.get_db_connection() as conn:
            await conn.execute("SELECT 1")
        db_latency = time.time() - db_start

        # 检查系统资源
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return HealthCheckResponse(
            status="healthy",
            redis=f"connected ({redis_latency * 1000:.2f}ms)",
            database=f"connected ({db_latency * 1000:.2f}ms)",
            timestamp=datetime.now(),
            version="1.0.0"
        )

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error="ServiceUnavailable",
                message="服务健康检查失败",
                detail=str(e)
            ).dict()
        )


@router.get("/metrics")
async def get_metrics():
    """获取系统指标"""
    try:
        # 系统指标
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # 网络指标
        net_io = psutil.net_io_counters()

        # 应用指标
        active_tasks = await spider_runner.get_all_tasks()
        running_tasks = len([t for t in active_tasks.values() if t.get('status') == 'running'])

        # Redis指标
        redis_info = await resource_manager.redis.info()

        metrics = {
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": round(memory.used / (1024 ** 3), 2),
                "memory_total_gb": round(memory.total / (1024 ** 3), 2),
                "disk_percent": disk.percent,
                "disk_used_gb": round(disk.used / (1024 ** 3), 2),
                "disk_total_gb": round(disk.total / (1024 ** 3), 2),
            },
            "network": {
                "bytes_sent_mb": round(net_io.bytes_sent / (1024 ** 2), 2),
                "bytes_recv_mb": round(net_io.bytes_recv / (1024 ** 2), 2),
            },
            "application": {
                "active_tasks": len(active_tasks),
                "running_tasks": running_tasks,
                "completed_tasks": len([t for t in active_tasks.values() if t.get('status') == 'completed']),
                "failed_tasks": len([t for t in active_tasks.values() if t.get('status') == 'failed']),
            },
            "redis": {
                "connected_clients": redis_info.get('connected_clients', 0),
                "used_memory_mb": round(int(redis_info.get('used_memory', 0)) / (1024 ** 2), 2),
                "keyspace_hits": redis_info.get('keyspace_hits', 0),
                "keyspace_misses": redis_info.get('keyspace_misses', 0),
            }
        }

        return metrics

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="MetricsError",
                message="获取指标失败",
                detail=str(e)
            ).dict()
        )


@router.get("/stats")
async def get_spider_stats():
    """获取爬虫统计信息"""
    try:
        active_tasks = await spider_runner.get_all_tasks()

        # 计算统计信息
        total_tasks = len(active_tasks)
        status_counts = {}
        total_items = 0

        for task in active_tasks.values():
            status = task.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            total_items += task.get('items_count', 0)

        # 计算成功率
        completed_count = status_counts.get('completed', 0)
        failed_count = status_counts.get('failed', 0)
        total_ended = completed_count + failed_count
        success_rate = (completed_count / total_ended * 100) if total_ended > 0 else 0

        stats = {
            "overview": {
                "total_tasks": total_tasks,
                "total_items": total_items,
                "success_rate": round(success_rate, 2),
            },
            "status_breakdown": status_counts,
            "recent_tasks": list(active_tasks.values())[-10:],  # 最近10个任务
        }

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="StatsError",
                message="获取统计信息失败",
                detail=str(e)
            ).dict()
        )
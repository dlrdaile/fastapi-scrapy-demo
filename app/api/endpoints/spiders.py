# app/api/endpoints/spiders.py
import json
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query

from app.core.resources import resource_manager
from app.models.schemas import SpiderRunRequest, SpiderTaskResponse
from app.spiders.spider_runner import spider_runner

router = APIRouter()


@router.post("/run", response_model=SpiderTaskResponse)
async def run_spider(
        request: SpiderRunRequest,
        background_tasks: BackgroundTasks
):
    """启动爬虫"""
    try:
        task_id = await spider_runner.run_spider(
            spider_name=request.spider_name,
            **request.spider_kwargs
        )

        return SpiderTaskResponse(
            task_id=task_id,
            status="started",
            message=f"爬虫 {request.spider_name} 已启动"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动爬虫失败: {str(e)}")


@router.get("/tasks/{task_id}", response_model=Dict[str, Any])
async def get_task_status(task_id: str):
    """获取任务状态"""
    task_info = await spider_runner.get_task_status(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task_info


@router.get("/tasks", response_model=Dict[str, Dict[str, Any]])
async def get_all_tasks():
    """获取所有任务"""
    return await spider_runner.get_all_tasks()


@router.get("/results/{task_id}")
async def get_crawl_results(
        task_id: str,
        start: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000)
):
    """获取爬取结果"""
    try:
        redis_key = f"crawl_results:{task_id}"

        # 从Redis获取结果
        items = await resource_manager.redis.lrange(redis_key, start, start + limit - 1)

        # 解析JSON数据
        parsed_items = [json.loads(item) for item in items]

        # 获取总数
        total = await resource_manager.redis.llen(redis_key)

        return {
            "task_id": task_id,
            "items": parsed_items,
            "pagination": {
                "start": start,
                "limit": limit,
                "total": total,
                "has_more": start + limit < total
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取结果失败: {str(e)}")


@router.post("/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    """停止任务"""
    success = await spider_runner.stop_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在或无法停止")

    return {"message": "任务停止请求已发送", "task_id": task_id}
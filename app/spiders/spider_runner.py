# app/spiders/spider_runner.py
import asyncio
import uuid
import json
from typing import Dict, Any, List, Optional

from loguru import logger
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging
from twisted.internet import asyncioreactor
from twisted.internet.defer import Deferred

from app.core.resources import resource_manager

# 设置asyncio reactor
asyncioreactor.install()


class AsyncSpiderRunner:
    """异步Spider运行器"""

    def __init__(self):
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.runner = CrawlerRunner(get_project_settings())

    async def run_spider(self, spider_name: str, **kwargs) -> str:
        """异步运行Spider"""
        task_id = str(uuid.uuid4())

        # 创建任务记录
        self.active_tasks[task_id] = {
            "spider_name": spider_name,
            "status": "running",
            "kwargs": kwargs,
            "start_time": asyncio.get_event_loop().time(),
            "items": []
        }

        # 在后台运行爬虫
        asyncio.create_task(self._run_spider_task(task_id, spider_name, **kwargs))

        return task_id

    async def _run_spider_task(self, task_id: str, spider_name: str, **kwargs):
        """运行Spider的后台任务"""
        try:
            # 使用Deferred来运行Scrapy爬虫
            deferred = self.runner.crawl(spider_name, task_id=task_id, **kwargs)

            # 添加回调处理
            deferred.addCallback(self._on_spider_success, task_id)
            deferred.addErrback(self._on_spider_error, task_id)

        except Exception as e:
            logger.error(f"task({task_id}):Spider {spider_name} failed, reason: {e}")
            await self._handle_spider_exception(task_id, str(e))

    def _on_spider_success(self, result, task_id: str):
        """爬虫成功回调"""
        if task_id in self.active_tasks and self.active_tasks[task_id]['status'] in ('stopping', 'stopped'):
            logger.info(f"Spider for task {task_id} finished as a result of being stopped.")
            return
        asyncio.create_task(self._update_task_status(task_id, "completed", result))

    def _on_spider_error(self, failure, task_id: str):
        """爬虫错误回调"""
        if task_id in self.active_tasks and self.active_tasks[task_id]['status'] in ('stopping', 'stopped'):
            logger.info(f"Spider for task {task_id} errored during stop process.")
            return
        error_msg = str(failure.value)
        asyncio.create_task(self._update_task_status(task_id, "failed", error_msg))

    async def _handle_spider_exception(self, task_id: str, error: str):
        """处理爬虫异常"""
        await self._update_task_status(task_id, "failed", error)

    async def _update_task_status(self, task_id: str, status: str, result: Any = None):
        """更新任务状态"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = status
            self.active_tasks[task_id]["end_time"] = asyncio.get_event_loop().time()

            if status == "failed":
                if result:
                    self.active_tasks[task_id]["failure_reason"] = result

    async def store_crawl_results(self, task_id: str, items: List[Dict]):
        """存储爬取结果"""
        try:
            redis_key = f"crawl_results:{task_id}"
            pipe = resource_manager.redis.pipeline()

            for item in items:
                pipe.rpush(redis_key, json.dumps(item))

            pipe.expire(redis_key, 3600)  # 1小时过期
            await pipe.execute()

            # 同时更新任务信息
            self.active_tasks[task_id]["items_count"] = len(items)

        except Exception as e:
            logger.error(f"存储爬取结果失败: {e}")

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.active_tasks.get(task_id)

    async def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """获取所有任务"""
        return self.active_tasks

    async def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        if task_id not in self.active_tasks or self.active_tasks[task_id]['status'] != 'running':
            logger.warning(f"Task {task_id} not found or not running.")
            return False

        # 查找与task_id关联的crawler
        target_crawler = None
        for crawler in self.runner.crawlers:
            if getattr(crawler.spider, 'task_id', None) == task_id:
                target_crawler = crawler
                break

        if target_crawler:
            logger.info(f"Stopping task {task_id} for spider {target_crawler.spider.name}")
            self.active_tasks[task_id]["status"] = "stopping"
            try:
                # stop() returns a Deferred, which can be awaited when asyncioreactor is installed
                d = target_crawler.stop()
                await d
            finally:
                self.active_tasks[task_id]["status"] = "stopped"
                self.active_tasks[task_id]["end_time"] = asyncio.get_event_loop().time()
            logger.info(f"Task {task_id} stopped.")
            return True
        else:
            logger.warning(f"Could not find running crawler for task {task_id}. It may have already finished.")
            # Fallback for tasks that are in active_tasks but crawler is not found
            self.active_tasks[task_id]["status"] = "stopped"
            self.active_tasks[task_id]["end_time"] = asyncio.get_event_loop().time()
            return True


# 全局Spider运行器实例
spider_runner = AsyncSpiderRunner()
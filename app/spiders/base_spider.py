# app/spiders/base_spider.py
import scrapy
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from itemadapter import ItemAdapter
from scrapy import signals
from scrapy.crawler import Crawler


class BaseSpider(scrapy.Spider):
    """基础蜘蛛类，提供通用功能"""

    # 通用设置
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'CONCURRENT_REQUESTS': 16,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 2,
        'HTTPCACHE_ENABLED': True,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 2.0,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = datetime.now()
        self.items_scraped = 0
        self.stats = {}

        # 从kwargs获取自定义参数
        self.task_id = kwargs.get('task_id')
        self.callback_url = kwargs.get('callback_url')
        self.max_items = kwargs.get('max_items', 1000)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """从爬虫器创建实例"""
        spider = super().from_crawler(crawler, *args, **kwargs)

        # 注册信号处理器
        crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(spider.item_scraped, signal=signals.item_scraped)

        return spider

    def spider_opened(self, spider):
        """蜘蛛开启时的回调"""
        spider.logger.info(f"爬虫 {spider.name} 开始运行")
        spider.logger.info(f"起始URL: {spider.start_urls}")

        # 记录开始时间
        self.stats['start_time'] = datetime.now().isoformat()

    def spider_closed(self, spider, reason):
        """蜘蛛关闭时的回调"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        self.stats.update({
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'items_scraped': self.items_scraped,
            'close_reason': reason
        })

        spider.logger.info(f"爬虫 {spider.name} 运行结束")
        spider.logger.info(f"运行时长: {duration:.2f}秒")
        spider.logger.info(f"抓取项目: {self.items_scraped}个")
        spider.logger.info(f"关闭原因: {reason}")

        # 如果有回调URL，发送统计信息
        if self.callback_url:
            asyncio.create_task(self._send_callback())

    def item_scraped(self, item, response, spider):
        """项目抓取时的回调"""
        self.items_scraped += 1

        # 检查是否达到最大项目数
        if self.items_scraped >= self.max_items:
            spider.logger.info(f"达到最大项目数 {self.max_items}，关闭爬虫")
            self.crawler.engine.close_spider(spider, 'max_items_reached')

    async def _send_callback(self):
        """发送回调通知"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                callback_data = {
                    'task_id': self.task_id,
                    'spider_name': self.name,
                    'status': 'completed',
                    'stats': self.stats,
                    'timestamp': datetime.now().isoformat()
                }

                async with session.post(
                        self.callback_url,
                        json=callback_data,
                        headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status != 200:
                        self.logger.warning(f"回调请求失败: {response.status}")
        except Exception as e:
            self.logger.error(f"发送回调失败: {e}")

    def parse_error(self, failure):
        """解析错误处理"""
        self.logger.error(f"请求失败: {failure.value}")

        # 记录错误统计
        if 'error_count' not in self.stats:
            self.stats['error_count'] = 0
        self.stats['error_count'] += 1

        # 可以根据错误类型进行不同的处理
        if failure.check(scrapy.exceptions.IgnoreRequest):
            self.logger.warning("请求被忽略")
        elif failure.check(scrapy.exceptions.DropItem):
            self.logger.warning("项目被丢弃")
        else:
            self.logger.error(f"未处理的错误: {failure}")

    def make_request(self, url, callback=None, method='GET', **kwargs):
        """创建请求的辅助方法"""
        if callback is None:
            callback = self.parse

        meta = kwargs.pop('meta', {})
        meta.update({
            'spider_name': self.name,
            'task_id': self.task_id
        })

        return scrapy.Request(
            url=url,
            callback=callback,
            method=method,
            meta=meta,
            errback=self.parse_error,
            **kwargs
        )

    def save_item(self, item):
        """保存项目的辅助方法"""
        # 这里可以添加项目验证、清理等逻辑
        adapter = ItemAdapter(item)

        # 添加时间戳
        adapter['crawled_at'] = datetime.now().isoformat()
        adapter['spider_name'] = self.name
        adapter['task_id'] = self.task_id

        return item
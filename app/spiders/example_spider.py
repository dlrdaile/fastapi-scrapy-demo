# app/spiders/example_spider.py
import asyncio

import scrapy
from loguru import logger

from app.spiders.base_spider import BaseSpider


class ExampleSpider(BaseSpider):
    name = "example_spider"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = ['https://httpbin.org/json']

    async def parse(self, response):
        """异步解析响应"""
        try:
            # 模拟异步操作
            await asyncio.sleep(0.1)
            # 提取JSON数据
            data = response.json()
            # 返回提取的数据
            yield {
                'url': response.url,
                'title': data.get('slideshow', {}).get('title'),
                'author': data.get('slideshow', {}).get('author'),
                'date': data.get('date'),
                'crawled_at': response.meta.get('crawled_at')
            }

        except Exception as e:
            self.logger.error(f"解析响应失败: {e}")
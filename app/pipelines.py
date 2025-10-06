# app/pipelines.py
import hashlib
import json
from typing import Dict, Any
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

from app.spiders.spider_runner import spider_runner


class ValidationPipeline:
    """数据验证管道"""

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # 检查必需字段
        required_fields = ['url']
        for field in required_fields:
            if field not in adapter or not adapter[field]:
                raise DropItem(f"缺少必需字段: {field}")

        # 验证URL格式
        url = adapter.get('url', '')
        if not url.startswith(('http://', 'https://')):
            raise DropItem(f"无效的URL格式: {url}")

        return item


class DuplicatesPipeline:
    """去重管道"""

    def __init__(self):
        self.seen_items = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # 生成项目指纹
        fingerprint = self._generate_fingerprint(adapter.asdict())

        if fingerprint in self.seen_items:
            raise DropItem(f"重复项目: {adapter.get('url')}")
        else:
            self.seen_items.add(fingerprint)
            return item

    def _generate_fingerprint(self, item: Dict[str, Any]) -> str:
        """生成项目指纹"""
        # 基于URL和标题生成指纹
        url = item.get('url', '')
        title = item.get('title', '')

        content = f"{url}:{title}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()


class StoragePipeline:
    """存储管道"""

    def __init__(self):
        self.stored_count = 0

    async def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        try:
            # 这里可以实现存储到数据库、文件等
            # 目前只是计数
            self.stored_count += 1

            # 记录统计信息
            if hasattr(spider, 'stats'):
                spider.stats['stored_count'] = self.stored_count

            # # 存储到Redis
            if hasattr(spider, 'task_id'):
                await spider_runner.store_crawl_results(spider.task_id, [adapter.asdict()])
            return item

        except Exception as e:
            spider.logger.error(f"存储项目失败: {e}")
            raise DropItem(f"存储失败: {e}")

    def close_spider(self, spider):
        """蜘蛛关闭时调用"""
        spider.logger.info(f"总共存储了 {self.stored_count} 个项目")

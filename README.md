# FastAPI Scrapy 集成演示项目

这个项目展示了如何将 FastAPI 和 Scrapy 集成在一起，创建一个具有 API 接口的爬虫管理系统。通过 FastAPI 提供的 RESTful API，您可以异步启动、监控和管理 Scrapy 爬虫任务。

## 功能特点

- 基于 FastAPI 的异步 API 服务
- 集成 Scrapy 爬虫框架
- 异步爬虫任务管理
- 健康监控端点
- Redis 和 PostgreSQL 数据存储
- 完整的 CORS 支持

## 系统要求

- Python 3.13 或更高版本
- Redis 服务器
- PostgreSQL 数据库

## 安装

1. 克隆仓库

```bash
git clone https://github.com/yourusername/fastapi-scrapy-demo.git
cd fastapi-scrapy-demo
```

2. 创建虚拟环境并安装依赖

```bash
# 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -e .
```

## 配置

在运行项目前，请确保配置以下环境变量或在 `.env` 文件中设置：

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=["*"]
```

## 运行服务

启动 FastAPI 服务：

```bash
python run.py
```

或者使用 uvicorn 直接启动：

```bash
uvicorn app.main:app --reload
```

服务默认运行在 http://localhost:8000

## API 端点

### 爬虫管理

- `GET /api/v1/spiders/list` - 获取所有可用爬虫列表
- `POST /api/v1/spiders/run/{spider_name}` - 启动指定爬虫
- `GET /api/v1/spiders/status/{task_id}` - 获取爬虫任务状态
- `GET /api/v1/spiders/results/{task_id}` - 获取爬虫结果

### 监控

- `GET /api/v1/monitoring/stats` - 获取系统资源使用统计
- `GET /health` - 健康检查端点

## 示例爬虫

项目包含一个示例爬虫 `example_spider`，它从 httpbin.org 获取 JSON 数据。您可以通过 API 启动这个爬虫：

```bash
curl -X POST "http://localhost:8000/api/v1/spiders/run/example_spider"
```

## 项目结构

```
├── app/
│   ├── api/                # API 相关代码
│   │   ├── endpoints/      # API 端点
│   ├── core/               # 核心配置和资源
│   ├── models/             # 数据模型和架构
│   ├── spiders/            # Scrapy 爬虫
│   ├── main.py             # FastAPI 应用入口
│   ├── settings.py         # 项目设置
├── pyproject.toml          # 项目依赖
├── run.py                  # 启动脚本
└── scrapy.cfg              # Scrapy 配置
```

## 扩展开发

### 添加新爬虫

1. 在 `app/spiders/` 目录下创建新的爬虫类，继承 `BaseSpider`
2. 实现 `parse` 方法处理响应
3. 通过 API 启动新爬虫

### 自定义配置

修改 `app/core/config.py` 文件以添加或更改配置项。

## 许可证

[MIT](LICENSE)
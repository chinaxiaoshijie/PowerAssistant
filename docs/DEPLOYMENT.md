# 部署指南

## 本地开发环境

### 使用 Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down
```

### 从源码运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 配置数据库和飞书凭证

# 3. 初始化数据库
alembic upgrade head

# 4. 启动服务
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 生产环境部署

### 使用 Docker

```bash
# 1. 构建镜像
docker build -t powerassistant:latest .

# 2. 运行容器
docker run -d \
  -p 8000:8000 \
  --name powerassistant \
  -e DATABASE_URL="postgresql://user:pass@host/db" \
  -e FEISHU_APP_ID="your_app_id" \
  -e FEISHU_APP_SECRET="your_app_secret" \
  powerassistant:latest
```

### 使用 Docker Compose (生产)

```bash
# 使用生产配置
docker-compose -f docker-compose.prod.yml up -d
```

### 配置要求

- **Python**: 3.11+
- **PostgreSQL**: 15+
- **Redis**: 7+ (可选，用于缓存)
- **内存**: 至少 2GB
- **磁盘**: 至少 10GB

## 环境变量

| 变量名 | 说明 | 示例 |
|-------|------|------|
| `DATABASE_URL` | PostgreSQL连接串 | `postgresql://user:pass@localhost/db` |
| `REDIS_URL` | Redis连接地址 | `redis://localhost:6379/0` |
| `FEISHU_APP_ID` | 飞书应用ID | `cli_xxxxxx` |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | `xxxxxxxx` |
| `AI_MODEL_API_KEY` | AI模型API密钥 | `sk-xxxxxxxx` |
| `SECRET_KEY` | 应用密钥 | `your-secret-key` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

## 监控和维护

### 日志查看

```bash
# Docker
docker logs -f powerassistant-app

# 本地
tail -f logs/app.log
```

### 数据库备份

```bash
# 备份
pg_dump -U postgres powerassistant > backup.sql

# 恢复
psql -U postgres powerassistant < backup.sql
```

### 健康检查

访问 `http://localhost:8000/api/v1/health` 检查服务状态。

## 故障排除

### 服务无法启动

1. 检查数据库连接是否正常
2. 确认环境变量配置正确
3. 查看日志文件获取详细错误信息

### 飞书同步失败

1. 检查飞书应用凭证是否正确
2. 确认应用已授权相应权限
3. 检查网络连接

### 性能问题

1. 启用Redis缓存
2. 优化数据库查询
3. 增加服务实例

# 部署指南

本文档介绍如何使用 Docker 部署管理助手系统。

## 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 2GB 可用内存
- 至少 10GB 磁盘空间

## 快速开始

### 1. 克隆代码

```bash
git clone <repository-url>
cd 管理助手
```

### 2. 配置环境变量

```bash
# 开发环境
cp .env.example .env

# 生产环境
cp .env.prod.example .env
```

编辑 `.env` 文件，设置以下必填项：

```bash
# 飞书配置（必填）
FEISHU_APP_ID=cli_xxxxxx
FEISHU_APP_SECRET=your_app_secret_here

# 数据库密码（生产环境必须修改）
DB_PASSWORD=your_secure_password
```

### 3. 启动服务

#### 开发环境

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down
```

#### 生产环境

```bash
# 使用生产环境配置
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f app

# 停止服务
docker-compose -f docker-compose.prod.yml down
```

## 服务访问

启动后，服务可通过以下地址访问：

| 服务 | URL | 说明 |
|------|-----|------|
| API 文档 | http://localhost:8000/api/docs | Swagger UI |
| 健康检查 | http://localhost:8000/api/v1/health | 服务健康状态 |
| API 根路径 | http://localhost:8000/api | API 信息 |

## 常用命令

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs -f app
docker-compose logs -f db

# 查看最近 100 行日志
docker-compose logs --tail=100 app
```

### 数据库操作

```bash
# 运行数据库迁移
docker-compose exec app alembic upgrade head

# 回滚迁移
docker-compose exec app alembic downgrade -1

# 查看迁移状态
docker-compose exec app alembic current
```

### 手动触发同步

```bash
# 触发全量同步
curl -X POST http://localhost:8000/api/v1/sync/full

# 触发增量同步
curl -X POST http://localhost:8000/api/v1/sync/incremental

# 查看同步状态
curl http://localhost:8000/api/v1/sync/status
```

### 重建服务

```bash
# 重新构建镜像
docker-compose build --no-cache

# 重新启动
docker-compose up -d
```

## 生产环境部署

### 1. 服务器准备

确保服务器已安装 Docker 和 Docker Compose：

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. 安全配置

```bash
# 生成随机密钥
openssl rand -hex 32

# 设置强密码
export DB_PASSWORD=$(openssl rand -base64 32)
```

### 3. SSL 证书（可选）

如果使用 HTTPS，将证书放入 `nginx/ssl/` 目录：

```bash
nginx/ssl/
├── cert.pem    # 证书
└── key.pem     # 私钥
```

### 4. 启动生产环境

```bash
# 拉取最新代码
git pull origin main

# 重新构建
docker-compose -f docker-compose.prod.yml build

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 检查状态
docker-compose -f docker-compose.prod.yml ps
```

## 监控与维护

### 健康检查

```bash
# 检查服务健康状态
curl http://localhost:8000/api/v1/health

# 检查飞书连接
curl http://localhost:8000/api/v1/health/feishu
```

### 备份数据库

```bash
# 创建备份
docker-compose exec db pg_dump -U postgres malong_management > backup_$(date +%Y%m%d).sql

# 恢复备份
cat backup_20240303.sql | docker-compose exec -T db psql -U postgres malong_management
```

### 更新部署

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建镜像
docker-compose build --no-cache

# 3. 运行迁移
docker-compose run --rm migration

# 4. 重启服务
docker-compose up -d

# 5. 检查状态
docker-compose ps
```

## 故障排查

### 服务无法启动

```bash
# 检查日志
docker-compose logs app

# 检查端口占用
netstat -tlnp | grep 8000

# 检查环境变量
docker-compose exec app env | grep FEISHU
```

### 数据库连接失败

```bash
# 检查数据库状态
docker-compose ps db

# 检查数据库日志
docker-compose logs db

# 测试连接
docker-compose exec db pg_isready -U postgres
```

### 同步失败

```bash
# 检查飞书配置
docker-compose exec app python -c "from src.config.settings import settings; print(settings.feishu.app_id)"

# 检查网络连通性
docker-compose exec app curl https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal

# 查看同步日志
docker-compose logs app | grep sync
```

## 卸载

```bash
# 停止并删除容器
docker-compose down

# 删除数据卷（会删除所有数据！）
docker-compose down -v

# 删除镜像
docker-compose down --rmi all
```

## 支持

如有问题，请联系：
- 技术负责人：[联系方式]
- 飞书开放平台：https://open.feishu.cn/

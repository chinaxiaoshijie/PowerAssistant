# 🐳 Docker 镜像构建与推送指南

> 一键构建 Docker 镜像并推送到私有仓库，在 Ubuntu 生产环境部署

---

## 📋 目录

1. [环境准备](#环境准备)
2. [构建镜像](#构建镜像)
3. [推送到私有仓库](#推送到私有仓库)
4. [生产环境部署](#生产环境部署)
5. [自动化脚本](#自动化脚本)

---

## 环境准备

### 本地环境 (Windows/macOS/Linux)

```bash
# 1. 确认 Docker 已安装
docker --version
docker compose version

# 2. 登录到 Docker Registry
# Docker Hub
docker login

# 私有仓库 (Harbor/GitLab Registry)
docker login registry.example.com

# AWS ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.<region>.amazonaws.com

# 阿里云容器镜像服务
docker login --username=<your_username> registry.cn-hangzhou.aliyuncs.com
```

### 服务器环境 (Ubuntu 生产环境)

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# 2. 验证安装
docker --version
docker compose version

# 3. 配置 Docker 开机自启
sudo systemctl enable docker
sudo systemctl start docker
```

---

## 构建镜像

### 1. 配置镜像标签

在项目根目录创建 `build-config.sh`:

```bash
#!/bin/bash

# 镜像配置
IMAGE_NAME="malong-management-assistant"
IMAGE_VERSION="1.0.0"

# 镜像仓库地址（根据实际情况修改）
# Docker Hub: username/repo
# 私有仓库: registry.example.com/namespace/repo
# AWS ECR: <account>.dkr.ecr.<region>.amazonaws.com/repo
# 阿里云: registry.cn-hangzhou.aliyuncs.com/namespace/repo
IMAGE_REGISTRY="your-registry.com/malong"

# 完整镜像名称
IMAGE_TAG="${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_VERSION}"
IMAGE_LATEST="${IMAGE_REGISTRY}/${IMAGE_NAME}:latest"

echo "Image Tag: $IMAGE_TAG"
echo "Latest Tag: $IMAGE_LATEST"
```

### 2. 构建镜像脚本

创建 `build-docker-image.sh`:

```bash
#!/bin/bash

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 加载配置
source build-config.sh 2>/dev/null || {
    IMAGE_NAME="malong-management-assistant"
    IMAGE_VERSION="1.0.0"
    IMAGE_REGISTRY="docker.io/library"  # 默认值
    IMAGE_TAG="${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_VERSION}"
    IMAGE_LATEST="${IMAGE_REGISTRY}/${IMAGE_NAME}:latest"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装，请先安装 Docker"
    exit 1
fi

log_info "开始构建镜像..."
log_info "镜像名称: $IMAGE_TAG"

# 构建镜像
docker build -t "$IMAGE_TAG" -t "$IMAGE_LATEST" \
    --target production \
    --progress=plain \
    .

log_success "镜像构建成功: $IMAGE_TAG"

# 显示镜像信息
echo ""
log_info "镜像信息:"
docker images "$IMAGE_TAG"

# 本地测试（可选）
read -p "是否在本地测试镜像？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "启动临时容器进行测试..."

    # 使用 docker run 测试
    docker run --rm \
        -e "DATABASE_URL=postgresql+asyncpg://test:test@localhost/test" \
        -e "FEISHU_APP_ID=test" \
        -e "FEISHU_APP_SECRET=test" \
        -p 8000:8000 \
        --name test-malong \
        "$IMAGE_TAG" &

    TEST_PID=$!
    sleep 5

    # 测试健康检查
    if curl -s http://localhost:8000/api/v1/health | grep -q "healthy"; then
        log_success "健康检查通过！"
        docker stop test-malong 2>/dev/null
    else
        log_warning "健康检查失败或服务未启动"
        docker stop test-malong 2>/dev/null
    fi
fi

log_success "镜像构建完成！"
echo ""
echo "下一步操作："
echo "  1. 推送镜像: bash push-docker-image.sh"
echo "  2. 或手动推送: docker push $IMAGE_TAG"
```

### 3. 手动构建命令

```bash
# 构建镜像（指定版本）
docker build -t your-registry.com/malong/malong-management-assistant:1.0.0 \
    --target production \
    .

# 同时打上 latest 标签
docker tag your-registry.com/malong/malong-management-assistant:1.0.0 \
    your-registry.com/malong/malong-management-assistant:latest
```

---

## 推送到私有仓库

### 1. 推送脚本

创建 `push-docker-image.sh`:

```bash
#!/bin/bash

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 加载配置
source build-config.sh 2>/dev/null || {
    IMAGE_NAME="malong-management-assistant"
    IMAGE_VERSION="1.0.0"
    IMAGE_REGISTRY="docker.io/library"
    IMAGE_TAG="${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_VERSION}"
    IMAGE_LATEST="${IMAGE_REGISTRY}/${IMAGE_NAME}:latest"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否已登录
if ! docker info | grep -q "Username"; then
    log_warning "未检测到 Docker 登录信息"
    read -p "是否现在登录？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker login "$IMAGE_REGISTRY"
    else
        log_error "推送取消"
        exit 1
    fi
fi

log_info "开始推送镜像到仓库: $IMAGE_REGISTRY"

# 推送版本标签
log_info "推送版本镜像: $IMAGE_TAG"
docker push "$IMAGE_TAG"

# 推送 latest 标签
log_info "推送 latest 镜像: $IMAGE_LATEST"
docker push "$IMAGE_LATEST"

log_success "镜像推送完成！"
echo ""
echo "镜像地址:"
echo "  $IMAGE_TAG"
echo "  $IMAGE_LATEST"
```

### 2. 手动推送命令

```bash
# 登录仓库
docker login your-registry.com

# 推送镜像
docker push your-registry.com/malong/malong-management-assistant:1.0.0
docker push your-registry.com/malong/malong-management-assistant:latest
```

---

## 🐧 生产环境部署 (Ubuntu)

### 1. 准备生产环境配置

在服务器上创建 `docker-compose.prod.yml`:

```yaml
version: "3.8"

services:
  # PostgreSQL 数据库
  db:
    image: postgres:15-alpine
    container_name: malong_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: malong
      POSTGRES_PASSWORD: ${DB_PASSWORD:-malong_password}
      POSTGRES_DB: malong_management
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U malong"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s
    networks:
      - malong_network

  # Redis 缓存（可选）
  redis:
    image: redis:7-alpine
    container_name: malong_redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - malong_network

  # 应用服务
  app:
    image: your-registry.com/malong/malong-management-assistant:1.0.0
    container_name: malong_app
    restart: unless-stopped
    env_file:
      - .env.prod
    environment:
      DATABASE_URL: postgresql+asyncpg://malong:${DB_PASSWORD:-malong_password}@db:5432/malong_management
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs
    networks:
      - malong_network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M

  # 数据库迁移
  migration:
    image: your-registry.com/malong/malong-management-assistant:1.0.0
    container_name: malong_migration
    env_file:
      - .env.prod
    environment:
      DATABASE_URL: postgresql+asyncpg://malong:${DB_PASSWORD:-malong_password}@db:5432/malong_management
    depends_on:
      db:
        condition: service_healthy
    networks:
      - malong_network
    command: >
      sh -c "echo '⏳ Waiting for database...' &&
             sleep 10 &&
             echo '🚀 Running database migrations...' &&
             alembic upgrade head &&
             echo '✅ Migration completed successfully'"
    restart: "no"

  # Adminer (可选 - 数据库管理界面)
  adminer:
    image: adminer:4
    container_name: malong_adminer
    restart: unless-stopped
    ports:
      - "8080:8080"
    depends_on:
      - db
    networks:
      - malong_network

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  malong_network:
    driver: bridge
```

### 2. 创建生产环境变量文件

创建 `.env.prod`:

```bash
# ========================================
# 应用配置
# ========================================
NAME=Malong Management Assistant
VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false

# ========================================
# 数据库配置
# ========================================
# 在 docker-compose.prod.yml 中通过环境变量覆盖
DATABASE_URL=postgresql+asyncpg://malong:malong_password@db:5432/malong_management

# 数据库密码（建议使用环境变量）
# export DB_PASSWORD=your_secure_password

# ========================================
# 飞书配置
# ========================================
FEISHU_APP_ID=cli_your_app_id_here
FEISHU_APP_SECRET=your_app_secret_here
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx

# ========================================
# AI 引擎配置
# ========================================
AI_MODEL_PROVIDER=deepseek
AI_MODEL_NAME=deepseek-chat
AI_MODEL_API_KEY=sk_your_api_key_here

# ========================================
# Redis 配置
# ========================================
REDIS_URL=redis://redis:6379/0
REDIS_ENABLED=true

# ========================================
# 定时任务配置
# ========================================
SYNC_INTERVAL=3600
ENABLE_SCHEDULER=true

# ========================================
# 日志配置
# ========================================
LOG_LEVEL=INFO
LOG_FILE=/app/logs/app.log

# ========================================
# 安全配置
# ========================================
# CORS 配置
CORS_ORIGINS=http://localhost:3000,https://your-domain.com

# API 密钥
API_SECRET_KEY=change_this_in_production_$(openssl rand -hex 32)
```

### 3. 部署脚本

创建 `deploy-to-production.sh`:

```bash
#!/bin/bash

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装"
    exit 1
fi

# 检查是否为 root 或 docker 组成员
if ! docker ps &> /dev/null; then
    log_error "Docker 权限不足，请使用 sudo 或将用户加入 docker 组"
    exit 1
fi

echo "========================================"
echo "   管理助手 - 生产环境部署"
echo "========================================"
echo ""

# 1. 检查必要文件
log_info "检查必要文件..."
REQUIRED_FILES=("docker-compose.prod.yml" ".env.prod")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        log_error "文件不存在: $file"
        log_error "请先创建配置文件"
        exit 1
    fi
done
log_success "配置文件检查通过"

# 2. 登录私有仓库
log_info "登录私有镜像仓库..."
docker login your-registry.com || {
    log_warning "登录失败，继续部署（可能使用本地镜像）"
}

# 3. 拉取最新镜像
log_info "拉取最新镜像..."
docker pull your-registry.com/malong/malong-management-assistant:1.0.0
docker pull your-registry.com/malong/malong-management-assistant:latest

# 4. 创建必要目录
log_info "创建必要目录..."
mkdir -p logs
chmod -R 755 logs

# 5. 设置环境变量
log_info "设置环境变量..."
if [ -z "$DB_PASSWORD" ]; then
    read -sp "请输入数据库密码（回车使用默认）: " DB_PASSWORD_INPUT
    echo
    export DB_PASSWORD=${DB_PASSWORD_INPUT:-malong_secure_password_$(openssl rand -hex 8)}
    log_success "数据库密码已设置"
fi

# 6. 启动服务
log_info "启动服务..."
docker compose -f docker-compose.prod.yml up -d

# 7. 等待服务启动
log_info "等待服务启动..."
sleep 15

# 8. 检查服务状态
log_info "检查服务状态..."
if docker compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    log_success "服务启动成功！"

    # 显示服务信息
    echo ""
    log_info "服务信息:"
    echo "  - 应用服务: http://localhost:8000"
    echo "  - 健康检查: http://localhost:8000/api/v1/health"
    echo "  - 数据库管理: http://localhost:8080 (Adminer)"
    echo ""

    # 9. 验证健康检查
    log_info "验证健康检查..."
    if curl -s http://localhost:8000/api/v1/health | grep -q "healthy"; then
        log_success "✅ 健康检查通过"
    else
        log_warning "⚠️  健康检查失败，查看日志:"
        docker compose -f docker-compose.prod.yml logs app --tail=50
    fi

    echo ""
    log_success "========================================"
    log_success "   部署完成！"
    log_success "========================================"
    echo ""
    echo "常用命令:"
    echo "  - 查看日志:    docker compose -f docker-compose.prod.yml logs -f app"
    echo "  - 重启服务:    docker compose -f docker-compose.prod.yml restart"
    echo "  - 停止服务:    docker compose -f docker-compose.prod.yml down"
    echo "  - 查看状态:    docker compose -f docker-compose.prod.yml ps"
    echo ""
else
    log_error "服务启动失败"
    docker compose -f docker-compose.prod.yml logs app
    exit 1
fi
```

### 4. 一键部署命令

```bash
# 给脚本执行权限
chmod +x deploy-to-production.sh

# 运行部署
./deploy-to-production.sh

# 或使用 sudo
sudo ./deploy-to-production.sh
```

---

## 🔧 完整工作流程

### 方式一：手动操作

```bash
# 本地构建和推送
# 1. 构建镜像
docker build -t your-registry.com/malong/malong-management-assistant:1.0.0 --target production .

# 2. 推送镜像
docker login your-registry.com
docker push your-registry.com/malong/malong-management-assistant:1.0.0

# 3. 服务器部署
# SSH 到服务器
ssh user@server

# 4. 拉取镜像并启动
docker pull your-registry.com/malong/malong-management-assistant:1.0.0
docker compose -f docker-compose.prod.yml up -d
```

### 方式二：使用脚本（推荐）

```bash
# 本地
bash build-docker-image.sh
bash push-docker-image.sh

# 服务器
scp docker-compose.prod.yml .env.prod user@server:/opt/malong-management/
ssh user@server
cd /opt/malong-management
bash deploy-to-production.sh
```

---

## 🔄 版本更新流程

### 1. 更新应用版本

修改 `build-config.sh`:

```bash
IMAGE_VERSION="1.0.1"  # 更新版本号
```

### 2. 构建新镜像并推送

```bash
bash build-docker-image.sh
bash push-docker-image.sh
```

### 3. 生产环境滚动更新

```bash
# 服务器上执行
cd /opt/malong-management

# 拉取新镜像
docker pull your-registry.com/malong/malong-management-assistant:1.0.1

# 更新 docker-compose.prod.yml 中的镜像版本
# your-registry.com/malong/malong-management-assistant:1.0.0
# 改为
# your-registry.com/malong/malong-management-assistant:1.0.1

# 重启服务
docker compose -f docker-compose.prod.yml up -d --force-recreate app

# 验证
curl http://localhost:8000/api/v1/health
```

---

## 📊 镜像优化建议

### 1. 多阶段构建（已实现）

当前 Dockerfile 已使用多阶段构建，减小镜像体积。

### 2. 使用更小的基础镜像

```dockerfile
# 可选：使用 alpine 版本进一步减小体积
FROM python:3.11-alpine as builder
```

### 3. 启用 BuildKit

```bash
# 使用 BuildKit 构建（更快、更小）
DOCKER_BUILDKIT=1 docker build -t image:tag .
```

### 4. 镜像扫描

```bash
# 扫描镜像安全漏洞
docker scan your-registry.com/malong/malong-management-assistant:1.0.0
```

---

## 🆘 故障排查

### 镜像构建失败

```bash
# 查看详细日志
docker build --progress=plain -t image:tag .

# 清理缓存重新构建
docker builder prune
docker build --no-cache -t image:tag .
```

### 镜像推送失败

```bash
# 检查登录状态
docker info | grep Username

# 重新登录
docker logout your-registry.com
docker login your-registry.com
```

### 生产环境部署失败

```bash
# 查看服务日志
docker compose -f docker-compose.prod.yml logs -f app

# 检查容器状态
docker compose -f docker-compose.prod.yml ps

# 进入容器调试
docker compose -f docker-compose.prod.yml exec app bash
```

---

## 📝 配置文件模板下载

下载所有配置文件:

```bash
# 下载到项目目录
curl -O https://raw.githubusercontent.com/your-repo/main/build-config.sh
curl -O https://raw.githubusercontent.com/your-repo/main/build-docker-image.sh
curl -O https://raw.githubusercontent.com/your-repo/main/push-docker-image.sh
curl -O https://raw.githubusercontent.com/your-repo/main/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/your-repo/main/deploy-to-production.sh

# 设置执行权限
chmod +x *.sh
```

---

## 🎉 总结

### 完整流程

```bash
# 1. 本地构建
bash build-docker-image.sh

# 2. 本地推送
bash push-docker-image.sh

# 3. 服务器部署
bash deploy-to-production.sh
```

### 关键文件

- ✅ `build-config.sh` - 镜像配置
- ✅ `build-docker-image.sh` - 构建脚本
- ✅ `push-docker-image.sh` - 推送脚本
- ✅ `docker-compose.prod.yml` - 生产环境编排
- ✅ `.env.prod` - 生产环境变量
- ✅ `deploy-to-production.sh` - 部署脚本

---

**部署完成！** 🎊

如有问题，请查看日志或联系技术支持。

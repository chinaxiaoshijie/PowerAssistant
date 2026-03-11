#!/bin/bash

###############################################################################
# 生产环境部署脚本 (Ubuntu)
#
# 功能:
#   - 自动登录私有仓库
#   - 拉取最新镜像
#   - 启动所有服务
#   - 验证健康状态
#   - 显示服务信息
#
# 使用方法:
#   1. 确保已创建 docker-compose.prod.yml 和 .env.prod
#   2. 运行: bash deploy-to-production.sh
###############################################################################

set -e

# ========================================
# 颜色输出
# ========================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
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

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

log_banner() {
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}   $1${NC}"
    echo -e "${PURPLE}========================================${NC}"
}

# ========================================
# 检查环境
# ========================================

log_banner "管理助手 - 生产环境部署"

# 检查 Docker
log_step "检查 Docker 环境..."
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装"
    log_info "安装命令: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    exit 1
fi

# 检查权限
if ! docker ps &> /dev/null; then
    log_error "Docker 权限不足"
    log_info "解决方法:"
    log_info "  sudo usermod -aG docker \$USER"
    log_info "  newgrp docker"
    exit 1
fi

log_success "Docker 环境检查通过"

# ========================================
# 检查必要文件
# ========================================

log_step "检查必要文件..."

REQUIRED_FILES=(
    "docker-compose.prod.yml"
    ".env.prod"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        log_error "文件不存在: $file"
        log_info "请先创建配置文件"
        exit 1
    fi
done

log_success "配置文件检查通过"

# ========================================
# 加载镜像配置
# ========================================

log_step "加载镜像配置..."

if [ -f "build-config.sh" ]; then
    source build-config.sh
    log_info "镜像: $IMAGE_TAG"
else
    log_warning "未找到 build-config.sh，使用默认镜像"
    IMAGE_TAG="your-registry.com/malong/malong-management-assistant:1.0.0"
fi

# ========================================
# 登录私有仓库
# ========================================

log_step "登录私有镜像仓库..."

# 检查是否已登录
if echo "$IMAGE_REGISTRY" | grep -qE "(docker.io|index.docker.io)"; then
    # Docker Hub 不强制登录（如果镜像是公开的）
    log_info "使用 Docker Hub 公开镜像"
    DOCKER_LOGIN_REQUIRED=false
else
    # 私有仓库需要登录
    DOCKER_LOGIN_REQUIRED=true
fi

if [ "$DOCKER_LOGIN_REQUIRED" = true ]; then
    if ! docker info 2>&1 | grep -q "Username"; then
        log_warning "未检测到 Docker 登录信息"
        read -p "是否现在登录私有仓库？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker login "$IMAGE_REGISTRY"
        else
            log_error "登录取消，无法拉取私有镜像"
            exit 1
        fi
    else
        log_success "已登录私有仓库"
    fi
fi

# ========================================
# 拉取最新镜像
# ========================================

log_step "拉取最新镜像..."

log_info "镜像: $IMAGE_TAG"

if docker pull "$IMAGE_TAG"; then
    log_success "镜像拉取成功"

    # 也拉取 latest 标签
    IMAGE_LATEST="${IMAGE_REGISTRY}/${IMAGE_NAME}:latest"
    if [ "$IMAGE_LATEST" != "$IMAGE_TAG" ]; then
        docker pull "$IMAGE_LATEST" 2>/dev/null || true
    fi
else
    log_error "镜像拉取失败"
    log_info "请检查:"
    log_info "  1. 镜像地址是否正确"
    log_info "  2. 是否已登录私有仓库"
    log_info "  3. 网络连接是否正常"
    exit 1
fi

# ========================================
# 创建必要目录
# ========================================

log_step "创建必要目录..."

mkdir -p logs
chmod -R 755 logs

log_success "目录创建完成"

# ========================================
# 设置环境变量
# ========================================

log_step "设置环境变量..."

# 数据库密码（如果未设置则生成随机密码）
if [ -z "$DB_PASSWORD" ]; then
    log_warning "未设置 DB_PASSWORD 环境变量"
    read -sp "请输入数据库密码（回车使用随机生成）: " DB_PASSWORD_INPUT
    echo

    if [ -n "$DB_PASSWORD_INPUT" ]; then
        export DB_PASSWORD="$DB_PASSWORD_INPUT"
    else
        # 生成随机密码
        export DB_PASSWORD="malong_$(openssl rand -hex 12)"
        log_info "使用随机密码: ${DB_PASSWORD:0:8}... (已保存到环境变量)"
    fi

    # 保存到 .env 文件
    echo "DB_PASSWORD=$DB_PASSWORD" >> .env.prod
    log_success "数据库密码已保存到 .env.prod"
else
    log_info "使用环境变量 DB_PASSWORD"
fi

# ========================================
# 启动服务
# ========================================

log_step "启动服务..."

log_info "使用 docker-compose.prod.yml"
docker compose -f docker-compose.prod.yml up -d

log_success "服务启动命令执行成功"

# ========================================
# 等待服务启动
# ========================================

log_step "等待服务启动..."

SERVICES_COUNT=$(docker compose -f docker-compose.prod.yml ps -q | wc -l)
log_info "检测到 $SERVICES_COUNT 个服务"

log_info "等待 15 秒..."
sleep 15

# ========================================
# 检查服务状态
# ========================================

log_step "检查服务状态..."

if docker compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    log_success "✅ 所有服务启动成功"

    echo ""
    log_info "服务状态:"
    docker compose -f docker-compose.prod.yml ps

    # 检查是否有失败的服务
    FAILED_COUNT=$(docker compose -f docker-compose.prod.yml ps | grep -c "Exit\|Restarting" || true)
    if [ "$FAILED_COUNT" -gt 0 ]; then
        log_warning "⚠️  有 $FAILED_COUNT 个服务状态异常"
        docker compose -f docker-compose.prod.yml ps | grep "Exit\|Restarting"
    fi
else
    log_error "❌ 服务启动失败"
    docker compose -f docker-compose.prod.yml logs --tail=50
    exit 1
fi

# ========================================
# 验证健康检查
# ========================================

log_step "验证应用健康状态..."

HEALTH_CHECK_URL="http://localhost:8000/api/v1/health"

if curl -s -f "$HEALTH_CHECK_URL" | grep -q "healthy"; then
    log_success "✅ 应用健康检查通过"

    # 显示详细健康信息
    HEALTH_INFO=$(curl -s "$HEALTH_CHECK_URL")
    log_info "健康信息: $HEALTH_INFO"
else
    log_warning "⚠️  健康检查失败，查看日志..."
    docker compose -f docker-compose.prod.yml logs app --tail=100
fi

# ========================================
# 显示服务信息
# ========================================

echo ""
log_banner "   部署完成！"
echo ""
echo "🌐 访问地址:"
echo ""
log_info "应用服务:"
echo "  http://localhost:8000"
echo ""
log_info "健康检查:"
echo "  http://localhost:8000/api/v1/health"
echo ""
log_info "API 文档 (开发环境):"
echo "  http://localhost:8000/api/docs"
echo ""
log_info "Dashboard:"
echo "  http://localhost:8000/dashboard"
echo ""
log_info "数据库管理 (Adminer):"
echo "  http://localhost:8080"
echo "  - 系统: PostgreSQL"
echo "  - 服务器: db"
echo "  - 用户名: malong"
echo "  - 密码: ${DB_PASSWORD:0:8}..."
echo "  - 数据库: malong_management"
echo ""

# ========================================
# 常用命令
# ========================================

echo "🔧 常用命令:"
echo ""
echo "  # 查看日志"
echo "  docker compose -f docker-compose.prod.yml logs -f app"
echo ""
echo "  # 重启服务"
echo "  docker compose -f docker-compose.prod.yml restart"
echo ""
echo "  # 重启应用服务"
echo "  docker compose -f docker-compose.prod.yml restart app"
echo ""
echo "  # 停止服务"
echo "  docker compose -f docker-compose.prod.yml down"
echo ""
echo "  # 查看服务状态"
echo "  docker compose -f docker-compose.prod.yml ps"
echo ""
echo "  # 进入应用容器"
echo "  docker compose -f docker-compose.prod.yml exec app bash"
echo ""
echo "  # 备份数据库"
echo "  docker compose -f docker-compose.prod.yml exec db pg_dump -U malong malong_management > backup_\$(date +'%Y%m%d').sql"
echo ""
echo "  # 查看资源使用"
echo "  docker stats"
echo ""

# ========================================
# 安全提示
# ========================================

echo "🔒 安全提示:"
echo ""
log_warning "生产环境建议:"
echo "  1. 配置防火墙，仅开放必要端口"
echo "  2. 使用 Nginx 反向代理并配置 SSL"
echo "  3. 修改默认密码"
echo "  4. 定期备份数据库"
echo "  5. 配置监控和告警"
echo ""

# ========================================
# 完成
# ========================================

log_banner "   🎉 部署完成！"
echo ""
log_success "应用已成功部署到生产环境"
log_info "如有问题，请查看日志: docker compose -f docker-compose.prod.yml logs -f app"
echo ""

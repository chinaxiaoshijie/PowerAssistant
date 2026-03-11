#!/bin/bash

###############################################################################
# Docker 镜像推送脚本
#
# 功能:
#   - 自动加载配置
#   - 检查登录状态
#   - 推送镜像到私有仓库
#   - 同时推送版本标签和 latest 标签
#
# 使用方法:
#   1. 登录仓库: docker login your-registry.com
#   2. 运行: bash push-docker-image.sh
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

# ========================================
# 检查 Docker
# ========================================

log_step "检查 Docker 环境..."

if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装"
    exit 1
fi

# ========================================
# 检查登录状态
# ========================================

log_step "检查 Docker 登录状态..."

if docker info 2>&1 | grep -q "Username"; then
    DOCKER_USER=$(docker info 2>&1 | grep -oP 'Username: \K(.+)')
    log_success "已登录: $DOCKER_USER"
else
    log_warning "未检测到 Docker 登录信息"
    echo ""
    read -p "是否现在登录？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 尝试从配置文件获取仓库地址
        if [ -f "build-config.sh" ]; then
            source build-config.sh
            docker login "$IMAGE_REGISTRY"
        else
            docker login
        fi
    else
        log_error "推送取消"
        exit 1
    fi
fi

# ========================================
# 加载配置
# ========================================

log_step "加载镜像配置..."

if [ -f "build-config.sh" ]; then
    source build-config.sh
    log_info "镜像: $IMAGE_TAG"
else
    log_error "未找到 build-config.sh 配置文件"
    log_info "请先创建 build-config.sh 并配置镜像信息"
    exit 1
fi

# ========================================
# 检查本地镜像
# ========================================

log_step "检查本地镜像..."

if docker images -q "$IMAGE_TAG" | grep -q .; then
    log_success "本地镜像存在: $IMAGE_TAG"
else
    log_error "本地镜像不存在: $IMAGE_TAG"
    log_info "请先运行: bash build-docker-image.sh"
    exit 1
fi

# ========================================
# 推送镜像
# ========================================

echo ""
echo "========================================"
log_step "开始推送镜像到仓库"
echo "========================================"
echo ""
log_info "仓库地址: $IMAGE_REGISTRY"
log_info "镜像名称: $IMAGE_NAME"
log_info "版本号: $IMAGE_VERSION"
echo ""

# 推送版本标签
log_step "推送版本镜像: $IMAGE_TAG"
docker push "$IMAGE_TAG"

# 推送 latest 标签
log_step "推送 latest 镜像: $IMAGE_LATEST"
docker push "$IMAGE_LATEST"

# ========================================
# 完成信息
# ========================================

echo ""
echo "========================================"
log_success "   镜像推送完成！"
echo "========================================"
echo ""
echo "📋 镜像地址:"
echo ""
echo "  版本标签:"
echo "  $IMAGE_TAG"
echo ""
echo "  Latest 标签:"
echo "  $IMAGE_LATEST"
echo ""
echo "✅ 镜像已推送到仓库，可在生产环境拉取使用"
echo ""
echo "🚀 生产环境部署命令:"
echo ""
echo "  # SSH 到服务器"
echo "  ssh user@server"
echo ""
echo "  # 拉取镜像"
echo "  docker pull $IMAGE_TAG"
echo ""
echo "  # 启动服务"
echo "  docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "========================================"

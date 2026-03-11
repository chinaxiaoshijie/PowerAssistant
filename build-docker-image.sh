#!/bin/bash

###############################################################################
# Docker 镜像构建脚本
#
# 功能:
#   - 自动加载配置
#   - 多阶段构建（production 目标）
#   - 自动打标签（版本号 + latest）
#   - 可选本地测试
#   - 输出镜像信息
#
# 使用方法:
#   1. 配置 build-config.sh
#   2. 运行: bash build-docker-image.sh
###############################################################################

set -e  # 遇到错误立即退出

# ========================================
# 颜色输出
# ========================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'  # No Color

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
    log_info "安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

DOCKER_VERSION=$(docker --version)
log_info "Docker 版本: $DOCKER_VERSION"

# ========================================
# 加载配置
# ========================================

log_step "加载构建配置..."

if [ -f "build-config.sh" ]; then
    source build-config.sh
    log_success "配置文件加载成功"
    log_info "镜像: $IMAGE_TAG"
else
    log_warning "未找到 build-config.sh，使用默认配置"
    IMAGE_NAME="malong-management-assistant"
    IMAGE_VERSION="1.0.0"
    IMAGE_REGISTRY="docker.io/library"
    IMAGE_TAG="${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_VERSION}"
    IMAGE_LATEST="${IMAGE_REGISTRY}/${IMAGE_NAME}:latest"
fi

# ========================================
# 检查必要文件
# ========================================

log_step "检查必要文件..."

REQUIRED_FILES=("Dockerfile" "requirements.txt")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        log_error "文件不存在: $file"
        exit 1
    fi
done
log_success "必要文件检查通过"

# ========================================
# 构建镜像
# ========================================

log_step "开始构建 Docker 镜像..."

log_info "构建参数:"
log_info "  - 镜像名称: $IMAGE_TAG"
log_info "  - 目标阶段: production"
log_info "  - Dockerfile: $DOCKERFILE_PATH"
log_info "  - 上下文: $BUILD_CONTEXT"

# 启用 BuildKit（如果配置）
if [ "$ENABLE_BUILDKIT" = true ]; then
    export DOCKER_BUILDKIT=1
    log_info "  - BuildKit: 启用"
fi

echo ""

# 构建镜像
docker build \
    -t "$IMAGE_TAG" \
    -t "$IMAGE_LATEST" \
    --target production \
    --progress=plain \
    -f "$DOCKERFILE_PATH" \
    "$BUILD_CONTEXT"

log_success "✅ 镜像构建成功！"

# ========================================
# 显示镜像信息
# ========================================

echo ""
log_step "镜像信息:"

IMAGE_ID=$(docker images --format "{{.ID}}" "$IMAGE_TAG")
IMAGE_SIZE=$(docker images --format "{{.Size}}" "$IMAGE_TAG")

log_info "  - 镜像 ID: $IMAGE_ID"
log_info "  - 镜像大小: $IMAGE_SIZE"
log_info "  - 创建时间: $(docker images --format "{{.CreatedAt}}" "$IMAGE_TAG")"

echo ""
docker images | grep -E "(REPOSITORY|$IMAGE_NAME)"

# ========================================
# 本地测试（可选）
# ========================================

echo ""
read -p "🔍 是否在本地测试镜像？(y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_step "本地测试镜像..."

    TEST_CONTAINER="malong-test-$(date +%s)"

    log_info "启动测试容器: $TEST_CONTAINER"

    # 启动测试容器（后台）
    docker run -d \
        --name "$TEST_CONTAINER" \
        -e "DATABASE_URL=postgresql+asyncpg://test:test@localhost/test" \
        -e "FEISHU_APP_ID=test" \
        -e "FEISHU_APP_SECRET=test" \
        -e "AI_MODEL_API_KEY=test" \
        -p 8001:8000 \
        "$IMAGE_TAG" > /dev/null 2>&1

    log_info "等待服务启动..."
    sleep 8

    # 测试健康检查
    if curl -s http://localhost:8001/api/v1/health | grep -q "healthy"; then
        log_success "✅ 健康检查通过！"
        TEST_RESULT="PASS"
    else
        log_warning "⚠️  健康检查失败（可能因缺少数据库连接）"
        TEST_RESULT="WARN"
    fi

    # 停止并删除测试容器
    log_info "清理测试容器..."
    docker stop "$TEST_CONTAINER" > /dev/null 2>&1
    docker rm "$TEST_CONTAINER" > /dev/null 2>&1

    log_success "测试容器已清理"
fi

# ========================================
# 完成信息
# ========================================

echo ""
echo "========================================"
log_success "   Docker 镜像构建完成！"
echo "========================================"
echo ""
echo "📋 镜像标签:"
echo "  $IMAGE_TAG"
echo "  $IMAGE_LATEST"
echo ""
echo "🚀 下一步操作:"
echo ""
echo "  1. 推送镜像到仓库:"
echo "     bash push-docker-image.sh"
echo "     或"
echo "     docker push $IMAGE_TAG"
echo ""
echo "  2. 查看镜像详情:"
echo "     docker inspect $IMAGE_TAG"
echo ""
echo "  3. 本地运行测试:"
echo "     docker run --rm -p 8000:8000 $IMAGE_TAG"
echo ""
echo "========================================"

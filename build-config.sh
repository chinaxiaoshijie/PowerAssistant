#!/bin/bash

###############################################################################
# Docker 镜像构建配置
#
# 说明:
#   1. 修改 IMAGE_REGISTRY 为你的私有仓库地址
#   2. 修改 IMAGE_VERSION 为当前版本号
#   3. 登录仓库后运行构建脚本
###############################################################################

# ========================================
# 镜像基本信息
# ========================================

# 镜像名称
IMAGE_NAME="malong-management-assistant"

# 镜像版本（每次构建时更新）
IMAGE_VERSION="1.0.0"

# ========================================
# 镜像仓库地址（重要：根据实际情况修改）
# ========================================

# 选择一个仓库地址并取消注释

# Docker Hub
IMAGE_REGISTRY="docker.io/yourusername"

# 私有 Harbor 仓库
# IMAGE_REGISTRY="registry.example.com/malong"

# AWS ECR
# IMAGE_REGISTRY="<aws_account_id>.dkr.ecr.<region>.amazonaws.com"

# 阿里云容器镜像服务
# IMAGE_REGISTRY="registry.cn-hangzhou.aliyuncs.com/malong-tech"

# 腾讯云容器镜像服务
# IMAGE_REGISTRY="ccr.ccs.tencentyun.com/malong"

# ========================================
# 完整镜像标签
# ========================================

IMAGE_TAG="${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_VERSION}"
IMAGE_LATEST="${IMAGE_REGISTRY}/${IMAGE_NAME}:latest"

# ========================================
# 构建参数（可选）
# ========================================

# 是否启用 BuildKit（推荐启用，构建更快）
ENABLE_BUILDKIT=true

# Dockerfile 路径
DOCKERFILE_PATH="Dockerfile"

# 构建上下文
BUILD_CONTEXT="."

# ========================================
# 输出配置信息
# ========================================

echo "========================================"
echo "   Docker 镜像构建配置"
echo "========================================"
echo ""
echo "📋 镜像信息:"
echo "  - 镜像名称: $IMAGE_NAME"
echo "  - 版本号:   $IMAGE_VERSION"
echo "  - 仓库地址: $IMAGE_REGISTRY"
echo ""
echo "🏷️  镜像标签:"
echo "  - 版本标签: $IMAGE_TAG"
echo "  - Latest:   $IMAGE_LATEST"
echo ""
echo "⚙️  构建配置:"
echo "  - BuildKit: $ENABLE_BUILDKIT"
echo "  - Dockerfile: $DOCKERFILE_PATH"
echo "  - 上下文: $BUILD_CONTEXT"
echo ""
echo "========================================"
echo ""
echo "✅ 配置完成！"
echo "🚀 运行 'bash build-docker-image.sh' 开始构建"
echo ""

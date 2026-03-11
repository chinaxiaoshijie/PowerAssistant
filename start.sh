#!/bin/bash

# 管理助手 - Docker 快速启动脚本
# Usage: ./start.sh

set -e

echo "=========================================="
echo "  管理助手 - Docker 快速启动"
echo "=========================================="
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker 未安装"
    echo "请先安装 Docker: https://www.docker.com/get-started"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: Docker Compose 未安装"
    echo "请先安装 Docker Compose"
    exit 1
fi

# 检查 .env.docker 文件
if [ ! -f .env.docker ]; then
    echo "⚠️  .env.docker 文件不存在"
    echo "正在创建 .env.docker..."
    cp .env.prod.example .env.docker
    echo "✅ 已创建 .env.docker"
    echo ""
    echo "⚠️  请编辑 .env.docker 并填写以下必需配置："
    echo "   - FEISHU_APP_ID"
    echo "   - FEISHU_APP_SECRET"
    echo "   - DASHSCOPE_API_KEY"
    echo ""
    echo "然后重新运行: ./start.sh"
    exit 1
fi

# 检查必需的环境变量
if grep -q "FEISHU_APP_ID=cli_xxxxxx" .env.docker || grep -q "FEISHU_APP_ID=" .env.docker | grep -q "^\s*$"; then
    echo "⚠️  请编辑 .env.docker 并填写 FEISHU_APP_ID"
    exit 1
fi

if grep -q "DASHSCOPE_API_KEY=sk-xxxxxx" .env.docker || grep -q "DASHSCOPE_API_KEY=" .env.docker | grep -q "^\s*$"; then
    echo "⚠️  请编辑 .env.docker 并填写 DASHSCOPE_API_KEY"
    exit 1
fi

echo "✅ 环境检查通过"
echo ""

# 构建并启动服务
echo "🚀 开始构建和启动服务..."
echo ""

docker-compose up -d --build

echo ""
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo ""
echo "📊 服务状态："
docker-compose ps

echo ""
echo "=========================================="
echo "  服务已启动！"
echo "=========================================="
echo ""
echo "🌐 访问地址："
echo "   - API 文档:    http://localhost:8000/api/docs"
echo "   - Dashboard:   http://localhost:8000/dashboard"
echo "   - 健康检查:    http://localhost:8000/api/v1/health"
echo "   - Adminer:     http://localhost:8080"
echo ""
echo "📝 查看日志："
echo "   docker-compose logs -f app"
echo ""
echo "🛑 停止服务："
echo "   docker-compose down"
echo ""

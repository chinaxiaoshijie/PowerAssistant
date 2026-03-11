#!/bin/bash

# 清理脚本
# 停止所有服务并清理资源

set -e

echo "=========================================="
echo "  管理助手 - 清理资源"
echo "=========================================="
echo ""

# 确认操作
read -p "⚠️  这将停止所有服务并删除数据。是否继续? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 取消操作"
    exit 1
fi

echo "1. 停止所有容器..."
docker-compose down

echo ""
echo "2. 删除数据卷（数据库和 Redis）..."
docker-compose down -v

echo ""
echo "3. 删除镜像..."
docker-compose down --rmi all

echo ""
echo "4. 清理临时文件..."
rm -f temp_*.json temp_*.txt 2>/dev/null || true

echo ""
echo "=========================================="
echo "  清理完成"
echo "=========================================="
echo ""
echo "下次启动需要重新初始化数据库："
echo "  docker-compose up -d --build"
echo ""

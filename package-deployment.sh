#!/bin/bash

###############################################################################
# 部署包生成脚本
#
# 功能: 将所有部署相关的文件打包成一个压缩包
# 使用方法: ./package-deployment.sh
###############################################################################

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   管理助手 - 部署包生成脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 创建部署包目录
PACKAGE_DIR="部署包-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$PACKAGE_DIR"

echo -e "${BLUE}[1/6]${NC} 复制部署文档..."
cp "部署指南-Ubuntu.md" "$PACKAGE_DIR/" 2>/dev/null || echo "⚠ 警告: 部署指南-Ubuntu.md 不存在"
cp "快速部署指南.md" "$PACKAGE_DIR/" 2>/dev/null || echo "⚠ 警告: 快速部署指南.md 不存在"
cp "README-部署包说明.md" "$PACKAGE_DIR/" 2>/dev/null || echo "⚠ 警告: README-部署包说明.md 不存在"
echo -e "${GREEN}✓${NC} 部署文档复制完成"

echo -e "${BLUE}[2/6]${NC} 复制部署脚本..."
cp "deploy-ubuntu.sh" "$PACKAGE_DIR/" 2>/dev/null || echo "⚠ 警告: deploy-ubuntu.sh 不存在"
chmod +x "$PACKAGE_DIR/deploy-ubuntu.sh" 2>/dev/null
echo -e "${GREEN}✓${NC} 部署脚本复制完成"

echo -e "${BLUE}[3/6]${NC} 复制环境变量模板..."
cp ".env.example" "$PACKAGE_DIR/" 2>/dev/null || echo "⚠ 警告: .env.example 不存在"
echo -e "${GREEN}✓${NC} 环境变量模板复制完成"

echo -e "${BLUE}[4/6]${NC} 复制 Docker Compose 配置..."
cp "docker-compose.yml" "$PACKAGE_DIR/" 2>/dev/null || echo "⚠ 警告: docker-compose.yml 不存在"
echo -e "${GREEN}✓${NC} Docker Compose 配置复制完成"

echo -e "${BLUE}[5/6]${NC} 创建使用说明..."
cat > "$PACKAGE_DIR/使用说明.txt" << 'EOF'
========================================
   管理助手 - Ubuntu 部署包
========================================

包含文件:
  - 部署指南-Ubuntu.md           完整部署指南（详细版）
  - 快速部署指南.md              快速参考卡片
  - README-部署包说明.md         部署包使用说明
  - deploy-ubuntu.sh            自动化部署脚本
  - .env.example                环境变量模板
  - docker-compose.yml          Docker 配置
  - 使用说明.txt                本文件

快速开始:
  1. 上传到 Ubuntu 服务器
  2. 运行: sudo bash deploy-ubuntu.sh
  3. 按提示操作即可

详细说明请查看: README-部署包说明.md

版本: 1.0.0
日期: 2026-03-09
========================================
EOF
echo -e "${GREEN}✓${NC} 使用说明创建完成"

echo -e "${BLUE}[6/6]${NC} 打包部署包..."
cd "$(dirname "$PACKAGE_DIR")"
tar -czf "${PACKAGE_DIR}.tar.gz" "$PACKAGE_DIR"
zip -r "${PACKAGE_DIR}.zip" "$PACKAGE_DIR" >/dev/null 2>&1 || echo "  (zip 命令未安装，仅生成 tar.gz)"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   部署包生成成功！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "生成的文件:"
ls -lh "${PACKAGE_DIR}"* 2>/dev/null
echo ""
echo "部署包大小:"
du -h "${PACKAGE_DIR}.tar.gz" 2>/dev/null | cut -f1
echo ""
echo "部署包位置:"
realpath "${PACKAGE_DIR}.tar.gz" 2>/dev/null
echo ""
echo -e "${YELLOW}提示:${NC}"
echo "  1. 上传部署包到服务器:"
echo "     scp ${PACKAGE_DIR}.tar.gz user@server:/tmp/"
echo ""
echo "  2. 在服务器上解压:"
echo "     tar -xzf ${PACKAGE_DIR}.tar.gz"
echo ""
echo "  3. 进入目录并部署:"
echo "     cd $PACKAGE_DIR"
echo "     sudo bash deploy-ubuntu.sh"
echo ""
echo -e "${GREEN}部署包已准备就绪！${NC}"
echo ""

#!/bin/bash

# 部署验证脚本
# 用于验证 Docker 部署是否成功

set -e

echo "=========================================="
echo "  管理助手 - 部署验证"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 验证函数
pass() {
    echo -e "${GREEN}✓ $1${NC}"
}

fail() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# 1. 检查 Docker 服务
echo "1. 检查 Docker 服务..."
if docker info > /dev/null 2>&1; then
    pass "Docker 服务正常运行"
else
    fail "Docker 服务未运行，请启动 Docker Desktop 或 Docker Engine"
fi

# 2. 检查容器状态
echo ""
echo "2. 检查容器状态..."
containers=$(docker-compose ps -q | wc -l)

if [ "$containers" -lt 4 ]; then
    fail "容器数量不足，期望至少 4 个容器"
fi

pass "所有容器已启动"

# 3. 检查健康状态
echo ""
echo "3. 检查服务健康状态..."

db_healthy=$(docker-compose ps db | grep -c "Up" || echo "0")
redis_healthy=$(docker-compose ps redis | grep -c "Up" || echo "0")
app_healthy=$(docker-compose ps app | grep -c "Up" || echo "0")

if [ "$db_healthy" -eq 1 ]; then
    pass "PostgreSQL 数据库运行中"
else
    fail "PostgreSQL 数据库未运行"
fi

if [ "$redis_healthy" -eq 1 ]; then
    pass "Redis 缓存运行中"
else
    warn "Redis 缓存未运行（可选）"
fi

if [ "$app_healthy" -eq 1 ]; then
    pass "应用服务运行中"
else
    fail "应用服务未运行"
fi

# 4. 测试健康检查接口
echo ""
echo "4. 测试健康检查接口..."
health_response=$(curl -s http://localhost:8000/api/v1/health)

if echo "$health_response" | grep -q "healthy"; then
    pass "健康检查接口正常"
    echo "   响应: $health_response"
else
    fail "健康检查接口异常"
    echo "   响应: $health_response"
fi

# 5. 检查数据库连接
echo ""
echo "5. 检查数据库连接..."
db_test=$(docker-compose exec -T db psql -U postgres -d malong_management -c "SELECT 1" 2>&1)

if echo "$db_test" | grep -q "1"; then
    pass "数据库连接正常"
    echo "   响应: $db_test"
else
    fail "数据库连接失败"
    echo "   错误: $db_test"
fi

# 6. 检查环境变量
echo ""
echo "6. 检查环境变量配置..."
app_env=$(docker-compose exec -T app env)

if echo "$app_env" | grep -q "FEISHU_APP_ID"; then
    pass "飞书配置已加载"

    # 检查是否为默认值
    if echo "$app_env" | grep -q "FEISHU_APP_ID=cli_xxxxxx"; then
        warn "飞书 APP_ID 使用默认值，请修改 .env.docker"
    fi
else
    fail "飞书配置未加载"
fi

if echo "$app_env" | grep -q "DASHSCOPE_API_KEY"; then
    pass "AI 模型配置已加载"

    if echo "$app_env" | grep -q "DASHSCOPE_API_KEY=sk-xxxxxx"; then
        warn "DashScope API Key 使用默认值，请修改 .env.docker"
    fi
else
    fail "AI 模型配置未加载"
fi

# 7. 检查可用端口
echo ""
echo "7. 检查端口监听..."
ports=$(netstat -an 2>/dev/null | grep -E "LISTEN" | grep -E ":8000|:5432|:6379|:8080" || ss -tuln 2>/dev/null | grep -E ":8000|:5432|:6379|:8080" || echo "")

if echo "$ports" | grep -q ":8000"; then
    pass "应用端口 8000 已监听"
else
    warn "应用端口 8000 未监听"
fi

if echo "$ports" | grep -q ":5432"; then
    pass "数据库端口 5432 已监听"
else
    warn "数据库端口 5432 未监听（可能在容器内部）"
fi

if echo "$ports" | grep -q ":8080"; then
    pass "Adminer 端口 8080 已监听"
else
    warn "Adminer 端口 8080 未监听"
fi

# 8. 访问测试
echo ""
echo "8. 访问测试..."
if curl -s -f http://localhost:8000/ > /dev/null; then
    pass "应用主页可访问"

    # 获取应用信息
    app_info=$(curl -s http://localhost:8000/)
    echo "   应用信息: $app_info"

    if echo "$app_info" | grep -q "dashboard"; then
        pass "Dashboard 路由正常"
    fi
else
    fail "应用主页无法访问"
fi

# 9. 检查日志
echo ""
echo "9. 检查应用日志..."
app_logs=$(docker-compose logs --tail=50 app)

if echo "$app_logs" | grep -q "application_startup"; then
    pass "应用启动日志正常"

    if echo "$app_logs" | grep -q "ERROR"; then
        warn "应用日志中存在错误"
    fi
else
    warn "未找到应用启动日志"
fi

# 总结
echo ""
echo "=========================================="
echo "  验证完成"
echo "=========================================="
echo ""
echo "访问地址："
echo "  - API 文档:    ${GREEN}http://localhost:8000/api/docs${NC}"
echo "  - Dashboard:   ${GREEN}http://localhost:8000/dashboard${NC}"
echo "  - 健康检查:    ${GREEN}http://localhost:8000/api/v1/health${NC}"
echo "  - Adminer:     ${GREEN}http://localhost:8080${NC}"
echo ""
echo "下一步："
echo "  1. 配置飞书应用权限"
echo "  2. 手动触发数据同步：curl http://localhost:8000/api/v1/sync/trigger"
echo "  3. 查看 Dashboard 了解系统状态"
echo ""

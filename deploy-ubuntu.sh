#!/bin/bash

###############################################################################
# 管理助手 - Ubuntu 快速部署脚本
#
# 使用方法:
#   1. 下载脚本: wget https://your-domain.com/deploy.sh
#   2. 授予执行权限: chmod +x deploy.sh
#   3. 运行脚本: ./deploy.sh
#
# 支持方式:
#   - docker: 使用 Docker 部署（推荐）
#   - native: 原生部署
#
# 要求:
#   - Ubuntu 20.04/22.04
#   - root 或 sudo 权限
#   - 项目代码已上传到 /opt/malong-management/
###############################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 检查是否为 root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 sudo 或 root 用户运行此脚本"
        exit 1
    fi
}

# 检查 Ubuntu 版本
check_ubuntu_version() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [[ "$VERSION_ID" != "20.04" && "$VERSION_ID" != "22.04" ]]; then
            log_warning "检测到 Ubuntu $VERSION_ID，推荐使用 20.04 或 22.04"
            read -p "是否继续? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        else
            log_success "Ubuntu $VERSION_ID 检查通过"
        fi
    else
        log_error "无法检测系统版本"
        exit 1
    fi
}

# 检查磁盘空间
check_disk_space() {
    AVAILABLE_SPACE=$(df / --output=avail | tail -1)
    REQUIRED_SPACE=10485760  # 10GB in KB

    if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
        log_error "磁盘空间不足，至少需要 10GB"
        exit 1
    fi
    log_success "磁盘空间检查通过"
}

# 检查内存
check_memory() {
    AVAILABLE_MEMORY=$(free -k | awk '/^Mem:/{print $2}')
    REQUIRED_MEMORY=2097152  # 2GB in KB

    if [ "$AVAILABLE_MEMORY" -lt "$REQUIRED_MEMORY" ]; then
        log_warning "内存不足 2GB ($((AVAILABLE_MEMORY/1024)) MB)，可能影响性能"
    else
        log_success "内存检查通过"
    fi
}

# 更新系统
update_system() {
    log_info "更新系统包..."
    apt update
    apt upgrade -y
    log_success "系统更新完成"
}

# 安装 Docker
install_docker() {
    log_info "安装 Docker..."

    # 安装依赖
    apt install -y ca-certificates curl gnupg

    # 添加 Docker GPG 密钥
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # 添加 Docker 仓库
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null

    # 安装 Docker
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # 启动 Docker
    systemctl enable --now docker

    # 验证安装
    if docker --version && docker compose version; then
        log_success "Docker 安装成功"
    else
        log_error "Docker 安装失败"
        exit 1
    fi
}

# 安装 PostgreSQL
install_postgresql() {
    log_info "安装 PostgreSQL 15..."

    # 添加 PostgreSQL 仓库
    apt install -y wget ca-certificates
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
        apt-key add -
    echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | \
        tee /etc/apt/sources.list.d/pgdg.list

    # 安装
    apt update
    apt install -y postgresql-15 postgresql-contrib

    # 启动服务
    systemctl enable --now postgresql

    # 创建数据库
    sudo -u postgres psql -c "CREATE DATABASE malong_management;"
    sudo -u postgres psql -c "CREATE USER malong_user WITH PASSWORD 'malong_password';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE malong_management TO malong_user;"
    sudo -u postgres psql -c "ALTER DATABASE malong_management OWNER TO malong_user;"

    log_success "PostgreSQL 安装并配置完成"
}

# 安装 Redis
install_redis() {
    log_info "安装 Redis..."
    apt install -y redis-server
    systemctl enable --now redis-server
    log_success "Redis 安装完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙..."

    # 允许必要端口
    ufw allow 22/tcp
    ufw allow 8000/tcp
    ufw allow 5432/tcp  # PostgreSQL
    ufw allow 6379/tcp  # Redis

    # 启用防火墙
    echo "y" | ufw enable

    log_success "防火墙配置完成"
}

# 创建部署目录
create_deployment_directory() {
    log_info "创建部署目录..."

    DEPLOY_DIR="/opt/malong-management"

    if [ ! -d "$DEPLOY_DIR" ]; then
        mkdir -p "$DEPLOY_DIR"
        chown -R $SUDO_USER:$SUDO_USER "$DEPLOY_DIR"
        log_success "部署目录创建完成: $DEPLOY_DIR"
    else
        log_warning "部署目录已存在: $DEPLOY_DIR"
    fi
}

# 创建环境配置文件
create_env_file() {
    log_info "创建环境配置文件..."

    DEPLOY_DIR="/opt/malong-management"
    ENV_FILE="$DEPLOY_DIR/.env.docker"

    cat > "$ENV_FILE" << 'EOF'
# ========================================
# 应用配置
# ========================================
NAME=Malong Management Assistant
VERSION=1.0.0
ENVIRONMENT=production

# ========================================
# 数据库配置
# ========================================
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/malong_management

# ========================================
# 飞书配置（部署后必须修改）
# ========================================
FEISHU_APP_ID=cli_CHANGE_THIS
FEISHU_APP_SECRET=CHANGE_THIS
FEISHU_WEBHOOK_URL=

# ========================================
# AI 引擎配置（部署后必须修改）
# ========================================
AI_MODEL_PROVIDER=deepseek
AI_MODEL_NAME=deepseek-chat
AI_MODEL_API_KEY=sk_CHANGE_THIS

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
EOF

    chown $SUDO_USER:$SUDO_USER "$ENV_FILE"
    chmod 600 "$ENV_FILE"

    log_warning "请在部署完成后修改 .env.docker 中的敏感信息（飞书和 AI API 密钥）"
    log_success "环境配置文件创建完成"
}

# 创建 Dockerfile
create_dockerfile() {
    log_info "创建 Dockerfile..."

    DEPLOY_DIR="/opt/malong-management"
    DOCKERFILE="$DEPLOY_DIR/Dockerfile"

    cat > "$DOCKERFILE" << 'EOF'
FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

FROM base AS dependencies

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS production

COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

RUN mkdir -p /app/logs
COPY . .

RUN python -c "import src" || echo "Health check passed"

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
EOF

    chown $SUDO_USER:$SUDO_USER "$DOCKERFILE"
    log_success "Dockerfile 创建完成"
}

# 创建 systemd 服务（原生部署）
create_systemd_service() {
    log_info "创建 systemd 服务..."

    cat > /etc/systemd/system/malong-management.service << 'EOF'
[Unit]
Description=Malong Management Assistant
After=network.target postgresql.service redis-server.service
Requires=postgresql.service redis-server.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/malong-management
Environment="PATH=/opt/malong-management/venv/bin"
Environment="PYTHONPATH=/opt/malong-management"
ExecStart=/opt/malong-management/venv/bin/gunicorn \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000 \
    --access-logfile /opt/malong-management/logs/gunicorn_access.log \
    --error-logfile /opt/malong-management/logs/gunicorn_error.log \
    --log-level info \
    src.main:app
Restart=always
RestartSec=10
LimitNOFILE=65536
NoNewPrivileges=true
PrivateTmp=true
StandardOutput=journal
StandardError=journal
SyslogIdentifier=malong-management

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_success "systemd 服务创建完成"
}

# 创建备份脚本
create_backup_script() {
    log_info "创建备份脚本..."

    DEPLOY_DIR="/opt/malong-management"

    cat > "$DEPLOY_DIR/backup.sh" << 'EOF'
#!/bin/bash

BACKUP_DIR="/opt/malong-management/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# 备份数据库
if [ -f docker-compose.yml ]; then
    docker compose exec -T db pg_dump -U postgres malong_management > "$BACKUP_DIR/db_$DATE.sql"
else
    sudo -u postgres pg_dump malong_management > "$BACKUP_DIR/db_$DATE.sql"
fi

# 压缩
gzip "$BACKUP_DIR/db_$DATE.sql"

# 清理旧备份
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_DIR/db_$DATE.sql.gz"
EOF

    chmod +x "$DEPLOY_DIR/backup.sh"
    chown $SUDO_USER:$SUDO_USER "$DEPLOY_DIR/backup.sh"

    # 设置每日备份
    (crontab -u $SUDO_USER -l 2>/dev/null; echo "0 1 * * * /opt/malong-management/backup.sh") | crontab -u $SUDO_USER -

    log_success "备份脚本创建完成并设置每日凌晨1点自动执行"
}

# 启动 Docker 服务
start_docker_services() {
    log_info "启动 Docker 服务..."

    cd /opt/malong-management

    # 创建日志目录
    sudo -u $SUDO_USER mkdir -p logs

    # 启动服务
    sudo -u $SUDO_USER docker compose up -d

    # 等待服务启动
    sleep 10

    # 检查状态
    if sudo -u $SUDO_USER docker compose ps | grep -q "Up"; then
        log_success "Docker 服务启动成功"

        # 显示服务信息
        echo ""
        log_info "服务信息:"
        echo "  - 应用服务: http://localhost:8000"
        echo "  - 数据库管理: http://localhost:8080"
        echo "  - API 文档: http://localhost:8000/api/docs (开发环境)"
        echo ""
        log_warning "首次部署请修改 .env.docker 中的敏感信息，然后重启服务:"
        echo "  docker compose restart app"
    else
        log_error "Docker 服务启动失败"
        sudo -u $SUDO_USER docker compose logs app
        exit 1
    fi
}

# 显示完成信息
show_completion_info() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║          ${GREEN}管理助手部署完成！${NC}                                    ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "下一步操作："
    echo ""
    echo "1. 修改环境配置（${RED}必须${NC}）:"
    echo "   vim /opt/malong-management/.env.docker"
    echo "   - FEISHU_APP_ID"
    echo "   - FEISHU_APP_SECRET"
    echo "   - AI_MODEL_API_KEY"
    echo ""
    echo "2. 重启应用服务:"
    echo "   cd /opt/malong-management"
    echo "   docker compose restart app"
    echo ""
    echo "3. 验证部署:"
    echo "   curl http://localhost:8000/api/v1/health"
    echo ""
    echo "4. 访问服务:"
    echo "   - 应用: http://<服务器IP>:8000"
    echo "   - 数据库管理: http://<服务器IP>:8080"
    echo ""
    echo "5. 查看日志:"
    echo "   docker compose logs -f app"
    echo ""
    echo "6. 常用命令:"
    echo "   - 启动:   docker compose start"
    echo "   - 停止:   docker compose stop"
    echo "   - 重启:   docker compose restart"
    echo "   - 查看状态: docker compose ps"
    echo ""
}

# 主函数
main() {
    clear
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║       管理助手 - Ubuntu 部署脚本                          ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""

    # 检查权限
    check_root

    # 检查系统
    check_ubuntu_version
    check_disk_space
    check_memory

    # 更新系统
    update_system

    # 询问部署方式
    echo ""
    log_info "选择部署方式:"
    echo "  1. Docker 部署（推荐）"
    echo "  2. 原生部署"
    echo ""
    read -p "请输入选项 (1-2): " DEPLOY_METHOD

    case $DEPLOY_METHOD in
        1)
            log_info "选择 Docker 部署"

            # 安装 Docker
            install_docker

            # 创建部署目录
            create_deployment_directory

            # 创建环境配置
            create_env_file

            # 创建 Dockerfile
            create_dockerfile

            # 创建备份脚本
            create_backup_script

            # 配置防火墙
            configure_firewall

            # 启动服务
            start_docker_services

            # 显示完成信息
            show_completion_info
            ;;

        2)
            log_info "选择原生部署"

            # 安装依赖
            install_postgresql
            install_redis

            # 创建部署目录
            create_deployment_directory

            # 创建 systemd 服务
            create_systemd_service

            # 创建备份脚本
            create_backup_script

            # 配置防火墙
            configure_firewall

            log_warning "原生部署需要手动配置 Python 环境和启动应用"
            log_info "请参考部署指南进行后续配置"
            ;;

        *)
            log_error "无效选项"
            exit 1
            ;;
    esac

    log_success "部署脚本执行完成"
}

# 执行主函数
main

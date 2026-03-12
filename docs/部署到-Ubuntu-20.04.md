# Ubuntu 20.04 生产环境部署指南

## 问题说明

### GitHub Actions Docker 构建错误

您遇到的错误是由于 GitHub Actions 的 Docker 缓存配置导致的：

```
ERROR: failed to build: Cache export is not supported for the docker driver.
```

**原因**: `cache-from` 和 `cache-to` 使用了 `type=gha`（GitHub Actions 缓存），但这需要 Docker Buildx 使用 `docker-container` 驱动，而不是默认的 `docker` 驱动。

---

## 解决方案

### 1. 修复 GitHub Actions Docker 构建

修改 `.github/workflows/docker-build.yml`:

```yaml
name: Docker Build and Push

on:
  push:
    branches: [ "master" ]
    tags: [ "v*" ]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to the Container registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata (tags, labels) for Docker
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          # 移除 cache-from 和 cache-to 配置，或使用正确的配置
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**关键修改**:
- 添加 `docker/setup-buildx-action@v3` 步骤来设置 Buildx
- 这会自动创建支持缓存的 builder

---

## Ubuntu 20.04 生产环境部署

### 系统要求

- **操作系统**: Ubuntu 20.04 LTS
- **Python**: 3.11+ (推荐 3.11)
- **PostgreSQL**: 15+
- **Redis**: 7+ (可选，用于缓存)
- **内存**: 至少 4GB (推荐 8GB)
- **磁盘**: 至少 20GB
- **CPU**: 至少 2核

### 部署步骤

#### 1. 更新系统

```bash
# 以 root 或 sudo 运行
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y curl wget git software-properties-common
```

#### 2. 安装 Python 3.11

```bash
# 添加 deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# 安装 Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 安装 pip
curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python3.11 get-pip.py
rm get-pip.py

# 验证安装
python3.11 --version  # 应显示 3.11.x
pip3.11 --version
```

#### 3. 安装 PostgreSQL 15

```bash
# 导入 PostgreSQL 签名密钥
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /usr/share/keyrings/postgresql-archive-keyring.gpg

# 添加 PostgreSQL 15 仓库
echo "deb [signed-by=/usr/share/keyrings/postgresql-archive-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/postgresql.list

sudo apt update
sudo apt install -y postgresql-15 postgresql-contrib-15

# 启动 PostgreSQL 服务
sudo systemctl enable postgresql
sudo systemctl start postgresql

# 创建数据库和用户
sudo -u postgres psql << EOF
CREATE DATABASE powerassistant;
CREATE USER powerassistant_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE powerassistant TO powerassistant_user;
ALTER USER powerassistant_user CREATEDB;
EOF

# 验证数据库
sudo -u postgres psql -c "\l"
```

#### 4. 安装 Redis (可选)

```bash
# 安装 Redis 7
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list

sudo apt update
sudo apt install -y redis-server

# 配置 Redis 作为服务
sudo systemctl enable redis-server
sudo systemctl start redis-server

# 验证 Redis
redis-cli ping  # 应返回 PONG
```

#### 5. 部署应用

```bash
# 创建部署目录
sudo mkdir -p /opt/powerassistant
sudo chown $USER:$USER /opt/powerassistant
cd /opt/powerassistant

# 克隆代码
git clone git@github.com:chinaxiaoshijie/PowerAssistant.git .

# 创建 Python 虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 创建环境变量配置
cp .env.example .env
```

#### 6. 配置环境变量

编辑 `.env` 文件:

```bash
nano .env
```

配置内容:

```bash
# 数据库配置
DATABASE_URL=postgresql://powerassistant_user:your_secure_password_here@localhost:5432/powerassistant

# Redis 配置 (可选)
REDIS_URL=redis://localhost:6379/0

# 飞书配置
FEISHU_APP_ID=cli_xxxxxx
FEISHU_APP_SECRET=xxxxxx

# AI 模型配置
AI_MODEL_API_KEY=sk-xxxxxx

# 应用配置
SECRET_KEY=your-random-secret-key-here-change-this-in-production
LOG_LEVEL=INFO
```

**安全提示**:
- 使用强密码替换 `your_secure_password_here`
- 使用随机字符串生成 `SECRET_KEY` (例如: `python -c "import secrets; print(secrets.token_hex(32))"`)
- 不要将 `.env` 文件提交到版本控制

#### 7. 初始化数据库

```bash
source venv/bin/activate

# 运行数据库迁移
alembic upgrade head

# 验证数据库表已创建
psql -U powerassistant_user -d powerassistant -c "\dt"
```

#### 8. 配置 systemd 服务

创建 systemd 服务文件:

```bash
sudo nano /etc/systemd/system/powerassistant.service
```

内容:

```ini
[Unit]
Description=PowerAssistant - AI Management Assistant
After=network.target postgresql.service redis-server.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/powerassistant
Environment="PATH=/opt/powerassistant/venv/bin"
ExecStart=/opt/powerassistant/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

# 日志配置
StandardOutput=journal
StandardError=journal
SyslogIdentifier=powerassistant

# 安全配置
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

启动服务:

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start powerassistant

# 设置开机自启
sudo systemctl enable powerassistant

# 检查服务状态
sudo systemctl status powerassistant

# 查看日志
sudo journalctl -u powerassistant -f
```

#### 9. 配置 Nginx (可选)

```bash
# 安装 Nginx
sudo apt install -y nginx

# 创建 Nginx 配置
sudo nano /etc/nginx/sites-available/powerassistant
```

配置内容:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为实际域名

    # 日志
    access_log /var/log/nginx/powerassistant-access.log;
    error_log /var/log/nginx/powerassistant-error.log;

    # 反向代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件
    location /static/ {
        alias /opt/powerassistant/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 健康检查
    location /api/v1/health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }
}
```

启用配置:

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/powerassistant /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

#### 10. 配置防火墙

```bash
# 允许 HTTP (80) 和 HTTPS (443)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 如果直接访问应用端口
sudo ufw allow 8000/tcp

# 启用防火墙
sudo ufw enable

# 检查状态
sudo ufw status
```

#### 11. 配置 SSL 证书 (可选)

使用 Let's Encrypt 获取免费 SSL 证书:

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

---

## 验证部署

### 1. 检查服务状态

```bash
# 检查应用服务
sudo systemctl status powerassistant

# 检查数据库
sudo systemctl status postgresql

# 检查 Redis (如果安装)
sudo systemctl status redis-server

# 检查 Nginx (如果安装)
sudo systemctl status nginx
```

### 2. 访问应用

```bash
# 本地测试
curl http://localhost:8000/api/v1/health

# 访问 Dashboard
curl http://localhost:8000/dashboard/

# 访问 API 文档
curl http://localhost:8000/docs
```

### 3. 检查日志

```bash
# 应用日志
sudo journalctl -u powerassistant -n 100

# Nginx 访问日志
tail -f /var/log/nginx/powerassistant-access.log

# Nginx 错误日志
tail -f /var/log/nginx/powerassistant-error.log
```

---

## 监控和维护

### 1. 日志轮转

```bash
sudo nano /etc/logrotate.d/powerassistant
```

配置:

```bash
/var/log/nginx/powerassistant-*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 `cat /var/run/nginx.pid`
        fi
    endscript
}
```

### 2. 数据库备份

创建备份脚本:

```bash
sudo nano /usr/local/bin/backup-powerassistant.sh
```

脚本内容:

```bash
#!/bin/bash

BACKUP_DIR="/opt/backups/powerassistant"
DATE=$(date +%Y%m%d_%H%M%S)
PGPASSWORD="your_secure_password_here" pg_dump -U powerassistant_user powerassistant > "$BACKUP_DIR/backup_$DATE.sql"

# 保留最近30天的备份
find "$BACKUP_DIR" -name "backup_*.sql" -mtime +30 -delete
```

创建定时任务:

```bash
# 编辑 crontab
crontab -e
```

添加:

```bash
# 每天凌晨2点备份
0 2 * * * /usr/local/bin/backup-powerassistant.sh
```

### 3. 应用更新

```bash
# 进入部署目录
cd /opt/powerassistant

# 激活虚拟环境
source venv/bin/activate

# 拉取最新代码
git pull origin master

# 安装新依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 重启服务
sudo systemctl restart powerassistant
```

---

## 故障排除

### 问题1: 应用无法启动

```bash
# 检查日志
sudo journalctl -u powerassistant -f

# 检查端口是否被占用
sudo netstat -tlnp | grep 8000

# 手动运行测试
source /opt/powerassistant/venv/bin/activate
cd /opt/powerassistant
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 问题2: 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
sudo systemctl status postgresql

# 测试数据库连接
psql -U powerassistant_user -d powerassistant -c "SELECT 1;"

# 检查 pg_hba.conf 配置
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

### 问题3: 飞书同步失败

```bash
# 检查环境变量
grep FEISHU_APP_ID /opt/powerassistant/.env

# 手动测试飞书 API
cd /opt/powerassistant
source venv/bin/activate
python -c "from src.services.feishu.client import FeishuClient; import asyncio; asyncio.run(FeishuClient().__aenter__())"
```

---

## 性能优化建议

### 1. 增加 Worker 数量

在 `powerassistant.service` 中调整 `--workers` 参数:

```ini
ExecStart=/opt/powerassistant/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 8
```

建议: CPU 核心数 * 2 + 1

### 2. 启用 Redis 缓存

在 `.env` 中配置:

```bash
REDIS_URL=redis://localhost:6379/0
```

### 3. 配置 Nginx 缓存

在 Nginx 配置中添加:

```nginx
# 启用 Gzip 压缩
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

# 启用缓存
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=powerassistant_cache:10m max_size=100m inactive=60m use_temp_path=off;
proxy_cache powerassistant_cache;
proxy_cache_valid 200 302 10m;
proxy_cache_valid 404 1m;
```

### 4. 数据库连接池

确保 SQLAlchemy 连接池配置合理:

```python
# 在 database.py 中
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,        # 连接池大小
    max_overflow=40,     # 最大溢出连接数
    pool_pre_ping=True,  # 预检测连接
    pool_recycle=3600,   # 连接回收时间
)
```

---

## 安全加固

### 1. 限制数据库访问

```bash
# 编辑 pg_hba.conf
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

只允许本地访问:

```
# IPv4 local connections:
host    powerassistant    powerassistant_user    127.0.0.1/32    md5
```

### 2. 配置防火墙

```bash
# 只允许必要的端口
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

### 3. 定期更新系统

```bash
# 创建自动更新脚本
sudo apt install -y unattended-upgrades

# 配置自动安全更新
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## Docker 替代部署方案

如果不想使用系统安装，可以使用 Docker:

```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 启动服务
cd /opt/powerassistant
sudo docker-compose up -d

# 查看日志
sudo docker-compose logs -f app
```

---

**部署完成！** 🎉

系统已部署在 Ubuntu 20.04 服务器上，可以通过域名或 IP 地址访问。

# 管理助手 - Docker 本地部署快速开始

## 🚀 快速启动（3 步）

### 1️⃣ 配置环境变量

**Linux/Mac:**
```bash
# 复制配置文件
cp .env.prod.example .env.docker

# 编辑配置文件（必须填写）
vi .env.docker  # 或使用你喜欢的编辑器
```

**Windows:**
```cmd
:: 复制配置文件
copy .env.prod.example .env.docker

:: 编辑配置文件（必须填写）
notepad .env.docker
```

**必需配置项：**

```bash
# 飞书应用配置（在 https://open.feishu.cn/ 创建企业自建应用）
FEISHU_APP_ID=cli_xxxxxx
FEISHU_APP_SECRET=xxxxxx

# 阿里云 DashScope API（在 https://dashscope.aliyun.com/ 获取）
DASHSCOPE_API_KEY=sk-xxxxxx
```

### 2️⃣ 启动服务

**Linux/Mac:**
```bash
# 使用快速启动脚本（推荐）
chmod +x start.sh
./start.sh

# 或手动启动
docker-compose up -d --build
```

**Windows:**
```cmd
:: 使用快速启动脚本（推荐）
start.bat

:: 或手动启动
docker-compose up -d --build
```

### 3️⃣ 访问系统

等待 1-2 分钟后访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| **API 文档** | http://localhost:8000/api/docs | Swagger UI |
| **Dashboard** | http://localhost:8000/dashboard | AI 情报中心 |
| **健康检查** | http://localhost:8000/api/v1/health | 系统状态 |
| **Adminer** | http://localhost:8080 | 数据库管理工具 |

数据库连接信息（用于 Adminer）：
- 系统：PostgreSQL
- 服务器：db
- 用户名：postgres
- 密码：postgres
- 数据库：malong_management

## 🔧 常用命令

### 查看日志
```bash
# 查看应用日志
docker-compose logs -f app

# 查看所有服务日志
docker-compose logs -f
```

### 管理服务
```bash
# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 重新构建并启动
docker-compose up -d --build
```

### 数据库操作
```bash
# 进入数据库容器
docker-compose exec db psql -U postgres -d malong_management

# 备份数据库
docker-compose exec db pg_dump -U postgres malong_management > backup.sql

# 恢复数据库
docker-compose exec -T db psql -U postgres -d malong_management < backup.sql
```

## 📁 项目结构

```
管理助手/
├── docker-compose.yml       # Docker Compose 配置
├── Dockerfile               # Docker 镜像构建文件
├── .env.docker             # Docker 环境变量配置 ⚠️ 必须配置
├── .env.prod.example       # 配置模板（复制为 .env.docker）
├── start.sh                # Linux/Mac 启动脚本
├── start.bat               # Windows 启动脚本
├── Docker-部署指南.md      # 详细部署文档
└── src/                    # 应用源代码
    ├── main.py            # FastAPI 入口
    ├── config/            # 配置文件
    ├── api/               # API 路由
    ├── services/          # 业务服务
    └── models/            # 数据模型
```

## ⚙️ 服务说明

| 服务名称 | 镜像 | 端口 | 说明 |
|---------|------|------|------|
| **app** | 自定义 | 8000 | FastAPI 应用服务 |
| **db** | postgres:15-alpine | 5432 | PostgreSQL 数据库 |
| **redis** | redis:7-alpine | 6379 | Redis 缓存 |
| **migration** | 自定义 | - | 数据库迁移（一次性） |
| **adminer** | adminer:4 | 8080 | 数据库管理工具（可选） |

## 🐛 故障排查

### 应用无法启动

```bash
# 检查日志
docker-compose logs app

# 检查容器状态
docker-compose ps

# 检查环境变量
docker-compose exec app env | grep FEISHU
```

### 数据库连接失败

```bash
# 检查数据库服务
docker-compose ps db

# 测试数据库连接
docker-compose exec db psql -U postgres -d malong_management -c "SELECT 1"
```

### 端口被占用

修改 `docker-compose.yml` 中的端口映射：

```yaml
app:
  ports:
    - "9000:8000"  # 改为 9000
```

### 内存不足

调整 Docker Desktop 的内存分配（设置 → Resources → Memory，至少 4GB）

## 📝 飞书应用配置步骤

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 登录企业管理员账号
3. 创建企业自建应用
4. 在「凭证与基础信息」中获取：
   - App ID
   - App Secret
5. 在「权限管理」中申请权限：
   - `contact:user.read` - 读取用户列表
   - `task:task:read` - 读取任务数据
   - `docs:doc:read` - 读取文档内容
   - `okr:okr:read` - 读取 OKR 数据
6. 在「应用功能」→「事件订阅」中配置接收事件（可选）
7. 将 App ID 和 App Secret 填入 `.env.docker`

## 🔐 安全建议

1. **不要提交真实密钥**：确保 `.env.docker` 在 `.gitignore` 中
2. **修改数据库密码**：在生产环境中修改 `docker-compose.yml` 中的 PostgreSQL 密码
3. **配置 HTTPS**：使用 Nginx 或 Traefik 配置 HTTPS
4. **限制 CORS**：生产环境中限制 `CORS_ALLOWED_ORIGINS`
5. **定期备份**：定期备份 `postgres_data` 卷

## 📚 更多文档

- [Docker-部署指南.md](./Docker-部署指南.md) - 详细部署文档
- [docs/](./docs/) - 项目技术文档
- [CLAUDE.md](./CLAUDE.md) - 项目配置说明

## 💡 技术栈

- **后端**: Python 3.11 + FastAPI
- **数据库**: PostgreSQL 15
- **缓存**: Redis 7
- **容器化**: Docker + Docker Compose
- **AI 引擎**: 阿里云 DashScope (Qwen)
- **数据源**: 飞书开放平台

## 🆘 获取帮助

- 查看日志：`docker-compose logs -f app`
- 检查文档：`docs/` 目录
- 联系支持：根据公司内部流程

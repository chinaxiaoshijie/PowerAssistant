# 快速启动指南

5 分钟快速配置飞书并启动管理助手。

## 步骤 1: 获取飞书凭证（2分钟）

### 1.1 创建应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 登录企业管理员账号
3. 点击「创建企业自建应用」
4. 填写应用名称：**管理助手**
5. 点击「创建应用」

### 1.2 获取凭证

1. 进入应用详情页
2. 点击「凭证与基础信息」
3. 复制 **App ID** 和 **App Secret**

```
示例格式：
App ID: cli_xxxxxxxxxxxxxxxx
App Secret: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 1.3 申请权限

1. 点击左侧「权限管理」
2. 搜索并勾选以下权限：
   - ✅ `contact:department:readonly`
   - ✅ `contact:user:readonly`
3. 点击「批量申请」
4. 填写理由：「用于企业内部研发管理系统同步组织架构」
5. 提交申请（通常即时通过）

## 步骤 2: 配置环境变量（1分钟）

编辑项目根目录的 `.env` 文件：

```bash
# 使用你喜欢的编辑器
nano .env  # 或 vim .env 或 code .env
```

填入飞书凭证：

```bash
# 飞书配置（必填）
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 其他配置保持默认即可
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/malong_management
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## 步骤 3: 验证配置（1分钟）

```bash
# 1. 激活虚拟环境
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 2. 运行验证脚本
python scripts/verify-feishu.py
```

预期输出：
```
============================================================
飞书配置验证
============================================================

✅ FEISHU_APP_ID: cli_xxxxxxxxxxxxxxxx
✅ FEISHU_APP_SECRET: xxxx****xxxx
✅ FEISHU_BASE_URL: https://open.feishu.cn/open-apis

============================================================
测试飞书 API 连接
============================================================

1. 获取访问令牌...
   ✅ 成功 (Token: t-xxxxxxxxxxxxxxxx...)

2. 获取部门列表...
   ✅ 成功 (获取 5 个部门)

3. 获取用户列表...
   ✅ 成功 (获取 10 个用户)

============================================================
✅ 飞书配置验证通过！
============================================================
```

## 步骤 4: 启动服务（1分钟）

### 方式一：Docker（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f app
```

### 方式二：本地运行

```bash
# 1. 确保 PostgreSQL 已安装并运行

# 2. 运行数据库迁移
alembic upgrade head

# 3. 启动应用
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 步骤 5: 测试 API（1分钟）

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 触发全量同步
curl -X POST http://localhost:8000/api/v1/sync/full

# 查看部门列表
curl http://localhost:8000/api/v1/organization/departments

# 查看员工列表
curl http://localhost:8000/api/v1/organization/employees
```

浏览器访问：
- API 文档：http://localhost:8000/api/docs
- 健康检查：http://localhost:8000/api/v1/health

## 故障排除

### 验证失败

```
❌ FEISHU_APP_ID 未配置
```
**解决**：检查 `.env` 文件是否存在，且包含正确的 App ID

### 连接失败

```
❌ 连接失败: tenant_access_token invalid
```
**解决**：
1. 检查 App ID 和 App Secret 是否正确
2. 确认应用已创建并启用
3. 检查权限是否已申请并审批

### 同步失败

```
Permission denied: contact:user:readonly
```
**解决**：
1. 在飞书开放平台申请权限
2. 确认权限已审批
3. 在飞书管理后台设置应用可见范围

## 获取帮助

- 📖 [详细配置文档](feishu-setup.md)
- 📖 [Docker 部署文档](deployment/docker.md)
- 🌐 [飞书开放平台](https://open.feishu.cn/)
- 🐛 提交 Issue 或联系技术支持

## 下一步

完成配置后，你可以：

1. **查看 API 文档**：http://localhost:8000/api/docs
2. **触发同步**：使用 API 或等待定时任务（每6小时）
3. **查询数据**：使用组织架构 API 查询部门、员工
4. **监控状态**：查看同步历史和状态

祝你使用愉快！

# 飞书开放平台配置指南

本文档详细介绍如何在飞书开放平台创建应用并配置权限，以获取 AppID 和 AppSecret。

## 一、创建飞书应用

### 1.1 访问飞书开放平台

1. 打开 [飞书开放平台](https://open.feishu.cn/)
2. 使用企业管理员账号登录
3. 进入「开发者后台」

### 1.2 创建企业自建应用

1. 点击「创建企业自建应用」
2. 填写应用信息：
   - **应用名称**：管理助手（或自定义）
   - **应用描述**：码隆科技研发与交付管理决策引擎
   - **应用图标**：上传应用图标（可选）
3. 点击「创建应用」

### 1.3 获取应用凭证

创建成功后，进入应用详情页：

1. 点击左侧「凭证与基础信息」
2. 记录以下信息：
   - **App ID**（格式：cli_xxxxxx）
   - **App Secret**（点击显示并复制）

```bash
# 示例格式
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

⚠️ **重要**：App Secret 只显示一次，请务必妥善保存！

## 二、配置应用权限

### 2.1 添加通讯录权限

管理助手需要访问组织架构信息，需要申请以下权限：

#### 必需权限

| 权限 | 权限代码 | 说明 |
|------|----------|------|
| 获取部门列表 | `contact:department:readonly` | 读取部门架构 |
| 获取部门详情 | `contact:department:readonly` | 读取部门详细信息 |
| 获取用户列表 | `contact:user:readonly` | 读取员工信息 |
| 获取用户详情 | `contact:user:readonly` | 读取员工详细信息 |

#### 可选权限（根据需求添加）

| 权限 | 权限代码 | 说明 |
|------|----------|------|
| 获取任务列表 | `task:task:read` | 读取飞书任务 |
| 获取文档内容 | `docs:doc:read` | 读取飞书文档 |
| 获取 OKR | `okr:okr:read` | 读取 OKR 数据 |

### 2.2 申请权限步骤

1. 进入应用详情页
2. 点击左侧「权限管理」
3. 在搜索框中输入权限代码（如 `contact:user:readonly`）
4. 勾选需要的权限
5. 点击「批量申请」
6. 填写申请理由：

```
申请理由示例：

用于企业内部研发管理系统同步组织架构，实现：
1. 自动同步部门和员工信息
2. 生成研发资源分配报告
3. 统计团队人员结构

此应用仅供企业内部使用，不会获取或存储敏感信息。
```

7. 提交申请，等待管理员审批（通常即时通过）

## 三、配置环境变量

### 3.1 开发环境

编辑项目根目录的 `.env` 文件：

```bash
# 飞书配置（从开放平台获取）
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 数据库配置（保持默认或修改）
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/malong_management

# 应用配置
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### 3.2 生产环境

编辑 `.env` 文件（基于 `.env.prod.example`）：

```bash
# 飞书配置（必填）
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 数据库配置（修改为强密码）
DB_USER=postgres
DB_PASSWORD=YourStrongPassword123!
DB_NAME=malong_management

# 应用配置
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## 四、验证配置

### 4.1 本地验证

```bash
# 1. 确保虚拟环境已激活
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 运行健康检查
python -c "
import asyncio
import sys
sys.path.insert(0, 'src')
from services.feishu.client import FeishuClient

async def test():
    async with FeishuClient() as client:
        token = await client._get_access_token()
        print(f'Token acquired: {token[:20]}...')
        print('✅ 飞书连接成功！')

asyncio.run(test())
"
```

### 4.2 Docker 验证

```bash
# 1. 启动服务
docker-compose up -d

# 2. 查看日志，确认无连接错误
docker-compose logs -f app

# 3. 测试健康检查端点
curl http://localhost:8000/api/v1/health/feishu
```

预期响应：
```json
{
  "status": "healthy",
  "message": "Feishu API connection successful",
  "timestamp": "2026-03-03T12:00:00"
}
```

### 4.3 测试部门同步

```bash
# 触发全量同步
curl -X POST http://localhost:8000/api/v1/sync/full

# 查看同步状态
curl http://localhost:8000/api/v1/sync/status

# 查看部门列表
curl http://localhost:8000/api/v1/organization/departments
```

## 五、常见问题

### 5.1 权限不足

**错误信息**：
```
Permission denied: contact:user:readonly
```

**解决方法**：
1. 检查是否已申请权限
2. 确认权限已审批通过
3. 重新获取 Token（权限变更后需要重新获取）

### 5.2 App Secret 错误

**错误信息**：
```
tenant_access_token invalid
```

**解决方法**：
1. 确认 App Secret 复制完整（无空格）
2. 检查环境变量是否正确设置
3. 在飞书平台重置 App Secret

### 5.3 网络连接失败

**错误信息**：
```
Cannot connect to host open.feishu.cn
```

**解决方法**：
1. 检查服务器网络连接
2. 确认防火墙允许访问飞书域名
3. 测试 DNS 解析：`nslookup open.feishu.cn`

### 5.4 部门数据为空

**可能原因**：
1. 应用未被授权访问通讯录
2. 同步用户没有部门查看权限

**解决方法**：
1. 确认已申请 `contact:department:readonly` 权限
2. 在飞书管理后台设置应用可见范围

## 六、飞书管理后台设置

### 6.1 设置应用可见范围

1. 进入飞书管理后台
2. 点击「工作台」→「应用管理」
3. 找到「管理助手」应用
4. 点击「设置可见范围」
5. 选择需要同步的部门或全员

### 6.2 配置 IP 白名单（可选）

如果飞书后台启用了 IP 白名单：

1. 进入应用详情页
2. 点击「安全设置」
3. 添加服务器公网 IP 到白名单

## 七、安全建议

### 7.1 密钥管理

- ✅ 使用环境变量存储 App Secret
- ✅ 生产环境使用 Docker Secrets 或密钥管理服务
- ❌ 不要将密钥提交到代码仓库
- ❌ 不要将密钥硬编码在代码中

### 7.2 权限最小化

- 只申请必需的权限
- 定期审查已授权的权限
- 移除不再需要的权限

### 7.3 定期轮换

- 定期更换 App Secret（建议每 90 天）
- 监控 API 调用日志
- 发现异常立即重置密钥

## 八、相关资源

- [飞书开放平台文档](https://open.feishu.cn/document/home/index)
- [获取 tenant_access_token](https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal)
- [通讯录 API](https://open.feishu.cn/document/server-docs/contact-v3/department/list)
- [权限列表](https://open.feishu.cn/document/server-docs/permission-list)

## 九、获取帮助

如遇到问题：
1. 查看飞书开放平台[开发者社区](https://open.feishu.cn/community)
2. 提交[工单](https://open.feishu.cn/contact)
3. 联系码隆科技技术支持

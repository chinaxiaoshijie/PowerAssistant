# 数据同步使用指南

## 快速开始

### 1. 一键数据同步（推荐）

确保服务正在运行，然后执行：

```powershell
cd D:\项目\管理助手
.\venv\Scripts\Activate.ps1
python run_sync.py
```

这会完成：
- 初始化数据库表结构
- 添加爬虫配置
- 从 GitHub 抓取 AI 项目数据
- 同步飞书通讯录

### 2. 启动自动调度（后台持续同步）

```powershell
python scripts/start_scheduler.py
```

调度任务：
| 任务 | 频率 | 说明 |
|------|------|------|
| GitHub 抓取 | 每 12 小时 | AI 项目和工具 |
| arXiv 抓取 | 每 6 小时 | AI 研究论文 |
| Hacker News | 每 3 小时 | 技术讨论 |
| 飞书同步 | 每小时 | 组织架构和员工 |
| 日报生成 | 每天 9:00 | 情报汇总报告 |

### 3. 通过 API 手动触发

确保服务运行后，访问 Swagger UI：
```
http://localhost:8000/api/docs
```

使用以下接口：
- `POST /api/v1/dashboard/trigger-crawl` - 手动触发抓取
- `POST /api/v1/sync/organization` - 手动同步飞书

## 查看数据

### Dashboard
打开浏览器访问：
```
http://localhost:8000/dashboard
```

### API 端点
- `GET /api/v1/dashboard/stats` - 统计数据
- `GET /api/v1/dashboard/items` - 情报列表
- `GET /api/v1/organization/departments` - 部门列表
- `GET /api/v1/organization/employees` - 员工列表

## 故障排查

### 数据库连接失败
```powershell
# 检查 PostgreSQL 是否运行
docker ps

# 如果没有运行，启动它
docker start malong-postgres
```

### 飞书同步失败
1. 检查 `.env` 文件中的飞书配置：
   - FEISHU_APP_ID
   - FEISHU_APP_SECRET

2. 确保飞书应用有权限：
   - `contact:department:readonly`
   - `contact:user:readonly`

### GitHub 抓取失败
GitHub API 有请求限制。如需更多配额，在 `.env` 中添加：
```
GITHUB_TOKEN=your_github_personal_access_token
```

## 数据结构

### IntelligenceItem（情报项）
```python
{
    "id": 1,
    "source_type": "github",  # github / arxiv / hackernews
    "title": "项目名称",
    "url": "https://...",
    "summary": "AI 生成的摘要",
    "relevance_score": 0.92,  # 0-1 相关度
    "tags": ["AI", "Python"],
    "is_read": False,
    "created_at": "2026-03-04..."
}
```

### Department（部门）
```python
{
    "id": 1,
    "feishu_dept_id": "部门ID",
    "name": "研发中心",
    "parent_id": "上级部门ID",
    "member_count": 50
}
```

### Employee（员工）
```python
{
    "id": 1,
    "feishu_user_id": "用户ID",
    "name": "张三",
    "email": "zhangsan@malong.com",
    "job_title": "高级工程师",
    "department_ids": ["部门ID1", "部门ID2"]
}
```

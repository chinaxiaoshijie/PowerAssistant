# API 文档

完整的 API 文档请访问: http://localhost:8000/docs

## 快速开始

### 健康检查

```bash
GET /api/v1/health
```

### 认证

所有 API 请求需要在 Header 中包含认证信息:

```
Authorization: Bearer YOUR_API_TOKEN
```

## 核心接口

### Dashboard

#### 获取概览数据

```bash
GET /api/v1/dashboard/stats
```

**响应**:
```json
{
  "total_tasks": 150,
  "completed_tasks": 100,
  "active_projects": 15,
  "overall_health": 0.85
}
```

### 飞书集成

#### 同步组织架构

```bash
POST /api/v1/feishu/sync/organization
```

#### 同步任务

```bash
POST /api/v1/feishu/sync/tasks
```

#### 同步项目

```bash
POST /api/v1/feishu/sync/projects
```

#### 同步 OKR

```bash
POST /api/v1/feishu/sync/okrs
```

### AI 智能体

#### 运行所有智能体

```bash
POST /api/v1/ai/agents/run
```

**响应**:
```json
{
  "timestamp": "2026-03-11T10:00:00",
  "agents": {
    "development_practice": {...},
    "algorithm_research": {...},
    "product_innovation": {...},
    "general_technology": {...}
  }
}
```

#### 运行特定智能体

```bash
POST /api/v1/ai/agents/{agent_type}
```

**参数**:
- `agent_type`: `development_practice` | `algorithm_research` | `product_innovation` | `general_technology`

### 报告

#### 生成周报

```bash
GET /api/v1/reports/weekly?week_offset=-1
```

**参数**:
- `week_offset`: 周偏移量 (0=本周, -1=上周)

#### 生成日报

```bash
GET /api/v1/reports/daily
```

#### 获取历史报告

```bash
GET /api/v1/reports/history
```

### 任务

#### 获取任务列表

```bash
GET /api/v1/tasks?status=all&page=1&limit=20
```

**参数**:
- `status`: `all` | `completed` | `in_progress`
- `page`: 页码
- `limit`: 每页数量

#### 获取任务详情

```bash
GET /api/v1/tasks/{task_id}
```

### 项目

#### 获取项目列表

```bash
GET /api/v1/projects?page=1&limit=20
```

#### 获取项目详情

```bash
GET /api/v1/projects/{project_id}
```

## 错误响应

```json
{
  "detail": "错误描述",
  "status_code": 400
}
```

## 常见错误码

| 状态码 | 说明 |
|-------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

## 更多信息

访问 http://localhost:8000/docs 查看完整的交互式 API 文档。

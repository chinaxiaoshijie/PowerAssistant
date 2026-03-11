# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**管理助手**是码隆科技（Malong Technologies）研发与交付部门的智能决策引擎系统。该系统打通飞书业务数据，结合 AI 大模型能力，为研发团队负责人提供日常管理、季度规划和战略决策支持。

### 核心业务场景

```
管理决策引擎
├── 感知层 - 飞书数据接入（组织架构/任务/项目/OKR）
├── 分析层 - 研发健康度/交付健康度指标体系
├── 决策层 - AI 生成管理建议与风险预警
└── 输出层 - 周报/月报/战略文档自动生成
```

### 数据来源

| 数据源 | 类型 | 用途 |
|-------|------|------|
| 飞书组织架构 | 成员、岗位、角色 | 团队结构分析 |
| 飞书任务管理 | 工作任务、状态 | 研发进度跟踪 |
| 飞书项目表格 | 里程碑、风险 | 交付健康监控 |
| 飞书 OKR | 目标、关键结果 | 战略对齐分析 |
| 飞书文档 | 技术文档、周报 | 知识沉淀分析 |

## 开发环境设置

### 前置要求

- Python 3.11+
- PostgreSQL 15+
- Redis (可选，用于缓存和任务队列)

### Everything Claude Code 安装

本项目使用 [everything-claude-code](https://github.com/affaan-m/everything-claude-code) 开发系统：

```bash
# 方式一：插件安装（推荐）
/plugin marketplace add affaan-m/everything-claude-code
/plugin install everything-claude-code@everything-claude-code

# 方式二：手动安装规则和代理
git clone https://github.com/affaan-m/everything-claude-code.git
cd everything-claude-code
./install.sh python
```

安装后可用功能：
- **斜杠命令**: `/plan`, `/tdd`, `/code-review`, `/build-fix` 等
- **子代理**: planner, architect, tdd-guide, code-reviewer, security-reviewer
- **技能系统**: backend-patterns, python-patterns, verification-loop 等
- **安全扫描**: `npx ecc-agentshield scan`

### 本地开发启动

```bash
# 1. 克隆仓库后进入目录
cd 管理助手

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置飞书 AppID/AppSecret 和数据库连接

# 5. 初始化数据库
alembic upgrade head

# 6. 启动开发服务器
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker 启动

```bash
# 启动所有服务（PostgreSQL + Redis + App）
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down
```

## 技术栈

| 层级 | 技术 | 说明 |
|-----|------|------|
| **后端框架** | Python + FastAPI | 易于对接大模型接口 |
| **数据库** | PostgreSQL | 关系型查询 + JSONB 存储 |
| **数据同步** | 飞书 OpenAPI | 定期拉取业务数据 |
| **AI 引擎** | 多模型可配置 | DeepSeek/Claude/OpenAI 等 |
| **前端** | Web Dashboard | 指标可视化看板 |
| **开发系统** | Everything Claude Code | Agent 驱动的开发工作流 |

## 项目结构

```
管理助手/
├── CLAUDE.md                      # 项目配置文件
├── 原始需求.md                     # 需求原始描述
├── 细化需求-chatgpt.md            # 细化需求文档
├── 飞书业务数据打通与独立决策引擎建设方案-gemini.md  # 架构方案
├── 飞书数据对接方案-chatgpt.md    # 飞书对接方案
├── src/                           # 源代码目录
│   ├── api/                       # FastAPI 接口层
│   ├── core/                      # 核心业务逻辑
│   ├── models/                    # 数据模型 (SQLAlchemy)
│   ├── services/                  # 业务服务层
│   │   ├── feishu/               # 飞书数据同步服务
│   │   ├── metrics/              # 指标计算服务
│   │   ├── ai_engine/            # AI 决策引擎
│   │   └── report/               # 报告生成服务
│   ├── tasks/                     # 定时任务 (Celery/APScheduler)
│   └── utils/                     # 工具函数
├── config/                        # 配置文件
├── tests/                         # 测试代码
├── docs/                          # 技术文档
│   ├── api/                      # API 文档
│   ├── architecture/             # 架构设计文档
│   └── deployment/               # 部署文档
├── scripts/                       # 数据迁移/初始化脚本
├── skills/                        # Everything Claude Code 技能
│   ├── feishu-sync/              # 飞书同步技能
│   └── report-generation/        # 报告生成技能
└── docker-compose.yml            # 本地开发环境
```

## Everything Claude Code 命令

### 核心斜杠命令

| 命令 | 用途 | 使用场景 |
|------|------|---------|
| `/plan` | 功能实现规划 | 开始新功能前制定计划 |
| `/tdd` | 测试驱动开发 | 编写测试 → 实现 → 重构 |
| `/code-review` | 代码审查 | 代码完成后质量检查 |
| `/build-fix` | 修复构建错误 | 构建/测试失败时使用 |
| `/refactor-clean` | 死代码清理 | 重构和清理代码 |
| `/checkpoint` | 保存验证状态 | 关键节点保存进度 |
| `/verify` | 运行验证循环 | 检查实现质量 |
| `/learn` | 模式提取 | 从当前会话提取技能 |
| `/skill-create` | 生成技能文件 | 从 git 历史生成技能 |

### Python 专用命令

| 命令 | 用途 |
|------|------|
| `/python-review` | Python 代码专项审查 |
| `/db-review` | 数据库/Supabase 审查 |
| `/setup-pm` | 配置包管理器 |

### 多服务编排

| 命令 | 用途 |
|------|------|
| `/pm2` | 配置 PM2 多服务 |
| `/multi-plan` | 多服务并行规划 |
| `/multi-execute` | 多服务并行执行 |

### 使用示例

```bash
# 规划新功能
/plan "实现飞书任务数据同步模块"

# TDD 开发流程
/tdd "编写任务同步服务的单元测试"

# 代码审查
/code-review

# 修复构建错误
/build-fix

# 保存进度并验证
/checkpoint
/verify

# 从当前工作提取技能
/skill-create
```

## 子代理系统

Everything Claude Code 提供 13+ 个专业子代理：

### 开发代理

| 代理 | 文件路径 | 用途 |
|------|---------|------|
| **planner** | `~/.claude/agents/planner.md` | 功能实现规划 |
| **architect** | `~/.claude/agents/architect.md` | 系统设计决策 |
| **tdd-guide** | `~/.claude/agents/tdd-guide.md` | 测试驱动开发 |
| **code-reviewer** | `~/.claude/agents/code-reviewer.md` | 代码质量审查 |
| **security-reviewer** | `~/.claude/agents/security-reviewer.md` | 安全漏洞分析 |
| **build-error-resolver** | `~/.claude/agents/build-error-resolver.md` | 构建错误解决 |
| **refactor-cleaner** | `~/.claude/agents/refactor-cleaner.md` | 死代码清理 |
| **doc-updater** | `~/.claude/agents/doc-updater.md` | 文档同步更新 |

### 测试代理

| 代理 | 文件路径 | 用途 |
|------|---------|------|
| **e2e-runner** | `~/.claude/agents/e2e-runner.md` | Playwright E2E 测试 |

### Python 专用代理

| 代理 | 文件路径 | 用途 |
|------|---------|------|
| **python-reviewer** | `~/.claude/agents/python-reviewer.md` | Python 代码审查 |
| **database-reviewer** | `~/.claude/agents/database-reviewer.md` | 数据库审查 |

### 使用方式

**方式一：斜杠命令（推荐）**
```bash
/plan "实现飞书组织架构同步"
/tdd "编写 FeishuSyncService 测试"
/code-review
```

**方式二：手动调用 Agent**
```bash
# 在 Claude Code 中使用 Agent 工具
agent: planner, prompt: "规划飞书数据同步模块的实现"
```

**方式三：并行多代理分析**
```bash
# 复杂问题使用多个代理并行分析
/multi-plan "设计指标计算引擎架构"
```

## 技能系统 (Skills)

### 可用技能

| 技能 | 路径 | 用途 |
|------|------|------|
| **backend-patterns** | `~/.claude/skills/backend-patterns/` | API、数据库、缓存模式 |
| **python-patterns** | `~/.claude/skills/python-patterns/` | Python 设计模式 |
| **golang-patterns** | `~/.claude/skills/golang-patterns/` | Go 设计模式 |
| **django-patterns** | `~/.claude/skills/django-patterns/` | Django 架构模式 |
| **django-security** | `~/.claude/skills/django-security/` | Django 安全实践 |
| **django-tdd** | `~/.claude/skills/django-tdd/` | Django TDD 方法 |
| **verification-loop** | `~/.claude/skills/verification-loop/` | 验证循环模式 |
| **security-scan** | `~/.claude/skills/security-scan/` | AgentShield 安全扫描 |
| **article-writing** | `~/.claude/skills/article-writing/` | 长文写作 |
| **market-research** | `~/.claude/skills/market-research/` | 市场研究 |
| **content-engine** | `~/.claude/skills/content-engine/` | 多平台内容 |
| **frontend-slides** | `~/.claude/skills/frontend-slides/` | HTML 演示文稿 |
| **continuous-learning** | `~/.claude/skills/continuous-learning/` | 自动模式提取 |
| **iterative-retrieval** | `~/.claude/skills/iterative-retrieval/` | 渐进式上下文细化 |
| **skill-creator** | `~/.claude/skills/skill-creator/` | 技能创建指南 |

### 项目技能创建

为本项目创建自定义技能：

```bash
# 从当前会话提取技能
/learn

# 从 git 历史生成技能
/skill-create

# 同时生成本能（模式）
/skill-create --instincts
```

## 规则系统

遵循 `~/.claude/rules/` 目录下的开发规范：

### 通用规则 (`common/`)

| 规则文件 | 内容 |
|---------|------|
| `coding-style.md` | 不可变性、文件组织、代码质量 |
| `testing.md` | TDD、80% 覆盖率要求 |
| `git-workflow.md` | 提交格式、PR 流程 |
| `performance.md` | 模型选择、上下文管理 |
| `patterns.md` | 设计模式、骨架项目 |
| `agents.md` | 子代理委托策略 |
| `security.md` | 强制安全检查 |
| `hooks.md` | Hook 架构、TodoWrite 最佳实践 |

### Python 规则 (`python/`)

| 规则文件 | 内容 |
|---------|------|
| `coding-style.md` | Python 类型注解、文档字符串 |
| `testing.md` | pytest、覆盖率工具 |
| `patterns.md` | Python 设计模式 |
| `security.md` | Python 安全实践 |
| `hooks.md` | Black、Ruff 格式化 |

### 规则优先级

语言特定规则 > 通用规则（具体覆盖一般）

## 编码规范

### Python 代码风格

1. **类型注解**：所有函数必须添加类型注解
2. **文档字符串**：使用 Google Style docstrings
3. **不可变性**：创建新对象，永不修改现有对象
4. **错误处理**：显式处理所有异常，不静默吞掉错误
5. **数据验证**：使用 Pydantic 进行输入验证
6. **日志记录**：使用 structlog 结构化日志
7. **文件大小**：200-400 行典型，800 行最大
8. **函数大小**：<50 行

### 示例代码

```python
from typing import Optional
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()


class TaskMetrics(BaseModel):
    """任务指标数据模型.

    Attributes:
        total_tasks: 总任务数
        delayed_tasks: 延期任务数
        completion_rate: 完成率
    """
    total_tasks: int
    delayed_tasks: int
    completion_rate: float

    @property
    def delay_rate(self) -> float:
        """计算延期率."""
        if self.total_tasks == 0:
            return 0.0
        return self.delayed_tasks / self.total_tasks


async def calculate_team_metrics(
    team_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> TaskMetrics:
    """计算团队任务指标.

    Args:
        team_id: 团队 ID
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD

    Returns:
        TaskMetrics 对象

    Raises:
        ValueError: 日期格式无效
        NotFoundError: 团队不存在
    """
    logger.info(
        "calculating_team_metrics",
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
    )
    # 实现逻辑...
```

## 测试要求

### TDD 工作流程（强制）

```bash
# 1. 编写测试（RED）
/tdd "编写 FeishuClient 连接测试"

# 2. 运行测试 - 应该失败
pytest tests/services/feishu/test_client.py -v

# 3. 实现代码（GREEN）
# 编写最小实现使测试通过

# 4. 运行测试 - 应该通过
pytest tests/services/feishu/test_client.py -v

# 5. 重构（IMPROVE）
# 使用 /refactor-clean 清理代码

# 6. 验证覆盖率（80%+）
pytest --cov=src --cov-report=term-missing
```

### 测试结构

```
tests/
├── conftest.py           # 共享 fixtures
├── unit/                 # 单元测试
│   ├── services/
│   │   ├── feishu/
│   │   ├── metrics/
│   │   └── ai_engine/
│   └── utils/
├── integration/          # 集成测试
│   ├── api/
│   └── database/
└── fixtures/             # 测试数据
    ├── feishu_data.json
    └── mock_responses/
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定模块
pytest tests/services/metrics/

# 覆盖率报告
pytest --cov=src --cov-report=html

# 使用验证循环
/verify
```

## 安全扫描

使用 AgentShield 进行安全审计：

```bash
# 快速扫描
npx ecc-agentshield scan

# 自动修复
npx ecc-agentshield scan --fix

# 深度分析（三 Opus 4.6 代理）
npx ecc-agentshield scan --opus --stream

# 生成安全配置
npx ecc-agentshield init
```

### 安全审查清单

代码提交前自动检查：
- [ ] 无硬编码密钥
- [ ] 所有输入已验证
- [ ] SQL 注入防护
- [ ] XSS 防护
- [ ] CSRF 保护
- [ ] 错误信息不泄露敏感数据

## 开发工作流

### 标准功能开发流程

```bash
# 1. 规划阶段
/plan "实现飞书任务数据同步模块"
# → 生成详细实施计划

# 2. TDD 阶段
/tdd "编写 TaskSyncService 及测试"
# → RED: 编写测试
# → GREEN: 实现代码
# → 运行 pytest 验证

# 3. 代码审查阶段
/code-review
# → 质量检查
# → 安全问题扫描

# 4. 验证阶段
/verify
# → 运行完整验证循环

# 5. 重构阶段（如需）
/refactor-clean

# 6. 最终检查
/checkpoint
```

### 复杂功能开发流程

```bash
# 1. 架构设计
# 使用 architect 代理

# 2. 并行规划多个模块
/multi-plan "设计指标计算引擎"

# 3. 并行执行
/multi-execute

# 4. 多代理代码审查
# code-reviewer + security-reviewer + python-reviewer 并行
```

### 修复问题流程

```bash
# 构建/测试失败
/build-fix

# 安全漏洞发现
# 1. npx ecc-agentshield scan
# 2. security-reviewer 代理分析

# 代码质量问题
/code-review
/refactor-clean
```

### 飞书数据同步开发

```bash
# 1. 规划数据同步架构
/plan "飞书数据同步服务设计"

# 2. 编写 API 客户端测试
/tdd "编写 FeishuAPIClient 测试"

# 3. 实现同步逻辑
# 4. 代码审查
/code-review

# 5. 验证数据一致性
/verify
```

## 核心功能模块

### 1. 飞书数据同步 (services/feishu/)

- 组织架构同步
- 任务数据拉取
- 项目进度同步
- 文档内容抓取

### 2. 指标计算引擎 (services/metrics/)

| 指标类别 | 具体指标 | 计算方式 |
|---------|---------|---------|
| 研发健康度 | 模块成熟度指数 | 任务完成进度占比 |
| 研发健康度 | 延期率 | 延期任务数/总任务数 |
| 研发健康度 | 技术债浓度 | 技术债标签任务占比 |
| 交付健康度 | 交付准时率 | 实际交付/计划交付 |
| 交付健康度 | 版本成功率 | 成功部署版本/迭代版本 |
| 组织健康度 | 人员依赖度 | 单点依赖人数比例 |

### 3. AI 决策引擎 (services/ai_engine/)

- 周报/月报自动摘要生成
- 异常检测与风险预警
- 管理决策建议生成
- 技术趋势自动抓取与分析

### 4. 报告生成器 (services/report/)

- Markdown 格式周报
- PPT 大纲生成
- 飞书卡片消息推送
- PDF 报告导出

## 飞书接入配置

1. 在飞书开放平台创建企业自建应用
2. 获取 `APP_ID` 和 `APP_SECRET`
3. 申请所需权限：
   - `contact:user.read` - 读取用户列表
   - `task:task:read` - 读取任务数据
   - `docs:doc:read` - 读取文档内容
   - `okr:okr:read` - 读取 OKR 数据
4. 将凭证配置到 `.env` 文件

## Docker 镜像构建与生产部署

### 一键部署流程

```bash
# 1. 配置镜像仓库地址
vim build-config.sh
# 修改 IMAGE_REGISTRY="your-registry.com/malong"

# 2. 构建 Docker 镜像
bash build-docker-image.sh

# 3. 推送镜像到私有仓库
docker login your-registry.com
bash push-docker-image.sh

# 4. SSH 到 Ubuntu 生产服务器
ssh user@server
cd /opt/malong-management

# 5. 上传配置文件
# 在本地执行: scp docker-compose.prod.yml .env.prod deploy-to-production.sh user@server:/opt/malong-management/

# 6. 一键部署
chmod +x deploy-to-production.sh
./deploy-to-production.sh

# 7. 验证
curl http://localhost:8000/api/v1/health
```

### 核心配置文件

- **build-config.sh** - 镜像配置（仓库地址、版本号）
- **docker-compose.prod.yml** - 生产环境 Docker 编排
- **.env.prod** - 环境变量配置（飞书、AI 密钥）
- **deploy-to-production.sh** - 一键部署脚本

### 部署文档

- 📖 [🐳Docker镜像构建与推送指南.md](./🐳Docker镜像构建与推送指南.md) - 详细指南
- 📖 [🐧Ubuntu生产环境部署配置-模板.md](./🐧Ubuntu生产环境部署配置-模板.md) - 配置模板
- 📖 [🚀Docker镜像构建与生产部署-快速指南.md](./🚀Docker镜像构建与生产部署-快速指南.md) - 快速参考
- 📖 [📦Docker部署文件清单.md](./📦Docker部署文件清单.md) - 完整清单

### 环境变量

| 变量名 | 说明 | 示例 |
|-------|------|------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql://user:pass@localhost/db` |
| `FEISHU_APP_ID` | 飞书应用 ID | `cli_xxxxxx` |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | `xxxxxxxx` |
| `AI_MODEL_API_KEY` | AI 模型 API 密钥 | `sk-xxxxxxxx` |
| `REDIS_URL` | Redis 连接地址 | `redis://localhost:6379/0` |

## 相关资源

### 项目文档
- [飞书开放平台](https://open.feishu.cn/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [码隆科技官网](https://www.malong.com)

### Everything Claude Code 资源
- [GitHub 仓库](https://github.com/affaan-m/everything-claude-code)
- [AgentShield 安全扫描](https://www.npmjs.com/package/ecc-agentshield)
- [ECC Tools GitHub App](https://github.com/marketplace/ecc-tools)

## 注意事项

1. **数据隐私**：处理飞书数据时遵守公司数据安全规范
2. **API 限流**：飞书 API 有调用频率限制，实现时需考虑限流和重试
3. **敏感信息**：飞书凭证和 AI API Key 不得提交到代码仓库
4. **数据一致性**：定时任务需考虑异常情况和数据同步冲突
5. **Agent 使用**：复杂功能优先使用 `/plan` 和 `/tdd` 命令
6. **代码审查**：所有代码提交前必须使用 `/code-review`
7. **安全检查**：定期运行 `npx ecc-agentshield scan`

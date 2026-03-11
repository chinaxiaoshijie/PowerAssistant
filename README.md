# 管理助手 (PowerAssistant)

> 码隆科技研发与交付部门的智能决策引擎系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 项目概述

**管理助手**是一个基于AI的智能决策引擎系统，通过打通飞书业务数据，结合大模型能力，为研发团队负责人提供：

- 📊 **数据感知** - 自动同步飞书组织架构、任务、项目、OKR数据
- 🧠 **智能分析** - 四个专业化AI智能体提供深度洞察
- 📈 **决策支持** - 自动化报告生成和风险预警
- 🎨 **可视化展示** - 美观的Dashboard仪表板

---

## ✨ 核心功能

### 1. 飞书数据同步 ✅
- 组织架构同步（每1小时）
- 任务数据同步（每2小时）
- 项目数据同步（每4小时）
- OKR数据同步（每6小时）

### 2. AI智能体系统 ✅
- **仕杰** - AI原生开发实践分析
- **运明** - AI算法研究分析
- **逍虓** - AI产品创新分析
- **通用技术趋势** - 技术趋势监控

### 3. 前端Dashboard ✅
- 概览页面 - 核心指标展示
- 任务管理 - 任务列表和状态
- 项目跟踪 - 项目进度和风险
- 智能情报 - 智能体分析结果
- 指标分析 - 数据可视化图表
- 报告中心 - 历史报告查看

### 4. 报告生成系统 ✅
- 周报生成（每周一10:00）
- 日报生成（每天9:00）
- 健康度指标计算
- AI智能摘要生成

### 5. 飞书通知推送 ✅
- 周报推送 - 飞书群组卡片消息
- 智能体分析推送 - 专业洞察分享
- 任务提醒 - 任务到期提醒
- 风险预警 - 项目风险告警

---

## 🚀 快速开始

### 环境要求
- Python 3.11+
- PostgreSQL 15+
- Docker (可选)

### 5分钟快速启动

```bash
# 1. 克隆项目
git clone git@github.com:chinaxiaoshijie/PowerAssistant.git
cd PowerAssistant

# 2. 安装依赖
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. 配置环境
cp .env.example .env
# 编辑 .env 配置数据库和飞书凭证

# 4. 初始化数据库
alembic upgrade head

# 5. 启动服务
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 访问系统
- 🎨 **Dashboard**: http://localhost:8000/dashboard/
- 📚 **API文档**: http://localhost:8000/docs
- 🔴 **API Redoc**: http://localhost:8000/redoc

---

## 📚 文档

### 入门指南
- [**快速使用指南**](./快速使用指南.md) - 5分钟快速上手
- [**项目完成总结**](./项目完成总结.md) - 详细功能说明
- [**检查清单**](./检查清单.md) - 质量检查和验证

### 技术文档
- [**架构设计**](./docs/architecture/) - 系统架构设计
- [**API文档**](http://localhost:8000/docs) - 在线API文档
- [**部署指南**](./docs/deployment/) - 部署到生产环境

---

## 🛠️ 技术栈

### 后端
- **Python 3.11+** - 编程语言
- **FastAPI** - Web框架
- **SQLAlchemy** - ORM
- **PostgreSQL** - 数据库
- **APScheduler** - 任务调度

### 前端
- **Vue.js 3** - 前端框架
- **Tailwind CSS** - 样式库
- **Chart.js** - 数据可视化

### 集成
- **飞书 OpenAPI** - 业务数据同步
- **多模型AI引擎** - 智能分析

---

## 📊 项目结构

```
PowerAssistant/
├── src/                           # 源代码
│   ├── api/                       # API路由
│   │   └── v1/
│   │       ├── dashboard.py       # 仪表板API
│   │       ├── feishu.py          # 飞书API
│   │       ├── ai.py              # AI智能体API
│   │       ├── reports.py         # 报告API
│   │       └── tasks.py           # 任务API
│   ├── services/                  # 业务服务
│   │   ├── feishu/               # 飞书集成
│   │   │   ├── client.py          # API客户端
│   │   │   ├── task_sync.py       # 任务同步
│   │   │   ├── project_sync.py    # 项目同步
│   │   │   ├── okr_sync.py        # OKR同步
│   │   │   └── notification.py    # 通知推送
│   │   ├── ai_intelligence/       # AI智能体
│   │   │   └── agents.py          # 智能体系统
│   │   ├── metrics/               # 指标计算
│   │   ├── report/                # 报告生成
│   │   └── ai_engine/             # AI引擎
│   ├── tasks/                     # 定时任务
│   │   └── scheduler.py           # 任务调度器
│   ├── models/                    # 数据模型
│   ├── database.py                # 数据库配置
│   └── main.py                    # 应用入口
├── static/                        # 静态文件
│   └── dashboard/
│       └── index.html             # 前端界面
├── docs/                          # 文档
├── tests/                         # 测试
├── .env.example                   # 环境配置模板
├── requirements.txt               # Python依赖
└── README.md                      # 项目说明
```

---

## 🎯 使用示例

### 1. 运行智能体分析

```bash
# 运行所有智能体
curl -X POST http://localhost:8000/api/v1/ai/agents/run

# 运行特定智能体
curl -X POST http://localhost:8000/api/v1/ai/agents/development_practice
```

### 2. 生成报告

```bash
# 生成周报（上周数据）
curl http://localhost:8000/api/v1/reports/weekly?week_offset=-1

# 生成日报
curl http://localhost:8000/api/v1/reports/daily
```

### 3. 查看统计数据

```bash
# 获取概览数据
curl http://localhost:8000/api/v1/dashboard/stats

# 获取任务列表
curl http://localhost:8000/api/v1/tasks

# 获取项目列表
curl http://localhost:8000/api/v1/projects
```

---

## 🔔 配置飞书通知

### 1. 获取群聊ID

在飞书中打开目标群聊，复制群聊ID（格式：`oc_xxx`）

### 2. 修改配置

编辑 `src/tasks/scheduler.py`，修改第399行：

```python
chat_id = "oc_your_actual_chat_id_here"
```

### 3. 通知类型

系统会自动发送：
- **日报** - 每天9:00
- **周报** - 每周一10:00
- **智能体分析** - 每24小时

---

## 🐛 常见问题

### Q1: 飞书同步失败

**解决方案**:
1. 检查 `.env` 中的 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`
2. 确认飞书应用已授权相应权限
3. 查看日志：`logs/app.log`

### Q2: 智能体分析无结果

**解决方案**:
1. 确保已配置AI模型API密钥
2. 检查数据库是否有情报数据
3. 手动触发情报收集

### Q3: Dashboard 数据为空

**解决方案**:
1. 触发数据同步
2. 等待定时任务执行（最多1小时）
3. 检查数据库连接

详细问题请参考 [**快速使用指南**](./快速使用指南.md#-常见问题)

---

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 📞 联系方式

- 项目仓库: [GitHub](https://github.com/chinaxiaoshijie/PowerAssistant)
- 问题反馈: [Issues](https://github.com/chinaxiaoshijie/PowerAssistant/issues)
- 文档: [docs/](./docs/)

---

## 🙏 致谢

感谢以下开源项目：

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能Web框架
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [Tailwind CSS](https://tailwindcss.com/) - 功能优先的CSS框架
- [APScheduler](https://apscheduler.readthedocs.io/) - 任务调度库

---

## 📊 项目状态

**状态**: ✅ **已达到可用状态**

所有核心功能已实现，文档齐全，代码质量良好。

系统可以立即投入使用，为码隆科技的研发管理提供智能化支持！

---

**交付日期**: 2026-03-11
**版本**: v1.0.0
**作者**: 码隆科技研发团队

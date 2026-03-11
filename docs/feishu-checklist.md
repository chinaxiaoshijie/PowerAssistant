# 飞书配置检查清单

使用此清单确保飞书配置完整正确。

## ✅ 飞书开放平台配置

### 创建应用
- [ ] 访问 [飞书开放平台](https://open.feishu.cn/)
- [ ] 使用企业管理员账号登录
- [ ] 创建「企业自建应用」
- [ ] 填写应用名称和描述
- [ ] 记录 App ID (`cli_xxxxxx`)
- [ ] 记录 App Secret

### 申请权限
- [ ] 进入「权限管理」
- [ ] 申请 `contact:department:readonly`
- [ ] 申请 `contact:user:readonly`
- [ ] 提交权限申请
- [ ] 确认权限已审批通过

### 设置可见范围（如需要）
- [ ] 进入飞书管理后台
- [ ] 打开「工作台」→「应用管理」
- [ ] 找到「管理助手」应用
- [ ] 设置可见范围（全员或指定部门）

## ✅ 环境变量配置

### 开发环境 (.env)
- [ ] 复制 `.env.example` 为 `.env`
- [ ] 填入 `FEISHU_APP_ID`
- [ ] 填入 `FEISHU_APP_SECRET`
- [ ] 检查 `DATABASE_URL` 配置
- [ ] 检查 `LOG_LEVEL` 设置

### 生产环境
- [ ] 复制 `.env.prod.example` 为 `.env`
- [ ] 填入生产环境 `FEISHU_APP_ID`
- [ ] 填入生产环境 `FEISHU_APP_SECRET`
- [ ] 设置强密码 `DB_PASSWORD`
- [ ] 检查 `ENVIRONMENT=production`

## ✅ 验证配置

### 本地验证
```bash
python scripts/verify-feishu.py
```

- [ ] App ID 显示正确
- [ ] App Secret 显示已配置
- [ ] Token 获取成功
- [ ] 部门列表获取成功
- [ ] 用户列表获取成功

### Docker 验证
```bash
docker-compose up -d
curl http://localhost:8000/api/v1/health/feishu
```

- [ ] 服务启动无错误
- [ ] 健康检查返回 `healthy`
- [ ] 飞书连接检查通过

## ✅ 功能测试

### 同步功能
- [ ] 触发全量同步成功
- [ ] 部门数据写入数据库
- [ ] 员工数据写入数据库
- [ ] 同步日志记录正确

### API 功能
- [ ] `GET /api/v1/organization/departments` 返回数据
- [ ] `GET /api/v1/organization/employees` 返回数据
- [ ] `GET /api/v1/sync/status` 显示同步状态
- [ ] `POST /api/v1/sync/incremental` 触发增量同步

## ✅ 安全检查

- [ ] App Secret 未提交到代码仓库
- [ ] 生产环境使用强密码
- [ ] 配置了适当的日志级别
- [ ] 启用了健康检查

## 🚀 部署检查（生产环境）

### Docker 部署
- [ ] 构建镜像成功
- [ ] 容器启动无错误
- [ ] 数据库连接正常
- [ ] 数据卷持久化配置
- [ ] 健康检查通过

### 监控配置
- [ ] 日志收集配置
- [ ] 错误告警配置（可选）
- [ ] 备份策略配置（可选）

## 📋 完成确认

所有检查项完成后：

1. ✅ 飞书配置正确
2. ✅ 应用运行正常
3. ✅ 数据同步成功
4. ✅ API 访问正常

**管理助手已就绪！**

---

## 问题反馈

如果在配置过程中遇到问题：

1. 查看 [详细配置文档](feishu-setup.md)
2. 查看 [快速启动指南](quickstart.md)
3. 检查 [故障排除](feishu-setup.md#五常见问题)
4. 联系技术支持

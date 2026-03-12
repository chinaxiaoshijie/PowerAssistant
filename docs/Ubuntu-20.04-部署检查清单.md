# Ubuntu 20.04 部署检查清单

## 系统准备

- [ ] 操作系统：Ubuntu 20.04 LTS 已安装
- [ ] 系统已更新：`sudo apt update && sudo apt upgrade -y`
- [ ] 基础工具已安装：`curl`, `wget`, `git`, `software-properties-common`

## Python 环境

- [ ] Python 3.11 已安装：`python3.11 --version`
- [ ] pip 3.11 已安装：`pip3.11 --version`
- [ ] 虚拟环境支持已安装：`python3.11-venv`

## 数据库

- [ ] PostgreSQL 15 已安装
- [ ] PostgreSQL 服务已启动：`sudo systemctl status postgresql`
- [ ] 数据库 `powerassistant` 已创建
- [ ] 数据库用户 `powerassistant_user` 已创建
- [ ] 用户密码已设置（强密码）
- [ ] 用户权限已授予

## Redis（可选）

- [ ] Redis 7 已安装
- [ ] Redis 服务已启动：`sudo systemctl status redis-server`
- [ ] Redis 连接测试通过：`redis-cli ping`

## 应用部署

- [ ] 部署目录已创建：`/opt/powerassistant`
- [ ] 代码已克隆：`git clone git@github.com:chinaxiaoshijie/PowerAssistant.git`
- [ ] Python 虚拟环境已创建
- [ ] 依赖已安装：`pip install -r requirements.txt`
- [ ] 环境变量文件已配置：`.env`
- [ ] 数据库连接字符串已配置
- [ ] 飞书 APP_ID 和 APP_SECRET 已配置
- [ ] AI 模型 API 密钥已配置
- [ ] SECRET_KEY 已设置（随机生成）
- [ ] 数据库迁移已执行：`alembic upgrade head`
- [ ] 数据库表已验证：`psql -U powerassistant_user -d powerassistant -c "\dt"`

## Systemd 服务

- [ ] systemd 服务文件已创建：`/etc/systemd/system/powerassistant.service`
- [ ] 服务已加载：`sudo systemctl daemon-reload`
- [ ] 服务已启动：`sudo systemctl start powerassistant`
- [ ] 服务已设置开机自启：`sudo systemctl enable powerassistant`
- [ ] 服务状态正常：`sudo systemctl status powerassistant`
- [ ] Worker 数量已配置（建议：CPU核心数 * 2 + 1）

## Nginx（可选）

- [ ] Nginx 已安装
- [ ] Nginx 配置文件已创建：`/etc/nginx/sites-available/powerassistant`
- [ ] 配置已启用：软链接到 `sites-enabled`
- [ ] Nginx 配置测试通过：`sudo nginx -t`
- [ ] Nginx 服务已重启：`sudo systemctl restart nginx`
- [ ] Nginx 已设置开机自启：`sudo systemctl enable nginx`

## SSL 证书（可选）

- [ ] Certbot 已安装
- [ ] SSL 证书已获取：`sudo certbot --nginx -d your-domain.com`
- [ ] 自动续期已测试：`sudo certbot renew --dry-run`

## 防火墙

- [ ] UFW 已安装
- [ ] 防火墙规则已配置：
  - [ ] 允许 SSH (22)
  - [ ] 允许 HTTP (80)
  - [ ] 允许 HTTPS (443)
  - [ ] 或允许应用端口 (8000)
- [ ] 防火墙已启用：`sudo ufw enable`
- [ ] 防火墙状态正常：`sudo ufw status`

## 功能验证

- [ ] 应用服务可访问：`curl http://localhost:8000/api/v1/health`
- [ ] Dashboard 可访问：`curl http://localhost:8000/dashboard/`
- [ ] API 文档可访问：`curl http://localhost:8000/docs`
- [ ] 应用日志正常：`sudo journalctl -u powerassistant -n 50`
- [ ] 数据库连接正常
- [ ] 飞书同步测试通过
- [ ] 智能体分析测试通过
- [ ] 报告生成测试通过

## 监控和维护

- [ ] 日志轮转已配置：`/etc/logrotate.d/powerassistant`
- [ ] 备份脚本已创建：`/usr/local/bin/backup-powerassistant.sh`
- [ ] 定时备份任务已配置：`crontab -e`（每天凌晨2点）
- [ ] 数据库备份测试通过
- [ ] 系统监控工具已安装（可选）：`htop`, `glances`
- [ ] 应用监控已配置（可选）：Prometheus, Grafana

## 性能优化

- [ ] Worker 数量已优化
- [ ] Redis 缓存已启用
- [ ] Nginx Gzip 压缩已配置
- [ ] Nginx 缓存已配置（可选）
- [ ] 数据库连接池已优化
- [ ] 数据库索引已优化

## 安全加固

- [ ] 数据库访问已限制（仅本地）
- [ ] 防火墙规则已优化（最小化开放端口）
- [ ] SSH 密钥登录已配置（禁用密码登录）
- [ ] 系统自动安全更新已启用
- [ ] 敏感信息未提交到版本控制（.env 文件）
- [ ] 密码和密钥已使用强随机生成

## 文档和记录

- [ ] 部署文档已保存
- [ ] 配置备份已完成
- [ ] 数据库备份策略已确认
- [ ] 团队成员已获得访问权限
- [ ] 紧急联系人信息已记录

## 后续维护计划

- [ ] 定期系统更新计划（每周）
- [ ] 数据库备份验证计划（每月）
- [ ] 应用日志审查计划（每周）
- [ ] 性能监控计划（持续）
- [ ] 安全审计计划（每季度）

---

**检查时间**: _______________
**检查人**: _______________
**服务器地址**: _______________
**备注**: _______________

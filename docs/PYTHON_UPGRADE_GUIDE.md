# Python 升级指南 (Windows)

## 当前版本
- Python 3.9.13

## 目标版本
- Python 3.11.x (推荐，稳定且性能好)
- 或 Python 3.12.x (最新版)

---

## 方案一：官方安装包（推荐）

### 步骤 1: 下载Python

1. 访问 https://www.python.org/downloads/windows/
2. 选择 **Python 3.11.8** (稳定版) 或 **Python 3.12.2** (最新版)
3. 下载 **Windows installer (64-bit)**

### 步骤 2: 安装

1. 运行下载的 `python-3.11.x-amd64.exe`
2. **重要**: 勾选 "☑️ Add Python to PATH"
3. 选择 "☑️ Install for all users"
4. 点击 "Customize installation"
5. 确保勾选以下选项：
   - ☑️ Documentation
   - ☑️ pip
   - ☑️ tcl/tk and IDLE
   - ☑️ Python test suite
   - ☑️ py launcher
   - ☑️ for all users
6. 点击 Next
7. 高级选项中勾选：
   - ☑️ Install for all users
   - ☑️ Precompile standard library
8. 点击 Install

### 步骤 3: 验证安装

打开新的 PowerShell 或 CMD：

```powershell
# 检查Python版本
python --version
# 应显示 Python 3.11.x

# 检查pip
pip --version

# 检查Python路径
where python
```

---

## 方案二：使用 Anaconda（推荐数据科学用户）

### 步骤 1: 下载Anaconda

访问 https://www.anaconda.com/download
下载 Anaconda Distribution (Python 3.11 版本)

### 步骤 2: 安装

1. 运行安装程序
2. 选择 "Add Anaconda to my PATH environment variable"
3. 完成安装

### 步骤 3: 创建新环境

```bash
# 创建Python 3.11环境
conda create -n malong python=3.11

# 激活环境
conda activate malong

# 验证
python --version
```

---

## 方案三：使用 pyenv-win（多版本管理）

### 步骤 1: 安装 pyenv-win

```powershell
# 使用pip安装
pip install pyenv-win

# 或手动安装
# 下载: https://github.com/pyenv-win/pyenv-win/archive/master.zip
# 解压到 C:\Users\<你的用户名>\.pyenv\pyenv-win
```

### 步骤 2: 配置环境变量

添加以下到系统环境变量 PATH：
```
%USERPROFILE%\.pyenv\pyenv-win\bin
%USERPROFILE%\.pyenv\pyenv-win\shims
```

### 步骤 3: 安装Python

```powershell
# 查看可用版本
pyenv install --list

# 安装Python 3.11
pyenv install 3.11.8

# 设置全局版本
pyenv global 3.11.8

# 验证
python --version
```

---

## 升级后操作

### 1. 重新创建虚拟环境

```powershell
# 删除旧虚拟环境
cd D:\项目\管理助手
rmdir /s venv

# 创建新虚拟环境 (Python 3.11)
python -m venv venv

# 激活
venv\Scripts\activate

# 验证Python版本
python --version
```

### 2. 重新安装依赖

```powershell
# 升级pip
python -m pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# 安装测试依赖
pip install pytest pytest-asyncio pytest-cov aiosqlite httpx

# 安装SQLAlchemy
pip install sqlalchemy aiosqlite asyncpg
```

### 3. 重新运行测试

```powershell
python -m pytest tests/ -v
```

---

## 版本对比

| 特性 | Python 3.9 | Python 3.11 | Python 3.12 |
|------|-----------|-------------|-------------|
| `dict \| None` 语法 | ❌ | ✅ | ✅ |
| 性能 | 基准 | 快10-60% | 快5% |
| 错误提示 | 一般 | 大幅改进 | 更好 |
| 类型系统 | 完整 | 完整 | 完整 |
| 稳定性 | 稳定 | 稳定 | 较新 |

**推荐**: Python 3.11（稳定且性能好）

---

## 常见问题

### Q1: 安装后 `python` 命令还是旧版本？

**解决**: 检查环境变量 PATH 顺序
```powershell
# 查看Python路径
where python

# 确保新Python路径在旧版本之前
# 系统属性 → 环境变量 → Path
# 将新Python路径移到最前面
```

### Q2: pip安装的包在哪里？

```powershell
# 查看pip位置
where pip

# 查看包安装位置
pip show <package_name>
```

### Q3: 如何切换回旧版本？

使用 pyenv-win：
```powershell
pyenv global 3.9.13
```

或修改 PATH 环境变量。

---

## 快速检查清单

升级后确认以下正常工作：

- [ ] `python --version` 显示新版本
- [ ] `pip --version` 正常
- [ ] 虚拟环境创建成功
- [ ] 项目依赖安装成功
- [ ] 测试运行通过
- [ ] 类型注解 `dict | None` 不再报错

---

## 需要帮助？

如果在升级过程中遇到问题，请告诉我：
1. 选择的升级方案
2. 遇到的错误信息
3. 当前Windows版本

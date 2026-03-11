@echo off
chcp 65001
echo ==========================================
echo Python 3.11 升级助手
echo ==========================================
echo.

REM 检查Python版本
echo [1/6] 检查当前Python版本...
python --version
echo.

REM 删除旧虚拟环境
echo [2/6] 删除旧虚拟环境...
if exist venv (
    rmdir /s /q venv
    echo 已删除旧虚拟环境
) else (
    echo 无旧虚拟环境
)
echo.

REM 创建新虚拟环境
echo [3/6] 创建新虚拟环境...
python -m venv venv
if %errorlevel% neq 0 (
    echo 创建虚拟环境失败！请检查Python是否已安装
    pause
    exit /b 1
)
echo 虚拟环境创建成功
echo.

REM 激活虚拟环境
echo [4/6] 激活虚拟环境...
call venv\Scripts\activate
echo 虚拟环境已激活
echo.

REM 升级pip
echo [5/6] 升级pip...
python -m pip install --upgrade pip
echo.

REM 安装依赖
echo [6/6] 安装依赖包...
pip install fastapi uvicorn sqlalchemy aiosqlite asyncpg alembic
pip install pydantic pydantic-settings python-dotenv
pip install aiohttp structlog python-dateutil
pip install pytest pytest-asyncio pytest-cov httpx
pip install apscheduler beautifulsoup4 lxml
pip install jinja2 aiofiles

echo.
echo ==========================================
echo 升级完成！
echo ==========================================
echo.
python --version
echo.
echo 测试类型注解支持:
python -c "x: dict | None = None; print('✅ Python 3.11+ 类型注解支持正常')"
echo.
pause

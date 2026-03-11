@echo off
REM 管理助手 - Docker Quick Start Script (Windows)
REM Usage: start.bat

REM UTF-8 Encoding
chcp 65001 >nul

echo =========================================
echo   Management Assistant - Docker Quick Start
echo =========================================
echo.

REM Check if Docker is installed
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not installed
    echo Please install Docker Desktop first: https://www.docker.com/get-started
    pause
    exit /b 1
)

REM Check if Docker Compose is available
where docker-compose >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    docker compose version >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Docker Compose is not available
        pause
        exit /b 1
    )
)

REM Check .env.docker file
if not exist .env.docker (
    echo [.env.docker] file not found
    echo Creating .env.docker from template...
    copy .env.prod.example .env.docker
    echo Created .env.docker
    echo.
    echo Please edit .env.docker and fill in required configurations:
    echo    - FEISHU_APP_ID
    echo    - FEISHU_APP_SECRET
    echo    - DASHSCOPE_API_KEY
    echo.
    echo Then run start.bat again
    pause
    exit /b 1
)

REM Check required environment variables
findstr /C:"FEISHU_APP_ID=cli_" .env.docker >nul
if %ERRORLEVEL% EQU 0 (
    echo [WARNING] Please edit .env.docker and set FEISHU_APP_ID
    pause
    exit /b 1
)

findstr /C:"DASHSCOPE_API_KEY=sk-" .env.docker >nul
if %ERRORLEVEL% EQU 0 (
    echo [WARNING] Please edit .env.docker and set DASHSCOPE_API_KEY
    pause
    exit /b 1
)

echo [OK] Environment check passed
echo.

REM Build and start services
echo [STARTING] Building and starting services...
echo.

docker compose up -d --build

echo.
echo [WAITING] Waiting for services to start...
timeout /t 5 /nobreak >nul

REM Check service status
echo.
echo [STATUS] Service status:
docker compose ps

echo.
echo =========================================
echo   Services started successfully!
echo =========================================
echo.
echo Access URLs:
echo    - API Docs:     http://localhost:8000/api/docs
echo    - Dashboard:    http://localhost:8000/dashboard
echo    - Health Check: http://localhost:8000/api/v1/health
echo    - Adminer:      http://localhost:8080
echo.
echo Common commands:
echo    - View logs:    docker compose logs -f app
echo    - Restart:      docker compose restart
echo    - Stop:         docker compose down
echo.

pause

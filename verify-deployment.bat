@echo off
REM Deployment Verification Script (Windows)
REM Usage: verify-deployment.bat

chcp 65001 >nul

echo =========================================
echo   Management Assistant - Deployment Verification
echo =========================================
echo.

REM 1. Check Docker service
echo 1. Checking Docker service...
docker info >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Docker service is running
) else (
    echo [ERROR] Docker service is not running
    pause
    exit /b 1
)

REM 2. Check container status
echo.
echo 2. Checking container status...

docker compose ps -q > temp_containers.txt
for /f %%i in ('type temp_containers.txt ^| find /c /v ""') do set container_count=%%i
del temp_containers.txt

if %container_count% LSS 4 (
    echo [ERROR] Insufficient containers, expected at least 4
    pause
    exit /b 1
)

echo [OK] All containers are running

REM 3. Check service health
echo.
echo 3. Checking service health...

docker compose ps db | find "Up" >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] PostgreSQL database is running
) else (
    echo [ERROR] PostgreSQL database is not running
    pause
    exit /b 1
)

docker compose ps redis | find "Up" >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Redis cache is running
) else (
    echo [WARNING] Redis cache is not running (optional)
)

docker compose ps app | find "Up" >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Application service is running
) else (
    echo [ERROR] Application service is not running
    pause
    exit /b 1
)

REM 4. Test health check endpoint
echo.
echo 4. Testing health check endpoint...

curl -s http://localhost:8000/api/v1/health > temp_health.json 2>nul
findstr "healthy" temp_health.json >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Health check endpoint is working
    type temp_health.json
) else (
    echo [ERROR] Health check endpoint failed
    type temp_health.json
)
del temp_health.json

REM 5. Check database connection
echo.
echo 5. Checking database connection...

docker compose exec -T db psql -U postgres -d malong_management -c "SELECT 1" > temp_db.txt 2>&1
findstr "1" temp_db.txt >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Database connection is working
) else (
    echo [ERROR] Database connection failed
    type temp_db.txt
)
del temp_db.txt

REM 6. Check environment variables
echo.
echo 6. Checking environment variables...

docker compose exec -T app env > temp_env.txt

findstr "FEISHU_APP_ID" temp_env.txt >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Feishu configuration loaded
) else (
    echo [ERROR] Feishu configuration not loaded
)

findstr "DASHSCOPE_API_KEY" temp_env.txt >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] AI model configuration loaded
) else (
    echo [ERROR] AI model configuration not loaded
)
del temp_env.txt

REM 7. Access test
echo.
echo 7. Access test...

curl -s -f http://localhost:8000/ > temp_home.json 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Application homepage is accessible
) else (
    echo [ERROR] Application homepage is not accessible
)
del temp_home.json

REM Summary
echo.
echo =========================================
echo   Verification completed
echo =========================================
echo.
echo Access URLs:
echo    - API Docs:     http://localhost:8000/api/docs
echo    - Dashboard:    http://localhost:8000/dashboard
echo    - Health Check: http://localhost:8000/api/v1/health
echo    - Adminer:      http://localhost:8080
echo.
echo Next steps:
echo    1. Configure Feishu app permissions
echo    2. Trigger data sync: curl http://localhost:8000/api/v1/sync/trigger
echo    3. Check Dashboard for system status
echo.

pause

@echo off
REM Cleanup script for Windows
REM Stops all services and cleans up resources

chcp 65001 >nul

echo =========================================
echo   Management Assistant - Cleanup Resources
echo =========================================
echo.

REM Confirm action
set /p CONFIRM="WARNING: This will stop all services and delete data. Continue? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo [CANCELLED] Operation cancelled
    pause
    exit /b 1
)

echo 1. Stopping all containers...
docker compose down

echo.
echo 2. Removing data volumes (database and Redis)...
docker compose down -v

echo.
echo 3. Removing images...
docker compose down --rmi all

echo.
echo 4. Cleaning up temporary files...
del temp_*.json temp_*.txt 2>nul

echo.
echo =========================================
echo   Cleanup completed
echo =========================================
echo.
echo To start fresh next time:
echo   docker compose up -d --build
echo.

pause

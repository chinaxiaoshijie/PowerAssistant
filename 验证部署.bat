@echo off
REM 管理助手 - 部署验证脚本
REM UTF-8 编码
chcp 65001 >nul

echo.
echo ========================================
echo   Deployment Verification
echo ========================================
echo.

echo [1/4] Checking service status...
docker compose ps

echo.
echo [2/4] Checking app container logs...
echo.
docker compose logs app --tail=30

echo.
echo [3/4] Testing health endpoint (waiting 5 seconds)...
timeout /t 5 /nobreak >nul

powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health' -UseBasicParsing; if ($response.StatusCode -eq 200) { Write-Host '[PASS] Health check passed' -ForegroundColor Green } else { Write-Host '[FAIL] Health check failed: Status code' $response.StatusCode -ForegroundColor Red } } catch { Write-Host '[FAIL] Health check failed:' $_.Exception.Message -ForegroundColor Red }"

echo.
echo [4/4] Summary
echo ========================================
echo.
echo If health check passed:
echo   - Open http://localhost:8000/api/docs to test the API
echo   - Open http://localhost:8000/dashboard to view the dashboard
echo.
echo If health check failed:
echo   - Check logs: docker compose logs -f app
echo   - Restart services: docker compose restart
echo   - Stop and retry: docker compose down ^&^& docker compose up -d
echo.
echo ========================================
echo.

pause
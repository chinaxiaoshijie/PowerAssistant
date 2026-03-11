# 管理助手 - Malong Management Assistant
# Python 3.11 + FastAPI + PostgreSQL
# 优化的多阶段构建，减小镜像体积并提高安全性

# ========================================
# 构建阶段
# ========================================
FROM python:3.11-slim as builder

# 设置环境变量，避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 安装系统依赖（仅构建时需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装 Python 依赖
COPY requirements.txt requirements-dev.txt /tmp/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# ========================================
# 生产阶段
# ========================================
FROM python:3.11-slim as production

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_HOME=/app

# 安装运行时依赖（最小化）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 创建非 root 用户（提高安全性）
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /app /app/logs && \
    chown -R appuser:appuser /app

# 设置工作目录
WORKDIR /app

# 复制应用代码（保持文件所有权）
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser pyproject.toml ./
COPY --chown=appuser:appuser static/ ./static/

# 切换到非 root 用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

# ========================================
# 开发阶段（用于本地开发）
# ========================================
FROM production as development

# 安装开发工具
RUN pip install --no-cache-dir -r /tmp/requirements-dev.txt

# 保持 root 用户以便调试
USER root

# 启用热重载
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

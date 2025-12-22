# NullForge - Autonomous Enterprise Software Platform
# Docker Image for containerized deployment

# ====================
# Build Stage
# ====================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ====================
# Production Stage
# ====================
FROM python:3.11-slim as production

LABEL org.opencontainers.image.title="NullForge"
LABEL org.opencontainers.image.description="Autonomous Enterprise Software Platform"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/RemyLoveLogicAI/NullForge"
LABEL org.opencontainers.image.licenses="MIT"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash nullforge

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=nullforge:nullforge . .

# Create workspace directory
RUN mkdir -p /workspace && chown nullforge:nullforge /workspace

# Switch to non-root user
USER nullforge

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NULLFORGE_WORKSPACE=/workspace \
    NULLFORGE_PROVIDER=venice

# Expose ports
# API Server
EXPOSE 8000
# MCP Server (optional)
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run API server
CMD ["python", "-m", "uvicorn", "aol_fire.api.server:app", "--host", "0.0.0.0", "--port", "8000"]

# ====================
# CLI Stage
# ====================
FROM production as cli

# Override command for CLI usage
ENTRYPOINT ["python", "nullforge.py"]
CMD ["--help"]

# ====================
# Development Stage
# ====================
FROM production as development

USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-asyncio \
    black \
    ruff \
    mypy \
    ipython

USER nullforge

# Mount points for development
VOLUME ["/app", "/workspace"]

CMD ["python", "-m", "uvicorn", "aol_fire.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

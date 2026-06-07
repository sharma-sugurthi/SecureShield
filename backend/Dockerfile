# =============================================================
# SecureShield Backend — Production Dockerfile
# Multi-stage build with security hardening for hackathon deploy
# =============================================================
# Build:  docker build -t secureshield-backend .
# Run:    docker run -p 8000:8000 --env-file .env secureshield-backend
# =============================================================

# ---- Stage 1: Builder (install deps with build tools) ----
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies needed for native extensions
# (asyncpg, pymupdf, etc.) — these stay in builder only
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       gcc \
       libmagic1 \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
# If requirements.txt hasn't changed, this layer is cached
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: Runtime (lean, non-root, hardened) ----
FROM python:3.11-slim AS runtime

# Metadata labels (OCI standard)
LABEL org.opencontainers.image.title="SecureShield Backend" \
      org.opencontainers.image.description="GenAI-powered health insurance claim eligibility engine" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="sharma-sugurthi" \
      org.opencontainers.image.source="https://github.com/sharma-sugurthi/SecureShield"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Default port for uvicorn
    PORT=8000 \
    # Production settings
    ENVIRONMENT=production \
    # Uvicorn workers (overridable at runtime)
    WEB_CONCURRENCY=2

WORKDIR /app

# Install minimal runtime dependencies only
# (libmagic for file type detection, ca-certs for HTTPS to Supabase)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libmagic1 \
       ca-certificates \
       curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

# ---- Security: Create non-root user ----
# CIS Docker Benchmark 4.1: Run container as non-root
RUN groupadd --gid 1001 secureshield \
    && useradd --uid 1001 --gid 1001 --shell /bin/false --create-home secureshield

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=secureshield:secureshield . .

# Create directories the app needs at runtime
RUN mkdir -p /app/reports /app/db \
    && chown -R secureshield:secureshield /app

# Drop privileges — run everything below as non-root
USER secureshield

# Expose the API port
EXPOSE ${PORT}

# Health check: hit the public /api/health endpoint
# Retries 3 times with 30s interval, 5s timeout, starts after 10s
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Start uvicorn with production settings
# - --workers: controlled by WEB_CONCURRENCY env var
# - --access-log: enabled for observability
# - --proxy-headers: trust X-Forwarded-For from Render/load-balancer
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY} --proxy-headers --access-log"]

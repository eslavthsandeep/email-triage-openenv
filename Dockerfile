# Dockerfile — Email Triage OpenEnv
# Runs a FastAPI server on port 7860 (Hugging Face Spaces default)

FROM python:3.11-slim

# Metadata
LABEL maintainer="hackathon-participant"
LABEL description="Email Triage OpenEnv — real-world inbox management for AI agents"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || true && \
    pip install --no-cache-dir openenv-core>=0.2.0 || true
# Copy source
COPY . .

# Create non-root user (HF Spaces requirement)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 7860

# Environment defaults (override via HF Space secrets)
ENV PORT=7860
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start server
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]

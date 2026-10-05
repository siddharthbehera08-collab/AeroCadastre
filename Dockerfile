# ==============================================================================
# AeroCadastre Root Dockerfile — Production-Ready FastAPI Backend for Render
# ==============================================================================
FROM python:3.12-slim-bookworm

# Python execution and stdout flushing environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    PROJECT_ROOT=/app

# Install minimal OS packages required for C-extensions and GIS libraries
# (libgdal, libgeos, libproj, libpq for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    gdal-bin \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency requirements first to optimize Docker layer cache
COPY requirements.txt .

# Install CPU-optimized PyTorch first to keep image lightweight and fast
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend application source and configs
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY synthetic_data/ ./synthetic_data/
COPY configs/ ./configs/
COPY models/ ./models/

# Expose dynamic PORT for Render
EXPOSE 8000

# Start FastAPI backend using uvicorn listening on 0.0.0.0:${PORT}
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

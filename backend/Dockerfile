# SCIPHR Backend — Docker image for Render deployment
#
# Build context: repo root (render.yaml sets dockerContext: .)
# WORKDIR /app
#   /app/backend/   — FastAPI app (main.py, intelligence/, ai_analyst.py, ...)
#   /app/src/       — predictor_golden.py + feature calculator
#   /app/models/    — golden_model.pkl (1.9MB XGBoost model)
#
# Python imports inside backend/ use PYTHONPATH=/app/backend so
# "from gemini_service import ..." resolves without package prefixes.
# main.py uses __file__-anchored paths for src/ and models/ — container-safe.

FROM python:3.11-slim

WORKDIR /app

# System deps: libpq for psycopg2, gcc for C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Layer cache: copy requirements first so pip install is cached between code-only deploys
COPY backend/requirements-prod.txt requirements-prod.txt
RUN pip install --no-cache-dir -r requirements-prod.txt

# Application source
COPY backend/ ./backend/
COPY src/ ./src/
COPY models/golden_model.pkl ./models/golden_model.pkl

# Make backend/ importable without package prefixes (e.g. "from gemini_service import ...")
ENV PYTHONPATH=/app/backend

# Render injects $PORT; default 8000 for local docker run
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}

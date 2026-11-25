# --- Stage 1: build the React frontend -------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Stage 2: API + analysers ----------------------------------------------
FROM python:3.13-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# SR-01: run as an unprivileged user, never as root.
RUN useradd --create-home --uid 10001 gatekeeper
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /build/backend/static ./static

ENV QG_DATA_DIR=/data QG_WORK_DIR=/work QG_STATIC_DIR=/app/static PYTHONUNBUFFERED=1
RUN mkdir -p /data /work && chown gatekeeper:gatekeeper /data /work
USER gatekeeper
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

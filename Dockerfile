# --- Stage 1: build the React frontend ------------------------------------
FROM node:20-alpine AS frontend-build

WORKDIR /frontend

# Install dependencies first for better layer caching.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy the rest of the frontend source and build production assets to /frontend/dist.
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python runtime ---------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY app ./app

# Copy built frontend assets from the node build stage.
COPY --from=frontend-build /frontend/dist ./frontend_dist

# Config and data are provided via mounted volumes at runtime.
VOLUME ["/config", "/data"]

EXPOSE 8099

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8099"]

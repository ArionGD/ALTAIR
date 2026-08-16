# Stage 1: Build the React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build the FastAPI runtime
FROM python:3.11-slim
WORKDIR /app

# Install basic compiler dependencies if any python wheels need build step
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase
COPY src/ ./src
COPY astro/ ./astro
COPY data/ ./data
COPY templates/ ./templates
COPY main.py .

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Cloud Run binds to $PORT dynamically (default is 8080)
EXPOSE 8080
ENV PORT=8080

# Start application
CMD ["python", "main.py"]

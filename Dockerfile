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

# Install python dependencies from the new backend folder
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase, database, advisor, quant_lab, and assets
COPY backend/ ./backend
COPY database/ ./database
COPY advisor/ ./advisor
COPY quant_lab/ ./quant_lab
COPY Garud_Quant-lab_logo.png ./
COPY "Altair Logo.png" ./

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Set working directory to backend/ for the runtime context
WORKDIR /app/backend

# Cloud Run binds to $PORT dynamically (default is 8080)
EXPOSE 8080
ENV PORT=8080

# Start application
CMD ["python", "main.py"]

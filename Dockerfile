# Optimized Dockerfile for LeaseSight
# 1. Use a lightweight base image
FROM python:3.11-slim

# 2. Set working directory
WORKDIR /app

# 3. Optimize Layer Caching: Install dependencies first
# This ensures that 'pip install' is only re-run if requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of the application
# Use .dockerignore to skip data, venv, and cache folders
COPY . .

# 5. Expose the port (FastAPI default)
EXPOSE 8080

# 6. Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]

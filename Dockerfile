# Optimized Dockerfile for LeaseSight
FROM python:3.11-slim

# 1. Environment Fixes
WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 2. Dependency Optimization
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Application Setup
COPY . .
EXPOSE 8080

# 4. Correct Startup Command
# Using "python api/main.py" as requested
CMD ["python", "api/main.py"]

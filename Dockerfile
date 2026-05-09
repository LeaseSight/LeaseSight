# Hardened Dockerfile for LeaseSight
FROM python:3.11-slim

# 1. Environment Setup
WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 2. Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Application context
# We copy everything, including the data folder
COPY . .

# 4. Final Fail-Safe: Create necessary dirs
RUN mkdir -p /app/data/raw_pdfs

EXPOSE 8080

# Using absolute path execution for stability
CMD ["python", "/app/api/main.py"]

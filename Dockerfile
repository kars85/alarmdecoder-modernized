# Base image
FROM python:3.11-slim

# Metadata
LABEL maintainer="Nu Tech Software Solutions, Inc."
LABEL description="Dockerfile for alarmdecoder-modernized"

# Environment settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run tests by default (can be overridden)
CMD ["pytest"]
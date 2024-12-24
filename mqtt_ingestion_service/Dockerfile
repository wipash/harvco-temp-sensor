# Use official Python 3.13 slim image as base
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir .

# Copy application code
COPY . .

# Declare environment variables
ENV MQTT_BROKER_URL=
ENV MQTT_BROKER_PORT=
ENV MQTT_USERNAME=
ENV MQTT_PASSWORD=
ENV MQTT_TOPIC=
ENV DATABASE_URL=
ENV LOG_LEVEL=

# Run the application
CMD ["python", "main.py"]

# Health check (optional but recommended)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import socket; socket.socket().connect((environ.get('MQTT_BROKER_URL'), int(environ.get('MQTT_BROKER_PORT'))))" || exit 1

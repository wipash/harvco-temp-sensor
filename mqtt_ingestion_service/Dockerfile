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
        bash \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir .

# Copy the entrypoint script first and make it executable
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy application code
COPY . .

# Declare environment variables
ENV MQTT_BROKER_URL="mqtt.harvco.nz"
ENV MQTT_BROKER_PORT="1883"
ENV MQTT_USERNAME="harvcoiot"
ENV MQTT_PASSWORD=
ENV MQTT_TOPIC="harvco/+/sensor/+/state"
ENV DATABASE_URL=
ENV LOG_LEVEL="INFO"

# Use the entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]

# Health check (optional but recommended)
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import socket; socket.socket().connect((environ.get('MQTT_BROKER_URL'), int(environ.get('MQTT_BROKER_PORT'))))" || exit 1

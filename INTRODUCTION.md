This document provides a comprehensive introduction to the Temperature Sensor Monitoring System project.

## Project Objective

The primary goal of this project is to build a system that:

    Collects temperature readings from remote sensors via MQTT.
    Stores these readings in a PostgreSQL database.
    Provides a web interface for users to view current and historical temperature data through interactive, time-filterable graphs.
    Ensures data security and access control through authentication and authorization mechanisms.

## System Architecture

The system consists of the following components:

    MQTT Broker (Mosquitto): Receives messages from remote temperature sensors.
    MQTT Ingestion Service: Subscribes to MQTT topics, processes incoming sensor data, and stores it in the database.
    Backend API Server (FastAPI): Serves as the API layer for the frontend application, handling authentication and data retrieval.
    Frontend Web Application (Next.js): Provides a user interface for logging in and viewing temperature data.
    Database (PostgreSQL): Stores user information, device metadata, and sensor readings.
    Shared Code: Contains common models, schemas, and utilities used by both backend services.
    Logging System (Loki): Aggregates logs from the services for monitoring and debugging.

## Development Approach

    Monorepo Structure: The entire project, including the MQTT ingestion service, API server, frontend application, and shared code, resides in a single repository for simplicity and ease of development.
    Test-Driven Development (TDD): Emphasis on writing tests before implementing functionality to ensure code reliability and facilitate maintenance.
    Modern Python Practices: Utilize dependency injection, type annotations, and asynchronous programming to create clean, efficient, and testable code.


## Project Structure

The repository is organized as follows:

project-root/
├── shared/
│   ├── models/
│   ├── schemas/
│   ├── utils/
├── api_server/
│   └── (API server code)
├── mqtt_ingestion_service/
│   ├── main.py
│   ├── config.py
│   ├── services/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── (Frontend application code)
├── README.md

## Technology Stack
### MQTT Ingestion Service

    Programming Language: Python 3.10+
    MQTT Client Library: asyncio-mqtt
    Asynchronous Programming: asyncio
    Database ORM: SQLAlchemy (with asyncio support)
    Configuration Management: pydantic's BaseSettings
    Logging: Python's built-in logging module
    Testing Frameworks: pytest, pytest-asyncio, pytest-mock

### Shared Code

    Models and Schemas: pydantic models for data validation and SQLAlchemy models for database representation.
    Utilities: Shared utility functions and classes.

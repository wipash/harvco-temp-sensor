**Architecture Decisions for the MQTT Ingestion Service**

---

### **Project Structure**

- **Monorepo Approach**: The entire project, including the MQTT ingestion service, API server, and shared code, will reside in a single repository for simplicity and ease of development.

  ```
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
  ├── README.md
  ```

- **Shared Code**: Common code such as database models, schemas, and utility functions are placed in the `shared/` directory and included in both services using relative paths.

### **Programming Language and Frameworks**

- **Language**: Python 3.10+
- **MQTT Client Library**: `asyncio-mqtt` for asynchronous MQTT communication.
- **Asynchronous Programming**: Use Python's `asyncio` library, leveraging `async`/`await` syntax.
- **Database ORM**: `SQLAlchemy 1.4+` with asyncio support for database interactions.
- **Configuration Management**: Use `pydantic`'s `BaseSettings` for environment variables and configuration handling.

### **Database**

- **Database**: PostgreSQL.
- **Database Models**: Defined using SQLAlchemy ORM and shared between services.
- **Database Session Management**: Asynchronous sessions with proper connection and transaction handling.

### **Testing**

- **Testing Framework**: `pytest` with `pytest-asyncio` for asynchronous code testing.
- **Mocking**: Use `unittest.mock` or `pytest-mock` to mock external dependencies like MQTT broker and database sessions in tests.
- **Test-Driven Development (TDD)**: Write tests before implementing each functionality to ensure correctness and facilitate refactoring.

### **Dependency Injection**

- Use explicit dependency injection to pass dependencies (e.g., database session, MQTT client) into functions and classes to enhance testability and maintainability.

### **Logging**

- Use the built-in `logging` module for logging events, errors, and other important information.
- Configure log levels and handlers appropriately for development and production environments.

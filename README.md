# Telegram Meeting-Scheduler Bot

A Telegram bot that enables explicit participant selection for meetings, validates Google Calendar availability, computes time intersections within working hours, and proposes mutually-available slots for voting.

## Features

- **Explicit Participant Selection**: Each meeting has a defined participant list selected by the organizer
- **Google Calendar Integration**: Validates availability using Google Calendar FreeBusy API
- **Time Intersection Computation**: Finds common free time slots across all participants
- **Working Hours Constraint**: Default 08:00–20:00 per user timezone
- **Batch Voting**: Five slots presented at a time with pagination
- **Reliability**: Re-validates availability before creating final events

## Technology Stack

- **Backend**: Python 3.11+
- **Web Framework**: FastAPI 0.104+
- **Bot Framework**: Aiogram 3.x
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0+
- **Migrations**: Alembic
- **Authentication**: Google OAuth 2.0
- **Encryption**: PyNaCl (libsodium)
- **Task Queue**: Celery with Redis
- **Monitoring**: Prometheus + Grafana

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd tg_bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/dev.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Set up database**
   ```bash
   make setup-db
   make migrate
   ```

6. **Start development environment**
   ```bash
   make dev
   ```

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Run tests
docker-compose exec api pytest

# Stop services
docker-compose down
```

## Development

### Project Structure

```
tg_bot/
├── src/                    # Source code
│   ├── bot/               # Telegram Bot (Aiogram)
│   ├── api/               # REST API (FastAPI)
│   ├── services/          # Business Logic Services
│   ├── providers/         # External Service Providers
│   ├── models/            # Database Models
│   ├── schemas/           # Pydantic Schemas
│   ├── database/          # Database Configuration
│   ├── config/            # Configuration Management
│   ├── utils/             # Utilities
│   └── workers/           # Background Workers
├── tests/                 # Test Suite
├── scripts/               # Development Scripts
├── docker/                # Docker Configuration
├── docs/                  # Documentation
└── requirements/          # Python Dependencies
```

### Available Commands

```bash
# Development
make install-dev          # Install development dependencies
make dev                  # Start development environment
make test                 # Run all tests
make test-unit            # Run unit tests
make test-integration     # Run integration tests
make test-e2e             # Run end-to-end tests

# Code Quality
make lint                 # Run linting
make format               # Format code
make check                # Run all checks

# Database
make setup-db             # Set up database
make migrate              # Create new migration
make upgrade              # Upgrade database
make downgrade            # Downgrade database

# Docker
make docker-build         # Build Docker images
make docker-up            # Start Docker services
make docker-down          # Stop Docker services

# Cleanup
make clean                # Clean temporary files
```

### Configuration

The application uses environment variables for configuration. Copy `env.example` to `.env` and modify as needed:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tg_bot_dev

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# Encryption
ENCRYPTION_KEY=your_32_byte_encryption_key_here
```

## API Documentation

When running in development mode, API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

The project includes comprehensive testing:

- **Unit Tests**: Test individual components
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete user flows

Run tests with:

```bash
# All tests
make test

# Specific test types
make test-unit
make test-integration
make test-e2e

# With coverage
pytest --cov=src tests/
```

## Monitoring

The application includes monitoring and observability:

- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **Structured Logging**: JSON-formatted logs
- **Health Checks**: Application health monitoring

Access monitoring dashboards:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for your changes
5. Run the test suite
6. Submit a pull request

### Code Style

The project uses automated code formatting and linting:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

These are enforced via pre-commit hooks:

```bash
# Install pre-commit hooks
make install-dev

# Run manually
pre-commit run --all-files
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Create an issue in the repository
- Check the documentation in the `docs/` directory
- Review the API documentation at `/docs`

## Roadmap

### MVP (Current)
- Google Calendar integration
- Required participants only
- Basic voting interface
- Simple time slot resolution

### Future Enhancements
- Additional calendar providers (Yandex Calendar)
- Optional attendees support
- Advanced user preferences
- Web interface
- Natural language processing
- Smart scheduling suggestions



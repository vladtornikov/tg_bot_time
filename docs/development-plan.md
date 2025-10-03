# Development Plan — Telegram Meeting-Scheduler Bot

**Version:** MVP — Selected Participants, Google-only  
**Last updated:** 2025-10-03 22:19 (Asia/Bangkok)

## 1. Project Overview

This development plan outlines the implementation strategy for the Telegram Meeting-Scheduler Bot, a system that enables explicit participant selection, Google Calendar integration, and automated time slot resolution with voting mechanisms.

### 1.1 Technology Stack

#### Core Technologies
- **Backend**: Python 3.11+
- **Web Framework**: FastAPI 0.104+
- **Bot Framework**: Aiogram 3.x
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0+
- **Migrations**: Alembic
- **Authentication**: Google OAuth 2.0
- **Encryption**: PyNaCl (libsodium) or AWS KMS
- **Task Queue**: Celery with Redis
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured JSON logging
- **Testing**: pytest, pytest-asyncio
- **Code Quality**: black, isort, flake8, mypy

#### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx or Caddy
- **SSL/TLS**: Let's Encrypt
- **Deployment**: Docker Swarm or Kubernetes
- **CI/CD**: GitHub Actions
- **Environment**: Development, Staging, Production

### 1.2 Project Structure

```
tg_bot/
├── src/
│   ├── bot/                    # Telegram Bot (Aiogram)
│   │   ├── __init__.py
│   │   ├── handlers/           # Command and callback handlers
│   │   │   ├── __init__.py
│   │   │   ├── commands.py     # /meet, /link_calendar commands
│   │   │   ├── callbacks.py    # Vote buttons, participant picker
│   │   │   └── middlewares.py  # Auth, logging, error handling
│   │   ├── keyboards/          # Inline keyboards and buttons
│   │   │   ├── __init__.py
│   │   │   ├── voting.py       # Vote buttons, Next 5
│   │   │   └── participants.py # Participant selection
│   │   ├── states.py           # FSM states
│   │   └── utils.py            # Bot utilities
│   ├── api/                    # REST API (FastAPI)
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app
│   │   ├── routes/             # API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── oauth.py        # OAuth endpoints
│   │   │   └── meetings.py     # Meeting endpoints
│   │   ├── dependencies.py     # FastAPI dependencies
│   │   └── middleware.py       # CORS, auth, logging
│   ├── services/               # Business Logic Services
│   │   ├── __init__.py
│   │   ├── scheduler.py        # Meeting lifecycle management
│   │   ├── calendar_provider.py # Calendar abstraction
│   │   ├── roster.py           # User and chat management
│   │   └── notification.py     # Notifications and reminders
│   ├── providers/              # External Service Providers
│   │   ├── __init__.py
│   │   ├── base.py             # Provider interface
│   │   ├── google.py           # Google Calendar provider
│   │   └── telegram.py         # Telegram API wrapper
│   ├── models/                 # Database Models
│   │   ├── __init__.py
│   │   ├── user.py             # User, Chat, ChatMembership
│   │   ├── meeting.py          # Meeting, MeetingParticipant
│   │   ├── oauth.py            # OAuthToken
│   │   └── vote.py             # Vote
│   ├── schemas/                # Pydantic Schemas
│   │   ├── __init__.py
│   │   ├── user.py             # User schemas
│   │   ├── meeting.py          # Meeting schemas
│   │   └── api.py              # API request/response schemas
│   ├── database/               # Database Configuration
│   │   ├── __init__.py
│   │   ├── connection.py       # Database connection
│   │   ├── session.py          # Session management
│   │   └── migrations/         # Alembic migrations
│   ├── config/                 # Configuration Management
│   │   ├── __init__.py
│   │   ├── settings.py         # Pydantic settings
│   │   └── environments/       # Environment-specific configs
│   ├── utils/                  # Utilities
│   │   ├── __init__.py
│   │   ├── encryption.py       # Token encryption
│   │   ├── timezone.py         # Timezone handling
│   │   ├── scheduling.py       # Time slot computation
│   │   └── validation.py       # Data validation
│   └── workers/                # Background Workers
│       ├── __init__.py
│       ├── oauth_reminders.py  # OAuth consent reminders
│       └── retry_tasks.py      # Retry failed operations
├── tests/                      # Test Suite
│   ├── __init__.py
│   ├── conftest.py             # pytest configuration
│   ├── unit/                   # Unit tests
│   │   ├── test_services/
│   │   ├── test_models/
│   │   └── test_utils/
│   ├── integration/            # Integration tests
│   │   ├── test_api/
│   │   ├── test_bot/
│   │   └── test_database/
│   └── e2e/                    # End-to-end tests
│       └── test_meeting_flow.py
├── scripts/                    # Development Scripts
│   ├── setup_db.py             # Database setup
│   ├── create_migration.py     # Migration creation
│   └── seed_data.py            # Test data seeding
├── docker/                     # Docker Configuration
│   ├── Dockerfile.bot          # Bot container
│   ├── Dockerfile.api          # API container
│   ├── Dockerfile.worker       # Worker container
│   └── docker-compose.yml      # Development environment
├── docs/                       # Documentation
│   ├── api/                    # API documentation
│   ├── deployment/             # Deployment guides
│   └── development/            # Development guides
├── .github/                    # GitHub Actions
│   └── workflows/
│       ├── ci.yml              # Continuous Integration
│       └── deploy.yml          # Deployment
├── requirements/               # Python Dependencies
│   ├── base.txt                # Core dependencies
│   ├── dev.txt                 # Development dependencies
│   ├── prod.txt                # Production dependencies
│   └── test.txt                # Testing dependencies
├── pyproject.toml              # Project configuration
├── alembic.ini                 # Alembic configuration
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
├── README.md                   # Project documentation
└── Makefile                    # Development commands
```

## 2. Development Phases

### Phase 1: Foundation Setup (Week 1-2)
**Goal**: Establish project foundation and core infrastructure

#### 2.1 Project Setup
- [ ] Initialize project structure
- [ ] Set up Python environment and dependencies
- [ ] Configure development tools (black, isort, flake8, mypy)
- [ ] Set up Docker development environment
- [ ] Configure CI/CD pipeline
- [ ] Set up database (PostgreSQL)
- [ ] Configure Alembic for migrations

#### 2.2 Core Models and Database
- [ ] Implement User model and related entities
- [ ] Implement Meeting model and relationships
- [ ] Implement OAuthToken model with encryption
- [ ] Implement Vote model
- [ ] Create database migrations
- [ ] Set up database connection and session management

#### 2.3 Configuration Management
- [ ] Implement Pydantic settings
- [ ] Set up environment-specific configurations
- [ ] Configure encryption utilities
- [ ] Set up logging configuration

#### 2.4 Basic API Structure
- [ ] Set up FastAPI application
- [ ] Implement basic middleware (CORS, logging, error handling)
- [ ] Create API dependency injection
- [ ] Set up API documentation

### Phase 2: Core Services (Week 3-4)
**Goal**: Implement core business logic services

#### 2.1 Roster Service
- [ ] Implement user registration and management
- [ ] Implement chat membership tracking
- [ ] Implement participant validation
- [ ] Add user timezone and working hours management

#### 2.2 Calendar Provider Layer
- [ ] Implement base calendar provider interface
- [ ] Implement Google Calendar provider
- [ ] Implement OAuth flow (start, callback, refresh)
- [ ] Implement FreeBusy API integration
- [ ] Implement event creation functionality
- [ ] Add error handling and retry logic

#### 2.3 Scheduler Service
- [ ] Implement meeting lifecycle management
- [ ] Implement time slot computation algorithm
- [ ] Implement working hours clipping
- [ ] Implement time intersection logic
- [ ] Implement candidate generation and pagination
- [ ] Add state machine implementation

#### 2.4 Notification Service
- [ ] Implement Telegram message sending
- [ ] Implement DM functionality
- [ ] Implement notification templates
- [ ] Add error handling for message delivery

### Phase 3: Bot Implementation (Week 5-6)
**Goal**: Implement Telegram bot functionality

#### 3.1 Bot Framework Setup
- [ ] Set up Aiogram 3.x application
- [ ] Configure webhook handling
- [ ] Implement bot middleware (auth, logging, error handling)
- [ ] Set up FSM states

#### 3.2 Command Handlers
- [ ] Implement `/meet` command handler
- [ ] Implement `/link_calendar` command handler
- [ ] Add command validation and parsing
- [ ] Implement participant mention handling
- [ ] Add error handling and user feedback

#### 3.3 Interactive Elements
- [ ] Implement participant picker keyboard
- [ ] Implement voting keyboard (Vote buttons)
- [ ] Implement "Next 5" button functionality
- [ ] Add callback query handlers
- [ ] Implement inline keyboard management

#### 3.4 Bot State Management
- [ ] Implement meeting creation flow
- [ ] Implement OAuth consent flow
- [ ] Implement voting flow
- [ ] Implement confirmation flow
- [ ] Add state persistence and recovery

### Phase 4: API Integration (Week 7-8)
**Goal**: Implement REST API endpoints

#### 4.1 OAuth Endpoints
- [ ] Implement `GET /oauth/google/start`
- [ ] Implement `GET /oauth/google/callback`
- [ ] Add OAuth state management
- [ ] Implement token refresh logic
- [ ] Add error handling and validation

#### 4.2 Meeting Endpoints
- [ ] Implement `POST /meetings`
- [ ] Implement `POST /meetings/{id}/resolve`
- [ ] Implement `POST /meetings/{id}/confirm`
- [ ] Add request validation
- [ ] Implement response schemas
- [ ] Add error handling

#### 4.3 API Security
- [ ] Implement request authentication
- [ ] Add rate limiting
- [ ] Implement input validation
- [ ] Add security headers
- [ ] Implement request logging

### Phase 5: Background Workers (Week 9-10)
**Goal**: Implement background task processing

#### 5.1 Task Queue Setup
- [ ] Set up Celery with Redis
- [ ] Configure task routing
- [ ] Set up task monitoring
- [ ] Implement task retry logic

#### 5.2 OAuth Reminders
- [ ] Implement consent reminder tasks
- [ ] Add reminder scheduling
- [ ] Implement reminder cancellation
- [ ] Add reminder tracking

#### 5.3 Retry Tasks
- [ ] Implement failed operation retries
- [ ] Add exponential backoff
- [ ] Implement task deduplication
- [ ] Add retry monitoring

### Phase 6: Testing and Quality Assurance (Week 11-12)
**Goal**: Comprehensive testing and quality assurance

#### 6.1 Unit Testing
- [ ] Write unit tests for all services
- [ ] Write unit tests for models
- [ ] Write unit tests for utilities
- [ ] Achieve >90% code coverage
- [ ] Add test data fixtures

#### 6.2 Integration Testing
- [ ] Write API integration tests
- [ ] Write bot integration tests
- [ ] Write database integration tests
- [ ] Test external service integrations
- [ ] Add test environment setup

#### 6.3 End-to-End Testing
- [ ] Write E2E tests for meeting flow
- [ ] Write E2E tests for OAuth flow
- [ ] Write E2E tests for voting flow
- [ ] Test error scenarios
- [ ] Add performance testing

#### 6.4 Code Quality
- [ ] Run code formatting and linting
- [ ] Fix type checking issues
- [ ] Review and refactor code
- [ ] Update documentation
- [ ] Perform security audit

### Phase 7: Deployment and Monitoring (Week 13-14)
**Goal**: Production deployment and monitoring setup

#### 7.1 Production Configuration
- [ ] Configure production environment
- [ ] Set up SSL/TLS certificates
- [ ] Configure reverse proxy
- [ ] Set up database backups
- [ ] Configure environment variables

#### 7.2 Monitoring and Observability
- [ ] Set up Prometheus metrics
- [ ] Configure Grafana dashboards
- [ ] Set up log aggregation
- [ ] Implement health checks
- [ ] Add alerting rules

#### 7.3 Deployment
- [ ] Set up deployment pipeline
- [ ] Configure container orchestration
- [ ] Implement blue-green deployment
- [ ] Set up database migrations
- [ ] Add deployment monitoring

#### 7.4 Performance Optimization
- [ ] Optimize database queries
- [ ] Implement caching strategies
- [ ] Add connection pooling
- [ ] Optimize API responses
- [ ] Load test the system

## 3. Implementation Guidelines

### 3.1 Code Standards

#### Python Code Style
- Follow PEP 8 guidelines
- Use type hints for all functions and methods
- Write docstrings for all public functions and classes
- Use meaningful variable and function names
- Keep functions small and focused
- Use dependency injection for testability

#### Database Design
- Use proper foreign key constraints
- Implement soft deletes where appropriate
- Use database indexes for performance
- Follow naming conventions (snake_case)
- Use database transactions for consistency
- Implement proper error handling

#### API Design
- Follow RESTful principles
- Use appropriate HTTP status codes
- Implement proper error responses
- Use consistent naming conventions
- Add request/response validation
- Document all endpoints

### 3.2 Security Best Practices

#### Authentication and Authorization
- Implement proper OAuth 2.0 flow
- Use secure token storage
- Implement token refresh logic
- Add request authentication
- Use least privilege principle
- Implement rate limiting

#### Data Protection
- Encrypt sensitive data at rest
- Use HTTPS for all communications
- Implement input validation
- Sanitize user inputs
- Use secure random number generation
- Implement proper error handling

#### Infrastructure Security
- Use container security best practices
- Implement network segmentation
- Use secure configuration management
- Implement monitoring and alerting
- Regular security updates
- Implement backup and recovery

### 3.3 Performance Guidelines

#### Database Performance
- Use proper indexing strategies
- Implement query optimization
- Use connection pooling
- Implement caching where appropriate
- Monitor database performance
- Use database transactions efficiently

#### API Performance
- Implement response caching
- Use async/await for I/O operations
- Implement request batching
- Monitor API performance
- Use compression for large responses
- Implement proper error handling

#### Bot Performance
- Use async operations for external calls
- Implement message queuing
- Use efficient keyboard generation
- Monitor bot response times
- Implement proper error handling
- Use connection pooling

### 3.4 Testing Strategy

#### Unit Testing
- Test all business logic
- Mock external dependencies
- Use test fixtures
- Achieve high code coverage
- Test error scenarios
- Use parameterized tests

#### Integration Testing
- Test API endpoints
- Test database operations
- Test external service integrations
- Use test databases
- Test authentication flows
- Test error handling

#### End-to-End Testing
- Test complete user flows
- Test error scenarios
- Use realistic test data
- Test performance under load
- Test security scenarios
- Automate test execution

## 4. Development Environment Setup

### 4.1 Prerequisites

#### Required Software
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose
- Git
- Node.js (for frontend tools if needed)

#### Development Tools
- VS Code or PyCharm
- Postman or Insomnia (for API testing)
- pgAdmin or DBeaver (for database management)
- Redis Commander (for Redis management)
- Docker Desktop

### 4.2 Environment Configuration

#### Local Development
```bash
# Clone the repository
git clone <repository-url>
cd tg_bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/dev.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Set up database
make setup-db

# Run migrations
make migrate

# Start development environment
make dev
```

#### Docker Development
```bash
# Start development environment
docker-compose up -d

# View logs
docker-compose logs -f

# Run tests
docker-compose exec api pytest

# Stop environment
docker-compose down
```

### 4.3 Development Workflow

#### Daily Development
1. Pull latest changes from main branch
2. Create feature branch
3. Implement changes with tests
4. Run tests and linting
5. Create pull request
6. Code review and merge

#### Testing Workflow
1. Write tests before implementation (TDD)
2. Run unit tests frequently
3. Run integration tests before commits
4. Run E2E tests before deployment
5. Monitor test coverage
6. Fix failing tests immediately

#### Deployment Workflow
1. Merge to main branch
2. Run CI/CD pipeline
3. Deploy to staging environment
4. Run smoke tests
5. Deploy to production
6. Monitor deployment

## 5. Risk Mitigation

### 5.1 Technical Risks

#### API Rate Limits
- **Risk**: Google Calendar API quotas exceeded
- **Mitigation**: Implement request throttling and caching
- **Monitoring**: Track API usage and implement alerts

#### Token Expiration
- **Risk**: OAuth tokens expire during operations
- **Mitigation**: Proactive token refresh and retry logic
- **Monitoring**: Monitor token expiration and refresh success

#### Database Performance
- **Risk**: Database queries become slow with scale
- **Mitigation**: Proper indexing and query optimization
- **Monitoring**: Database performance monitoring

### 5.2 Business Risks

#### User Adoption
- **Risk**: Low participation rates
- **Mitigation**: User-friendly interface and clear instructions
- **Monitoring**: Track user engagement metrics

#### Privacy Concerns
- **Risk**: Users concerned about calendar data access
- **Mitigation**: Clear privacy policy and minimal data access
- **Monitoring**: User feedback and privacy complaints

#### Scalability Limits
- **Risk**: Performance degradation with growth
- **Mitigation**: Horizontal scaling and performance optimization
- **Monitoring**: Performance metrics and capacity planning

### 5.3 Operational Risks

#### Service Outages
- **Risk**: External service dependencies fail
- **Mitigation**: Graceful degradation and fallback mechanisms
- **Monitoring**: Service health monitoring and alerting

#### Data Loss
- **Risk**: Database corruption or data loss
- **Mitigation**: Regular backups and disaster recovery
- **Monitoring**: Backup verification and recovery testing

#### Security Breaches
- **Risk**: Unauthorized access to user data
- **Mitigation**: Security best practices and regular audits
- **Monitoring**: Security monitoring and incident response

## 6. Success Metrics

### 6.1 Technical Metrics
- **Response Time**: ≤2 seconds p95 for slot resolution
- **Availability**: 99.9% uptime
- **Error Rate**: <1% error rate
- **Test Coverage**: >90% code coverage
- **Performance**: Support ≤30 participants per meeting

### 6.2 Business Metrics
- **User Adoption**: Track active users and meeting creation
- **Success Rate**: Track successful meeting scheduling
- **User Satisfaction**: Monitor user feedback and ratings
- **Feature Usage**: Track feature adoption and usage patterns

### 6.3 Quality Metrics
- **Code Quality**: Maintain high code quality standards
- **Security**: Zero security incidents
- **Reliability**: Minimal service disruptions
- **Maintainability**: Easy to maintain and extend

## 7. Future Enhancements

### 7.1 Short-term (3-6 months)
- **Additional Calendar Providers**: Yandex Calendar support
- **Optional Attendees**: Support for optional participants
- **Advanced Preferences**: User preference management
- **Mobile App**: Native mobile application
- **Web Interface**: Admin web application

### 7.2 Medium-term (6-12 months)
- **Natural Language Processing**: NLP for meeting creation
- **Smart Scheduling**: AI-powered scheduling suggestions
- **Integration APIs**: Third-party integrations
- **Advanced Analytics**: Meeting analytics and insights
- **Multi-language Support**: Internationalization

### 7.3 Long-term (12+ months)
- **Enterprise Features**: Advanced enterprise functionality
- **Workflow Automation**: Automated workflow management
- **Advanced Security**: Enterprise-grade security features
- **Scalability**: Global deployment and scaling
- **AI Integration**: Advanced AI-powered features

This development plan provides a comprehensive roadmap for implementing the Telegram Meeting-Scheduler Bot system, with clear phases, guidelines, and success metrics to ensure successful delivery of the MVP.


# Tests Directory

This directory contains all test-related files for the AI-First Internal Helpdesk Portal backend.

## Directory Structure

### Core Test Files
- `test_*.py` - Unit and integration tests for various components
- `__init__.py` - Python package initialization
- `pytest.ini` - Pytest configuration (located in backend root)

### Test Categories

#### Authentication & Authorization
- `test_auth.py` - Authentication system tests
- `test_registration.py` - User registration tests
- `test_user_service.py` - User service tests

#### Ticket Management
- `test_ticket_*.py` - Ticket-related tests
  - `test_ticket_service.py` - Ticket service unit tests
  - `test_ticket_endpoints.py` - Ticket API endpoint tests
  - `test_ticket_schema.py` - Ticket schema validation tests
  - `test_ticket_authorization.py` - Role-based access control tests
  - `test_ticket_creation_ai_integration.py` - AI integration tests
  - `test_ticket_simple.py` - Basic ticket functionality tests

#### AI Services
- `test_ai_*.py` - AI-related tests
  - `test_ai_agent.py` - AI agent response suggestion tests
  - `test_ai_bot.py` - Self-serve AI bot tests
  - `test_ai_hsa.py` - Harmful/Spam Analysis tests
  - `test_ai_routing.py` - Department routing tests
  - `test_ai_services.py` - General AI services tests
  - `test_ai_agent_websocket_integration.py` - AI WebSocket integration tests

#### Real-Time Communication
- `test_websocket_*.py` - WebSocket-related tests
  - `test_websocket_chat.py` - WebSocket chat functionality tests
  - `test_websocket_integration.py` - WebSocket integration tests
- `test_message_service.py` - Message service tests

#### Content & Safety
- `test_content_flagging.py` - Content flagging system tests
- `test_hsa_manual.py` - Manual HSA testing utilities

#### Infrastructure
- `test_database.py` - Database connection and operations tests
- `test_webhooks.py` - Webhook system tests
- `test_webhook_integration.py` - Webhook integration tests
- `test_rag.py` - RAG (Retrieval-Augmented Generation) tests
- `test_routing.py` - General routing tests

#### Application
- `test_root.py` - Root endpoint tests
- `test_home.py` - Home page tests

### Utilities Directory (`utilities/`)
Contains helper scripts and debugging tools:

- `debug_hsa.py` - HSA debugging utilities
- `debug_tickets.py` - Ticket debugging utilities  
- `seed_admin.py` - Admin user seeding script

### Testing Tools
- `websocket_test_client.py` - WebSocket testing client
- `WEBSOCKET_TESTING_GUIDE.md` - WebSocket testing documentation

## Running Tests

### All Tests
```bash
cd backend
pytest
```

### Specific Test Categories
```bash
# AI tests
pytest tests/test_ai_*.py

# Ticket tests  
pytest tests/test_ticket_*.py

# WebSocket tests
pytest tests/test_websocket_*.py

# Authentication tests
pytest tests/test_auth.py tests/test_registration.py
```

### Individual Test Files
```bash
pytest tests/test_ai_agent.py -v
```

### Test Coverage
```bash
pytest --cov=app tests/
```

## Test Configuration

- **pytest.ini**: Located in backend root, contains pytest configuration
- **Fixtures**: Shared fixtures are defined in individual test files
- **Database**: Tests use a test MongoDB database
- **Authentication**: Tests use mock authentication where needed

## Adding New Tests

1. Create test files following the naming convention: `test_<component>.py`
2. Use descriptive test class and method names
3. Include docstrings for test methods
4. Use appropriate fixtures for setup/teardown
5. Follow existing patterns for consistency

## Debugging

Use the utilities in the `utilities/` directory for debugging specific components:

- Run `python tests/utilities/debug_hsa.py` for HSA debugging
- Run `python tests/utilities/debug_tickets.py` for ticket debugging
- Run `python tests/utilities/seed_admin.py` to create admin users

## Documentation

- `WEBSOCKET_TESTING_GUIDE.md` - Comprehensive WebSocket testing guide
- Individual test files contain inline documentation
- See main `IMPLEMENTATION_SUMMARY.md` for overall project documentation

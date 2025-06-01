# AI-First Internal Helpdesk Portal - Backend

This is the backend API for the AI-First Internal Helpdesk Portal built with FastAPI and MongoDB.

## Features

- User authentication and authorization (JWT-based)
- Role-based access control (User, Agent, Admin)
- Ticket management system
- MongoDB integration
- Comprehensive test suite

## Setup

### Prerequisites

- Python 3.8+
- MongoDB Atlas account or local MongoDB instance
- Virtual environment (recommended)

### Installation

1. Create and activate virtual environment:
```bash
py -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with the following variables:
```
MONGODB_URI=your_mongodb_connection_string
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=development
```

### Running the Application

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, you can access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

Run all tests:
```bash
pytest
```

Run specific test files:
```bash
pytest tests/test_auth.py
pytest tests/test_ticket_endpoints.py
```

## Code Quality

Format code:
```bash
black .
```

Lint code:
```bash
flake8 .
```

## Project Structure

```
backend/
├── app/
│   ├── core/           # Core functionality (auth, database)
│   ├── models/         # Database models
│   ├── routers/        # API route handlers
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic
│   └── utils/          # Utility functions
├── tests/              # Test files
├── main.py             # FastAPI application entry point
├── requirements.txt    # Python dependencies
└── pytest.ini         # Pytest configuration
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user info

### Tickets
- `POST /tickets` - Create new ticket
- `GET /tickets` - Get tickets (filtered by user role)
- `GET /tickets/{ticket_id}` - Get specific ticket
- `PUT /tickets/{ticket_id}` - Update ticket

### Users
- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update user profile

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | Required |
| `SECRET_KEY` | JWT secret key | Required |
| `ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time | 30 |
| `ENVIRONMENT` | Application environment | development |

## Contributing

1. Follow the existing code style
2. Write tests for new features
3. Update documentation as needed
4. Run tests and linting before committing

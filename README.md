# AI-First Internal Helpdesk Portal

A comprehensive internal helpdesk system with AI-powered features for ticket routing, response suggestions, and misuse detection. This project includes both backend API and frontend web application.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ with pip
- Node.js 16+ with npm
- MongoDB Atlas account or local MongoDB instance

### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
py -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Create .env file with your MongoDB URI
echo "MONGODB_URI=your_mongodb_connection_string" > .env
echo "SECRET_KEY=your_secret_key_here" >> .env

# Seed database with test users (optional)
python seed_admin.py

# Start the backend server
uvicorn main:app --reload
```

### 2. Frontend Setup
```bash
# Create frontend with Vite (if not exists)
npm create vite@latest frontend --template react

# Navigate to frontend directory (in a new terminal)
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

### 3. Access the Application
- **Frontend**: http://localhost:5174 (or next available port)
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 4. Demo Accounts
After running the seed script, you can login with these test accounts:
- **Admin**: admin / admin123
- **User**: testuser / password123
- **IT Agent**: itagent / password123
- **HR Agent**: hragent / password123

## 📋 Current Features (Phase 0-1 Complete)

### ✅ Authentication & Authorization
- JWT-based authentication
- Role-based access control (User, IT Agent, HR Agent, Admin)
- User registration and login
- Secure password hashing

### ✅ Ticket Management System
- Create tickets with title, description, and urgency levels
- Role-based ticket access control
- Ticket filtering by status and department
- Edit tickets based on permissions
- Comprehensive ticket lifecycle management

### ✅ User Dashboards
- **User Dashboard**: Personal ticket overview and creation
- **Agent Dashboard**: Department-specific ticket management
- **Admin Dashboard**: System-wide ticket overview and statistics

### ✅ Database Integration
- MongoDB with Motor (async driver)
- Comprehensive data models
- Database connection management
- Rate limiting (5 tickets per 24 hours per user)

### ✅ Testing & Quality
- Comprehensive test suite with pytest
- Role-based access control tests
- Database integration tests
- Code formatting with Black
- API endpoint testing

## 🔮 Planned Features (Future Phases)

### Phase 2: LLM Auto-Routing & HSA Filtering
- AI-powered ticket routing to IT/HR departments
- Harmful/Spam Analysis (HSA) for content filtering
- Webhook system for internal notifications

### Phase 3: Self-Serve AI Bot
- RAG-powered knowledge base queries
- User homepage AI assistant
- Context-aware responses

### Phase 4: Real-Time Chat
- WebSocket-based chat within tickets
- Message persistence and history
- Real-time notifications

### Phase 5: Agent-Side AI Suggestions
- AI-powered response suggestions for agents
- Knowledge base integration
- Response quality feedback

### Phase 6: Admin Panel & Misuse Detection
- Automated misuse pattern detection
- Admin dashboard for flagged content
- User behavior analysis

## 🏗️ Project Structure

```
AI-First-Internal-Helpdesk-Portal/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── core/              # Database and auth core
│   │   ├── models/            # Database models
│   │   ├── routers/           # API route handlers
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   └── utils/             # Utility functions
│   ├── tests/                 # Test suite
│   ├── main.py               # FastAPI application
│   └── requirements.txt      # Python dependencies
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── context/          # React context providers
│   │   ├── services/         # API service modules
│   │   └── utils/            # Utility functions
│   ├── public/               # Static assets
│   └── package.json          # Node.js dependencies
└── README.md                 # This file
```

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **MongoDB** - Document database with Motor async driver
- **JWT** - JSON Web Tokens for authentication
- **Pydantic** - Data validation and serialization
- **pytest** - Testing framework

### Frontend
- **React 18** - Frontend framework
- **React Router 6** - Client-side routing
- **Axios** - HTTP client for API calls
- **Vite** - Build tool and development server

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest                    # Run all tests
pytest -v                # Verbose output
pytest tests/test_auth.py # Run specific test file
```

### Test Coverage
- Authentication and authorization
- Ticket CRUD operations
- Role-based access control
- Database operations
- API endpoint validation

## 📚 API Documentation

The backend provides interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints
- `POST /auth/login` - User authentication
- `POST /auth/register` - User registration
- `GET /auth/me` - Get current user
- `POST /tickets` - Create ticket
- `GET /tickets` - List tickets (role-filtered)
- `GET /tickets/{id}` - Get specific ticket
- `PUT /tickets/{id}` - Update ticket

## 🔧 Configuration

### Backend Environment Variables
```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/helpdesk_db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=development
```

### Frontend Configuration
The frontend is configured to connect to the backend at `http://localhost:8000`. Update `src/services/api.js` if needed.

## 🚀 Deployment

### Backend Deployment
- Compatible with any ASGI server (Uvicorn, Gunicorn)
- Environment variables for configuration
- MongoDB Atlas for production database

### Frontend Deployment
- Build with `npm run build`
- Serve static files with any web server
- Configure API base URL for production

## 🤝 Contributing

1. Follow the existing code structure
2. Write tests for new features
3. Use Black for Python code formatting
4. Follow React best practices for frontend
5. Update documentation for new features

## 📄 License

This project is for internal use and development purposes.

## 🆘 Support

For setup issues or questions:
1. Check the troubleshooting guides in each directory
2. Review the test files for usage examples
3. Check the API documentation for endpoint details
4. Ensure all prerequisites are installed correctly

---

**Current Status**: Phase 0-1 Complete ✅  
**Next Phase**: LLM Auto-Routing & HSA Filtering  
**Last Updated**: December 2024

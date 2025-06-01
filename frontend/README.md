# AI-First Internal Helpdesk Portal - Frontend

A modern, minimalist React frontend for the AI-First Internal Helpdesk Portal built with Vite.

## Features

- **Authentication**: JWT-based login with role-based access control
- **Dashboard**: Role-specific dashboards for users, agents, and admins
- **Ticket Management**: Create, view, edit, and manage support tickets
- **Responsive Design**: Clean, minimalist UI that works on all devices
- **Real-time Updates**: Automatic token refresh and error handling

## Tech Stack

- **React 19** - Frontend framework
- **React Router 6** - Client-side routing
- **Axios** - HTTP client for API calls
- **Vite** - Build tool and development server

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/          # Reusable React components
│   ├── Layout.jsx      # Main layout wrapper
│   └── ProtectedRoute.jsx # Route protection
├── context/            # React context providers
│   └── AuthContext.jsx # Authentication state management
├── pages/              # Page components
│   ├── Login.jsx       # Login page
│   ├── Dashboard.jsx   # User dashboard
│   ├── TicketList.jsx  # Ticket listing
│   ├── CreateTicket.jsx # Ticket creation form
│   └── TicketDetail.jsx # Ticket detail view
├── services/           # API service layer
│   └── api.js          # API client and endpoints
├── App.jsx             # Main app component
└── main.jsx            # Entry point
```

## API Integration

The frontend connects to the backend API at `http://localhost:8000`. Key features:

- **Automatic token management**: JWT tokens are automatically included in requests
- **Error handling**: 401 errors automatically redirect to login
- **Request/Response interceptors**: Centralized error handling and token refresh

## User Roles

- **User**: Can create and manage their own tickets
- **IT Agent**: Can view and manage IT department tickets
- **HR Agent**: Can view and manage HR department tickets
- **Admin**: Can view and manage all tickets across departments

## Development

The application uses modern React patterns:

- **Functional components** with hooks
- **Context API** for state management
- **Protected routes** for authentication
- **Responsive design** with inline styles
- **Error boundaries** for graceful error handling

## Environment Configuration

The frontend automatically connects to:
- Backend API: `http://localhost:8000`
- Development server: `http://localhost:5174` (or next available port)

## Demo Credentials

For testing purposes, you can use:
- Username: `admin`
- Password: `admin123`

## Contributing

1. Follow React best practices
2. Use functional components with hooks
3. Maintain the minimalist design approach
4. Test all user flows before committing
5. Update documentation for new features

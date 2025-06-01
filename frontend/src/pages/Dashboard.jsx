import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { dashboardAPI, ticketAPI, TICKET_STATUS, TICKET_URGENCY } from '../services/api';
import { Link } from 'react-router-dom';
import AIChatModal from '../components/AIChatModal';
import NotificationBell from '../components/NotificationBell';
import Ripple from '../components/Ripple';

const Dashboard = () => {
  const { user, isUser, isAgent, isAdmin } = useAuth();
  const [dashboardData, setDashboardData] = useState(null);
  const [recentTickets, setRecentTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isAIChatOpen, setIsAIChatOpen] = useState(false);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);

        // Fetch dashboard data based on role
        let dashboardResponse;
        if (isUser) {
          dashboardResponse = await dashboardAPI.getUserHome();
        } else if (isAgent) {
          dashboardResponse = await dashboardAPI.getAgentHome();
        } else if (isAdmin) {
          dashboardResponse = await dashboardAPI.getAdminHome();
        }

        setDashboardData(dashboardResponse);

        // Fetch recent tickets
        const ticketsResponse = await ticketAPI.getTickets({ limit: 5 });
        setRecentTickets(ticketsResponse.tickets || []);

      } catch (error) {
        console.error('Dashboard fetch error:', error);
        setError('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [isUser, isAgent, isAdmin]);

  const getStatusColor = (status) => {
    const colors = {
      [TICKET_STATUS.OPEN]: '#e74c3c',
      [TICKET_STATUS.ASSIGNED]: '#f39c12',
      [TICKET_STATUS.RESOLVED]: '#27ae60',
      [TICKET_STATUS.CLOSED]: '#95a5a6'
    };
    return colors[status] || '#95a5a6';
  };

  const getUrgencyColor = (urgency) => {
    const colors = {
      [TICKET_URGENCY.LOW]: '#27ae60',
      [TICKET_URGENCY.MEDIUM]: '#f39c12',
      [TICKET_URGENCY.HIGH]: '#e74c3c'
    };
    return colors[urgency] || '#95a5a6';
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <Ripple color="#3869d4" size="medium" text="Loading dashboard..." textColor="#74787e" />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        backgroundColor: '#fee',
        color: '#c33',
        padding: '1rem',
        borderRadius: '4px',
        border: '1px solid #fcc'
      }}>
        {error}
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Header Section */}
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="dashboard-title">Welcome back, {user?.username}!</h1>
          <p className="dashboard-subtitle">
            {isUser ? 'Welcome to the User Home Page' :
             isAgent ? 'Welcome to the Agent Dashboard' :
             'Welcome to the Admin Dashboard'}
          </p>
        </div>
        <div className="header-actions">
          <NotificationBell />
          {isUser && (
            <button
              onClick={() => setIsAIChatOpen(true)}
              className="ai-resolve-btn"
            >
              <span className="material-icons">auto_awesome</span>
              Resolve with AI
            </button>
          )}
        </div>
      </header>

      {/* Quick Actions */}
      <section className="quick-actions">
        <Link to="/tickets/new" className="action-card action-card-primary">
          <span className="material-icons action-icon">note_add</span>
          <h3 className="action-title">Create New Ticket</h3>
          <p className="action-description">Submit a new support request</p>
        </Link>

        <Link to="/tickets" className="action-card action-card-secondary">
          <span className="material-icons action-icon">receipt_long</span>
          <h3 className="action-title">View All Tickets</h3>
          <p className="action-description">Manage your support tickets</p>
        </Link>
      </section>

      {/* Recent Tickets */}
      <section className="recent-tickets">
        <h3 className="section-title">Recent Tickets</h3>

        {recentTickets.length === 0 ? (
          <div className="empty-state">
            <p>No tickets found. <Link to="/tickets/new">Create your first ticket</Link></p>
          </div>
        ) : (
          <div className="tickets-list">
            {recentTickets.map((ticket) => (
              <Link
                key={ticket.id}
                to={`/tickets/${ticket.ticket_id}`}
                className="ticket-item"
              >
                <div className="ticket-header">
                  <h4 className="ticket-title">{ticket.title}</h4>
                  <div className="ticket-badges">
                    <span className={`status-badge status-${ticket.status.toLowerCase()}`}>
                      {ticket.status.toUpperCase()}
                    </span>
                    <span className={`urgency-badge urgency-${ticket.urgency.toLowerCase()}`}>
                      {ticket.urgency.toUpperCase()}
                    </span>
                  </div>
                </div>
                <p className="ticket-description">
                  {ticket.description.length > 100
                    ? `${ticket.description.substring(0, 100)}...`
                    : ticket.description
                  }
                </p>
                <div className="ticket-meta">
                  Created: {new Date(ticket.created_at).toLocaleDateString()}
                  {ticket.department && ` • Department: ${ticket.department}`}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* AI Chat Modal */}
      <AIChatModal
        isOpen={isAIChatOpen}
        onClose={() => setIsAIChatOpen(false)}
      />
    </div>
  );
};

export default Dashboard;

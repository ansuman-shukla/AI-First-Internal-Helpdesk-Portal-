import React, { useState, useEffect, useCallback } from 'react';
import { ticketAPI, TICKET_STATUS, TICKET_DEPARTMENT } from '../services/api';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Ripple from '../components/Ripple';

const TicketList = () => {
  const { user, isUser, isAgent, isAdmin } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    status: '',
    department: '',
    search: '',
    page: 1,
    limit: 10
  });
  const [totalCount, setTotalCount] = useState(0);
  const [deleteLoading, setDeleteLoading] = useState(null);

  useEffect(() => {
    fetchTickets();
  }, [filters]);

  // Debounced search effect
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchQuery !== filters.search) {
        handleFilterChange('search', searchQuery);
      }
    }, 500); // 500ms debounce

    return () => clearTimeout(timeoutId);
  }, [searchQuery, filters.search]);

  const fetchTickets = async () => {
    try {
      setLoading(true);
      const response = await ticketAPI.getTickets(filters);
      setTickets(response.tickets || []);
      setTotalCount(response.total_count || 0);
    } catch (error) {
      console.error('Error fetching tickets:', error);
      setError('Failed to load tickets');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      page: 1 // Reset to first page when filters change
    }));
  };

  const handlePageChange = (newPage) => {
    setFilters(prev => ({
      ...prev,
      page: newPage
    }));
  };

  const handleDeleteTicket = async (ticketId, ticketTitle) => {
    if (!window.confirm(`Are you sure you want to delete the ticket "${ticketTitle}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeleteLoading(ticketId);
      await ticketAPI.deleteTicket(ticketId);

      // Refresh the ticket list
      await fetchTickets();

      // Show success message (you could use a toast notification here)
      alert('Ticket deleted successfully');
    } catch (error) {
      console.error('Error deleting ticket:', error);
      if (error.response?.status === 403) {
        alert('You do not have permission to delete this ticket');
      } else if (error.response?.status === 404) {
        alert('Ticket not found');
      } else {
        alert('Failed to delete ticket. Please try again.');
      }
    } finally {
      setDeleteLoading(null);
    }
  };

  const getStatusBadgeClass = (status) => {
    const statusMap = {
      open: 'status-open',
      assigned: 'status-assigned',
      resolved: 'status-resolved',
      closed: 'status-closed'
    };
    return `ticket-status-badge ${statusMap[status] || 'status-open'}`;
  };

  const getUrgencyBadgeClass = (urgency) => {
    const urgencyMap = {
      low: 'urgency-low',
      medium: 'urgency-medium',
      high: 'urgency-high'
    };
    return `ticket-urgency-badge ${urgencyMap[urgency] || 'urgency-low'}`;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 1) return '1 day ago';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.ceil(diffDays / 7)} weeks ago`;
    return date.toLocaleDateString();
  };

  const totalPages = Math.ceil(totalCount / filters.limit);

  if (loading && filters.page === 1) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <Ripple color="#3869d4" size="medium" text="Loading tickets..." textColor="#74787e" />
      </div>
    );
  }

  // Get page title based on user role
  const getPageTitle = () => {
    if (isAdmin) return 'All tickets';
    if (isAgent) return 'Department tickets';
    return 'My tickets';
  };

  return (
    <div className="ticket-list-page">
      {/* Page Header */}
      <header className="ticket-list-page-header">
        <h2 className="ticket-list-page-title">{getPageTitle()}</h2>
        <p className="ticket-list-page-subtitle">
          {isAdmin && 'View and manage all tickets across departments'}
          {isAgent && 'View tickets assigned to your department'}
          {isUser && 'View and manage your support requests'}
        </p>
      </header>

      {/* Ticket List Container */}
      <div className="modern-ticket-container">
        {/* Header with search and actions */}
        <div className="modern-ticket-header">
          <div className="search-container">
            <span className="material-icons search-icon">search</span>
            <input
              type="text"
              placeholder="Search in all tickets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>
          <div className="header-actions">
            <button
              className={`filter-btn ${showFilters ? 'active' : ''}`}
              onClick={() => setShowFilters(!showFilters)}
            >
              <span className="material-icons">filter_list</span>
              {showFilters ? 'Hide filters' : 'Add filter'}
            </button>
            <Link to="/tickets/new" className="new-ticket-btn-modern">
              <span className="material-icons">add</span>
              New Ticket
            </Link>
          </div>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="filter-panel">
            <div className="filter-row">
              <div className="filter-group">
                <label htmlFor="status-filter" className="filter-label">Status</label>
                <select
                  id="status-filter"
                  value={filters.status}
                  onChange={(e) => handleFilterChange('status', e.target.value)}
                  className="filter-select"
                >
                  <option value="">All Statuses</option>
                  {Object.values(TICKET_STATUS).map(status => (
                    <option key={status} value={status}>
                      {status.charAt(0).toUpperCase() + status.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              {(isAgent || isAdmin) && (
                <div className="filter-group">
                  <label htmlFor="department-filter" className="filter-label">Department</label>
                  <select
                    id="department-filter"
                    value={filters.department}
                    onChange={(e) => handleFilterChange('department', e.target.value)}
                    className="filter-select"
                  >
                    <option value="">All Departments</option>
                    {Object.values(TICKET_DEPARTMENT).map(dept => (
                      <option key={dept} value={dept}>
                        {dept.toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="filter-actions">
                <button
                  onClick={() => {
                    setFilters({
                      status: '',
                      department: '',
                      search: '',
                      page: 1,
                      limit: 10
                    });
                    setSearchQuery('');
                  }}
                  className="clear-filters-btn"
                >
                  Clear All
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div style={{
            backgroundColor: '#fee',
            color: '#c33',
            padding: '1rem',
            borderRadius: '4px',
            margin: 'var(--spacing-md)',
            border: '1px solid #fcc'
          }}>
            {error}
          </div>
        )}

        {/* Modern Ticket Table */}
        <div className="table-container">
          {tickets.length === 0 ? (
            <div className="empty-state">
              <span className="material-icons empty-icon">confirmation_number</span>
              <h3>No tickets found</h3>
              <p>
                {filters.status || filters.department
                  ? 'Try adjusting your filters or '
                  : ''
                }
                <Link to="/tickets/new">create your first ticket</Link>
              </p>
            </div>
          ) : (
            <table className="modern-ticket-table">
              <thead>
                <tr>
                  <th>TITLE</th>
                  {(isAgent || isAdmin) && <th>USER</th>}
                  <th>STATUS</th>
                  <th>PRIORITY</th>
                  <th>UPDATED</th>
                  <th>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((ticket) => (
                  <tr key={ticket.id}>
                    <td>
                      <div className="ticket-title-modern">
                        <Link
                          to={`/tickets/${ticket.ticket_id}`}
                          className="ticket-title-link"
                        >
                          {ticket.title}
                        </Link>
                        <div className="ticket-meta-modern">
                          #{ticket.ticket_id} • {ticket.department || 'General'}
                        </div>
                      </div>
                    </td>
                    {(isAgent || isAdmin) && (
                      <td>
                        <div className="user-info-cell">
                          <div className="user-name">
                            {ticket.user_info?.username || 'Unknown User'}
                          </div>
                          <div className="user-email">
                            {ticket.user_info?.email || 'No email'}
                          </div>
                        </div>
                      </td>
                    )}
                    <td>
                      <span className={`modern-badge status-${ticket.status.toLowerCase()}`}>
                        {ticket.status.charAt(0).toUpperCase() + ticket.status.slice(1)}
                      </span>
                    </td>
                    <td>
                      <span className={`modern-badge priority-${ticket.urgency.toLowerCase()}`}>
                        {ticket.urgency.charAt(0).toUpperCase() + ticket.urgency.slice(1)}
                      </span>
                    </td>
                    <td className="updated-cell">
                      {formatDate(ticket.updated_at)}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Link
                          to={`/tickets/${ticket.ticket_id}`}
                          className="view-link"
                        >
                          View →
                        </Link>
                        {isAdmin && (
                          <button
                            onClick={() => handleDeleteTicket(ticket.ticket_id, ticket.title)}
                            disabled={deleteLoading === ticket.ticket_id}
                            className="delete-ticket-btn"
                            title="Delete ticket"
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: deleteLoading === ticket.ticket_id ? 'not-allowed' : 'pointer',
                              padding: '4px',
                              borderRadius: '4px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              opacity: deleteLoading === ticket.ticket_id ? 0.5 : 1,
                              transition: 'all 0.2s ease'
                            }}
                            onMouseEnter={(e) => {
                              if (deleteLoading !== ticket.ticket_id) {
                                e.target.style.backgroundColor = '#fee';
                              }
                            }}
                            onMouseLeave={(e) => {
                              e.target.style.backgroundColor = 'transparent';
                            }}
                          >
                            {deleteLoading === ticket.ticket_id ? (
                              <Ripple color="#dc3545" size="small" />
                            ) : (
                              <span
                                className="material-icons"
                                style={{
                                  fontSize: '18px',
                                  color: '#dc3545',
                                  lineHeight: 1
                                }}
                              >
                                delete
                              </span>
                            )}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Modern Pagination */}
      <div className="modern-pagination">
        <span className="pagination-info">Rows per page: {filters.limit}</span>
        <span className="pagination-info">
          {Math.min((filters.page - 1) * filters.limit + 1, totalCount)}-{Math.min(filters.page * filters.limit, totalCount)} of {totalCount}
        </span>
        <div className="pagination-controls">
          <button
            onClick={() => handlePageChange(filters.page - 1)}
            disabled={filters.page === 1}
            className="pagination-btn"
          >
            <span className="material-icons">chevron_left</span>
          </button>
          <button
            onClick={() => handlePageChange(filters.page + 1)}
            disabled={filters.page === totalPages}
            className="pagination-btn"
          >
            <span className="material-icons">chevron_right</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default TicketList;

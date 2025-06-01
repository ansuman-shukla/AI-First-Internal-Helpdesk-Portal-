import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ticketAPI, TICKET_STATUS, TICKET_URGENCY, TICKET_DEPARTMENT } from '../services/api';
import { useAuth } from '../context/AuthContext';
import TicketChat from '../components/TicketChat';
import Ripple from '../components/Ripple';

const TicketDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isUser, isAgent, isAdmin } = useAuth();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({});
  const [updateLoading, setUpdateLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  useEffect(() => {
    fetchTicket();
  }, [id]);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const fetchTicket = async () => {
    try {
      setLoading(true);
      const ticketData = await ticketAPI.getTicketById(id);
      setTicket(ticketData);
      setEditData({
        title: ticketData.title,
        description: ticketData.description,
        urgency: ticketData.urgency,
        status: ticketData.status,
        department: ticketData.department || '',
        feedback: ticketData.feedback || ''
      });
    } catch (error) {
      console.error('Error fetching ticket:', error);
      if (error.response?.status === 404) {
        const errorMessage = error.response?.data?.detail || 'Ticket not found';
        setError(errorMessage);
        // Redirect to tickets list after 3 seconds
        setTimeout(() => {
          navigate('/tickets');
        }, 3000);
      } else if (error.response?.status === 403) {
        const errorMessage = error.response?.data?.detail || 'You do not have permission to view this ticket';
        setError(errorMessage);
        // Redirect to tickets list after 3 seconds
        setTimeout(() => {
          navigate('/tickets');
        }, 3000);
      } else {
        setError('Failed to load ticket');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    // Ensure editData is synchronized with current ticket state
    setEditData({
      title: ticket.title,
      description: ticket.description,
      urgency: ticket.urgency,
      status: ticket.status,
      department: ticket.department || '',
      feedback: ticket.feedback || ''
    });
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditData({
      title: ticket.title,
      description: ticket.description,
      urgency: ticket.urgency,
      status: ticket.status,
      department: ticket.department || '',
      feedback: ticket.feedback || ''
    });
  };

  const handleSaveEdit = async () => {
    try {
      setUpdateLoading(true);

      // Prepare update data - only include fields that can be updated
      const updateData = {};

      // Users can only edit title, description, urgency if status is open
      if (isUser && ticket.status === TICKET_STATUS.OPEN) {
        updateData.title = editData.title;
        updateData.description = editData.description;
        updateData.urgency = editData.urgency;
      }

      // Agents and admins can update status, department, feedback
      if (isAgent || isAdmin) {
        if (editData.status !== ticket.status) updateData.status = editData.status;
        if (editData.department !== ticket.department) updateData.department = editData.department;
        if (editData.feedback !== ticket.feedback) updateData.feedback = editData.feedback;

        // Agents/admins can also edit title/description
        if (editData.title !== ticket.title) updateData.title = editData.title;
        if (editData.description !== ticket.description) updateData.description = editData.description;
        if (editData.urgency !== ticket.urgency) updateData.urgency = editData.urgency;
      }

      console.log('Sending update data:', updateData);
      const updatedTicket = await ticketAPI.updateTicket(id, updateData);
      console.log('Received updated ticket:', updatedTicket);
      setTicket(updatedTicket);

      // Update editData to reflect the saved changes
      setEditData({
        title: updatedTicket.title,
        description: updatedTicket.description,
        urgency: updatedTicket.urgency,
        status: updatedTicket.status,
        department: updatedTicket.department || '',
        feedback: updatedTicket.feedback || ''
      });

      setIsEditing(false);
    } catch (error) {
      console.error('Error updating ticket:', error);
      let errorMessage = 'Failed to update ticket';

      if (error.response?.status === 404) {
        errorMessage = error.response?.data?.detail || 'Ticket not found';
      } else if (error.response?.status === 403) {
        errorMessage = error.response?.data?.detail || 'You do not have permission to edit this ticket';
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }

      alert(errorMessage);
    } finally {
      setUpdateLoading(false);
    }
  };

  const handleEditChange = (e) => {
    const { name, value } = e.target;
    setEditData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleDeleteTicket = async () => {
    if (!window.confirm(`Are you sure you want to delete the ticket "${ticket.title}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeleteLoading(true);
      await ticketAPI.deleteTicket(id);

      // Navigate back to tickets list
      navigate('/tickets');
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
      setDeleteLoading(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      open: '#e74c3c',
      assigned: '#f39c12',
      resolved: '#27ae60',
      closed: '#95a5a6'
    };
    return colors[status] || '#95a5a6';
  };

  const getUrgencyColor = (urgency) => {
    const colors = {
      low: '#27ae60',
      medium: '#f39c12',
      high: '#e74c3c'
    };
    return colors[urgency] || '#95a5a6';
  };

  // Determine if user can edit ticket based on role and status
  const canEdit = ticket && (
    // Users can edit their own tickets if status is open
    (isUser && ticket.status === TICKET_STATUS.OPEN && ticket.user_id === user?.user_id) ||
    // Agents and admins can edit tickets in their domain
    (isAgent || isAdmin)
  );

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <Ripple color="#3869d4" size="medium" text="Loading ticket..." textColor="#74787e" />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <div style={{
          backgroundColor: '#fee',
          color: '#c33',
          padding: '2rem',
          borderRadius: '8px',
          border: '1px solid #fcc',
          maxWidth: '500px',
          margin: '0 auto'
        }}>
          <h2 style={{ margin: '0 0 1rem 0' }}>Error</h2>
          <p style={{ margin: '0 0 1rem 0' }}>{error}</p>
          {(error.includes('not found') || error.includes('permission')) && (
            <p style={{ margin: '0 0 1rem 0', fontSize: '0.875rem', color: '#666' }}>
              Redirecting to tickets list in 3 seconds...
            </p>
          )}
          <Link
            to="/tickets"
            style={{
              color: '#3498db',
              textDecoration: 'none',
              fontWeight: 'bold'
            }}
          >
            ← Back to Tickets
          </Link>
        </div>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <div>Ticket not found</div>
      </div>
    );
  }

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#f3f4f6',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <header style={{
        backgroundColor: 'white',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: '1rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            <Link
              to="/tickets"
              style={{
                display: 'flex',
                alignItems: 'center',
                fontSize: '0.875rem',
                color: '#3b82f6',
                textDecoration: 'none',
                fontWeight: '500',
                marginBottom: '0.25rem'
              }}
            >
              <span className="material-icons" style={{ fontSize: '1.125rem', marginRight: '0.25rem' }}>
                arrow_back_ios
              </span>
              Back to Tickets
            </Link>
            <h1 style={{
              fontSize: '1.5rem',
              fontWeight: '600',
              color: '#1f2937',
              margin: '0.25rem 0'
            }}>
              {isEditing ? (
                <input
                  type="text"
                  name="title"
                  value={editData.title}
                  onChange={handleEditChange}
                  style={{
                    fontSize: '1.5rem',
                    fontWeight: '600',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    padding: '0.5rem',
                    width: '100%',
                    maxWidth: '600px',
                    backgroundColor: 'white'
                  }}
                />
              ) : (
                ticket.title
              )}
            </h1>
            <p style={{
              fontSize: '0.875rem',
              color: '#6b7280',
              margin: 0
            }}>
              Ticket #{ticket.ticket_id}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {/* Status Badge */}
            <span style={{
              padding: '0.25rem 0.75rem',
              fontSize: '0.75rem',
              fontWeight: '600',
              borderRadius: '9999px',
              textTransform: 'uppercase',
              backgroundColor: getStatusColor(ticket.status),
              color: 'white'
            }}>
              {isEditing ? (
                <select
                  name="status"
                  value={editData.status}
                  onChange={handleEditChange}
                  style={{
                    backgroundColor: 'transparent',
                    color: 'white',
                    border: 'none',
                    fontSize: '0.75rem',
                    fontWeight: '600'
                  }}
                >
                  <option value={TICKET_STATUS.OPEN} style={{ color: 'black' }}>OPEN</option>
                  <option value={TICKET_STATUS.ASSIGNED} style={{ color: 'black' }}>ASSIGNED</option>
                  <option value={TICKET_STATUS.RESOLVED} style={{ color: 'black' }}>RESOLVED</option>
                  <option value={TICKET_STATUS.CLOSED} style={{ color: 'black' }}>CLOSED</option>
                </select>
              ) : (
                ticket.status.toUpperCase()
              )}
            </span>

            {/* Urgency Badge */}
            <span style={{
              padding: '0.25rem 0.75rem',
              fontSize: '0.75rem',
              fontWeight: '600',
              borderRadius: '9999px',
              textTransform: 'uppercase',
              backgroundColor: getUrgencyColor(isEditing ? editData.urgency : ticket.urgency),
              color: 'white'
            }}>
              {isEditing ? (
                <select
                  name="urgency"
                  value={editData.urgency}
                  onChange={handleEditChange}
                  style={{
                    backgroundColor: 'transparent',
                    color: 'white',
                    border: 'none',
                    fontSize: '0.75rem',
                    fontWeight: '600'
                  }}
                >
                  <option value={TICKET_URGENCY.LOW} style={{ color: 'black' }}>LOW</option>
                  <option value={TICKET_URGENCY.MEDIUM} style={{ color: 'black' }}>MEDIUM</option>
                  <option value={TICKET_URGENCY.HIGH} style={{ color: 'black' }}>HIGH</option>
                </select>
              ) : (
                ticket.urgency.toUpperCase()
              )}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content - Side by Side Layout */}
      <div style={{
        flex: 1,
        display: 'flex',
        overflow: 'hidden',
        padding: '1.5rem',
        gap: '1.5rem'
      }}>

        {/* Left Side - Chat Section */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'white',
          borderRadius: '0.5rem',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          overflow: 'hidden'
        }}>
          <TicketChat ticketId={id} ticket={ticket} />
        </div>

        {/* Right Side - Ticket Information */}
        <div style={{
          width: '384px', // w-96 equivalent
          flexShrink: 0,
          backgroundColor: 'white',
          borderRadius: '0.5rem',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}>
          {/* Ticket Details */}
          <div style={{ padding: '1.5rem', flex: 1, overflow: 'auto' }}>
            <h3 style={{
              fontSize: '1.125rem',
              fontWeight: '600',
              color: '#1f2937',
              marginBottom: '0.75rem'
            }}>
              Description
            </h3>
            {isEditing ? (
              <textarea
                name="description"
                value={editData.description}
                onChange={handleEditChange}
                rows={4}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem',
                  fontFamily: 'inherit',
                  resize: 'vertical',
                  boxSizing: 'border-box',
                  backgroundColor: '#f9fafb'
                }}
              />
            ) : (
              <p style={{
                fontSize: '0.875rem',
                color: '#4b5563',
                backgroundColor: '#f9fafb',
                padding: '0.75rem',
                borderRadius: '0.375rem',
                marginBottom: '1.5rem',
                lineHeight: '1.6',
                whiteSpace: 'pre-wrap'
              }}>
                {ticket.description}
              </p>
            )}

            <h3 style={{
              fontSize: '1.125rem',
              fontWeight: '600',
              color: '#1f2937',
              marginBottom: '1rem'
            }}>
              Ticket Information
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem' }}>
              <div>
                <p style={{ color: '#6b7280', fontWeight: '500', margin: 0 }}>Created:</p>
                <p style={{ color: '#1f2937', margin: 0 }}>
                  {new Date(ticket.created_at).toLocaleString()}
                </p>
              </div>
              <div>
                <p style={{ color: '#6b7280', fontWeight: '500', margin: 0 }}>Last Updated:</p>
                <p style={{ color: '#1f2937', margin: 0 }}>
                  {new Date(ticket.updated_at).toLocaleString()}
                </p>
              </div>
              <div>
                <p style={{ color: '#6b7280', fontWeight: '500', margin: 0 }}>Department:</p>
                <p style={{ color: '#1f2937', margin: 0 }}>
                  {ticket.department || 'Not assigned'}
                </p>
              </div>
            </div>

            {/* Edit Actions */}
            {canEdit && isEditing && (
              <div style={{
                display: 'flex',
                gap: '0.5rem',
                justifyContent: 'flex-end',
                marginTop: '1rem',
                paddingTop: '1rem',
                borderTop: '1px solid #e5e7eb'
              }}>
                <button
                  onClick={handleCancelEdit}
                  style={{
                    padding: '0.5rem 1rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    backgroundColor: 'white',
                    color: '#6b7280',
                    cursor: 'pointer',
                    fontSize: '0.875rem'
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={updateLoading}
                  style={{
                    padding: '0.5rem 1rem',
                    border: 'none',
                    borderRadius: '0.375rem',
                    backgroundColor: updateLoading ? '#9ca3af' : '#10b981',
                    color: 'white',
                    cursor: updateLoading ? 'not-allowed' : 'pointer',
                    fontWeight: '500',
                    fontSize: '0.875rem'
                  }}
                >
                  {updateLoading ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            )}

            {/* Action Buttons */}
            {(canEdit || isAdmin) && !isEditing && (
              <div style={{
                marginTop: '1rem',
                paddingTop: '1rem',
                borderTop: '1px solid #e5e7eb',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem'
              }}>
                {canEdit && (
                  <button
                    onClick={handleEdit}
                    style={{
                      padding: '0.5rem 1rem',
                      border: 'none',
                      borderRadius: '0.375rem',
                      backgroundColor: '#3b82f6',
                      color: 'white',
                      cursor: 'pointer',
                      fontWeight: '500',
                      fontSize: '0.875rem',
                      width: '100%'
                    }}
                  >
                    Edit Ticket
                  </button>
                )}

                {isAdmin && (
                  <button
                    onClick={handleDeleteTicket}
                    disabled={deleteLoading}
                    style={{
                      padding: '0.5rem 1rem',
                      border: 'none',
                      borderRadius: '0.375rem',
                      backgroundColor: deleteLoading ? '#9ca3af' : '#dc3545',
                      color: 'white',
                      cursor: deleteLoading ? 'not-allowed' : 'pointer',
                      fontWeight: '500',
                      fontSize: '0.875rem',
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    {deleteLoading ? (
                      <>
                        <Ripple color="#ffffff" size="small" />
                        Deleting...
                      </>
                    ) : (
                      <>
                        <span className="material-icons" style={{ fontSize: '1rem' }}>
                          delete
                        </span>
                        Delete Ticket
                      </>
                    )}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TicketDetail;

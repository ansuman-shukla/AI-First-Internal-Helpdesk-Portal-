import React, { useState } from 'react';
import { ticketAPI, TICKET_URGENCY, TICKET_DEPARTMENT } from '../services/api';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const CreateTicket = () => {
  const navigate = useNavigate();
  const { user, isAdmin, isAgent } = useAuth();
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    urgency: TICKET_URGENCY.MEDIUM,
    department: '' // Optional department field for agents/admins
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [contentFlaggedAlert, setContentFlaggedAlert] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear errors when user starts typing
    if (error) setError(null);
    if (contentFlaggedAlert) setContentFlaggedAlert(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Basic validation
    if (!formData.title.trim()) {
      setError('Title is required');
      return;
    }
    if (!formData.description.trim()) {
      setError('Description is required');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      // Prepare ticket data - only include department if it's set
      const ticketData = {
        title: formData.title.trim(),
        description: formData.description.trim(),
        urgency: formData.urgency
      };

      // Only include department if it's selected (for agents/admins)
      if (formData.department) {
        ticketData.department = formData.department;
      }

      const ticket = await ticketAPI.createTicket(ticketData);
      console.log('Ticket created:', ticket);
      navigate(`/tickets/${ticket.ticket_id}`);
    } catch (error) {
      console.error('Error creating ticket:', error);

      // Handle content flagged errors (422 status)
      if (error.response?.status === 422 && error.response?.data?.detail?.error_type === 'content_flagged') {
        const flaggedData = error.response.data.detail;

        // Set content flagged alert with detailed information
        setContentFlaggedAlert({
          contentType: flaggedData.content_type,
          message: flaggedData.message,
          originalTitle: flaggedData.title,
          originalDescription: flaggedData.description
        });

        // Keep the form data as is so user can edit
        // Don't navigate away - stay on the form
        setError(null); // Clear any previous errors
        return; // Don't set generic error message
      }

      // Handle other errors
      let errorMessage = 'Failed to create ticket';

      if (error.response?.status === 429) {
        errorMessage = 'Rate limit exceeded. You can only create 5 tickets per 24 hours.';
      } else if (error.response?.data?.detail) {
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        } else {
          errorMessage = 'Failed to create ticket. Please try again.';
        }
      }

      setError(errorMessage);
      setContentFlaggedAlert(null); // Clear content flagged alert if showing other error
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="create-ticket-page">
      <div className="create-ticket-header">
        <h2 className="create-ticket-title">Create New Ticket</h2>
        <p className="create-ticket-subtitle">Submit a new support request to our helpdesk team</p>
      </div>

      <div className="create-ticket-form-container">
        {error && (
          <div className="error-alert">
            {error}
          </div>
        )}

        {contentFlaggedAlert && (
          <div className={`content-flagged-alert ${contentFlaggedAlert.contentType}`}>
            <div className="alert-content">
              <span className="alert-icon">
                {contentFlaggedAlert.contentType === 'profanity' ? '⚠️' :
                 contentFlaggedAlert.contentType === 'spam' ? '🚫' : '❌'}
              </span>
              <div className="alert-text">
                <div className="alert-title">
                  {contentFlaggedAlert.contentType === 'profanity' ? 'Inappropriate Language Detected' :
                   contentFlaggedAlert.contentType === 'spam' ? 'Spam Content Detected' : 'Inappropriate Content Detected'}
                </div>
                <div className="alert-message">
                  {contentFlaggedAlert.message}
                </div>
                <div className="alert-instruction">
                  Please edit your content above and try again.
                </div>
              </div>
              <button
                onClick={() => setContentFlaggedAlert(null)}
                className="alert-dismiss"
                title="Dismiss"
              >
                ×
              </button>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="create-ticket-form">
          <div className="form-group">
            <label htmlFor="title" className="form-label">
              Title <span className="required">*</span>
            </label>
            <input
              type="text"
              id="title"
              name="title"
              value={formData.title}
              onChange={handleChange}
              required
              maxLength={200}
              className={`form-input ${contentFlaggedAlert ? 'flagged' : ''}`}
              placeholder="Brief description of your issue"
            />
            <p className="form-help">
              {formData.title.length}/200 characters
            </p>
          </div>

          <div className="form-group">
            <label htmlFor="description" className="form-label">
              Description <span className="required">*</span>
            </label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              required
              maxLength={2000}
              rows={6}
              className={`form-textarea ${contentFlaggedAlert ? 'flagged' : ''}`}
              placeholder="Please provide detailed information about your issue, including any error messages, steps to reproduce, and what you expected to happen."
            />
            <p className="form-help">
              {formData.description.length}/2000 characters
            </p>
          </div>

          <div className="form-group">
            <label htmlFor="urgency" className="form-label">
              Urgency Level
            </label>
            <div className="select-container">
              <select
                id="urgency"
                name="urgency"
                value={formData.urgency}
                onChange={handleChange}
                className="form-select"
              >
                <option value={TICKET_URGENCY.MEDIUM}>Medium - Standard support request</option>
                <option value={TICKET_URGENCY.LOW}>Low - Non-critical issue</option>
                <option value={TICKET_URGENCY.HIGH}>High - Urgent attention needed</option>
              </select>
              <span className="material-icons select-arrow">expand_more</span>
            </div>
            <p className="form-help">
              Select the appropriate urgency level for your request
            </p>
          </div>

          {/* Department field - show for all users */}
          <div className="form-group">
            <label htmlFor="department" className="form-label">
              Department (Optional)
            </label>
            <div className="select-container">
              <select
                id="department"
                name="department"
                value={formData.department}
                onChange={handleChange}
                className="form-select"
              >
                <option value="">Auto-assign department</option>
                {/* Show department options for agents/admins, auto-assign only for users */}
                {(isAgent || isAdmin) && (
                  <>
                    <option value={TICKET_DEPARTMENT.IT}>IT Department</option>
                    <option value={TICKET_DEPARTMENT.HR}>HR Department</option>
                  </>
                )}
              </select>
              <span className="material-icons select-arrow">expand_more</span>
            </div>
            <p className="form-help">
              {(isAgent || isAdmin)
                ? "Leave empty for automatic department assignment based on ticket content"
                : "Department will be automatically assigned based on your ticket content"
              }
            </p>
          </div>

          <div className="form-actions">
            <button
              type="button"
              onClick={() => navigate('/tickets')}
              className="btn-cancel"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-submit"
            >
              {isSubmitting ? 'Creating...' : 'Create Ticket'}
            </button>
          </div>
        </form>
      </div>

      {/* Tips Section */}
    </div>
  );
};

export default CreateTicket;

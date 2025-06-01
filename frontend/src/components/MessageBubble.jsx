import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { MESSAGE_FEEDBACK, MESSAGE_ROLES } from '../services/api';
import { useAuth } from '../context/AuthContext';

const MessageBubble = ({ message, onFeedback }) => {
  const { user } = useAuth();
  const [feedbackLoading, setFeedbackLoading] = useState(false);

  // Determine if this message is from the current user
  const isOwnMessage = message.sender_id === user?.user_id;
  
  // Determine message styling based on sender role and AI status
  const getMessageStyle = () => {
    if (isOwnMessage) {
      return {
        backgroundColor: '#3b82f6',
        color: 'white',
        alignSelf: 'flex-end'
      };
    }

    // AI messages get a distinct color
    if (message.isAI) {
      return {
        backgroundColor: '#eafaf1', // Light green for AI messages
        color: '#1f2937',
        alignSelf: 'flex-start'
      };
    }

    // Agent/Admin messages or other users
    return {
      backgroundColor: '#f3f4f6', // Light gray for agent messages
      color: '#1f2937',
      alignSelf: 'flex-start'
    };
  };

  const messageStyle = getMessageStyle();

  // Format timestamp
  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInHours = (now - date) / (1000 * 60 * 60);
    
    if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else {
      return date.toLocaleDateString([], { 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit', 
        minute: '2-digit' 
      });
    }
  };

  // Get sender display name
  const getSenderName = () => {
    if (isOwnMessage) {
      return 'You';
    }

    // Don't show AI indicator in sender name - it will be shown separately
    switch (message.sender_role) {
      case MESSAGE_ROLES.IT_AGENT:
        return '👨‍💻 IT Agent';
      case MESSAGE_ROLES.HR_AGENT:
        return '👩‍💼 HR Agent';
      case MESSAGE_ROLES.ADMIN:
        return '👑 Admin';
      default:
        return `User ${message.sender_id.slice(-4)}`;
    }
  };

  // Handle feedback click
  const handleFeedback = async (feedbackType) => {
    if (!onFeedback || feedbackLoading) return;
    
    try {
      setFeedbackLoading(true);
      await onFeedback(message.id, feedbackType);
    } catch (error) {
      console.error('Failed to update feedback:', error);
    } finally {
      setFeedbackLoading(false);
    }
  };

  // Show feedback buttons for AI messages and agent messages (but not own messages)
  const showFeedback = (message.isAI || 
    (message.sender_role === MESSAGE_ROLES.IT_AGENT || 
     message.sender_role === MESSAGE_ROLES.HR_AGENT || 
     message.sender_role === MESSAGE_ROLES.ADMIN)) && 
    !isOwnMessage;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: isOwnMessage ? 'flex-end' : 'flex-start',
      marginBottom: '1rem'
    }}>
      {/* Message bubble container */}
      <div style={{
        maxWidth: '70%',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Message bubble */}
        <div style={{
          padding: '0.75rem',
          borderRadius: '0.5rem',
          backgroundColor: messageStyle.backgroundColor,
          color: messageStyle.color,
          wordWrap: 'break-word',
          whiteSpace: 'pre-wrap',
          lineHeight: '1.4',
          boxShadow: '0 1px 2px rgba(0, 0, 0, 0.1)'
        }}>
        {/* Message content - use markdown for AI messages */}
        <div style={{
          fontSize: '0.875rem',
          margin: '0 0 0.25rem 0',
          color: 'inherit' // Ensure color inheritance from parent
        }}>
          {message.isAI ? (
            <ReactMarkdown
              components={{
                // Custom styling for markdown elements in chat bubbles
                p: ({ children }) => (
                  <p style={{
                    margin: '0 0 0.5rem 0',
                    lineHeight: '1.4',
                    color: 'inherit' // Inherit color from message bubble
                  }}>{children}</p>
                ),
                ul: ({ children }) => (
                  <ul style={{
                    margin: '0.5rem 0',
                    paddingLeft: '1.2rem',
                    color: 'inherit'
                  }}>{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol style={{
                    margin: '0.5rem 0',
                    paddingLeft: '1.2rem',
                    color: 'inherit'
                  }}>{children}</ol>
                ),
                li: ({ children }) => (
                  <li style={{
                    margin: '0.2rem 0',
                    color: 'inherit'
                  }}>{children}</li>
                ),
                strong: ({ children }) => (
                  <strong style={{
                    fontWeight: 'bold',
                    color: 'inherit'
                  }}>{children}</strong>
                ),
                em: ({ children }) => (
                  <em style={{
                    fontStyle: 'italic',
                    color: 'inherit'
                  }}>{children}</em>
                ),
                code: ({ children }) => (
                  <code style={{
                    backgroundColor: isOwnMessage ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.1)',
                    padding: '0.1rem 0.3rem',
                    borderRadius: '3px',
                    fontSize: '0.8rem',
                    fontFamily: 'monospace',
                    color: 'inherit'
                  }}>{children}</code>
                ),
                pre: ({ children }) => (
                  <pre style={{
                    backgroundColor: isOwnMessage ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.1)',
                    padding: '0.5rem',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    fontFamily: 'monospace',
                    overflow: 'auto',
                    margin: '0.5rem 0',
                    color: 'inherit'
                  }}>{children}</pre>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      color: isOwnMessage ? '#87ceeb' : '#3498db',
                      textDecoration: 'underline'
                    }}
                  >
                    {children}
                  </a>
                ),
                h1: ({ children }) => (
                  <h1 style={{
                    fontSize: '1rem',
                    fontWeight: 'bold',
                    margin: '0.5rem 0',
                    color: 'inherit'
                  }}>{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 style={{
                    fontSize: '0.95rem',
                    fontWeight: 'bold',
                    margin: '0.5rem 0',
                    color: 'inherit'
                  }}>{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 style={{
                    fontSize: '0.9rem',
                    fontWeight: 'bold',
                    margin: '0.5rem 0',
                    color: 'inherit'
                  }}>{children}</h3>
                ),
                blockquote: ({ children }) => (
                  <blockquote style={{
                    borderLeft: `3px solid ${isOwnMessage ? 'rgba(255,255,255,0.5)' : '#3498db'}`,
                    paddingLeft: '0.5rem',
                    margin: '0.5rem 0',
                    fontStyle: 'italic',
                    color: 'inherit'
                  }}>{children}</blockquote>
                )
              }}
            >
              {message.content}
            </ReactMarkdown>
          ) : (
            <p style={{
              margin: 0,
              lineHeight: '1.4',
              color: 'inherit' // Ensure color inheritance for non-AI messages
            }}>{message.content}</p>
          )}
        </div>

          {/* Timestamp and sender info */}
          <p style={{
            fontSize: '0.75rem',
            margin: 0,
            opacity: 0.7,
            textAlign: isOwnMessage ? 'right' : 'left',
            color: 'inherit' // Ensure color inheritance for timestamp
          }}>
            {isOwnMessage ? 'You' : getSenderName()} • {formatTimestamp(message.timestamp)}
          </p>

          {/* AI indicator - only show once */}
          {message.isAI && (
            <div style={{
              fontSize: '0.75rem',
              fontWeight: '500',
              marginTop: '0.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
              opacity: 0.8,
              textAlign: isOwnMessage ? 'right' : 'left',
              color: 'inherit' // Ensure color inheritance for AI indicator
            }}>
              🤖 AI Generated
            </div>
          )}
        </div>

        {/* Feedback buttons - positioned under the chat bubble */}
        {showFeedback && (
          <div style={{
            display: 'flex',
            gap: '0.25rem',
            marginTop: '0.5rem',
            justifyContent: isOwnMessage ? 'flex-end' : 'flex-start'
          }}>
            <button
              onClick={() => handleFeedback(MESSAGE_FEEDBACK.UP)}
              disabled={feedbackLoading}
              style={{
                background: message.feedback === MESSAGE_FEEDBACK.UP ? '#10b981' : 'transparent',
                color: message.feedback === MESSAGE_FEEDBACK.UP ? 'white' : '#6b7280',
                border: '1px solid #e5e7eb',
                borderRadius: '0.375rem',
                padding: '0.375rem',
                fontSize: '0.875rem',
                cursor: feedbackLoading ? 'not-allowed' : 'pointer',
                opacity: feedbackLoading ? 0.6 : 1,
                transition: 'all 0.2s ease',
                minWidth: '2rem',
                height: '2rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title="Helpful"
            >
              👍
            </button>

            <button
              onClick={() => handleFeedback(MESSAGE_FEEDBACK.DOWN)}
              disabled={feedbackLoading}
              style={{
                background: message.feedback === MESSAGE_FEEDBACK.DOWN ? '#ef4444' : 'transparent',
                color: message.feedback === MESSAGE_FEEDBACK.DOWN ? 'white' : '#6b7280',
                border: '1px solid #e5e7eb',
                borderRadius: '0.375rem',
                padding: '0.375rem',
                fontSize: '0.875rem',
                cursor: feedbackLoading ? 'not-allowed' : 'pointer',
                opacity: feedbackLoading ? 0.6 : 1,
                transition: 'all 0.2s ease',
                minWidth: '2rem',
                height: '2rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title="Not helpful"
            >
              👎
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;

import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { messageAPI, MESSAGE_FEEDBACK, aiAgentAPI } from '../services/api';
import MessageBubble from './MessageBubble';
import { useAuth } from '../context/AuthContext';
import Ripple from './Ripple';

const TicketChat = ({ ticketId, ticket }) => {
  const { user, isAgent } = useAuth();
  const [messageInput, setMessageInput] = useState('');

  // Debug logging for agent status
  console.log('TicketChat Debug - User:', user);
  console.log('TicketChat Debug - isAgent:', isAgent);
  console.log('TicketChat Debug - User role:', user?.role);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [hasMoreMessages, setHasMoreMessages] = useState(true);

  // AI suggestion states
  const [isLoadingSuggestion, setIsLoadingSuggestion] = useState(false);
  const [suggestionError, setSuggestionError] = useState(null);
  const [showSuggestion, setShowSuggestion] = useState(false);
  const [currentSuggestion, setCurrentSuggestion] = useState('');
  
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const inputRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  const {
    isConnected,
    connectionStatus,
    error: wsError,
    messages: wsMessages,
    typingUsers,
    sendMessage,
    sendTyping,
    addMessage,
    clearMessages
  } = useWebSocket(ticketId);

  const [allMessages, setAllMessages] = useState([]);

  // Load message history
  useEffect(() => {
    const loadMessageHistory = async () => {
      try {
        setLoadingHistory(true);
        setError(null);

        console.log('Loading message history for ticket:', ticketId);
        const response = await messageAPI.getTicketMessages(ticketId, 1, 50);
        console.log('Message history response:', response);

        if (response.messages) {
          setAllMessages(response.messages);
          setHasMoreMessages(response.pagination?.has_more || false);
          console.log('Loaded', response.messages.length, 'messages');
        }
      } catch (error) {
        console.error('Failed to load message history:', error);
        setError(`Failed to load message history: ${error.message}`);
      } finally {
        setLoadingHistory(false);
      }
    };

    if (ticketId) {
      loadMessageHistory();
    }
  }, [ticketId]);

  // Merge WebSocket messages with loaded messages
  useEffect(() => {
    if (wsMessages.length > 0) {
      setAllMessages(prev => {
        const newMessages = [...prev];
        
        wsMessages.forEach(wsMessage => {
          // Check if message already exists
          const exists = newMessages.some(msg => msg.id === wsMessage.id);
          if (!exists) {
            newMessages.push(wsMessage);
          }
        });
        
        // Sort by timestamp
        return newMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
      });
    }
  }, [wsMessages]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [allMessages]);

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Handle message input change with typing indicator
  const handleInputChange = (e) => {
    setMessageInput(e.target.value);
    
    // Send typing indicator
    if (isConnected && e.target.value.trim()) {
      sendTyping();
      
      // Clear existing timeout
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      
      // Set timeout to stop sending typing indicators
      typingTimeoutRef.current = setTimeout(() => {
        // Typing indicator will expire on the server side
      }, 1000);
    }
  };

  // Handle sending message
  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    const content = messageInput.trim();
    if (!content || isLoading) return;

    try {
      setIsLoading(true);
      setError(null);
      
      // Clear input immediately for better UX
      setMessageInput('');
      
      // Send via WebSocket if connected
      if (isConnected) {
        console.log('Sending message via WebSocket:', content);
        const success = sendMessage(content);
        if (!success) {
          throw new Error('Failed to send message via WebSocket');
        }
      } else {
        // Fallback to HTTP API if WebSocket is not connected
        console.log('WebSocket not connected, using HTTP API fallback');
        const messageData = {
          content,
          message_type: 'user_message',
          isAI: false,
          feedback: MESSAGE_FEEDBACK.NONE
        };

        console.log('Sending message via HTTP:', messageData);
        const response = await messageAPI.sendMessage(ticketId, messageData);
        console.log('HTTP message response:', response);

        // Add to local state for immediate display
        // Backend returns {message: messageObject}, so extract the message
        const sentMessage = response.message || response;
        addMessage(sentMessage);
        console.log('Added message to local state:', sentMessage);
      }
      
    } catch (error) {
      console.error('Failed to send message:', error);
      setError('Failed to send message. Please try again.');
      // Restore message input on error
      setMessageInput(content);
    } finally {
      setIsLoading(false);
      // Focus back to input
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }
  };

  // Handle message feedback
  const handleMessageFeedback = async (messageId, feedback) => {
    try {
      await messageAPI.updateMessageFeedback(ticketId, messageId, feedback);
      
      // Update local message state
      setAllMessages(prev => 
        prev.map(msg => 
          msg.id === messageId 
            ? { ...msg, feedback }
            : msg
        )
      );
    } catch (error) {
      console.error('Failed to update message feedback:', error);
      throw error;
    }
  };

  // Handle AI suggestion request
  const handleAISuggestion = async () => {
    if (!isAgent || isLoadingSuggestion || allMessages.length === 0) return;

    try {
      setIsLoadingSuggestion(true);
      setSuggestionError(null);

      // Prepare conversation context from messages
      const conversationContext = allMessages.map(msg => ({
        id: msg.id,
        ticket_id: msg.ticket_id,
        sender_id: msg.sender_id,
        sender_role: msg.sender_role,
        message_type: msg.message_type,
        content: msg.content,
        isAI: msg.isAI || false,
        feedback: msg.feedback || 'none',
        timestamp: msg.timestamp
      }));

      console.log('Requesting AI suggestion for ticket:', ticketId);
      console.log('Conversation context:', conversationContext);

      const response = await aiAgentAPI.suggestResponse(ticketId, conversationContext);

      console.log('AI suggestion response:', response);
      setCurrentSuggestion(response.suggested_response);
      setShowSuggestion(true);

    } catch (error) {
      console.error('Failed to get AI suggestion:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to get AI suggestion. Please try again.';
      setSuggestionError(errorMessage);
    } finally {
      setIsLoadingSuggestion(false);
    }
  };

  // Handle using AI suggestion
  const handleUseSuggestion = () => {
    setMessageInput(currentSuggestion);
    setShowSuggestion(false);
    setCurrentSuggestion('');
    // Focus the input
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  // Handle sending AI suggestion directly as AI message
  const handleSendAIReply = async () => {
    if (!currentSuggestion.trim()) {
      return;
    }

    try {
      console.log('Sending AI reply directly:', currentSuggestion);
      console.log('WebSocket connection status:', connectionStatus);
      console.log('Is connected:', isConnected);

      // Try WebSocket first, fallback to HTTP if needed
      if (isConnected) {
        console.log('Sending AI reply via WebSocket');
        const success = sendMessage(currentSuggestion, {
          messageType: 'agent_message',
          isAI: true,
          feedback: 'none'
        });

        if (!success) {
          console.log('WebSocket send failed, falling back to HTTP API');
          throw new Error('WebSocket send failed');
        }
      } else {
        console.log('WebSocket not connected, using HTTP API fallback');
        throw new Error('WebSocket not connected');
      }

      // Clear the suggestion
      setShowSuggestion(false);
      setCurrentSuggestion('');

      console.log('AI reply sent successfully');

    } catch (error) {
      console.error('Failed to send AI reply via WebSocket:', error);

      // Try HTTP API fallback
      try {
        console.log('Attempting HTTP API fallback for AI reply');
        const messageData = {
          content: currentSuggestion,
          message_type: 'agent_message',
          isAI: true,
          feedback: MESSAGE_FEEDBACK.NONE
        };

        console.log('Sending AI message via HTTP:', messageData);
        const response = await messageAPI.sendMessage(ticketId, messageData);
        console.log('HTTP AI message response:', response);

        // Add to local state for immediate display
        const sentMessage = response.message || response;
        addMessage(sentMessage);
        console.log('Added AI message to local state:', sentMessage);

        // Clear the suggestion
        setShowSuggestion(false);
        setCurrentSuggestion('');

        console.log('AI reply sent successfully via HTTP fallback');

      } catch (httpError) {
        console.error('HTTP API fallback also failed:', httpError);
        setSuggestionError(`Failed to send AI reply: ${error.message}. HTTP fallback also failed: ${httpError.message}`);
      }
    }
  };

  // Handle dismissing AI suggestion
  const handleDismissSuggestion = () => {
    setShowSuggestion(false);
    setCurrentSuggestion('');
  };

  // Handle key press in input
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  // Connection status indicator
  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return '#27ae60';
      case 'connecting': return '#f39c12';
      case 'reconnecting': return '#e67e22';
      case 'error': return '#e74c3c';
      case 'failed': return '#c0392b';
      default: return '#95a5a6';
    }
  };

  const getConnectionStatusText = () => {
    switch (connectionStatus) {
      case 'connected': return 'Connected';
      case 'connecting': return 'Connecting...';
      case 'reconnecting': return 'Reconnecting...';
      case 'error': return 'Connection Error';
      case 'failed': return 'Connection Failed';
      default: return 'Disconnected';
    }
  };

  if (loadingHistory) {
    return (
      <div style={{
        padding: '2rem',
        textAlign: 'center',
        color: '#7f8c8d'
      }}>
        <Ripple color="#3869d4" size="medium" text="Loading chat history..." textColor="#74787e" />
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: 'white',
      overflow: 'hidden'
    }}>
      {/* Chat Header */}
      <div style={{
        padding: '1rem',
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <span className="material-icons" style={{ color: '#8b5cf6', fontSize: '1.25rem' }}>
            chat
          </span>
          <h2 style={{
            fontSize: '1.125rem',
            fontWeight: '500',
            color: '#1f2937',
            margin: 0
          }}>
            Ticket Chat
          </h2>
        </div>

        {/* Connection Status */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.25rem',
          fontSize: '0.75rem',
          color: '#10b981'
        }}>
          <span className="material-icons" style={{ fontSize: '0.875rem' }}>
            lens
          </span>
          <span>
            {getConnectionStatusText()}
          </span>
        </div>
      </div>

      {/* Messages Container */}
      <div
        ref={messagesContainerRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem'
        }}
      >
        {/* Error Message */}
        {(error || wsError) && (
          <div style={{
            backgroundColor: '#fee',
            color: '#c33',
            padding: '0.75rem',
            borderRadius: '4px',
            border: '1px solid #fcc',
            marginBottom: '1rem',
            fontSize: '0.9rem'
          }}>
            {error || wsError}
          </div>
        )}

        {/* AI Suggestion Error */}
        {suggestionError && (
          <div style={{
            backgroundColor: '#fff3cd',
            color: '#856404',
            padding: '0.75rem',
            borderRadius: '4px',
            border: '1px solid #ffeaa7',
            marginBottom: '1rem',
            fontSize: '0.9rem'
          }}>
            AI Suggestion Error: {suggestionError}
          </div>
        )}

        {/* AI Suggestion Modal */}
        {showSuggestion && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}>
            <div style={{
              backgroundColor: 'white',
              borderRadius: '8px',
              padding: '1.5rem',
              maxWidth: '600px',
              width: '90%',
              maxHeight: '80vh',
              overflow: 'auto',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                marginBottom: '1rem',
                gap: '0.5rem'
              }}>
                <span style={{ fontSize: '1.2rem' }}>🤖</span>
                <h3 style={{ margin: 0, color: '#2c3e50' }}>AI Response Suggestion</h3>
              </div>

              <div style={{
                backgroundColor: '#f8f9fa',
                padding: '1rem',
                borderRadius: '6px',
                border: '1px solid #e9ecef',
                marginBottom: '1rem',
                fontSize: '0.95rem',
                lineHeight: '1.5',
                color: '#2c3e50'
              }}>
                {currentSuggestion}
              </div>

              <div style={{
                display: 'flex',
                gap: '0.5rem',
                justifyContent: 'flex-end'
              }}>
                <button
                  onClick={handleDismissSuggestion}
                  style={{
                    padding: '0.5rem 1rem',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    backgroundColor: 'white',
                    color: '#666',
                    cursor: 'pointer',
                    fontSize: '0.9rem'
                  }}
                >
                  Dismiss
                </button>
                <button
                  onClick={handleUseSuggestion}
                  style={{
                    padding: '0.5rem 1rem',
                    border: '1px solid #3498db',
                    borderRadius: '4px',
                    backgroundColor: 'white',
                    color: '#3498db',
                    cursor: 'pointer',
                    fontSize: '0.9rem',
                    fontWeight: 'bold'
                  }}
                >
                  Edit & Send
                </button>
                <button
                  onClick={handleSendAIReply}
                  style={{
                    padding: '0.5rem 1rem',
                    border: 'none',
                    borderRadius: '4px',
                    backgroundColor: '#9b59b6',
                    color: 'white',
                    cursor: 'pointer',
                    fontSize: '0.9rem',
                    fontWeight: 'bold',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.3rem'
                  }}
                >
                  <span>🤖</span>
                  <span>Send AI Reply</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Messages */}
        {allMessages.length === 0 ? (
          <div style={{
            textAlign: 'center',
            color: '#7f8c8d',
            padding: '2rem',
            fontStyle: 'italic'
          }}>
            No messages yet. Start the conversation!
          </div>
        ) : (
          allMessages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onFeedback={handleMessageFeedback}
            />
          ))
        )}

        {/* Typing Indicators */}
        {typingUsers.length > 0 && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem',
            color: '#7f8c8d',
            fontSize: '0.8rem',
            fontStyle: 'italic'
          }}>
            <div style={{
              display: 'flex',
              gap: '2px'
            }}>
              <div style={{
                width: '4px',
                height: '4px',
                borderRadius: '50%',
                backgroundColor: '#7f8c8d',
                animation: 'pulse 1.5s infinite'
              }} />
              <div style={{
                width: '4px',
                height: '4px',
                borderRadius: '50%',
                backgroundColor: '#7f8c8d',
                animation: 'pulse 1.5s infinite 0.2s'
              }} />
              <div style={{
                width: '4px',
                height: '4px',
                borderRadius: '50%',
                backgroundColor: '#7f8c8d',
                animation: 'pulse 1.5s infinite 0.4s'
              }} />
            </div>
            Someone is typing...
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input */}
      <div style={{
        padding: '1rem',
        borderTop: '1px solid #e5e7eb'
      }}>
        <form onSubmit={handleSendMessage}>
          <div style={{
            display: 'flex',
            alignItems: 'stretch',
            gap: '0.5rem',
            height: '48px'
          }}>
            <textarea
              ref={inputRef}
              value={messageInput}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
              disabled={isLoading}
              rows={1}
              style={{
                flex: 1,
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '24px',
                resize: 'none',
                fontSize: '0.875rem',
                fontFamily: 'inherit',
                outline: 'none',
                backgroundColor: 'white',
                color: '#374151',
                height: '100%',
                minHeight: '48px',
                maxHeight: '48px',
                lineHeight: '1.2'
              }}
            />

            {/* AI Suggest Button - Only show for agents */}
            {isAgent && (
              <button
                type="button"
                onClick={handleAISuggestion}
                disabled={isLoadingSuggestion || allMessages.length === 0}
                style={{
                  padding: '0 1rem',
                  border: '1px solid #8b5cf6',
                  borderRadius: '24px',
                  backgroundColor: (isLoadingSuggestion || allMessages.length === 0) ? '#e5e7eb' : 'white',
                  color: (isLoadingSuggestion || allMessages.length === 0) ? '#9ca3af' : '#8b5cf6',
                  cursor: (isLoadingSuggestion || allMessages.length === 0) ? 'not-allowed' : 'pointer',
                  fontWeight: '500',
                  fontSize: '0.875rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.375rem',
                  height: '100%',
                  minHeight: '48px',
                  whiteSpace: 'nowrap',
                  flexShrink: 0
                }}
                title={allMessages.length === 0 ? 'No conversation to analyze' : 'Get AI response suggestion'}
              >
                {isLoadingSuggestion ? (
                  <Ripple color="#3869d4" size="small" text="" textColor="#74787e" />
                ) : (
                  <>
                    <span>🤖</span>
                    <span>AI Suggest</span>
                  </>
                )}
              </button>
            )}

            <button
              type="submit"
              disabled={!messageInput.trim() || isLoading}
              style={{
                backgroundColor: (!messageInput.trim() || isLoading) ? '#9ca3af' : '#3b82f6',
                color: 'white',
                fontWeight: '500',
                padding: '0 1.5rem',
                borderRadius: '24px',
                fontSize: '0.875rem',
                border: 'none',
                cursor: (!messageInput.trim() || isLoading) ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.375rem',
                height: '100%',
                minHeight: '48px',
                whiteSpace: 'nowrap',
                flexShrink: 0
              }}
            >
              {isLoading ? 'Sending...' : 'Send'}
              <span className="material-icons" style={{ fontSize: '0.875rem' }}>
                send
              </span>
            </button>
          </div>
        </form>
      </div>

      {/* CSS for typing animation */}
      <style jsx>{`
        @keyframes pulse {
          0%, 60%, 100% {
            opacity: 0.3;
          }
          30% {
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
};

export default TicketChat;

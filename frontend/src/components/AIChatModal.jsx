import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { aiBotAPI } from '../services/api';
import Ripple from './Ripple';

const AIChatModal = ({ isOpen, onClose }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      text: inputValue.trim(),
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await aiBotAPI.selfServeQuery(userMessage.text, sessionId);
      
      const aiMessage = {
        id: Date.now() + 1,
        text: response.answer,
        isUser: false,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('AI query error:', error);
      
      const errorMessage = {
        id: Date.now() + 1,
        text: 'Sorry, I encountered an error while processing your request. Please try again or create a support ticket if the issue persists.',
        isUser: false,
        isError: true,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClose = () => {
    setMessages([]);
    setInputValue('');
    onClose();
  };

  const startNewConversation = () => {
    setMessages([]);
    setInputValue('');
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  if (!isOpen) return null;

  return (
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
        borderRadius: '12px',
        width: '90%',
        maxWidth: '600px',
        height: '80%',
        maxHeight: '700px',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.3)'
      }}>
        {/* Header */}
        <div style={{
          padding: '1rem 1.5rem',
          borderBottom: '1px solid #e1e8ed',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#f8f9fa',
          borderRadius: '12px 12px 0 0'
        }}>
          <div>
            <h3 style={{ margin: 0, color: '#2c3e50', fontSize: '1.2rem' }}>
              🤖 Resolve with AI
            </h3>
            <p style={{ margin: '0.25rem 0 0 0', color: '#7f8c8d', fontSize: '0.9rem' }}>
              Get instant help with your questions
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={startNewConversation}
              style={{
                padding: '0.5rem',
                border: '1px solid #ddd',
                borderRadius: '6px',
                backgroundColor: 'white',
                cursor: 'pointer',
                fontSize: '0.9rem',
                color: '#666'
              }}
              title="Start new conversation"
            >
              🔄
            </button>
            <button
              onClick={handleClose}
              style={{
                padding: '0.5rem 0.75rem',
                border: 'none',
                borderRadius: '6px',
                backgroundColor: '#e74c3c',
                color: 'white',
                cursor: 'pointer',
                fontSize: '1rem'
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Messages */}
        <div style={{
          flex: 1,
          padding: '1rem',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem'
        }}>
          {messages.length === 0 && (
            <div style={{
              textAlign: 'center',
              color: '#7f8c8d',
              padding: '2rem',
              fontSize: '0.95rem'
            }}>
              <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>👋</div>
              <p>Hi! I'm your AI assistant. I can help you with:</p>
              <ul style={{ textAlign: 'left', display: 'inline-block', margin: '1rem 0' }}>
                <li>IT troubleshooting and technical issues</li>
                <li>HR policies and procedures</li>
                <li>Software installation and usage</li>
                <li>Account and access problems</li>
                <li>General helpdesk questions</li>
              </ul>
              <p>Just type your question below to get started!</p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              style={{
                display: 'flex',
                justifyContent: message.isUser ? 'flex-end' : 'flex-start'
              }}
            >
              <div style={{
                maxWidth: '80%',
                padding: '0.75rem 1rem',
                borderRadius: message.isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                backgroundColor: message.isUser
                  ? '#3498db'
                  : message.isError
                    ? '#e74c3c'
                    : '#f1f3f4',
                color: message.isUser || message.isError ? 'white' : '#2c3e50',
                fontSize: '0.95rem',
                lineHeight: '1.4',
                wordWrap: 'break-word'
              }}>
                {/* Render AI responses with markdown, user messages as plain text */}
                {message.isUser ? (
                  <div>{message.text}</div>
                ) : (
                  <ReactMarkdown
                    components={{
                      // Custom styling for markdown elements
                      p: ({ children }) => (
                        <p style={{ margin: '0 0 0.5rem 0', lineHeight: '1.4' }}>{children}</p>
                      ),
                      ul: ({ children }) => (
                        <ul style={{ margin: '0.5rem 0', paddingLeft: '1.2rem' }}>{children}</ul>
                      ),
                      ol: ({ children }) => (
                        <ol style={{ margin: '0.5rem 0', paddingLeft: '1.2rem' }}>{children}</ol>
                      ),
                      li: ({ children }) => (
                        <li style={{ margin: '0.2rem 0' }}>{children}</li>
                      ),
                      strong: ({ children }) => (
                        <strong style={{ fontWeight: 'bold' }}>{children}</strong>
                      ),
                      em: ({ children }) => (
                        <em style={{ fontStyle: 'italic' }}>{children}</em>
                      ),
                      code: ({ children }) => (
                        <code style={{
                          backgroundColor: message.isUser || message.isError ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.1)',
                          padding: '0.1rem 0.3rem',
                          borderRadius: '3px',
                          fontSize: '0.85rem',
                          fontFamily: 'monospace'
                        }}>{children}</code>
                      ),
                      pre: ({ children }) => (
                        <pre style={{
                          backgroundColor: message.isUser || message.isError ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.1)',
                          padding: '0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.85rem',
                          fontFamily: 'monospace',
                          overflow: 'auto',
                          margin: '0.5rem 0'
                        }}>{children}</pre>
                      ),
                      a: ({ href, children }) => (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            color: message.isUser || message.isError ? '#87ceeb' : '#3498db',
                            textDecoration: 'underline'
                          }}
                        >
                          {children}
                        </a>
                      ),
                      h1: ({ children }) => (
                        <h1 style={{ fontSize: '1.1rem', fontWeight: 'bold', margin: '0.5rem 0' }}>{children}</h1>
                      ),
                      h2: ({ children }) => (
                        <h2 style={{ fontSize: '1.05rem', fontWeight: 'bold', margin: '0.5rem 0' }}>{children}</h2>
                      ),
                      h3: ({ children }) => (
                        <h3 style={{ fontSize: '1rem', fontWeight: 'bold', margin: '0.5rem 0' }}>{children}</h3>
                      ),
                      blockquote: ({ children }) => (
                        <blockquote style={{
                          borderLeft: `3px solid ${message.isUser || message.isError ? 'rgba(255,255,255,0.5)' : '#3498db'}`,
                          paddingLeft: '0.5rem',
                          margin: '0.5rem 0',
                          fontStyle: 'italic'
                        }}>{children}</blockquote>
                      )
                    }}
                  >
                    {message.text}
                  </ReactMarkdown>
                )}
                <div style={{
                  fontSize: '0.75rem',
                  opacity: 0.7,
                  marginTop: '0.25rem'
                }}>
                  {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
              <div style={{
                padding: '0.75rem 1rem',
                borderRadius: '18px 18px 18px 4px',
                backgroundColor: '#f1f3f4',
                color: '#7f8c8d',
                fontSize: '0.95rem'
              }}>
                <Ripple color="#3498db" size="small" text="AI is thinking..." textColor="#7f8c8d" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div style={{
          padding: '1rem',
          borderTop: '1px solid #e1e8ed',
          backgroundColor: '#f8f9fa',
          borderRadius: '0 0 12px 12px'
        }}>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your question here..."
              disabled={isLoading}
              style={{
                flex: 1,
                padding: '0.75rem',
                border: '1px solid #ddd',
                borderRadius: '20px',
                fontSize: '0.95rem',
                outline: 'none',
                backgroundColor: isLoading ? '#f5f5f5' : 'white'
              }}
            />
            <button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              style={{
                padding: '0.75rem 1.5rem',
                border: 'none',
                borderRadius: '20px',
                backgroundColor: (!inputValue.trim() || isLoading) ? '#bdc3c7' : '#3498db',
                color: 'white',
                cursor: (!inputValue.trim() || isLoading) ? 'not-allowed' : 'pointer',
                fontSize: '0.95rem',
                fontWeight: 'bold'
              }}
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIChatModal;

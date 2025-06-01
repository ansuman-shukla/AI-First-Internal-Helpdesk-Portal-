import { useState, useEffect, useCallback, useRef } from 'react';
import webSocketService from '../services/websocket';
import { useAuth } from '../context/AuthContext';

/**
 * Custom hook for managing WebSocket connections in ticket chat
 * @param {string} ticketId - The ticket ID to connect to
 * @returns {object} - WebSocket state and methods
 */
export const useWebSocket = (ticketId) => {
  const { user } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [messages, setMessages] = useState([]);
  const [typingUsers, setTypingUsers] = useState(new Set());
  const [error, setError] = useState(null);
  
  // Refs to store cleanup functions
  const unsubscribeRefs = useRef([]);
  const typingTimeoutRef = useRef(null);

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(async () => {
    if (!ticketId || !user) {
      console.log('Missing ticketId or user for WebSocket connection');
      return;
    }

    const token = localStorage.getItem('token');
    if (!token) {
      console.error('No authentication token available for WebSocket connection');
      setError('Authentication token not found');
      return;
    }

    console.log('Attempting WebSocket connection with token:', token.substring(0, 20) + '...');

    try {
      setConnectionStatus('connecting');
      setError(null);

      const success = await webSocketService.connect(ticketId, token);
      if (success) {
        setIsConnected(true);
        setConnectionStatus('connected');
      }
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      setError(error.message);
      setConnectionStatus('error');
      setIsConnected(false);
    }
  }, [ticketId, user]);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    webSocketService.disconnect();
    setIsConnected(false);
    setConnectionStatus('disconnected');
    setError(null);
    
    // Clear typing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
  }, []);

  /**
   * Send a chat message
   */
  const sendMessage = useCallback((content, options = {}) => {
    try {
      webSocketService.sendMessage(content, options);
      return true;
    } catch (error) {
      console.error('Failed to send message:', error);
      setError(error.message);
      return false;
    }
  }, []);

  /**
   * Send typing indicator
   */
  const sendTyping = useCallback(() => {
    try {
      webSocketService.sendTyping();
      
      // Clear existing timeout
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      
      // Set timeout to stop typing indicator after 3 seconds
      typingTimeoutRef.current = setTimeout(() => {
        // Note: In a real implementation, you might want to send a "stop typing" message
        // For now, we'll just let the typing indicator expire on the receiving end
      }, 3000);
      
    } catch (error) {
      console.error('Failed to send typing indicator:', error);
    }
  }, []);

  /**
   * Add a message to the local state (for optimistic updates)
   */
  const addMessage = useCallback((message) => {
    setMessages(prev => [...prev, message]);
  }, []);

  /**
   * Clear all messages
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  /**
   * Set up WebSocket event listeners
   */
  useEffect(() => {
    if (!ticketId) return;

    // Clear previous subscriptions
    unsubscribeRefs.current.forEach(unsubscribe => unsubscribe());
    unsubscribeRefs.current = [];

    // Message handlers
    const unsubscribeNewMessage = webSocketService.onMessage('new_message', (data) => {
      console.log('Received new message:', data);
      if (data.message) {
        setMessages(prev => {
          // Check if message already exists to avoid duplicates
          const exists = prev.some(msg => msg.id === data.message.id);
          if (exists) return prev;
          
          return [...prev, data.message];
        });
      }
    });

    const unsubscribeTyping = webSocketService.onMessage('typing', (data) => {
      console.log('User typing:', data);
      if (data.user_id) {
        setTypingUsers(prev => new Set([...prev, data.user_id]));
        
        // Remove typing indicator after 5 seconds
        setTimeout(() => {
          setTypingUsers(prev => {
            const newSet = new Set(prev);
            newSet.delete(data.user_id);
            return newSet;
          });
        }, 5000);
      }
    });

    const unsubscribeUserJoined = webSocketService.onMessage('user_joined', (data) => {
      console.log('User joined:', data);
      // You can add a system message or notification here
    });

    const unsubscribeUserLeft = webSocketService.onMessage('user_left', (data) => {
      console.log('User left:', data);
      // Remove from typing users if they were typing
      if (data.user_id) {
        setTypingUsers(prev => {
          const newSet = new Set(prev);
          newSet.delete(data.user_id);
          return newSet;
        });
      }
    });

    const unsubscribePong = webSocketService.onMessage('pong', (data) => {
      console.log('Received pong:', data);
      // Connection is alive
    });

    const unsubscribeError = webSocketService.onMessage('error', (data) => {
      console.error('WebSocket error message:', data);
      setError(data.message || 'WebSocket error');
    });

    // Connection handlers
    const unsubscribeConnected = webSocketService.onConnection('connected', () => {
      setIsConnected(true);
      setConnectionStatus('connected');
      setError(null);
    });

    const unsubscribeDisconnected = webSocketService.onConnection('disconnected', () => {
      setIsConnected(false);
      setConnectionStatus('disconnected');
    });

    const unsubscribeConnectionError = webSocketService.onConnection('error', (data) => {
      setError(data.error?.message || 'Connection error');
      setConnectionStatus('error');
      setIsConnected(false);
    });

    const unsubscribeReconnecting = webSocketService.onConnection('reconnecting', (data) => {
      setConnectionStatus('reconnecting');
      console.log(`Reconnecting... attempt ${data.attempt}`);
    });

    const unsubscribeMaxReconnect = webSocketService.onConnection('max_reconnect_attempts', () => {
      setConnectionStatus('failed');
      setError('Failed to reconnect after multiple attempts');
    });

    // Store all unsubscribe functions
    unsubscribeRefs.current = [
      unsubscribeNewMessage,
      unsubscribeTyping,
      unsubscribeUserJoined,
      unsubscribeUserLeft,
      unsubscribePong,
      unsubscribeError,
      unsubscribeConnected,
      unsubscribeDisconnected,
      unsubscribeConnectionError,
      unsubscribeReconnecting,
      unsubscribeMaxReconnect
    ];

    // Auto-connect when ticketId changes
    if (user) {
      connect();
    }

    // Cleanup on unmount or ticketId change
    return () => {
      unsubscribeRefs.current.forEach(unsubscribe => unsubscribe());
      unsubscribeRefs.current = [];

      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
        typingTimeoutRef.current = null;
      }
    };
  }, [ticketId, user, connect]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    // Connection state
    isConnected,
    connectionStatus,
    error,
    
    // Messages
    messages,
    typingUsers: Array.from(typingUsers),
    
    // Actions
    connect,
    disconnect,
    sendMessage,
    sendTyping,
    addMessage,
    clearMessages,
    
    // Utilities
    getStatus: () => webSocketService.getStatus()
  };
};

import { WS_MESSAGE_TYPES } from './api';

class WebSocketService {
  constructor() {
    this.ws = null;
    this.ticketId = null;
    this.token = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second
    this.messageHandlers = new Map();
    this.connectionHandlers = new Map();
    this.pingInterval = null;
    this.pingIntervalTime = 30000; // 30 seconds
  }

  /**
   * Connect to WebSocket for a specific ticket
   * @param {string} ticketId - The ticket ID to connect to
   * @param {string} token - JWT authentication token
   * @returns {Promise<boolean>} - Success status
   */
  async connect(ticketId, token) {
    if (this.isConnected && this.ticketId === ticketId) {
      console.log('Already connected to this ticket');
      return true;
    }

    // Disconnect existing connection if any
    if (this.ws) {
      this.disconnect();
    }

    this.ticketId = ticketId;
    this.token = token;

    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `ws://localhost:8000/ws/chat/${ticketId}?token=${encodeURIComponent(token)}`;
        console.log('Connecting to WebSocket:', wsUrl);
        
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = (event) => {
          console.log('WebSocket connected successfully');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.startPingInterval();
          this.notifyConnectionHandlers('connected', { ticketId, event });
          resolve(true);
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('WebSocket message received:', data);
            this.handleMessage(data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket connection closed:', event.code, event.reason);
          this.isConnected = false;
          this.stopPingInterval();
          this.notifyConnectionHandlers('disconnected', { ticketId, event });

          // Attempt to reconnect if not a normal closure
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.notifyConnectionHandlers('error', { ticketId, error });
          reject(error);
        };

        // Timeout for connection
        setTimeout(() => {
          if (!this.isConnected) {
            reject(new Error('WebSocket connection timeout'));
          }
        }, 10000); // 10 second timeout

      } catch (error) {
        console.error('Error creating WebSocket connection:', error);
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.ws) {
      this.stopPingInterval();
      this.ws.close(1000, 'Client disconnecting');
      this.ws = null;
    }
    this.isConnected = false;
    this.ticketId = null;
    this.token = null;
    this.reconnectAttempts = 0;
  }

  /**
   * Send a chat message
   * @param {string} content - Message content
   * @param {object} options - Additional message options
   */
  sendMessage(content, options = {}) {
    if (!this.isConnected || !this.ws) {
      throw new Error('WebSocket not connected');
    }

    const message = {
      type: WS_MESSAGE_TYPES.CHAT,
      ticket_id: this.ticketId,
      content: content.trim(),
      message_type: options.messageType || 'user_message',
      isAI: options.isAI || false,
      feedback: options.feedback || 'none'
    };

    console.log('Sending message:', message);
    this.ws.send(JSON.stringify(message));
  }

  /**
   * Send typing indicator
   */
  sendTyping() {
    if (!this.isConnected || !this.ws) {
      return;
    }

    const message = {
      type: WS_MESSAGE_TYPES.TYPING,
      ticket_id: this.ticketId
    };

    this.ws.send(JSON.stringify(message));
  }

  /**
   * Send ping message
   */
  sendPing() {
    if (!this.isConnected || !this.ws) {
      return;
    }

    const message = {
      type: WS_MESSAGE_TYPES.PING,
      ticket_id: this.ticketId
    };

    this.ws.send(JSON.stringify(message));
  }

  /**
   * Start ping interval to keep connection alive
   */
  startPingInterval() {
    this.stopPingInterval(); // Clear any existing interval
    this.pingInterval = setInterval(() => {
      this.sendPing();
    }, this.pingIntervalTime);
  }

  /**
   * Stop ping interval
   */
  stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnection attempts reached');
      this.notifyConnectionHandlers('max_reconnect_attempts', { ticketId: this.ticketId });
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
    this.notifyConnectionHandlers('reconnecting', { 
      ticketId: this.ticketId, 
      attempt: this.reconnectAttempts,
      delay 
    });

    setTimeout(() => {
      if (this.ticketId && this.token) {
        this.connect(this.ticketId, this.token).catch(error => {
          console.error('Reconnection failed:', error);
        });
      }
    }, delay);
  }

  /**
   * Handle incoming WebSocket messages
   * @param {object} data - Parsed message data
   */
  handleMessage(data) {
    const { type } = data;
    
    // Notify all handlers for this message type
    const handlers = this.messageHandlers.get(type) || [];
    handlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error('Error in message handler:', error);
      }
    });

    // Notify all handlers for 'all' message types
    const allHandlers = this.messageHandlers.get('all') || [];
    allHandlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error('Error in message handler:', error);
      }
    });
  }

  /**
   * Add message handler for specific message type
   * @param {string} type - Message type or 'all' for all messages
   * @param {function} handler - Handler function
   * @returns {function} - Unsubscribe function
   */
  onMessage(type, handler) {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    
    this.messageHandlers.get(type).push(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(type);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  /**
   * Add connection event handler
   * @param {string} event - Event type (connected, disconnected, error, reconnecting, max_reconnect_attempts)
   * @param {function} handler - Handler function
   * @returns {function} - Unsubscribe function
   */
  onConnection(event, handler) {
    if (!this.connectionHandlers.has(event)) {
      this.connectionHandlers.set(event, []);
    }
    
    this.connectionHandlers.get(event).push(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.connectionHandlers.get(event);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  /**
   * Notify connection handlers
   * @param {string} event - Event type
   * @param {object} data - Event data
   */
  notifyConnectionHandlers(event, data) {
    const handlers = this.connectionHandlers.get(event) || [];
    handlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        console.error('Error in connection handler:', error);
      }
    });
  }

  /**
   * Get connection status
   * @returns {object} - Connection status information
   */
  getStatus() {
    return {
      isConnected: this.isConnected,
      ticketId: this.ticketId,
      reconnectAttempts: this.reconnectAttempts,
      maxReconnectAttempts: this.maxReconnectAttempts
    };
  }
}

// Create singleton instance
const webSocketService = new WebSocketService();

export default webSocketService;

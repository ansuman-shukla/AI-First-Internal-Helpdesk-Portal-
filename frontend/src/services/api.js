import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API functions
export const authAPI = {
  login: async (credentials) => {
    const response = await api.post('/auth/login', credentials);
    return response.data;
  },

  register: async (userData) => {
    const response = await api.post('/auth/register', userData);
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  logout: async () => {
    const response = await api.post('/auth/logout');
    return response.data;
  }
};

// Ticket API functions
export const ticketAPI = {
  createTicket: async (ticketData) => {
    const response = await api.post('/tickets', ticketData);
    return response.data;
  },
  
  getTickets: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.department) params.append('department', filters.department);
    if (filters.search) params.append('search', filters.search);
    if (filters.page) params.append('page', filters.page);
    if (filters.limit) params.append('limit', filters.limit);

    const response = await api.get(`/tickets?${params.toString()}`);
    return response.data;
  },
  
  getTicketById: async (ticketId) => {
    const response = await api.get(`/tickets/${ticketId}`);
    return response.data;
  },
  
  updateTicket: async (ticketId, updateData) => {
    const response = await api.put(`/tickets/${ticketId}`, updateData);
    return response.data;
  },

  deleteTicket: async (ticketId) => {
    const response = await api.delete(`/tickets/${ticketId}`);
    return response.data;
  }
};

// Dashboard API functions
export const dashboardAPI = {
  getUserHome: async () => {
    const response = await api.get('/user/home');
    return response.data;
  },

  getAgentHome: async () => {
    const response = await api.get('/agent/home');
    return response.data;
  },

  getAdminHome: async () => {
    const response = await api.get('/admin/home');
    return response.data;
  }
};

// AI Bot API functions (Phase 3)
export const aiBotAPI = {
  selfServeQuery: async (query, sessionId = null) => {
    const payload = { query };
    if (sessionId) {
      payload.session_id = sessionId;
    }

    const response = await api.post('/ai/self-serve-query', payload);
    return response.data;
  },

  getSelfServeInfo: async () => {
    const response = await api.get('/ai/self-serve-info');
    return response.data;
  }
};

// AI Agent API functions (Phase 5)
export const aiAgentAPI = {
  suggestResponse: async (ticketId, conversationContext) => {
    const payload = {
      ticket_id: ticketId,
      conversation_context: conversationContext
    };

    const response = await api.post('/ai/suggest-response', payload);
    return response.data;
  },

  getAgentTools: async () => {
    const response = await api.get('/ai/agent-tools');
    return response.data;
  }
};

// Admin API functions
export const adminAPI = {
  getMisuseReports: async (params = {}) => {
    const queryParams = new URLSearchParams();

    if (params.page) queryParams.append('page', params.page);
    if (params.limit) queryParams.append('limit', params.limit);
    if (params.unreviewed_only) queryParams.append('unreviewed_only', params.unreviewed_only);

    const response = await api.get(`/admin/misuse-reports?${queryParams.toString()}`);
    return response.data;
  },

  getMisuseReportById: async (reportId) => {
    const response = await api.get(`/admin/misuse-reports/${reportId}`);
    return response.data;
  },

  markMisuseReportReviewed: async (reportId, actionTaken = null) => {
    const params = new URLSearchParams();
    if (actionTaken) params.append('action_taken', actionTaken);

    const response = await api.post(`/admin/misuse-reports/${reportId}/mark-reviewed?${params.toString()}`);
    return response.data;
  },

  getAnalyticsOverview: async () => {
    try {
      const response = await api.get('/admin/analytics/overview');
      return response.data;
    } catch (error) {
      // Return mock data if analytics not implemented yet
      return {
        total_tickets: 0,
        open_tickets: 0,
        misuse_reports: 0,
        active_users: 0
      };
    }
  },

  getTrendingTopics: async () => {
    const response = await api.get('/admin/analytics/trending-topics');
    return response.data;
  },

  getFlaggedUsers: async () => {
    const response = await api.get('/admin/analytics/flagged-users');
    return response.data;
  },

  getResolutionTimes: async () => {
    const response = await api.get('/admin/analytics/resolution-times');
    return response.data;
  },

  runMisuseDetection: async () => {
    const response = await api.post('/admin/jobs/run-misuse-detection');
    return response.data;
  },

  runInactivityDetection: async () => {
    const response = await api.post('/admin/jobs/run-inactivity-detection');
    return response.data;
  },

  getSystemManagement: async () => {
    const response = await api.get('/admin/system-management');
    return response.data;
  },

  // Analytics endpoints
  getDashboardMetrics: async (days = 7) => {
    const response = await api.get(`/admin/analytics/dashboard-metrics?days=${days}`);
    return response.data;
  },

  getTimeSeriesAnalytics: async (days = 30, granularity = 'daily') => {
    const response = await api.get(`/admin/analytics/time-series?days=${days}&granularity=${granularity}`);
    return response.data;
  },

  getPerformanceMetrics: async (days = 30) => {
    const response = await api.get(`/admin/analytics/performance-metrics?days=${days}`);
    return response.data;
  },

  getTrendingTopics: async (days = 30, limit = 10, forceRefresh = false) => {
    const response = await api.get(`/admin/analytics/trending-topics?days=${days}&limit=${limit}&force_refresh=${forceRefresh}`);
    return response.data;
  },

  refreshTrendingTopicsCache: async (days = 30, limit = 10) => {
    const response = await api.post(`/admin/analytics/trending-topics/refresh?days=${days}&limit=${limit}`);
    return response.data;
  },

  getTrendingTopicsCacheStatus: async () => {
    const response = await api.get('/admin/analytics/trending-topics/cache-status');
    return response.data;
  },

  clearTrendingTopicsCache: async () => {
    const response = await api.delete('/admin/analytics/trending-topics/cache');
    return response.data;
  },

  // Document management endpoints
  uploadDocument: async (file, category) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);

    const response = await api.post('/admin/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getKnowledgeBaseStats: async () => {
    const response = await api.get('/admin/documents/stats');
    return response.data;
  }
};

// Message API functions (Phase 4)
export const messageAPI = {
  getTicketMessages: async (ticketId, page = 1, limit = 50) => {
    const params = new URLSearchParams();
    params.append('page', page);
    params.append('limit', limit);

    const response = await api.get(`/tickets/${ticketId}/messages?${params.toString()}`);
    return response.data;
  },

  sendMessage: async (ticketId, messageData) => {
    const response = await api.post(`/tickets/${ticketId}/messages`, messageData);
    return response.data;
  },

  updateMessageFeedback: async (ticketId, messageId, feedback) => {
    const response = await api.put(`/tickets/${ticketId}/messages/${messageId}/feedback`, {
      feedback
    });
    return response.data;
  }
};

// Constants for ticket enums (matching backend)
export const TICKET_STATUS = {
  OPEN: 'open',
  ASSIGNED: 'assigned',
  RESOLVED: 'resolved',
  CLOSED: 'closed'
};

export const TICKET_URGENCY = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high'
};

export const TICKET_DEPARTMENT = {
  IT: 'IT',
  HR: 'HR'
};

export const USER_ROLES = {
  USER: 'user',
  IT_AGENT: 'it_agent',
  HR_AGENT: 'hr_agent',
  ADMIN: 'admin'
};

// Message constants (Phase 4)
export const MESSAGE_TYPES = {
  USER_MESSAGE: 'user_message',
  AGENT_MESSAGE: 'agent_message',
  SYSTEM_MESSAGE: 'system_message'
};

export const MESSAGE_FEEDBACK = {
  UP: 'up',
  DOWN: 'down',
  NONE: 'none'
};

export const MESSAGE_ROLES = {
  USER: 'user',
  IT_AGENT: 'it_agent',
  HR_AGENT: 'hr_agent',
  ADMIN: 'admin'
};

// WebSocket message types
export const WS_MESSAGE_TYPES = {
  CHAT: 'chat',
  TYPING: 'typing',
  PING: 'ping',
  PONG: 'pong'
};

// Notification API functions
export const notificationAPI = {
  getNotifications: async (params = {}) => {
    const queryParams = new URLSearchParams();

    if (params.page) queryParams.append('page', params.page);
    if (params.limit) queryParams.append('limit', params.limit);
    if (params.unread_only) queryParams.append('unread_only', params.unread_only);

    const response = await api.get(`/notifications?${queryParams.toString()}`);
    return response.data;
  },

  getUnreadCount: async () => {
    const response = await api.get('/notifications/unread-count');
    return response.data;
  },

  markAsRead: async (notificationId) => {
    const response = await api.put(`/notifications/${notificationId}/read`);
    return response.data;
  },

  markAllAsRead: async () => {
    const response = await api.put('/notifications/mark-all-read');
    return response.data;
  },

  deleteNotification: async (notificationId) => {
    const response = await api.delete(`/notifications/${notificationId}`);
    return response.data;
  }
};

// Notification types enum (should match backend)
export const NOTIFICATION_TYPES = {
  TICKET_CREATED: 'ticket_created',
  TICKET_ASSIGNED: 'ticket_assigned',
  TICKET_UPDATED: 'ticket_updated',
  MESSAGE_RECEIVED: 'message_received',
  MISUSE_DETECTED: 'misuse_detected',
  SYSTEM_ALERT: 'system_alert'
};

export default api;

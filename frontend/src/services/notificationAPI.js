/**
 * Notification API service
 * 
 * This module provides API functions for notification management
 * including fetching, marking as read, and managing user notifications.
 */

import api from './api';

// Notification API functions
export const notificationAPI = {
  /**
   * Get notifications for the current user with pagination
   * 
   * @param {Object} params - Query parameters
   * @param {number} params.page - Page number (1-based)
   * @param {number} params.limit - Number of notifications per page
   * @param {boolean} params.unread_only - Return only unread notifications
   * @returns {Promise<Object>} Paginated notification list
   */
  getNotifications: async (params = {}) => {
    const queryParams = new URLSearchParams();
    
    if (params.page) queryParams.append('page', params.page);
    if (params.limit) queryParams.append('limit', params.limit);
    if (params.unread_only) queryParams.append('unread_only', params.unread_only);
    
    const response = await api.get(`/notifications?${queryParams.toString()}`);
    return response.data;
  },

  /**
   * Get notification counts for the current user
   * 
   * @returns {Promise<Object>} Notification counts (unread and total)
   */
  getUnreadCount: async () => {
    const response = await api.get('/notifications/unread-count');
    return response.data;
  },

  /**
   * Mark a specific notification as read
   * 
   * @param {string} notificationId - ID of the notification to mark as read
   * @returns {Promise<Object>} Success response
   */
  markAsRead: async (notificationId) => {
    const response = await api.put(`/notifications/${notificationId}/read`);
    return response.data;
  },

  /**
   * Mark all notifications as read for the current user
   * 
   * @returns {Promise<Object>} Success response with count
   */
  markAllAsRead: async () => {
    const response = await api.put('/notifications/mark-all-read');
    return response.data;
  },

  /**
   * Delete a specific notification
   * 
   * @param {string} notificationId - ID of the notification to delete
   * @returns {Promise<Object>} Success response
   */
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

// Helper functions for notification display
export const getNotificationIcon = (type) => {
  const icons = {
    [NOTIFICATION_TYPES.TICKET_CREATED]: '🎫',
    [NOTIFICATION_TYPES.TICKET_ASSIGNED]: '📋',
    [NOTIFICATION_TYPES.TICKET_UPDATED]: '🔄',
    [NOTIFICATION_TYPES.MESSAGE_RECEIVED]: '💬',
    [NOTIFICATION_TYPES.MISUSE_DETECTED]: '⚠️',
    [NOTIFICATION_TYPES.SYSTEM_ALERT]: '🔔'
  };
  return icons[type] || '📢';
};

export const getNotificationColor = (type) => {
  const colors = {
    [NOTIFICATION_TYPES.TICKET_CREATED]: '#3869d4',
    [NOTIFICATION_TYPES.TICKET_ASSIGNED]: '#f39c12',
    [NOTIFICATION_TYPES.TICKET_UPDATED]: '#27ae60',
    [NOTIFICATION_TYPES.MESSAGE_RECEIVED]: '#9b59b6',
    [NOTIFICATION_TYPES.MISUSE_DETECTED]: '#e74c3c',
    [NOTIFICATION_TYPES.SYSTEM_ALERT]: '#34495e'
  };
  return colors[type] || '#95a5a6';
};

export const formatNotificationTime = (timestamp) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffInMinutes = Math.floor((now - date) / (1000 * 60));
  
  if (diffInMinutes < 1) {
    return 'Just now';
  } else if (diffInMinutes < 60) {
    return `${diffInMinutes}m ago`;
  } else if (diffInMinutes < 1440) { // 24 hours
    const hours = Math.floor(diffInMinutes / 60);
    return `${hours}h ago`;
  } else {
    const days = Math.floor(diffInMinutes / 1440);
    if (days === 1) {
      return 'Yesterday';
    } else if (days < 7) {
      return `${days}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  }
};

export default notificationAPI;

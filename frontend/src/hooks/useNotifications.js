/**
 * useNotifications hook
 * 
 * Custom React hook for managing notification state and operations
 */

import { useState, useEffect, useCallback } from 'react';
import { notificationAPI } from '../services/api';

export const useNotifications = () => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);

  // Fetch notifications
  const fetchNotifications = useCallback(async (pageNum = 1, unreadOnly = false, append = false) => {
    try {
      setLoading(true);
      setError(null);

      const response = await notificationAPI.getNotifications({
        page: pageNum,
        limit: 20,
        unread_only: unreadOnly
      });

      if (append && pageNum > 1) {
        setNotifications(prev => [...prev, ...response.notifications]);
      } else {
        setNotifications(response.notifications);
      }

      setUnreadCount(response.unread_count);
      setTotalCount(response.total);
      setPage(pageNum);
      setHasNext(response.has_next);

    } catch (err) {
      console.error('Error fetching notifications:', err);
      setError('Failed to load notifications');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch unread count only
  const fetchUnreadCount = useCallback(async () => {
    try {
      const response = await notificationAPI.getUnreadCount();
      setUnreadCount(response.unread_count);
      setTotalCount(response.total_count);
    } catch (err) {
      console.error('Error fetching unread count:', err);
    }
  }, []);

  // Mark notification as read
  const markAsRead = useCallback(async (notificationId) => {
    try {
      await notificationAPI.markAsRead(notificationId);
      
      // Update local state
      setNotifications(prev => 
        prev.map(notification => 
          notification.notification_id === notificationId
            ? { ...notification, read: true, read_at: new Date().toISOString() }
            : notification
        )
      );
      
      // Update unread count
      setUnreadCount(prev => Math.max(0, prev - 1));
      
      return true;
    } catch (err) {
      console.error('Error marking notification as read:', err);
      setError('Failed to mark notification as read');
      return false;
    }
  }, []);

  // Mark all notifications as read
  const markAllAsRead = useCallback(async () => {
    try {
      const response = await notificationAPI.markAllAsRead();
      
      // Update local state
      setNotifications(prev => 
        prev.map(notification => ({
          ...notification,
          read: true,
          read_at: new Date().toISOString()
        }))
      );
      
      setUnreadCount(0);
      
      return response.count;
    } catch (err) {
      console.error('Error marking all notifications as read:', err);
      setError('Failed to mark all notifications as read');
      return 0;
    }
  }, []);

  // Delete notification
  const deleteNotification = useCallback(async (notificationId) => {
    try {
      await notificationAPI.deleteNotification(notificationId);
      
      // Update local state
      const deletedNotification = notifications.find(n => n.notification_id === notificationId);
      setNotifications(prev => 
        prev.filter(notification => notification.notification_id !== notificationId)
      );
      
      // Update counts
      setTotalCount(prev => Math.max(0, prev - 1));
      if (deletedNotification && !deletedNotification.read) {
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
      
      return true;
    } catch (err) {
      console.error('Error deleting notification:', err);
      setError('Failed to delete notification');
      return false;
    }
  }, [notifications]);

  // Load more notifications (pagination)
  const loadMore = useCallback(() => {
    if (hasNext && !loading) {
      fetchNotifications(page + 1, false, true);
    }
  }, [hasNext, loading, page, fetchNotifications]);

  // Refresh notifications
  const refresh = useCallback(() => {
    fetchNotifications(1, false, false);
  }, [fetchNotifications]);

  // Add new notification (for real-time updates)
  const addNotification = useCallback((notification) => {
    setNotifications(prev => [notification, ...prev]);
    setTotalCount(prev => prev + 1);
    if (!notification.read) {
      setUnreadCount(prev => prev + 1);
    }
  }, []);

  // Update notification (for real-time updates)
  const updateNotification = useCallback((notificationId, updates) => {
    setNotifications(prev => 
      prev.map(notification => 
        notification.notification_id === notificationId
          ? { ...notification, ...updates }
          : notification
      )
    );
    
    // Update unread count if read status changed
    if (updates.read !== undefined) {
      const notification = notifications.find(n => n.notification_id === notificationId);
      if (notification && notification.read !== updates.read) {
        setUnreadCount(prev => updates.read ? Math.max(0, prev - 1) : prev + 1);
      }
    }
  }, [notifications]);

  // Initial load
  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  // Auto-refresh unread count every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  return {
    // State
    notifications,
    unreadCount,
    totalCount,
    loading,
    error,
    page,
    hasNext,
    
    // Actions
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    loadMore,
    refresh,
    addNotification,
    updateNotification,
    
    // Helpers
    clearError: () => setError(null)
  };
};

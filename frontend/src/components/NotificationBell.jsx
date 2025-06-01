/**
 * NotificationBell component
 * 
 * A notification bell icon with unread count badge and dropdown list
 */

import React, { useState, useRef, useEffect } from 'react';
import { useNotifications } from '../hooks/useNotifications';
import { NOTIFICATION_TYPES } from '../services/api';
import Ripple from './Ripple';

// Helper functions for notification display
const getNotificationIcon = (type) => {
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

const getNotificationColor = (type) => {
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

const formatNotificationTime = (timestamp) => {
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

const NotificationBell = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);
  const dropdownRef = useRef(null);
  const bellRef = useRef(null);

  const {
    notifications,
    unreadCount,
    loading,
    error,
    hasNext,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    loadMore,
    refresh,
    clearError
  } = useNotifications();

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        dropdownRef.current && 
        !dropdownRef.current.contains(event.target) &&
        bellRef.current &&
        !bellRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleBellClick = () => {
    setIsOpen(!isOpen);
    if (!isOpen) {
      clearError();
    }
  };

  const handleNotificationClick = async (notification) => {
    if (!notification.read) {
      await markAsRead(notification.notification_id);
    }
    
    // Navigate to relevant page based on notification data
    if (notification.data?.ticket_id) {
      window.location.href = `/tickets/${notification.data.ticket_id}`;
    }
  };

  const handleMarkAllRead = async () => {
    await markAllAsRead();
  };

  const handleDeleteNotification = async (e, notificationId) => {
    e.stopPropagation();
    await deleteNotification(notificationId);
  };

  const filteredNotifications = showUnreadOnly 
    ? notifications.filter(n => !n.read)
    : notifications;

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      {/* Notification Bell */}
      <button
        ref={bellRef}
        onClick={handleBellClick}
        style={{
          position: 'relative',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          padding: '8px',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease',
          fontSize: '1.2rem',
          outline: 'none'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
        }}
        onFocus={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.1)';
          e.currentTarget.style.boxShadow = '0 0 0 2px rgba(56, 105, 212, 0.3)';
        }}
        onBlur={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent';
          e.currentTarget.style.boxShadow = 'none';
        }}
        title={`${unreadCount} unread notifications`}
      >
        <span
          className="material-icons"
          style={{
            color: '#f59e0b',
            fontSize: '1.5rem',
            pointerEvents: 'none' // Prevent icon from interfering with button events
          }}
        >
          notifications
        </span>

        {/* Unread Count Badge */}
        {unreadCount > 0 && (
          <span style={{
            position: 'absolute',
            top: '2px',
            right: '2px',
            backgroundColor: '#e74c3c',
            color: 'white',
            borderRadius: '50%',
            width: '18px',
            height: '18px',
            fontSize: '0.7rem',
            fontWeight: 'bold',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minWidth: '18px',
            pointerEvents: 'none' // Prevent badge from interfering with button events
          }}>
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Notification Dropdown */}
      {isOpen && (
        <div
          ref={dropdownRef}
          style={{
            position: 'absolute',
            top: '100%',
            right: '0',
            width: '350px',
            maxHeight: '500px',
            backgroundColor: 'white',
            border: '1px solid #e1e8ed',
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            zIndex: 1000,
            overflow: 'hidden'
          }}
        >
          {/* Header */}
          <div style={{
            padding: '12px 16px',
            borderBottom: '1px solid #e1e8ed',
            backgroundColor: '#f8f9fa',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <h3 style={{
              margin: 0,
              fontSize: '1rem',
              fontWeight: 'bold',
              color: '#2c3e50'
            }}>
              Notifications
            </h3>
            
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => setShowUnreadOnly(!showUnreadOnly)}
                style={{
                  background: showUnreadOnly ? '#3869d4' : 'transparent',
                  color: showUnreadOnly ? 'white' : '#3869d4',
                  border: `1px solid #3869d4`,
                  borderRadius: '4px',
                  padding: '4px 8px',
                  fontSize: '0.75rem',
                  cursor: 'pointer'
                }}
              >
                {showUnreadOnly ? 'Show All' : 'Unread Only'}
              </button>
              
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  style={{
                    background: 'transparent',
                    color: '#27ae60',
                    border: '1px solid #27ae60',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    fontSize: '0.75rem',
                    cursor: 'pointer'
                  }}
                >
                  Mark All Read
                </button>
              )}
            </div>
          </div>

          {/* Content */}
          <div style={{
            maxHeight: '400px',
            overflowY: 'auto'
          }}>
            {loading && (
              <div style={{
                padding: '20px',
                textAlign: 'center',
                color: '#7f8c8d'
              }}>
                <Ripple color="#3869d4" size="small" text="Loading notifications..." textColor="#7f8c8d" />
              </div>
            )}

            {error && (
              <div style={{
                padding: '12px 16px',
                backgroundColor: '#fee',
                color: '#c33',
                fontSize: '0.9rem'
              }}>
                {error}
              </div>
            )}

            {!loading && filteredNotifications.length === 0 && (
              <div style={{
                padding: '40px 20px',
                textAlign: 'center',
                color: '#7f8c8d'
              }}>
                <span className="material-icons" style={{ fontSize: '2rem', marginBottom: '8px', display: 'block' }}>
                  notifications_none
                </span>
                <div>
                  {showUnreadOnly ? 'No unread notifications' : 'No notifications yet'}
                </div>
              </div>
            )}

            {/* Notification List */}
            {filteredNotifications.map((notification) => (
              <div
                key={notification.notification_id}
                onClick={() => handleNotificationClick(notification)}
                style={{
                  padding: '12px 16px',
                  borderBottom: '1px solid #f1f3f4',
                  cursor: 'pointer',
                  backgroundColor: notification.read ? 'white' : '#f8f9ff',
                  transition: 'background-color 0.2s ease',
                  position: 'relative'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.backgroundColor = notification.read ? '#f8f9fa' : '#f0f0ff';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.backgroundColor = notification.read ? 'white' : '#f8f9ff';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                  {/* Icon */}
                  <div style={{
                    fontSize: '1.2rem',
                    color: getNotificationColor(notification.type),
                    marginTop: '2px'
                  }}>
                    {getNotificationIcon(notification.type)}
                  </div>

                  {/* Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontWeight: notification.read ? 'normal' : 'bold',
                      fontSize: '0.9rem',
                      color: '#2c3e50',
                      marginBottom: '4px'
                    }}>
                      {notification.title}
                    </div>
                    
                    <div style={{
                      fontSize: '0.8rem',
                      color: '#7f8c8d',
                      lineHeight: '1.3',
                      marginBottom: '4px'
                    }}>
                      {notification.message}
                    </div>
                    
                    <div style={{
                      fontSize: '0.75rem',
                      color: '#95a5a6'
                    }}>
                      {formatNotificationTime(notification.created_at)}
                    </div>
                  </div>

                  {/* Delete Button */}
                  <button
                    onClick={(e) => handleDeleteNotification(e, notification.notification_id)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      padding: '4px',
                      borderRadius: '4px',
                      color: '#95a5a6',
                      fontSize: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                    title="Delete notification"
                  >
                    <span className="material-icons" style={{ fontSize: '16px' }}>close</span>
                  </button>
                </div>

                {/* Unread Indicator */}
                {!notification.read && (
                  <div style={{
                    position: 'absolute',
                    left: '4px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    width: '4px',
                    height: '4px',
                    backgroundColor: '#3869d4',
                    borderRadius: '50%'
                  }} />
                )}
              </div>
            ))}

            {/* Load More Button */}
            {hasNext && !loading && (
              <div style={{ padding: '12px 16px', textAlign: 'center' }}>
                <button
                  onClick={loadMore}
                  style={{
                    background: 'transparent',
                    color: '#3869d4',
                    border: '1px solid #3869d4',
                    borderRadius: '4px',
                    padding: '8px 16px',
                    fontSize: '0.9rem',
                    cursor: 'pointer'
                  }}
                >
                  Load More
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;

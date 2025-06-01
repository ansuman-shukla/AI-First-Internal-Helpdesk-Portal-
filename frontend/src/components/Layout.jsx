import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import NotificationBell from './NotificationBell';

const Layout = ({ children }) => {
  const { user, logout, isAuthenticated, isUser, isAgent, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (!isAuthenticated) {
    return children;
  }

  const isActive = (path) => {
    // Exact match for dashboard
    if (path === '/dashboard') {
      return location.pathname === '/dashboard' || location.pathname === '/';
    }
    // Exact match for tickets list
    if (path === '/tickets') {
      return location.pathname === '/tickets';
    }
    // Exact match for new ticket
    if (path === '/tickets/new') {
      return location.pathname === '/tickets/new';
    }
    // Exact match for admin
    if (path === '/admin') {
      return location.pathname === '/admin';
    }
    // For other paths, use startsWith
    return location.pathname.startsWith(path);
  };

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  // Navigation items based on user role
  const getNavigationItems = () => {
    const baseItems = [
      { path: '/dashboard', label: 'Dashboard', icon: 'dashboard' }
    ];

    if (isUser) {
      return [
        ...baseItems,
        { path: '/tickets', label: 'My Tickets', icon: 'article' },
        { path: '/tickets/new', label: 'New Ticket', icon: 'add_circle_outline' }
      ];
    }

    if (isAgent) {
      return [
        ...baseItems,
        { path: '/tickets', label: 'All Tickets', icon: 'article' },
        { path: '/tickets/new', label: 'New Ticket', icon: 'add_circle_outline' }
      ];
    }

    if (isAdmin) {
      return [
        ...baseItems,
        { path: '/tickets', label: 'All Tickets', icon: 'article' },
        { path: '/tickets/new', label: 'New Ticket', icon: 'add_circle_outline' },
        { path: '/admin', label: 'Admin Panel', icon: 'settings' }
      ];
    }

    return baseItems;
  };

  const navigationItems = getNavigationItems();

  return (
    <div className="sidebar-layout">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        {/* Sidebar Header */}
        <div className="sidebar-header">
          <Link to="/dashboard" className="sidebar-title">
            <span className="material-icons sidebar-icon">confirmation_number</span>
            {!sidebarCollapsed && <span>Tickets</span>}
          </Link>
          <button
            onClick={toggleSidebar}
            className="sidebar-toggle"
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? '»' : '«'}
          </button>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          {navigationItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`sidebar-nav-item ${isActive(item.path) ? 'active' : ''}`}
              title={sidebarCollapsed ? item.label : ''}
            >
              <span className="material-icons nav-icon">{item.icon}</span>
              {!sidebarCollapsed && <span className="nav-label">{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* User Info & Logout */}
        <div className="user-info">
          {!sidebarCollapsed && (
            <>
              <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--color-sidebar-text)',
                marginBottom: 'var(--spacing-xs)'
              }}>
                <strong>{user?.username}</strong>
              </div>
              <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'rgba(255, 255, 255, 0.7)',
                marginBottom: 'var(--spacing-sm)'
              }}>
                {user?.role?.replace('_', ' ').toUpperCase()}
              </div>
            </>
          )}
          <button
            onClick={handleLogout}
            className="logout-btn"
            title={sidebarCollapsed ? 'Logout' : ''}
          >
            <span className="material-icons">logout</span>
            {!sidebarCollapsed && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        {children}
      </main>
    </div>
  );
};

export default Layout;

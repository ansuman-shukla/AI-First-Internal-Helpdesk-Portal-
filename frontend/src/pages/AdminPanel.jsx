import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { dashboardAPI, adminAPI } from '../services/api';
import { Link } from 'react-router-dom';
import AnalyticsDashboard from '../components/AnalyticsDashboard';
import Ripple from '../components/Ripple';

const AdminPanel = () => {
  const { user, isAdmin } = useAuth();
  const [misuseReports, setMisuseReports] = useState([]);
  const [allMisuseReports, setAllMisuseReports] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [systemStatus, setSystemStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showSystemManagement, setShowSystemManagement] = useState(false);
  const [showMisuseReportsModal, setShowMisuseReportsModal] = useState(false);
  const [loadingAllReports, setLoadingAllReports] = useState(false);
  const [showDocumentUpload, setShowDocumentUpload] = useState(false);
  const [knowledgeBaseStats, setKnowledgeBaseStats] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(null);

  // Debug logging
  console.log('AdminPanel render - user:', user, 'isAdmin:', isAdmin, 'loading:', loading, 'error:', error);

  const fetchSystemStatus = async () => {
    try {
      const systemResponse = await adminAPI.getSystemManagement();
      setSystemStatus(systemResponse);
    } catch (error) {
      console.error('Failed to fetch system status:', error);
      setSystemStatus(null);
    }
  };

  const fetchAllMisuseReports = async () => {
    try {
      setLoadingAllReports(true);
      // Fetch all reports (not just unreviewed ones)
      const allReportsResponse = await adminAPI.getMisuseReports({ limit: 100, unreviewed_only: false });
      setAllMisuseReports(allReportsResponse.reports || []);
    } catch (error) {
      console.error('Failed to fetch all misuse reports:', error);
      setAllMisuseReports([]);
    } finally {
      setLoadingAllReports(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const analyticsResponse = await adminAPI.getAnalyticsOverview();
      const analyticsData = analyticsResponse.analytics || analyticsResponse;
      setAnalytics(analyticsData);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    }
  };

  const handleMarkReviewed = async (reportId) => {
    try {
      // Call the mark reviewed API
      await adminAPI.markMisuseReportReviewed(reportId);

      // Refresh the reports to show updated status
      await fetchAllMisuseReports();

      // Also refresh the main analytics to update the count
      await fetchAnalytics();
    } catch (error) {
      console.error('Failed to mark report as reviewed:', error);
      alert('Failed to mark report as reviewed. Please try again.');
    }
  };

  const handleSystemManagementClick = async () => {
    setShowSystemManagement(true);
    if (!systemStatus) {
      await fetchSystemStatus();
    }
  };

  const fetchKnowledgeBaseStats = async () => {
    try {
      const stats = await adminAPI.getKnowledgeBaseStats();
      setKnowledgeBaseStats(stats);
    } catch (error) {
      console.error('Failed to fetch knowledge base stats:', error);
      setKnowledgeBaseStats(null);
    }
  };

  const handleDocumentUpload = async (file, category, onUploadSuccess) => {
    try {
      setUploadProgress({ status: 'uploading', progress: 0 });

      const result = await adminAPI.uploadDocument(file, category);

      setUploadProgress({
        status: 'success',
        progress: 100,
        message: `Document uploaded successfully! ${result.vectors_stored} vectors created.`
      });

      // Refresh knowledge base stats
      await fetchKnowledgeBaseStats();

      // Call success callback to clear the file in modal
      if (onUploadSuccess) {
        onUploadSuccess();
      }

      // Clear progress after 3 seconds
      setTimeout(() => {
        setUploadProgress(null);
      }, 3000);

    } catch (error) {
      console.error('Document upload failed:', error);
      setUploadProgress({
        status: 'error',
        progress: 0,
        message: error.response?.data?.detail || 'Upload failed. Please try again.'
      });

      // Clear error after 5 seconds
      setTimeout(() => {
        setUploadProgress(null);
      }, 5000);
    }
  };

  const handleDocumentUploadClick = async () => {
    setShowDocumentUpload(true);
    if (!knowledgeBaseStats) {
      await fetchKnowledgeBaseStats();
    }
  };

  useEffect(() => {
    const fetchAdminData = async () => {
      try {
        setLoading(true);

        // Fetch admin dashboard data
        await dashboardAPI.getAdminHome();

        // Fetch recent misuse reports
        try {
          const misuseResponse = await adminAPI.getMisuseReports({ limit: 5, unreviewed_only: true });
          setMisuseReports(misuseResponse.reports || []);
        } catch (misuseError) {
          console.warn('Misuse reports not available:', misuseError);
          setMisuseReports([]);
        }

        // Fetch analytics overview
        try {
          const analyticsResponse = await adminAPI.getAnalyticsOverview();
          // Extract analytics from the response structure
          const analyticsData = analyticsResponse.analytics || analyticsResponse;
          setAnalytics(analyticsData);
        } catch (analyticsError) {
          console.warn('Analytics not available:', analyticsError);
          setAnalytics(null);
        }

      } catch (error) {
        console.error('Admin panel fetch error:', error);
        setError('Failed to load admin panel data');
      } finally {
        setLoading(false);
      }
    };

    if (isAdmin) {
      fetchAdminData();
    }
  }, [isAdmin]);

  // Redirect if not admin
  if (!isAdmin) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem', color: '#e74c3c' }}>
        <h2>Access Denied</h2>
        <p>You need admin privileges to access this page.</p>
        <p>Current user: {user?.username || 'Not logged in'}</p>
        <p>Is admin: {isAdmin ? 'Yes' : 'No'}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <Ripple color="#3869d4" size="medium" text="Loading admin panel..." textColor="#74787e" />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem', color: '#e74c3c' }}>
        <h2>Error</h2>
        <p>{error}</p>
        <button
          onClick={() => window.location.reload()}
          style={{
            padding: '0.5rem 1rem',
            background: '#3869d4',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            marginTop: '1rem'
          }}
        >
          Reload Page
        </button>
      </div>
    );
  }

  return (
    <div className="admin-panel-container">
      {/* Header Section */}
      <header className="admin-header">
        <div className="header-content">
          <h1 className="admin-title">Admin Panel</h1>
          <p className="admin-subtitle">
            System administration and monitoring dashboard
          </p>
        </div>
      </header>

      {/* Quick Actions */}
      <section className="admin-actions">
        <Link to="/tickets" className="admin-card admin-card-primary">
          <span className="material-icons admin-icon">receipt_long</span>
          <h3 className="admin-card-title">🎫 All Tickets</h3>
          <p className="admin-card-description">View and manage all support tickets</p>
        </Link>

        <div
          className="admin-card admin-card-warning"
          onClick={() => {
            setShowMisuseReportsModal(true);
            fetchAllMisuseReports();
          }}
        >
          <span className="material-icons admin-icon">warning</span>
          <h3 className="admin-card-title">⚠️ Misuse Reports</h3>
          <p className="admin-card-description">
            {analytics?.misuse_statistics?.unreviewed_reports || misuseReports.length} unreviewed reports
          </p>
        </div>

        <div
          className="admin-card admin-card-secondary"
          onClick={handleSystemManagementClick}
        >
          <span className="material-icons admin-icon">settings</span>
          <h3 className="admin-card-title">🔧 System Management</h3>
          <p className="admin-card-description">
            {systemStatus ?
              `System Health: ${systemStatus.overall_health?.toUpperCase() || 'UNKNOWN'}` :
              'Monitor system health and status'
            }
          </p>
        </div>

        <div
          className="admin-card admin-card-info admin-card-compact"
          onClick={handleDocumentUploadClick}
        >
          <span className="material-icons admin-icon-small">upload_file</span>
          <h3 className="admin-card-title-small">📄 Upload Documents</h3>
          <p className="admin-card-description-small">
            {knowledgeBaseStats ?
              `${knowledgeBaseStats.total_documents} docs, ${knowledgeBaseStats.total_vectors} vectors` :
              '0 documents, 0 vectors'
            }
          </p>
        </div>
      </section>

      {/* Analytics Dashboard */}
      <section className="analytics-dashboard-section">
        <AnalyticsDashboard />
      </section>



      {/* System Management Modal */}
      {showSystemManagement && (
        <div className="system-management-modal">
          <div className="modal-overlay" onClick={() => setShowSystemManagement(false)}></div>
          <div className="modal-content">
            <div className="modal-header">
              <h2 className="modal-title">System Management</h2>
              <button
                className="modal-close"
                onClick={() => setShowSystemManagement(false)}
              >
                <span className="material-icons">close</span>
              </button>
            </div>

            <div className="modal-body">
              {systemStatus ? (
                <>
                  {/* Overall Health Status */}
                  <div className="health-overview">
                    <div className={`health-status health-${systemStatus.overall_health}`}>
                      <span className="material-icons health-icon">
                        {systemStatus.overall_health === 'healthy' ? 'check_circle' : 'error'}
                      </span>
                      <div className="health-info">
                        <h3>Overall System Health</h3>
                        <p className="health-text">{systemStatus.overall_health?.toUpperCase()}</p>
                        <p className="health-timestamp">
                          Last checked: {new Date(systemStatus.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Component Status Grid */}
                  <div className="components-grid">
                    <h4 className="components-title">System Components</h4>

                    {/* Database Component */}
                    <div className={`component-card component-${systemStatus.components?.database?.status}`}>
                      <div className="component-header">
                        <span className="material-icons component-icon">storage</span>
                        <h5>Database</h5>
                        <span className={`status-badge status-${systemStatus.components?.database?.status}`}>
                          {systemStatus.components?.database?.status?.toUpperCase()}
                        </span>
                      </div>
                      <div className="component-details">
                        <p>Connected: {systemStatus.components?.database?.details?.connected ? 'Yes' : 'No'}</p>
                        <p>Database: {systemStatus.components?.database?.details?.database_name}</p>
                        <p>Ping: {systemStatus.components?.database?.details?.ping_ok ? 'OK' : 'Failed'}</p>
                      </div>
                    </div>

                    {/* AI Services Component */}
                    <div className={`component-card component-${systemStatus.components?.ai_services?.status}`}>
                      <div className="component-header">
                        <span className="material-icons component-icon">psychology</span>
                        <h5>AI Services</h5>
                        <span className={`status-badge status-${systemStatus.components?.ai_services?.status}`}>
                          {systemStatus.components?.ai_services?.status?.toUpperCase()}
                        </span>
                      </div>
                      <div className="component-details">
                        <p>Config Valid: {systemStatus.components?.ai_services?.details?.config_valid ? 'Yes' : 'No'}</p>
                        <p>Vector Store: {systemStatus.components?.ai_services?.details?.vector_store_initialized ? 'Ready' : 'Not Ready'}</p>
                        <p>HSA: {systemStatus.components?.ai_services?.details?.services_available?.hsa ? 'Available' : 'Unavailable'}</p>
                        <p>RAG: {systemStatus.components?.ai_services?.details?.services_available?.rag ? 'Available' : 'Unavailable'}</p>
                      </div>
                    </div>

                    {/* Scheduler Component */}
                    <div className={`component-card component-${systemStatus.components?.scheduler?.status}`}>
                      <div className="component-header">
                        <span className="material-icons component-icon">schedule</span>
                        <h5>Scheduler</h5>
                        <span className={`status-badge status-${systemStatus.components?.scheduler?.status}`}>
                          {systemStatus.components?.scheduler?.status?.toUpperCase()}
                        </span>
                      </div>
                      <div className="component-details">
                        <p>Running: {systemStatus.components?.scheduler?.details?.running ? 'Yes' : 'No'}</p>
                        <p>Jobs: {systemStatus.components?.scheduler?.details?.jobs_count || 0}</p>
                        <p>Misuse Detection: {systemStatus.components?.scheduler?.details?.misuse_detection_enabled ? 'Enabled' : 'Disabled'}</p>
                      </div>
                    </div>

                    {/* Webhooks Component */}
                    <div className={`component-card component-${systemStatus.components?.webhooks?.status}`}>
                      <div className="component-header">
                        <span className="material-icons component-icon">webhook</span>
                        <h5>Webhooks</h5>
                        <span className={`status-badge status-${systemStatus.components?.webhooks?.status}`}>
                          {systemStatus.components?.webhooks?.status?.toUpperCase()}
                        </span>
                      </div>
                      <div className="component-details">
                        <p>Responding: {systemStatus.components?.webhooks?.details?.responding ? 'Yes' : 'No'}</p>
                        <p>Health Check: {systemStatus.components?.webhooks?.details?.health_check_passed ? 'Passed' : 'Failed'}</p>
                      </div>
                    </div>
                  </div>

                  {/* Summary Statistics */}
                  <div className="system-summary">
                    <h4>System Summary</h4>
                    <div className="summary-stats">
                      <div className="summary-stat">
                        <span className="stat-number">{systemStatus.summary?.total_components || 0}</span>
                        <span className="stat-label">Total Components</span>
                      </div>
                      <div className="summary-stat healthy">
                        <span className="stat-number">{systemStatus.summary?.healthy_components || 0}</span>
                        <span className="stat-label">Healthy</span>
                      </div>
                      <div className="summary-stat unhealthy">
                        <span className="stat-number">{systemStatus.summary?.unhealthy_components || 0}</span>
                        <span className="stat-label">Unhealthy</span>
                      </div>
                      <div className="summary-stat error">
                        <span className="stat-number">{systemStatus.summary?.error_components || 0}</span>
                        <span className="stat-label">Errors</span>
                      </div>
                    </div>
                  </div>

                  {/* Refresh Button */}
                  <div className="modal-actions">
                    <button
                      className="refresh-button"
                      onClick={fetchSystemStatus}
                    >
                      <span className="material-icons">refresh</span>
                      Refresh Status
                    </button>
                  </div>
                </>
              ) : (
                <div className="loading-state">
                  <Ripple color="#3869d4" size="medium" text="Loading system status..." textColor="#74787e" />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Misuse Reports Modal */}
      {showMisuseReportsModal && (
        <div className="system-management-modal">
          <div className="modal-overlay" onClick={() => setShowMisuseReportsModal(false)}></div>
          <div className="modal-content">
            <div className="modal-header">
              <h2 className="modal-title">Misuse Reports</h2>
              <button
                className="modal-close"
                onClick={() => setShowMisuseReportsModal(false)}
              >
                <span className="material-icons">close</span>
              </button>
            </div>

            <div className="modal-body">
              {loadingAllReports ? (
                <div className="loading-state">
                  <Ripple color="#3869d4" size="medium" text="Loading all misuse reports..." textColor="#74787e" />
                </div>
              ) : (
                <div className="misuse-reports-container">
                  <div className="reports-overview">
                    <div className="reports-summary">
                      <div className="summary-item">
                        <span className="summary-number">{allMisuseReports.length}</span>
                        <span className="summary-label">Total Reports</span>
                      </div>
                      <div className="summary-item">
                        <span className="summary-number">
                          {allMisuseReports.filter(r => !r.admin_reviewed).length}
                        </span>
                        <span className="summary-label">Unreviewed</span>
                      </div>
                      <div className="summary-item">
                        <span className="summary-number">
                          {allMisuseReports.filter(r => r.severity_level === 'high' || r.severity === 'high').length}
                        </span>
                        <span className="summary-label">High Priority</span>
                      </div>
                    </div>
                  </div>

                  <div className="reports-list">
                    <h3>Flagged Users</h3>
                    {allMisuseReports.length > 0 ? (
                      <div className="reports-grid">
                        {allMisuseReports.map((report, index) => (
                        <div key={index} className="report-card">
                          <div className="report-header">
                            <div className="user-info">
                              <span className="material-icons">person</span>
                              <div className="user-details">
                                <span className="user-name">
                                  {report.user_name || `User ${report.user_id?.substring(0, 8)}...` || 'Unknown User'}
                                </span>
                                <span className="user-id">ID: {report.user_id?.substring(0, 8)}...</span>
                              </div>
                            </div>
                            <span className={`severity-badge-modal severity-${report.severity_level || report.severity || 'medium'}`}>
                              {(report.severity_level || report.severity || 'medium').toUpperCase()}
                            </span>
                          </div>

                          <div className="report-details">
                            <div className="detail-row">
                              <span className="detail-label">Violation Type:</span>
                              <span className="detail-value">
                                {report.misuse_type || report.violation_type || 'General Violation'}
                              </span>
                            </div>
                            <div className="detail-row">
                              <span className="detail-label">Detection Date:</span>
                              <span className="detail-value">
                                {report.detection_date ? new Date(report.detection_date).toLocaleDateString() : 'Unknown'}
                              </span>
                            </div>
                            <div className="detail-row">
                              <span className="detail-label">Status:</span>
                              <span className={`status-indicator ${report.admin_reviewed ? 'reviewed' : 'pending'}`}>
                                {report.admin_reviewed ? 'Reviewed' : 'Pending Review'}
                              </span>
                            </div>
                          </div>

                          <div className="report-actions">
                            {!report.admin_reviewed && (
                              <button
                                className="action-button review-button"
                                onClick={() => handleMarkReviewed(report.id)}
                              >
                                <span className="material-icons">check</span>
                                Mark Reviewed
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="no-reports">
                      <span className="material-icons">check_circle</span>
                      <p>No misuse reports found</p>
                    </div>
                  )}
                </div>

                  <div className="modal-actions">
                    <button className="refresh-button" onClick={fetchAllMisuseReports}>
                      <span className="material-icons">refresh</span>
                      Refresh Reports
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Document Upload Modal */}
      {showDocumentUpload && (
        <DocumentUploadModal
          onClose={() => setShowDocumentUpload(false)}
          onUpload={handleDocumentUpload}
          uploadProgress={uploadProgress}
          knowledgeBaseStats={knowledgeBaseStats}
        />
      )}
    </div>
  );
};

// Document Upload Modal Component
const DocumentUploadModal = ({ onClose, onUpload, uploadProgress, knowledgeBaseStats }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('general');
  const [dragOver, setDragOver] = useState(false);

  const categories = [
    { value: 'policy', label: 'Policy' },
    { value: 'procedure', label: 'Procedure' },
    { value: 'faq', label: 'FAQ' },
    { value: 'troubleshooting', label: 'Troubleshooting' },
    { value: 'general', label: 'General' }
  ];

  const supportedTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain'
  ];

  const handleFileSelect = (file) => {
    if (!supportedTypes.includes(file.type)) {
      alert('Unsupported file type. Please upload PDF, DOCX, PPTX, or TXT files.');
      return;
    }

    if (file.size > 50 * 1024 * 1024) { // 50MB limit
      alert('File too large. Maximum size is 50MB.');
      return;
    }

    setSelectedFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const clearSelectedFile = () => {
    setSelectedFile(null);
    // Also clear the file input element
    const fileInput = document.getElementById('file-input');
    if (fileInput) {
      fileInput.value = '';
    }
  };

  const handleUpload = () => {
    if (!selectedFile) {
      alert('Please select a file to upload.');
      return;
    }

    onUpload(selectedFile, selectedCategory, clearSelectedFile);
  };

  return (
    <div className="system-management-modal">
      <div className="modal-overlay" onClick={onClose}></div>
      <div className="modal-content">
        <div className="modal-header">
          <h2 className="modal-title">Upload Document to Knowledge Base</h2>
          <button className="modal-close" onClick={onClose}>
            <span className="material-icons">close</span>
          </button>
        </div>

        <div className="modal-body">
          {/* Knowledge Base Stats */}
          {knowledgeBaseStats && (
            <div className="kb-stats-overview">
              <h4>Current Knowledge Base</h4>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-number">{knowledgeBaseStats.total_documents}</span>
                  <span className="stat-label">Documents</span>
                </div>
                <div className="stat-item">
                  <span className="stat-number">{knowledgeBaseStats.total_vectors}</span>
                  <span className="stat-label">Vectors</span>
                </div>
                <div className="stat-item">
                  <span className="stat-number">{knowledgeBaseStats.total_size_mb}MB</span>
                  <span className="stat-label">Total Size</span>
                </div>
              </div>
            </div>
          )}

          {/* Upload Progress */}
          {uploadProgress && (
            <div className={`upload-progress upload-${uploadProgress.status}`}>
              <div className="progress-header">
                <span className="material-icons">
                  {uploadProgress.status === 'uploading' ? 'upload' :
                   uploadProgress.status === 'success' ? 'check_circle' : 'error'}
                </span>
                <span className="progress-text">
                  {uploadProgress.status === 'uploading' ? 'Uploading...' :
                   uploadProgress.status === 'success' ? 'Success!' : 'Error'}
                </span>
              </div>
              {uploadProgress.message && (
                <p className="progress-message">{uploadProgress.message}</p>
              )}
              {uploadProgress.status === 'uploading' && (
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${uploadProgress.progress}%` }}></div>
                </div>
              )}
            </div>
          )}

          {/* File Upload Area */}
          <div className="upload-section">
            <div
              className={`file-drop-zone ${dragOver ? 'drag-over' : ''} ${selectedFile ? 'has-file' : ''}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => document.getElementById('file-input').click()}
            >
              <input
                id="file-input"
                type="file"
                accept=".pdf,.docx,.pptx,.txt"
                onChange={(e) => e.target.files[0] && handleFileSelect(e.target.files[0])}
                style={{ display: 'none' }}
              />

              {selectedFile ? (
                <div className="selected-file">
                  <span className="material-icons file-icon">description</span>
                  <div className="file-info">
                    <span className="file-name">{selectedFile.name}</span>
                    <span className="file-size">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</span>
                  </div>
                  <button
                    className="remove-file"
                    onClick={(e) => {
                      e.stopPropagation();
                      clearSelectedFile();
                    }}
                  >
                    <span className="material-icons">close</span>
                  </button>
                </div>
              ) : (
                <div className="drop-zone-content">
                  <span className="material-icons upload-icon">cloud_upload</span>
                  <p className="drop-text">
                    <strong>Click to upload</strong> or drag and drop
                  </p>
                  <p className="file-types">PDF, DOCX, PPTX, TXT (max 50MB)</p>
                </div>
              )}
            </div>

            {/* Category Selection */}
            <div className="category-selection">
              <label htmlFor="category-select">Document Category:</label>
              <select
                id="category-select"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="category-select"
              >
                {categories.map(cat => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Upload Actions */}
          <div className="modal-actions">
            <button
              className="cancel-button"
              onClick={onClose}
              disabled={uploadProgress?.status === 'uploading'}
            >
              Cancel
            </button>
            <button
              className="upload-button"
              onClick={handleUpload}
              disabled={!selectedFile || uploadProgress?.status === 'uploading'}
            >
              <span className="material-icons">upload</span>
              Upload Document
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;

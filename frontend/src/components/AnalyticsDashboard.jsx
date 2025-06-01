import React, { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Doughnut, Bar, Line, Pie } from 'react-chartjs-2';
import { adminAPI } from '../services/api';
import Ripple from './Ripple';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const AnalyticsDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [timeSeriesData, setTimeSeriesData] = useState(null);
  const [performanceData, setPerformanceData] = useState(null);
  const [trendingTopics, setTrendingTopics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState(7);

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch all analytics data
      const [dashboard, timeSeries, performance, topics] = await Promise.all([
        adminAPI.getDashboardMetrics(selectedPeriod),
        adminAPI.getTimeSeriesAnalytics(selectedPeriod * 4, 'daily'),
        adminAPI.getPerformanceMetrics(selectedPeriod * 4),
        adminAPI.getTrendingTopics(selectedPeriod * 4, 10)
      ]);

      setDashboardData(dashboard.dashboard_metrics);
      setTimeSeriesData(timeSeries.time_series_analytics);
      setPerformanceData(performance.performance_metrics);
      setTrendingTopics(topics.topics_analysis);

      // Debug logging
      console.log('Trending topics data:', topics.topics_analysis);
      console.log('Number of trending topics:', topics.topics_analysis?.trending_topics?.length || 0);

    } catch (error) {
      console.error('Failed to fetch analytics data:', error);
      setError('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshTrendingTopics = async () => {
    try {
      setLoading(true);

      // Force refresh trending topics
      const topics = await adminAPI.getTrendingTopics(selectedPeriod * 4, 10, true);
      setTrendingTopics(topics.topics_analysis);

      console.log('Trending topics refreshed:', topics.cache_info);

    } catch (error) {
      console.error('Error refreshing trending topics:', error);
      setError('Failed to refresh trending topics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalyticsData();
  }, [selectedPeriod]);

  const handlePeriodChange = (days) => {
    setSelectedPeriod(days);
  };

  if (loading) {
    return (
      <div className="analytics-loading">
        <Ripple color="#3869d4" size="medium" text="Loading analytics dashboard..." textColor="#74787e" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics-error">
        <span className="material-icons error-icon">error</span>
        <p>{error}</p>
        <button onClick={fetchAnalyticsData} className="retry-button">
          <span className="material-icons">refresh</span>
          Retry
        </button>
      </div>
    );
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
      },
    },
  };

  const barChartOptions = {
    ...chartOptions,
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  };

  return (
    <div className="analytics-dashboard">
      {/* Header */}
      <div className="analytics-header">
        <h2>Analytics Dashboard</h2>
        <div className="period-selector">
          <button
            className={selectedPeriod === 7 ? 'active' : ''}
            onClick={() => handlePeriodChange(7)}
          >
            7 Days
          </button>
          <button
            className={selectedPeriod === 30 ? 'active' : ''}
            onClick={() => handlePeriodChange(30)}
          >
            30 Days
          </button>
          <button
            className={selectedPeriod === 90 ? 'active' : ''}
            onClick={() => handlePeriodChange(90)}
          >
            90 Days
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      {dashboardData?.kpis && (
        <div className="kpi-section">
          <div className="kpi-cards">
            <div className="kpi-card">
              <div className="kpi-icon">
                <span className="material-icons">confirmation_number</span>
              </div>
              <div className="kpi-content">
                <div className="kpi-value">{dashboardData.kpis.total_tickets}</div>
                <div className="kpi-label">Total Tickets</div>
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-icon">
                <span className="material-icons">pending_actions</span>
              </div>
              <div className="kpi-content">
                <div className="kpi-value">{dashboardData.kpis.open_tickets}</div>
                <div className="kpi-label">Open Tickets</div>
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-icon">
                <span className="material-icons">trending_up</span>
              </div>
              <div className="kpi-content">
                <div className="kpi-value">{dashboardData.kpis.resolution_rate}%</div>
                <div className="kpi-label">Resolution Rate</div>
              </div>
            </div>
            <div className="kpi-card">
              <div className="kpi-icon">
                <span className="material-icons">schedule</span>
              </div>
              <div className="kpi-content">
                <div className="kpi-value">{dashboardData.kpis.avg_resolution_time_hours}h</div>
                <div className="kpi-label">Avg Resolution Time</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <div className="charts-grid">
        {/* Status Distribution */}
        {dashboardData?.charts?.status_distribution && (
          <div className="chart-container">
            <h3>Ticket Status Distribution</h3>
            <div className="chart-wrapper">
              <Doughnut
                data={{
                  labels: dashboardData.charts.status_distribution.labels,
                  datasets: [{
                    data: dashboardData.charts.status_distribution.data,
                    backgroundColor: dashboardData.charts.status_distribution.colors,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                  }]
                }}
                options={chartOptions}
              />
            </div>
          </div>
        )}

        {/* Department Workload */}
        {dashboardData?.charts?.department_workload && (
          <div className="chart-container">
            <h3>Department Workload</h3>
            <div className="chart-wrapper">
              <Bar
                data={dashboardData.charts.department_workload}
                options={barChartOptions}
              />
            </div>
          </div>
        )}

        {/* Urgency Distribution */}
        {dashboardData?.charts?.urgency_distribution && (
          <div className="chart-container">
            <h3>Urgency Distribution</h3>
            <div className="chart-wrapper">
              <Pie
                data={{
                  labels: dashboardData.charts.urgency_distribution.labels,
                  datasets: [{
                    data: dashboardData.charts.urgency_distribution.data,
                    backgroundColor: dashboardData.charts.urgency_distribution.colors,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                  }]
                }}
                options={chartOptions}
              />
            </div>
          </div>
        )}

        {/* Daily Creation Trend */}
        {dashboardData?.charts?.daily_creation_trend && (
          <div className="chart-container chart-wide">
            <h3>Daily Ticket Creation Trend</h3>
            <div className="chart-wrapper">
              <Line
                data={{
                  labels: dashboardData.charts.daily_creation_trend.labels,
                  datasets: [{
                    label: dashboardData.charts.daily_creation_trend.label,
                    data: dashboardData.charts.daily_creation_trend.data,
                    borderColor: '#3869d4',
                    backgroundColor: 'rgba(56, 105, 212, 0.1)',
                    tension: 0.4,
                    fill: true
                  }]
                }}
                options={chartOptions}
              />
            </div>
          </div>
        )}
      </div>

      {/* Agent Performance Table */}
      {dashboardData?.charts?.agent_performance?.top_agents && (
        <div className="performance-section">
          <h3>Top Agent Performance</h3>
          <div className="performance-table">
            <table>
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Assigned</th>
                  <th>Resolved</th>
                  <th>Closed</th>
                  <th>Resolution Rate</th>
                </tr>
              </thead>
              <tbody>
                {dashboardData.charts.agent_performance.top_agents.map((agent, index) => (
                  <tr key={index}>
                    <td>{agent.agent_name}</td>
                    <td>{agent.assigned_tickets}</td>
                    <td>{agent.resolved_tickets}</td>
                    <td>{agent.closed_tickets}</td>
                    <td>
                      <span className="resolution-rate">{agent.resolution_rate}%</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Trending Topics */}
      <div className="trending-section">
        <div className="trending-header">
          <h3>Trending Issues</h3>
          <div className="trending-controls">
            {trendingTopics?.from_cache && (
              <span className="cache-indicator">
                <span className="material-icons">cached</span>
                Cached
              </span>
            )}
            <button
              className="refresh-btn"
              onClick={handleRefreshTrendingTopics}
              disabled={loading}
              title="Refresh trending topics"
            >
              <span className="material-icons">refresh</span>
            </button>
          </div>
        </div>
        <div className="trending-topics">
          {trendingTopics?.trending_topics && trendingTopics.trending_topics.length > 0 ? (
            trendingTopics.trending_topics.slice(0, 5).map((topic, index) => (
              <div key={index} className="topic-card">
                <div className="topic-rank">#{index + 1}</div>
                <div className="topic-content">
                  <div className="topic-title">{topic.topic}</div>
                  <div className="topic-stats">
                    <span className="topic-count">{topic.count} tickets</span>
                    <span className="topic-percentage">{topic.percentage}%</span>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="no-topics">
              <span className="material-icons">trending_up</span>
              <p>No trending topics available</p>
              <p className="no-topics-subtitle">
                {trendingTopics ?
                  `Analyzed ${trendingTopics.total_tickets_analyzed || 0} tickets` :
                  'Loading trending topics...'
                }
              </p>
            </div>
          )}
        </div>
        {trendingTopics?.generated_at && (
          <div className="trending-footer">
            <span className="last-updated">
              Last updated: {new Date(trendingTopics.generated_at).toLocaleString()}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalyticsDashboard;

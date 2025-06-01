"""
Analytics Service

Provides comprehensive analytics and reporting functionality for the admin panel.
Includes ticket volume analytics, resolution time tracking, user activity metrics,
and trending topics analysis using LLM integration.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.services.ai.trending_topics import extract_trending_topics

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for generating analytics and reports for admin dashboard"""
    
    def __init__(self):
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.tickets_collection = None
        self.users_collection = None
        self.misuse_reports_collection = None
        self.messages_collection = None
    
    async def _ensure_db_connection(self):
        """Ensure database connection is established"""
        if self.db is None:
            from app.core.database import connect_to_mongo
            try:
                await connect_to_mongo()
            except Exception as e:
                logger.warning(f"Could not establish MongoDB connection: {e}")

            self.db = get_database()
            if self.db is None:
                raise ConnectionError("Database connection not available")

            self.tickets_collection = self.db.tickets
            self.users_collection = self.db.users
            self.misuse_reports_collection = self.db.misuse_reports
            self.messages_collection = self.db.messages
    
    def _get_date_filter(self, days: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate date filter for MongoDB queries.
        
        Args:
            days: Number of days to look back (None for all-time)
            
        Returns:
            MongoDB date filter query
        """
        if days is None:
            return {}
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return {"created_at": {"$gte": cutoff_date}}
    
    async def get_overview_analytics(self, days: Optional[int] = None) -> Dict[str, Any]:
        """
        Get overview analytics for admin dashboard.

        Args:
            days: Number of days to analyze (None for all-time)

        Returns:
            Dictionary containing overview analytics
        """
        await self._ensure_db_connection()
        
        try:
            logger.info(f"Generating overview analytics for {days or 'all-time'} days")
            
            date_filter = self._get_date_filter(days)
            
            # Get ticket statistics
            ticket_stats = await self._get_ticket_volume_stats(date_filter)
            
            # Get user statistics
            user_stats = await self._get_user_activity_stats(date_filter)
            
            # Get misuse statistics
            misuse_stats = await self._get_misuse_stats(date_filter)
            
            # Get resolution time statistics
            resolution_stats = await self._get_resolution_time_stats(date_filter)
            
            overview = {
                "period": f"Last {days} days" if days else "All time",
                "generated_at": datetime.utcnow().isoformat(),
                "ticket_statistics": ticket_stats,
                "user_statistics": user_stats,
                "misuse_statistics": misuse_stats,
                "resolution_statistics": resolution_stats
            }
            
            logger.info("Overview analytics generated successfully")
            return overview
            
        except Exception as e:
            logger.error(f"Error generating overview analytics: {str(e)}")
            raise
    
    async def _get_ticket_volume_stats(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Get ticket volume statistics"""
        pipeline = [
            {"$match": date_filter},
            {
                "$group": {
                    "_id": None,
                    "total_tickets": {"$sum": 1},
                    "open_tickets": {
                        "$sum": {"$cond": [{"$eq": ["$status", "open"]}, 1, 0]}
                    },
                    "assigned_tickets": {
                        "$sum": {"$cond": [{"$eq": ["$status", "assigned"]}, 1, 0]}
                    },
                    "resolved_tickets": {
                        "$sum": {"$cond": [{"$eq": ["$status", "resolved"]}, 1, 0]}
                    },
                    "closed_tickets": {
                        "$sum": {"$cond": [{"$eq": ["$status", "closed"]}, 1, 0]}
                    },
                    "it_tickets": {
                        "$sum": {"$cond": [{"$eq": ["$department", "IT"]}, 1, 0]}
                    },
                    "hr_tickets": {
                        "$sum": {"$cond": [{"$eq": ["$department", "HR"]}, 1, 0]}
                    },
                    "high_urgency": {
                        "$sum": {"$cond": [{"$eq": ["$urgency", "high"]}, 1, 0]}
                    },
                    "medium_urgency": {
                        "$sum": {"$cond": [{"$eq": ["$urgency", "medium"]}, 1, 0]}
                    },
                    "low_urgency": {
                        "$sum": {"$cond": [{"$eq": ["$urgency", "low"]}, 1, 0]}
                    },
                    "flagged_tickets": {
                        "$sum": {"$cond": [{"$eq": ["$misuse_flag", True]}, 1, 0]}
                    }
                }
            }
        ]

        result = await self.tickets_collection.aggregate(pipeline).to_list(1)
        stats = result[0] if result else {
            "total_tickets": 0, "open_tickets": 0, "assigned_tickets": 0,
            "resolved_tickets": 0, "closed_tickets": 0, "it_tickets": 0,
            "hr_tickets": 0, "high_urgency": 0, "medium_urgency": 0,
            "low_urgency": 0, "flagged_tickets": 0
        }

        # Remove the _id field if it exists
        if "_id" in stats:
            del stats["_id"]

        return stats
    
    async def _get_user_activity_stats(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Get user activity statistics"""
        # Total active users (users who created tickets in the period)
        pipeline = [
            {"$match": date_filter},
            {"$group": {"_id": "$user_id"}},
            {"$count": "active_users"}
        ]
        
        active_users_result = await self.tickets_collection.aggregate(pipeline).to_list(1)
        active_users = active_users_result[0]["active_users"] if active_users_result else 0
        
        # Total registered users
        total_users = await self.users_collection.count_documents({})
        
        return {
            "total_registered_users": total_users,
            "active_users": active_users,
            "activity_rate": round((active_users / total_users * 100), 2) if total_users > 0 else 0
        }
    
    async def _get_misuse_stats(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Get misuse statistics"""
        # Adjust date filter for misuse reports (use detection_date instead of created_at)
        misuse_date_filter = {}
        if "created_at" in date_filter:
            misuse_date_filter["detection_date"] = date_filter["created_at"]
        
        pipeline = [
            {"$match": misuse_date_filter},
            {
                "$group": {
                    "_id": None,
                    "total_reports": {"$sum": 1},
                    "unreviewed_reports": {
                        "$sum": {"$cond": [{"$eq": ["$admin_reviewed", False]}, 1, 0]}
                    },
                    "high_severity": {
                        "$sum": {"$cond": [{"$eq": ["$severity_level", "high"]}, 1, 0]}
                    },
                    "medium_severity": {
                        "$sum": {"$cond": [{"$eq": ["$severity_level", "medium"]}, 1, 0]}
                    },
                    "low_severity": {
                        "$sum": {"$cond": [{"$eq": ["$severity_level", "low"]}, 1, 0]}
                    }
                }
            }
        ]
        
        result = await self.misuse_reports_collection.aggregate(pipeline).to_list(1)
        return result[0] if result else {
            "total_reports": 0, "unreviewed_reports": 0,
            "high_severity": 0, "medium_severity": 0, "low_severity": 0
        }
    
    async def _get_resolution_time_stats(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Get resolution time statistics"""
        # Only include closed tickets for resolution time calculation
        filter_query = {**date_filter, "status": "closed", "closed_at": {"$ne": None}}
        
        pipeline = [
            {"$match": filter_query},
            {
                "$addFields": {
                    "resolution_time_hours": {
                        "$divide": [
                            {"$subtract": ["$closed_at", "$created_at"]},
                            1000 * 60 * 60  # Convert milliseconds to hours
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": "$department",
                    "avg_resolution_time": {"$avg": "$resolution_time_hours"},
                    "min_resolution_time": {"$min": "$resolution_time_hours"},
                    "max_resolution_time": {"$max": "$resolution_time_hours"},
                    "total_resolved": {"$sum": 1}
                }
            }
        ]
        
        results = await self.tickets_collection.aggregate(pipeline).to_list(10)
        
        # Format results
        resolution_stats = {
            "overall": {"avg_hours": 0, "total_resolved": 0},
            "by_department": {}
        }
        
        total_time = 0
        total_resolved = 0
        
        for result in results:
            dept = result["_id"]
            avg_time = round(result["avg_resolution_time"], 2)
            resolved_count = result["total_resolved"]
            
            resolution_stats["by_department"][dept] = {
                "avg_resolution_hours": avg_time,
                "min_resolution_hours": round(result["min_resolution_time"], 2),
                "max_resolution_hours": round(result["max_resolution_time"], 2),
                "total_resolved": resolved_count
            }
            
            total_time += result["avg_resolution_time"] * resolved_count
            total_resolved += resolved_count
        
        if total_resolved > 0:
            resolution_stats["overall"]["avg_hours"] = round(total_time / total_resolved, 2)
            resolution_stats["overall"]["total_resolved"] = total_resolved
        
        return resolution_stats


    async def get_trending_topics(self, days: Optional[int] = 30, limit: int = 10, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get trending topics from cache or generate fresh analysis.

        This method now uses caching to avoid expensive LLM analysis on every request.
        Topics are cached for 24 hours and refreshed via scheduled jobs.

        Args:
            days: Number of days to analyze (default: 30)
            limit: Maximum number of topics to return
            force_refresh: Force refresh even if cache is valid

        Returns:
            Dictionary containing trending topics with counts (cached or fresh)
        """
        try:
            logger.info(f"Getting trending topics for last {days} days (force_refresh: {force_refresh})")

            # Use the cache service to get trending topics
            from app.services.trending_topics_cache import trending_topics_cache_service

            result = await trending_topics_cache_service.get_trending_topics(
                days=days,
                limit=limit,
                force_refresh=force_refresh
            )

            # Add cache indicator to the result
            if not result.get("cache_refresh"):
                result["from_cache"] = True
                logger.info("Returned trending topics from cache")
            else:
                result["from_cache"] = False
                logger.info("Returned fresh trending topics analysis")

            return result

        except Exception as e:
            logger.error(f"Error getting trending topics: {str(e)}")
            raise

    async def get_flagged_users_analytics(self, days: Optional[int] = None) -> Dict[str, Any]:
        """
        Get analytics about flagged users and their violations.

        Args:
            days: Number of days to analyze (None for all-time)

        Returns:
            Dictionary containing flagged users analytics
        """
        await self._ensure_db_connection()

        try:
            logger.info(f"Generating flagged users analytics for {days or 'all-time'} days")

            # Adjust date filter for misuse reports
            date_filter = {}
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                date_filter["detection_date"] = {"$gte": cutoff_date}

            # Get flagged users with violation details
            pipeline = [
                {"$match": date_filter},
                {
                    "$group": {
                        "_id": "$user_id",
                        "total_violations": {"$sum": 1},
                        "violation_types": {"$addToSet": "$misuse_type"},
                        "severity_levels": {"$addToSet": "$severity_level"},
                        "latest_violation": {"$max": "$detection_date"},
                        "unreviewed_count": {
                            "$sum": {"$cond": [{"$eq": ["$admin_reviewed", False]}, 1, 0]}
                        }
                    }
                },
                {"$sort": {"total_violations": -1}},
                {"$limit": 50}  # Top 50 flagged users
            ]

            flagged_users = await self.misuse_reports_collection.aggregate(pipeline).to_list(50)

            # Get user details for flagged users
            user_ids = [user["_id"] for user in flagged_users]
            users_cursor = self.users_collection.find(
                {"_id": {"$in": user_ids}},
                {"username": 1, "email": 1, "created_at": 1}
            )
            users_dict = {str(user["_id"]): user async for user in users_cursor}

            # Combine user details with violation data
            detailed_flagged_users = []
            for user_data in flagged_users:
                user_id = str(user_data["_id"])
                user_info = users_dict.get(user_id, {})

                detailed_flagged_users.append({
                    "user_id": user_id,
                    "username": user_info.get("username", "Unknown"),
                    "email": user_info.get("email", "Unknown"),
                    "total_violations": user_data["total_violations"],
                    "violation_types": user_data["violation_types"],
                    "severity_levels": user_data["severity_levels"],
                    "latest_violation": user_data["latest_violation"].isoformat(),
                    "unreviewed_count": user_data["unreviewed_count"],
                    "user_since": user_info.get("created_at", datetime.utcnow()).isoformat()
                })

            # Get violation type summary
            violation_summary_pipeline = [
                {"$match": date_filter},
                {
                    "$group": {
                        "_id": "$misuse_type",
                        "count": {"$sum": 1},
                        "unique_users": {"$addToSet": "$user_id"}
                    }
                },
                {
                    "$project": {
                        "violation_type": "$_id",
                        "total_violations": "$count",
                        "unique_users_count": {"$size": "$unique_users"}
                    }
                },
                {"$sort": {"total_violations": -1}}
            ]

            violation_summary = await self.misuse_reports_collection.aggregate(violation_summary_pipeline).to_list(10)

            result = {
                "period": f"Last {days} days" if days else "All time",
                "total_flagged_users": len(detailed_flagged_users),
                "flagged_users": detailed_flagged_users,
                "violation_summary": violation_summary,
                "generated_at": datetime.utcnow().isoformat()
            }

            logger.info(f"Generated flagged users analytics: {len(detailed_flagged_users)} users")
            return result

        except Exception as e:
            logger.error(f"Error generating flagged users analytics: {str(e)}")
            raise

    async def get_user_activity_analytics(self, days: Optional[int] = 30) -> Dict[str, Any]:
        """
        Get detailed user activity analytics.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary containing user activity analytics
        """
        await self._ensure_db_connection()

        try:
            logger.info(f"Generating user activity analytics for last {days} days")

            date_filter = self._get_date_filter(days)

            # Get most active users by ticket count
            pipeline = [
                {"$match": date_filter},
                {
                    "$group": {
                        "_id": "$user_id",
                        "ticket_count": {"$sum": 1},
                        "open_tickets": {
                            "$sum": {"$cond": [{"$eq": ["$status", "open"]}, 1, 0]}
                        },
                        "resolved_tickets": {
                            "$sum": {"$cond": [{"$eq": ["$status", "resolved"]}, 1, 0]}
                        },
                        "closed_tickets": {
                            "$sum": {"$cond": [{"$eq": ["$status", "closed"]}, 1, 0]}
                        },
                        "latest_ticket": {"$max": "$created_at"}
                    }
                },
                {"$sort": {"ticket_count": -1}},
                {"$limit": 20}  # Top 20 most active users
            ]

            active_users = await self.tickets_collection.aggregate(pipeline).to_list(20)

            # Get user details
            user_ids = [user["_id"] for user in active_users]
            users_cursor = self.users_collection.find(
                {"_id": {"$in": user_ids}},
                {"username": 1, "email": 1, "role": 1}
            )
            users_dict = {str(user["_id"]): user async for user in users_cursor}

            # Combine user details with activity data
            detailed_active_users = []
            for user_data in active_users:
                user_id = str(user_data["_id"])
                user_info = users_dict.get(user_id, {})

                detailed_active_users.append({
                    "user_id": user_id,
                    "username": user_info.get("username", "Unknown"),
                    "email": user_info.get("email", "Unknown"),
                    "role": user_info.get("role", "user"),
                    "ticket_count": user_data["ticket_count"],
                    "open_tickets": user_data["open_tickets"],
                    "resolved_tickets": user_data["resolved_tickets"],
                    "closed_tickets": user_data["closed_tickets"],
                    "latest_ticket": user_data["latest_ticket"].isoformat(),
                    "resolution_rate": round(
                        (user_data["closed_tickets"] / user_data["ticket_count"] * 100), 2
                    ) if user_data["ticket_count"] > 0 else 0
                })

            result = {
                "period": f"Last {days} days",
                "most_active_users": detailed_active_users,
                "generated_at": datetime.utcnow().isoformat()
            }

            logger.info(f"Generated user activity analytics: {len(detailed_active_users)} users")
            return result

        except Exception as e:
            logger.error(f"Error generating user activity analytics: {str(e)}")
            raise

    async def get_dashboard_metrics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get comprehensive dashboard metrics optimized for interactive visualizations.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary containing dashboard metrics for charts
        """
        await self._ensure_db_connection()

        try:
            logger.info(f"Generating dashboard metrics for last {days} days")

            date_filter = self._get_date_filter(days)

            # Get basic overview
            overview = await self.get_overview_analytics(days)

            # Get ticket status distribution for donut chart
            status_distribution = await self._get_status_distribution(date_filter)

            # Get department workload for bar chart
            department_workload = await self._get_department_workload(date_filter)

            # Get urgency distribution for pie chart
            urgency_distribution = await self._get_urgency_distribution(date_filter)

            # Get daily ticket creation for line chart
            daily_creation = await self._get_daily_ticket_creation(days)

            # Get agent performance summary
            agent_performance = await self._get_agent_performance_summary(date_filter)

            # Calculate key performance indicators
            kpis = await self._calculate_kpis(date_filter)

            dashboard_metrics = {
                "period": f"Last {days} days",
                "generated_at": datetime.utcnow().isoformat(),
                "overview": overview,
                "charts": {
                    "status_distribution": status_distribution,
                    "department_workload": department_workload,
                    "urgency_distribution": urgency_distribution,
                    "daily_creation_trend": daily_creation,
                    "agent_performance": agent_performance
                },
                "kpis": kpis
            }

            logger.info(f"Dashboard metrics generated successfully for {days} days")
            return dashboard_metrics

        except Exception as e:
            logger.error(f"Error generating dashboard metrics: {str(e)}")
            raise

    async def get_time_series_analytics(self, days: int = 30, granularity: str = "daily") -> Dict[str, Any]:
        """
        Get time-series analytics for trend visualization.

        Args:
            days: Number of days to analyze
            granularity: Time granularity (daily, weekly, monthly)

        Returns:
            Dictionary containing time-series data
        """
        await self._ensure_db_connection()

        try:
            logger.info(f"Generating time-series analytics for {days} days with {granularity} granularity")

            # Get ticket creation trends
            creation_trends = await self._get_ticket_creation_trends(days, granularity)

            # Get resolution trends
            resolution_trends = await self._get_ticket_resolution_trends(days, granularity)

            # Get response time trends
            response_time_trends = await self._get_response_time_trends(days, granularity)

            # Get user activity trends
            user_activity_trends = await self._get_user_activity_trends(days, granularity)

            time_series_data = {
                "period": f"Last {days} days",
                "granularity": granularity,
                "generated_at": datetime.utcnow().isoformat(),
                "trends": {
                    "ticket_creation": creation_trends,
                    "ticket_resolution": resolution_trends,
                    "response_times": response_time_trends,
                    "user_activity": user_activity_trends
                }
            }

            logger.info(f"Time-series analytics generated successfully")
            return time_series_data

        except Exception as e:
            logger.error(f"Error generating time-series analytics: {str(e)}")
            raise

    async def get_performance_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get performance metrics for agents and departments.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary containing performance metrics
        """
        await self._ensure_db_connection()

        try:
            logger.info(f"Generating performance metrics for last {days} days")

            date_filter = self._get_date_filter(days)

            # Get agent performance details
            agent_performance = await self._get_detailed_agent_performance(date_filter)

            # Get department efficiency metrics
            department_efficiency = await self._get_department_efficiency(date_filter)

            # Get SLA compliance metrics
            sla_compliance = await self._get_sla_compliance(date_filter)

            # Get customer satisfaction metrics
            satisfaction_metrics = await self._get_satisfaction_metrics(date_filter)

            performance_metrics = {
                "period": f"Last {days} days",
                "generated_at": datetime.utcnow().isoformat(),
                "agent_performance": agent_performance,
                "department_efficiency": department_efficiency,
                "sla_compliance": sla_compliance,
                "customer_satisfaction": satisfaction_metrics
            }

            logger.info(f"Performance metrics generated successfully")
            return performance_metrics

        except Exception as e:
            logger.error(f"Error generating performance metrics: {str(e)}")
            raise

    # Helper methods for dashboard metrics
    async def _get_status_distribution(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Get ticket status distribution for donut chart"""
        pipeline = [
            {"$match": date_filter},
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"count": -1}}
        ]

        results = await self.tickets_collection.aggregate(pipeline).to_list(10)

        labels = []
        data = []
        colors = {
            "open": "#ff6b6b",
            "assigned": "#4ecdc4",
            "resolved": "#45b7d1",
            "closed": "#96ceb4"
        }

        for result in results:
            status = result["_id"]
            count = result["count"]
            labels.append(status.title())
            data.append(count)

        return {
            "labels": labels,
            "data": data,
            "colors": [colors.get(label.lower(), "#95a5a6") for label in labels],
            "chart_type": "doughnut"
        }

    async def _get_department_workload(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Get department workload for bar chart"""
        pipeline = [
            {"$match": date_filter},
            {
                "$group": {
                    "_id": "$department",
                    "total_tickets": {"$sum": 1},
                    "open_tickets": {
                        "$sum": {"$cond": [{"$eq": ["$status", "open"]}, 1, 0]}
                    },
                    "assigned_tickets": {
                        "$sum": {"$cond": [{"$eq": ["$status", "assigned"]}, 1, 0]}
                    },
                    "resolved_tickets": {
                        "$sum": {"$cond": [{"$eq": ["$status", "resolved"]}, 1, 0]}
                    }
                }
            }
        ]

        results = await self.tickets_collection.aggregate(pipeline).to_list(10)

        departments = []
        total_data = []
        open_data = []
        assigned_data = []
        resolved_data = []

        for result in results:
            dept = result["_id"] or "Unassigned"
            departments.append(dept)
            total_data.append(result["total_tickets"])
            open_data.append(result["open_tickets"])
            assigned_data.append(result["assigned_tickets"])
            resolved_data.append(result["resolved_tickets"])

        return {
            "labels": departments,
            "datasets": [
                {
                    "label": "Total",
                    "data": total_data,
                    "backgroundColor": "#3869d4"
                },
                {
                    "label": "Open",
                    "data": open_data,
                    "backgroundColor": "#ff6b6b"
                },
                {
                    "label": "Assigned",
                    "data": assigned_data,
                    "backgroundColor": "#4ecdc4"
                },
                {
                    "label": "Resolved",
                    "data": resolved_data,
                    "backgroundColor": "#96ceb4"
                }
            ],
            "chart_type": "bar"
        }

    async def _get_urgency_distribution(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Get urgency distribution for pie chart"""
        pipeline = [
            {"$match": date_filter},
            {
                "$group": {
                    "_id": "$urgency",
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"count": -1}}
        ]

        results = await self.tickets_collection.aggregate(pipeline).to_list(10)

        labels = []
        data = []
        colors = {
            "high": "#e74c3c",
            "medium": "#f39c12",
            "low": "#27ae60"
        }

        for result in results:
            urgency = result["_id"]
            count = result["count"]
            labels.append(urgency.title())
            data.append(count)

        return {
            "labels": labels,
            "data": data,
            "colors": [colors.get(label.lower(), "#95a5a6") for label in labels],
            "chart_type": "pie"
        }

    async def _get_daily_ticket_creation(self, days: int) -> Dict[str, Any]:
        """Get daily ticket creation trend for line chart"""
        from datetime import datetime, timezone, timedelta

        # Generate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": start_date, "$lte": end_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at"
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]

        results = await self.tickets_collection.aggregate(pipeline).to_list(days + 1)

        # Create complete date range with zeros for missing days
        labels = []
        data = []
        result_dict = {result["_id"]: result["count"] for result in results}

        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            labels.append(date_str)
            data.append(result_dict.get(date_str, 0))
            current_date += timedelta(days=1)

        return {
            "labels": labels,
            "data": data,
            "chart_type": "line",
            "label": "Daily Ticket Creation"
        }

    async def _get_agent_performance_summary(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Get agent performance summary for dashboard"""
        # Get tickets assigned to agents
        pipeline = [
            {"$match": {**date_filter, "assignee_id": {"$ne": None}}},
            {
                "$group": {
                    "_id": "$assignee_id",
                    "assigned_tickets": {"$sum": 1},
                    "resolved_tickets": {
                        "$sum": {"$cond": [{"$eq": ["$status", "resolved"]}, 1, 0]}
                    },
                    "closed_tickets": {
                        "$sum": {"$cond": [{"$eq": ["$status", "closed"]}, 1, 0]}
                    }
                }
            },
            {"$sort": {"assigned_tickets": -1}},
            {"$limit": 10}  # Top 10 agents
        ]

        results = await self.tickets_collection.aggregate(pipeline).to_list(10)

        # Get agent names
        agent_ids = [str(result["_id"]) for result in results]
        agents_cursor = self.users_collection.find(
            {"_id": {"$in": [ObjectId(aid) for aid in agent_ids if aid]}}
        )
        agents = await agents_cursor.to_list(100)
        agents_dict = {str(agent["_id"]): agent for agent in agents}

        agent_data = []
        for result in results:
            agent_id = str(result["_id"])
            agent_info = agents_dict.get(agent_id, {})

            resolution_rate = 0
            if result["assigned_tickets"] > 0:
                resolution_rate = round(
                    (result["closed_tickets"] / result["assigned_tickets"]) * 100, 1
                )

            agent_data.append({
                "agent_name": agent_info.get("username", "Unknown Agent"),
                "assigned_tickets": result["assigned_tickets"],
                "resolved_tickets": result["resolved_tickets"],
                "closed_tickets": result["closed_tickets"],
                "resolution_rate": resolution_rate
            })

        return {
            "top_agents": agent_data,
            "chart_type": "table"
        }

    async def _calculate_kpis(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate key performance indicators"""
        # Get basic ticket counts
        total_tickets = await self.tickets_collection.count_documents(date_filter)
        open_tickets = await self.tickets_collection.count_documents({**date_filter, "status": "open"})
        resolved_tickets = await self.tickets_collection.count_documents({**date_filter, "status": "resolved"})
        closed_tickets = await self.tickets_collection.count_documents({**date_filter, "status": "closed"})

        # Calculate resolution rate
        resolution_rate = 0
        if total_tickets > 0:
            resolution_rate = round(((resolved_tickets + closed_tickets) / total_tickets) * 100, 1)

        # Get average resolution time for closed tickets
        avg_resolution_time = 0
        pipeline = [
            {"$match": {**date_filter, "status": "closed", "closed_at": {"$ne": None}}},
            {
                "$addFields": {
                    "resolution_time_hours": {
                        "$divide": [
                            {"$subtract": ["$closed_at", "$created_at"]},
                            1000 * 60 * 60  # Convert to hours
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_resolution_time": {"$avg": "$resolution_time_hours"}
                }
            }
        ]

        resolution_result = await self.tickets_collection.aggregate(pipeline).to_list(1)
        if resolution_result:
            avg_resolution_time = round(resolution_result[0]["avg_resolution_time"], 1)

        # Get user satisfaction (from feedback)
        satisfaction_pipeline = [
            {"$match": {**date_filter, "feedback": {"$ne": None}}},
            {"$count": "feedback_count"}
        ]

        feedback_result = await self.tickets_collection.aggregate(satisfaction_pipeline).to_list(1)
        feedback_count = feedback_result[0]["feedback_count"] if feedback_result else 0

        return {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "resolution_rate": resolution_rate,
            "avg_resolution_time_hours": avg_resolution_time,
            "tickets_with_feedback": feedback_count,
            "backlog_size": open_tickets
        }

    # Stub methods for time-series and performance analytics
    async def _get_ticket_creation_trends(self, days: int, granularity: str) -> Dict[str, Any]:
        """Get ticket creation trends over time"""
        # This is a stub implementation - would be enhanced with real time-series logic
        return {
            "labels": [f"Day {i}" for i in range(1, min(days, 30) + 1)],
            "data": [5, 8, 12, 7, 15, 10, 9] * (days // 7 + 1),
            "chart_type": "line",
            "label": "Ticket Creation Trend"
        }

    async def _get_ticket_resolution_trends(self, days: int, granularity: str) -> Dict[str, Any]:
        """Get ticket resolution trends over time"""
        # This is a stub implementation
        return {
            "labels": [f"Day {i}" for i in range(1, min(days, 30) + 1)],
            "data": [3, 6, 8, 5, 12, 8, 7] * (days // 7 + 1),
            "chart_type": "line",
            "label": "Ticket Resolution Trend"
        }

    async def _get_response_time_trends(self, days: int, granularity: str) -> Dict[str, Any]:
        """Get response time trends over time"""
        # This is a stub implementation
        return {
            "labels": [f"Day {i}" for i in range(1, min(days, 30) + 1)],
            "data": [2.5, 3.1, 1.8, 2.9, 2.2, 3.5, 2.7] * (days // 7 + 1),
            "chart_type": "line",
            "label": "Average Response Time (hours)"
        }

    async def _get_user_activity_trends(self, days: int, granularity: str) -> Dict[str, Any]:
        """Get user activity trends over time"""
        # This is a stub implementation
        return {
            "labels": [f"Day {i}" for i in range(1, min(days, 30) + 1)],
            "data": [25, 32, 28, 35, 40, 38, 33] * (days // 7 + 1),
            "chart_type": "line",
            "label": "Active Users"
        }

    async def _get_detailed_agent_performance(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed agent performance metrics"""
        # This is a stub implementation
        return {
            "agents": [
                {
                    "name": "John Doe",
                    "tickets_handled": 45,
                    "avg_resolution_time": 2.3,
                    "satisfaction_score": 4.2,
                    "department": "IT"
                },
                {
                    "name": "Jane Smith",
                    "tickets_handled": 38,
                    "avg_resolution_time": 1.8,
                    "satisfaction_score": 4.5,
                    "department": "HR"
                }
            ]
        }

    async def _get_department_efficiency(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Get department efficiency metrics"""
        # This is a stub implementation
        return {
            "departments": [
                {
                    "name": "IT",
                    "total_tickets": 120,
                    "avg_resolution_time": 2.5,
                    "first_contact_resolution": 75,
                    "escalation_rate": 15
                },
                {
                    "name": "HR",
                    "total_tickets": 85,
                    "avg_resolution_time": 1.8,
                    "first_contact_resolution": 82,
                    "escalation_rate": 8
                }
            ]
        }

    async def _get_sla_compliance(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Get SLA compliance metrics"""
        # This is a stub implementation
        return {
            "overall_compliance": 87.5,
            "by_urgency": {
                "high": 92.0,
                "medium": 85.5,
                "low": 89.2
            },
            "by_department": {
                "IT": 85.0,
                "HR": 90.0
            }
        }

    async def _get_satisfaction_metrics(self, date_filter: Dict[str, Any]) -> Dict[str, Any]:
        """Get customer satisfaction metrics"""
        # This is a stub implementation
        return {
            "overall_satisfaction": 4.2,
            "total_feedback": 156,
            "satisfaction_distribution": {
                "5_star": 45,
                "4_star": 62,
                "3_star": 28,
                "2_star": 15,
                "1_star": 6
            }
        }


# Create singleton instance
analytics_service = AnalyticsService()

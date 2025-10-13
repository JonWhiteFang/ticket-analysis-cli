"""Analysis models for ticket analysis results and search criteria.

This module contains data models for analysis operations including search criteria,
analysis results, and related data structures used throughout the analysis pipeline.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from .ticket import TicketStatus, TicketSeverity


@dataclass
class SearchCriteria:
    """Search criteria for ticket queries.
    
    Defines the parameters used to filter and search for tickets in the system.
    All criteria are optional and can be combined for complex queries.
    
    Attributes:
        status: List of ticket statuses to filter by
        severity: List of ticket severities to filter by
        assignee: Username of the assignee to filter by
        resolver_group: Resolver group name to filter by
        created_after: Only include tickets created after this date
        created_before: Only include tickets created before this date
        updated_after: Only include tickets updated after this date
        updated_before: Only include tickets updated before this date
        tags: List of tags that tickets must have
        search_text: Free text search in title and description
        max_results: Maximum number of results to return
        offset: Number of results to skip (for pagination)
    """
    status: Optional[List[TicketStatus]] = None
    severity: Optional[List[TicketSeverity]] = None
    assignee: Optional[str] = None
    resolver_group: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    updated_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None
    tags: Optional[List[str]] = None
    search_text: Optional[str] = None
    max_results: int = 1000
    offset: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search criteria to dictionary for API calls.
        
        Returns:
            Dictionary representation suitable for API requests.
        """
        criteria = {}
        
        if self.status:
            criteria["status"] = [s.value for s in self.status]
        if self.severity:
            criteria["severity"] = [s.value for s in self.severity]
        if self.assignee:
            criteria["assignee"] = self.assignee
        if self.resolver_group:
            criteria["resolver_group"] = self.resolver_group
        if self.created_after:
            criteria["created_after"] = self.created_after.isoformat()
        if self.created_before:
            criteria["created_before"] = self.created_before.isoformat()
        if self.updated_after:
            criteria["updated_after"] = self.updated_after.isoformat()
        if self.updated_before:
            criteria["updated_before"] = self.updated_before.isoformat()
        if self.tags:
            criteria["tags"] = self.tags
        if self.search_text:
            criteria["search_text"] = self.search_text
        
        criteria["max_results"] = self.max_results
        criteria["offset"] = self.offset
        return criteria
    
    def to_mcp_query(self) -> str:
        """Convert search criteria to MCP Lucene query format.
        
        Returns:
            Lucene query string for MCP search operations.
        """
        query_parts = []
        
        if self.status:
            status_values = [f'"{s.value}"' for s in self.status]
            query_parts.append(f"status:({' OR '.join(status_values)})")
        
        if self.severity:
            severity_values = [f'"{s.value}"' for s in self.severity]
            query_parts.append(f"severity:({' OR '.join(severity_values)})")
        
        if self.assignee:
            query_parts.append(f'assignee:"{self.assignee}"')
        
        if self.resolver_group:
            query_parts.append(f'resolver_group:"{self.resolver_group}"')
        
        if self.created_after:
            query_parts.append(f"created_date:[{self.created_after.isoformat()} TO *]")
        
        if self.created_before:
            query_parts.append(f"created_date:[* TO {self.created_before.isoformat()}]")
        
        if self.search_text:
            # Escape special characters for Lucene
            escaped_text = self.search_text.replace('"', '\\"')
            query_parts.append(f'(title:"{escaped_text}" OR description:"{escaped_text}")')
        
        if self.tags:
            tag_queries = [f'tags:"{tag}"' for tag in self.tags]
            query_parts.append(f"({' AND '.join(tag_queries)})")
        
        return " AND ".join(query_parts) if query_parts else "*:*"
    
    def validate(self) -> None:
        """Validate search criteria parameters.
        
        Raises:
            ValueError: If criteria parameters are invalid.
        """
        if self.max_results <= 0:
            raise ValueError("max_results must be positive")
        
        if self.max_results > 10000:
            raise ValueError("max_results cannot exceed 10000")
        
        if self.offset < 0:
            raise ValueError("offset cannot be negative")
        
        if self.created_after and self.created_before:
            if self.created_after >= self.created_before:
                raise ValueError("created_after must be before created_before")
        
        if self.updated_after and self.updated_before:
            if self.updated_after >= self.updated_before:
                raise ValueError("updated_after must be before updated_before")


@dataclass
class AnalysisResult:
    """Results from ticket analysis operations.
    
    Contains the complete results of analyzing a set of tickets, including
    calculated metrics, trend data, and summary information.
    
    Attributes:
        metrics: Dictionary of calculated metrics
        trends: Dictionary of trend analysis data
        summary: Dictionary of summary information
        generated_at: When the analysis was performed
        ticket_count: Number of tickets analyzed
        date_range: Date range of analyzed tickets (start, end)
        analysis_duration: How long the analysis took to complete
        metadata: Additional analysis metadata
    """
    metrics: Dict[str, Any]
    trends: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    ticket_count: int = 0
    original_count: int = 0
    date_range: Optional[tuple] = None
    analysis_duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_metric(self, metric_name: str, default: Any = None) -> Any:
        """Get a specific metric value.
        
        Args:
            metric_name: Name of the metric to retrieve.
            default: Default value if metric not found.
            
        Returns:
            Metric value or default if not found.
        """
        return self.metrics.get(metric_name, default)
    
    def has_metric(self, metric_name: str) -> bool:
        """Check if a specific metric exists.
        
        Args:
            metric_name: Name of the metric to check.
            
        Returns:
            True if metric exists, False otherwise.
        """
        return metric_name in self.metrics
    
    def get_trend(self, trend_name: str, default: Any = None) -> Any:
        """Get a specific trend value.
        
        Args:
            trend_name: Name of the trend to retrieve.
            default: Default value if trend not found.
            
        Returns:
            Trend value or default if not found.
        """
        return self.trends.get(trend_name, default)
    
    def add_metric(self, name: str, value: Any) -> None:
        """Add or update a metric.
        
        Args:
            name: Metric name.
            value: Metric value.
        """
        self.metrics[name] = value
    
    def add_trend(self, name: str, value: Any) -> None:
        """Add or update a trend.
        
        Args:
            name: Trend name.
            value: Trend value.
        """
        self.trends[name] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis result to dictionary.
        
        Returns:
            Dictionary representation of the analysis result.
        """
        return {
            "metrics": self.metrics,
            "trends": self.trends,
            "summary": self.summary,
            "generated_at": self.generated_at.isoformat(),
            "ticket_count": self.ticket_count,
            "date_range": self.date_range,
            "analysis_duration": self.analysis_duration,
            "metadata": self.metadata
        }


@dataclass
class MetricDefinition:
    """Definition of a metric that can be calculated.
    
    Attributes:
        name: Metric name
        description: Human-readable description
        unit: Unit of measurement (e.g., 'hours', 'count', 'percentage')
        category: Metric category for grouping
        calculation_method: Description of how the metric is calculated
    """
    name: str
    description: str
    unit: str
    category: str = "general"
    calculation_method: str = ""


@dataclass
class TrendPoint:
    """A single point in a trend analysis.
    
    Attributes:
        timestamp: When this data point was recorded
        value: The metric value at this time
        label: Optional label for this point
        metadata: Additional metadata for this point
    """
    timestamp: datetime
    value: float
    label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendAnalysis:
    """Trend analysis results for a specific metric.
    
    Attributes:
        metric_name: Name of the metric being analyzed
        data_points: List of trend points
        trend_direction: Overall trend direction ('up', 'down', 'stable')
        slope: Calculated slope of the trend line
        correlation: Correlation coefficient
        period_start: Start of the analysis period
        period_end: End of the analysis period
    """
    metric_name: str
    data_points: List[TrendPoint]
    trend_direction: str = "stable"
    slope: Optional[float] = None
    correlation: Optional[float] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    
    def add_point(self, timestamp: datetime, value: float, 
                  label: Optional[str] = None) -> None:
        """Add a data point to the trend.
        
        Args:
            timestamp: When this data point was recorded.
            value: The metric value.
            label: Optional label for this point.
        """
        self.data_points.append(TrendPoint(timestamp, value, label))
    
    def get_latest_value(self) -> Optional[float]:
        """Get the most recent value in the trend.
        
        Returns:
            Latest value or None if no data points.
        """
        if not self.data_points:
            return None
        return max(self.data_points, key=lambda p: p.timestamp).value
    
    def get_value_range(self) -> tuple:
        """Get the min and max values in the trend.
        
        Returns:
            Tuple of (min_value, max_value) or (None, None) if no data.
        """
        if not self.data_points:
            return (None, None)
        
        values = [p.value for p in self.data_points]
        return (min(values), max(values))
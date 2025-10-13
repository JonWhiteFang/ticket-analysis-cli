"""Comprehensive tests for analysis data models.

This module contains unit tests for SearchCriteria, AnalysisResult,
MetricDefinition, TrendPoint, and TrendAnalysis models, covering
dataclass instantiation, validation, conversions, and edge cases.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List

from ticket_analyzer.models.analysis import (
    SearchCriteria, AnalysisResult, MetricDefinition, TrendPoint, TrendAnalysis
)
from ticket_analyzer.models.ticket import TicketStatus, TicketSeverity


class TestSearchCriteria:
    """Test cases for SearchCriteria dataclass."""
    
    def test_default_initialization(self) -> None:
        """Test SearchCriteria with default values."""
        criteria = SearchCriteria()
        
        assert criteria.status is None
        assert criteria.severity is None
        assert criteria.assignee is None
        assert criteria.resolver_group is None
        assert criteria.created_after is None
        assert criteria.created_before is None
        assert criteria.updated_after is None
        assert criteria.updated_before is None
        assert criteria.tags is None
        assert criteria.search_text is None
        assert criteria.max_results == 1000
        assert criteria.offset == 0
    
    def test_initialization_with_all_fields(self) -> None:
        """Test SearchCriteria with all fields populated."""
        created_after = datetime(2024, 1, 1)
        created_before = datetime(2024, 1, 31)
        updated_after = datetime(2024, 1, 15)
        updated_before = datetime(2024, 1, 30)
        
        criteria = SearchCriteria(
            status=[TicketStatus.OPEN, TicketStatus.IN_PROGRESS],
            severity=[TicketSeverity.SEV_1, TicketSeverity.SEV_2],
            assignee="testuser",
            resolver_group="Test Team",
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before,
            tags=["urgent", "bug"],
            search_text="authentication error",
            max_results=500,
            offset=10
        )
        
        assert criteria.status == [TicketStatus.OPEN, TicketStatus.IN_PROGRESS]
        assert criteria.severity == [TicketSeverity.SEV_1, TicketSeverity.SEV_2]
        assert criteria.assignee == "testuser"
        assert criteria.resolver_group == "Test Team"
        assert criteria.created_after == created_after
        assert criteria.created_before == created_before
        assert criteria.updated_after == updated_after
        assert criteria.updated_before == updated_before
        assert criteria.tags == ["urgent", "bug"]
        assert criteria.search_text == "authentication error"
        assert criteria.max_results == 500
        assert criteria.offset == 10
    
    def test_to_dict_with_all_fields(self) -> None:
        """Test converting SearchCriteria to dictionary with all fields."""
        created_after = datetime(2024, 1, 1, 10, 0, 0)
        created_before = datetime(2024, 1, 31, 18, 0, 0)
        
        criteria = SearchCriteria(
            status=[TicketStatus.OPEN, TicketStatus.RESOLVED],
            severity=[TicketSeverity.SEV_2],
            assignee="testuser",
            resolver_group="Test Team",
            created_after=created_after,
            created_before=created_before,
            tags=["urgent"],
            search_text="login issue",
            max_results=100,
            offset=20
        )
        
        result = criteria.to_dict()
        
        expected = {
            "status": ["Open", "Resolved"],
            "severity": ["SEV_2"],
            "assignee": "testuser",
            "resolver_group": "Test Team",
            "created_after": "2024-01-01T10:00:00",
            "created_before": "2024-01-31T18:00:00",
            "tags": ["urgent"],
            "search_text": "login issue",
            "max_results": 100,
            "offset": 20
        }
        
        assert result == expected
    
    def test_to_dict_with_minimal_fields(self) -> None:
        """Test converting SearchCriteria to dictionary with minimal fields."""
        criteria = SearchCriteria(max_results=50, offset=5)
        
        result = criteria.to_dict()
        
        expected = {
            "max_results": 50,
            "offset": 5
        }
        
        assert result == expected
    
    def test_to_mcp_query_with_all_fields(self) -> None:
        """Test converting SearchCriteria to MCP Lucene query with all fields."""
        created_after = datetime(2024, 1, 1, 10, 0, 0)
        created_before = datetime(2024, 1, 31, 18, 0, 0)
        
        criteria = SearchCriteria(
            status=[TicketStatus.OPEN, TicketStatus.IN_PROGRESS],
            severity=[TicketSeverity.SEV_1, TicketSeverity.SEV_2],
            assignee="testuser",
            resolver_group="Test Team",
            created_after=created_after,
            created_before=created_before,
            tags=["urgent", "bug"],
            search_text="authentication error"
        )
        
        query = criteria.to_mcp_query()
        
        # Check that all expected parts are in the query
        assert 'status:("Open" OR "In Progress")' in query
        assert 'severity:("SEV_1" OR "SEV_2")' in query
        assert 'assignee:"testuser"' in query
        assert 'resolver_group:"Test Team"' in query
        assert 'created_date:[2024-01-01T10:00:00 TO *]' in query
        assert 'created_date:[* TO 2024-01-31T18:00:00]' in query
        assert '(tags:"urgent" AND tags:"bug")' in query
        assert '(title:"authentication error" OR description:"authentication error")' in query
        
        # Check that parts are joined with AND
        assert " AND " in query
    
    def test_to_mcp_query_with_minimal_fields(self) -> None:
        """Test converting SearchCriteria to MCP query with minimal fields."""
        criteria = SearchCriteria()
        query = criteria.to_mcp_query()
        assert query == "*:*"  # Match all when no criteria
    
    def test_to_mcp_query_with_single_status(self) -> None:
        """Test MCP query generation with single status."""
        criteria = SearchCriteria(status=[TicketStatus.OPEN])
        query = criteria.to_mcp_query()
        assert 'status:("Open")' in query
    
    def test_to_mcp_query_escapes_special_characters(self) -> None:
        """Test that special characters in search text are escaped."""
        criteria = SearchCriteria(search_text='error "authentication" failed')
        query = criteria.to_mcp_query()
        assert 'error \\"authentication\\" failed' in query
    
    def test_validate_success(self) -> None:
        """Test successful validation of SearchCriteria."""
        created_after = datetime(2024, 1, 1)
        created_before = datetime(2024, 1, 31)
        updated_after = datetime(2024, 1, 10)
        updated_before = datetime(2024, 1, 20)
        
        criteria = SearchCriteria(
            max_results=100,
            offset=0,
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before
        )
        
        # Should not raise any exception
        criteria.validate()
    
    def test_validate_max_results_zero(self) -> None:
        """Test validation fails for zero max_results."""
        criteria = SearchCriteria(max_results=0)
        
        with pytest.raises(ValueError, match="max_results must be positive"):
            criteria.validate()
    
    def test_validate_max_results_negative(self) -> None:
        """Test validation fails for negative max_results."""
        criteria = SearchCriteria(max_results=-1)
        
        with pytest.raises(ValueError, match="max_results must be positive"):
            criteria.validate()
    
    def test_validate_max_results_too_large(self) -> None:
        """Test validation fails for max_results exceeding limit."""
        criteria = SearchCriteria(max_results=10001)
        
        with pytest.raises(ValueError, match="max_results cannot exceed 10000"):
            criteria.validate()
    
    def test_validate_negative_offset(self) -> None:
        """Test validation fails for negative offset."""
        criteria = SearchCriteria(offset=-1)
        
        with pytest.raises(ValueError, match="offset cannot be negative"):
            criteria.validate()
    
    def test_validate_invalid_created_date_range(self) -> None:
        """Test validation fails when created_after >= created_before."""
        created_after = datetime(2024, 1, 31)
        created_before = datetime(2024, 1, 1)  # Before created_after
        
        criteria = SearchCriteria(
            created_after=created_after,
            created_before=created_before
        )
        
        with pytest.raises(ValueError, match="created_after must be before created_before"):
            criteria.validate()
    
    def test_validate_equal_created_dates(self) -> None:
        """Test validation fails when created dates are equal."""
        same_date = datetime(2024, 1, 15)
        
        criteria = SearchCriteria(
            created_after=same_date,
            created_before=same_date
        )
        
        with pytest.raises(ValueError, match="created_after must be before created_before"):
            criteria.validate()
    
    def test_validate_invalid_updated_date_range(self) -> None:
        """Test validation fails when updated_after >= updated_before."""
        updated_after = datetime(2024, 1, 20)
        updated_before = datetime(2024, 1, 10)  # Before updated_after
        
        criteria = SearchCriteria(
            updated_after=updated_after,
            updated_before=updated_before
        )
        
        with pytest.raises(ValueError, match="updated_after must be before updated_before"):
            criteria.validate()


class TestAnalysisResult:
    """Test cases for AnalysisResult dataclass."""
    
    def test_default_initialization(self) -> None:
        """Test AnalysisResult with default values."""
        metrics = {"total_tickets": 100, "avg_resolution_time": 24.5}
        result = AnalysisResult(metrics=metrics)
        
        assert result.metrics == metrics
        assert result.trends == {}
        assert result.summary == {}
        assert isinstance(result.generated_at, datetime)
        assert result.ticket_count == 0
        assert result.date_range is None
        assert result.analysis_duration is None
        assert result.metadata == {}
    
    def test_initialization_with_all_fields(self) -> None:
        """Test AnalysisResult with all fields populated."""
        metrics = {"total_tickets": 150}
        trends = {"weekly_trend": [1, 2, 3, 4]}
        summary = {"key_insight": "Tickets increasing"}
        generated_at = datetime(2024, 1, 15, 10, 30, 0)
        date_range = (datetime(2024, 1, 1), datetime(2024, 1, 31))
        metadata = {"analysis_version": "1.0"}
        
        result = AnalysisResult(
            metrics=metrics,
            trends=trends,
            summary=summary,
            generated_at=generated_at,
            ticket_count=150,
            date_range=date_range,
            analysis_duration=45.2,
            metadata=metadata
        )
        
        assert result.metrics == metrics
        assert result.trends == trends
        assert result.summary == summary
        assert result.generated_at == generated_at
        assert result.ticket_count == 150
        assert result.date_range == date_range
        assert result.analysis_duration == 45.2
        assert result.metadata == metadata
    
    def test_get_metric_existing(self) -> None:
        """Test getting an existing metric."""
        metrics = {"total_tickets": 100, "avg_resolution_time": 24.5}
        result = AnalysisResult(metrics=metrics)
        
        assert result.get_metric("total_tickets") == 100
        assert result.get_metric("avg_resolution_time") == 24.5
    
    def test_get_metric_nonexistent_with_default(self) -> None:
        """Test getting a nonexistent metric with default value."""
        result = AnalysisResult(metrics={})
        
        assert result.get_metric("nonexistent", "default") == "default"
        assert result.get_metric("nonexistent", 0) == 0
    
    def test_get_metric_nonexistent_without_default(self) -> None:
        """Test getting a nonexistent metric without default value."""
        result = AnalysisResult(metrics={})
        
        assert result.get_metric("nonexistent") is None
    
    def test_has_metric(self) -> None:
        """Test checking if metrics exist."""
        metrics = {"total_tickets": 100}
        result = AnalysisResult(metrics=metrics)
        
        assert result.has_metric("total_tickets") is True
        assert result.has_metric("nonexistent") is False
    
    def test_get_trend_existing(self) -> None:
        """Test getting an existing trend."""
        trends = {"weekly": [1, 2, 3], "monthly": [10, 20, 30]}
        result = AnalysisResult(metrics={}, trends=trends)
        
        assert result.get_trend("weekly") == [1, 2, 3]
        assert result.get_trend("monthly") == [10, 20, 30]
    
    def test_get_trend_nonexistent(self) -> None:
        """Test getting a nonexistent trend."""
        result = AnalysisResult(metrics={})
        
        assert result.get_trend("nonexistent") is None
        assert result.get_trend("nonexistent", []) == []
    
    def test_add_metric(self) -> None:
        """Test adding metrics to the result."""
        result = AnalysisResult(metrics={})
        
        result.add_metric("new_metric", 42)
        result.add_metric("another_metric", "value")
        
        assert result.metrics["new_metric"] == 42
        assert result.metrics["another_metric"] == "value"
    
    def test_add_trend(self) -> None:
        """Test adding trends to the result."""
        result = AnalysisResult(metrics={})
        
        result.add_trend("new_trend", [1, 2, 3])
        result.add_trend("another_trend", {"data": "value"})
        
        assert result.trends["new_trend"] == [1, 2, 3]
        assert result.trends["another_trend"] == {"data": "value"}
    
    def test_to_dict_conversion(self) -> None:
        """Test converting AnalysisResult to dictionary."""
        metrics = {"total_tickets": 100}
        trends = {"weekly": [1, 2, 3]}
        summary = {"insight": "test"}
        generated_at = datetime(2024, 1, 15, 10, 30, 0)
        date_range = (datetime(2024, 1, 1), datetime(2024, 1, 31))
        metadata = {"version": "1.0"}
        
        result = AnalysisResult(
            metrics=metrics,
            trends=trends,
            summary=summary,
            generated_at=generated_at,
            ticket_count=100,
            date_range=date_range,
            analysis_duration=30.5,
            metadata=metadata
        )
        
        dict_result = result.to_dict()
        
        expected = {
            "metrics": metrics,
            "trends": trends,
            "summary": summary,
            "generated_at": "2024-01-15T10:30:00",
            "ticket_count": 100,
            "date_range": date_range,
            "analysis_duration": 30.5,
            "metadata": metadata
        }
        
        assert dict_result == expected


class TestMetricDefinition:
    """Test cases for MetricDefinition dataclass."""
    
    def test_initialization_with_required_fields(self) -> None:
        """Test MetricDefinition with required fields only."""
        metric = MetricDefinition(
            name="resolution_time",
            description="Average time to resolve tickets",
            unit="hours"
        )
        
        assert metric.name == "resolution_time"
        assert metric.description == "Average time to resolve tickets"
        assert metric.unit == "hours"
        assert metric.category == "general"  # Default value
        assert metric.calculation_method == ""  # Default value
    
    def test_initialization_with_all_fields(self) -> None:
        """Test MetricDefinition with all fields populated."""
        metric = MetricDefinition(
            name="sev1_count",
            description="Number of SEV-1 tickets",
            unit="count",
            category="severity",
            calculation_method="Count tickets with severity = SEV_1"
        )
        
        assert metric.name == "sev1_count"
        assert metric.description == "Number of SEV-1 tickets"
        assert metric.unit == "count"
        assert metric.category == "severity"
        assert metric.calculation_method == "Count tickets with severity = SEV_1"
    
    def test_equality(self) -> None:
        """Test MetricDefinition equality comparison."""
        metric1 = MetricDefinition("test", "Test metric", "count")
        metric2 = MetricDefinition("test", "Test metric", "count")
        metric3 = MetricDefinition("other", "Other metric", "count")
        
        assert metric1 == metric2
        assert metric1 != metric3


class TestTrendPoint:
    """Test cases for TrendPoint dataclass."""
    
    def test_initialization_with_required_fields(self) -> None:
        """Test TrendPoint with required fields only."""
        timestamp = datetime(2024, 1, 15, 10, 0, 0)
        point = TrendPoint(timestamp=timestamp, value=42.5)
        
        assert point.timestamp == timestamp
        assert point.value == 42.5
        assert point.label is None
        assert point.metadata == {}
    
    def test_initialization_with_all_fields(self) -> None:
        """Test TrendPoint with all fields populated."""
        timestamp = datetime(2024, 1, 15, 10, 0, 0)
        metadata = {"source": "api", "confidence": 0.95}
        
        point = TrendPoint(
            timestamp=timestamp,
            value=100.0,
            label="Peak value",
            metadata=metadata
        )
        
        assert point.timestamp == timestamp
        assert point.value == 100.0
        assert point.label == "Peak value"
        assert point.metadata == metadata
    
    def test_default_metadata_independence(self) -> None:
        """Test that default metadata dictionaries are independent."""
        point1 = TrendPoint(datetime.now(), 1.0)
        point2 = TrendPoint(datetime.now(), 2.0)
        
        point1.metadata["key"] = "value1"
        point2.metadata["key"] = "value2"
        
        assert point1.metadata["key"] == "value1"
        assert point2.metadata["key"] == "value2"


class TestTrendAnalysis:
    """Test cases for TrendAnalysis dataclass."""
    
    def test_initialization_with_required_fields(self) -> None:
        """Test TrendAnalysis with required fields only."""
        data_points = [
            TrendPoint(datetime(2024, 1, 1), 10.0),
            TrendPoint(datetime(2024, 1, 2), 15.0)
        ]
        
        trend = TrendAnalysis(
            metric_name="ticket_count",
            data_points=data_points
        )
        
        assert trend.metric_name == "ticket_count"
        assert trend.data_points == data_points
        assert trend.trend_direction == "stable"  # Default
        assert trend.slope is None
        assert trend.correlation is None
        assert trend.period_start is None
        assert trend.period_end is None
    
    def test_initialization_with_all_fields(self) -> None:
        """Test TrendAnalysis with all fields populated."""
        data_points = [TrendPoint(datetime(2024, 1, 1), 10.0)]
        period_start = datetime(2024, 1, 1)
        period_end = datetime(2024, 1, 31)
        
        trend = TrendAnalysis(
            metric_name="resolution_time",
            data_points=data_points,
            trend_direction="up",
            slope=1.5,
            correlation=0.85,
            period_start=period_start,
            period_end=period_end
        )
        
        assert trend.metric_name == "resolution_time"
        assert trend.data_points == data_points
        assert trend.trend_direction == "up"
        assert trend.slope == 1.5
        assert trend.correlation == 0.85
        assert trend.period_start == period_start
        assert trend.period_end == period_end
    
    def test_add_point(self) -> None:
        """Test adding data points to trend analysis."""
        trend = TrendAnalysis(metric_name="test", data_points=[])
        
        timestamp1 = datetime(2024, 1, 1, 10, 0, 0)
        timestamp2 = datetime(2024, 1, 2, 10, 0, 0)
        
        trend.add_point(timestamp1, 100.0)
        trend.add_point(timestamp2, 150.0, "Peak")
        
        assert len(trend.data_points) == 2
        
        point1 = trend.data_points[0]
        assert point1.timestamp == timestamp1
        assert point1.value == 100.0
        assert point1.label is None
        
        point2 = trend.data_points[1]
        assert point2.timestamp == timestamp2
        assert point2.value == 150.0
        assert point2.label == "Peak"
    
    def test_get_latest_value_with_data(self) -> None:
        """Test getting latest value when data points exist."""
        trend = TrendAnalysis(metric_name="test", data_points=[])
        
        # Add points in non-chronological order
        trend.add_point(datetime(2024, 1, 1), 10.0)
        trend.add_point(datetime(2024, 1, 3), 30.0)  # Latest
        trend.add_point(datetime(2024, 1, 2), 20.0)
        
        latest = trend.get_latest_value()
        assert latest == 30.0  # Should be the value with latest timestamp
    
    def test_get_latest_value_empty_data(self) -> None:
        """Test getting latest value when no data points exist."""
        trend = TrendAnalysis(metric_name="test", data_points=[])
        
        latest = trend.get_latest_value()
        assert latest is None
    
    def test_get_value_range_with_data(self) -> None:
        """Test getting value range when data points exist."""
        trend = TrendAnalysis(metric_name="test", data_points=[])
        
        trend.add_point(datetime(2024, 1, 1), 15.0)
        trend.add_point(datetime(2024, 1, 2), 5.0)   # Min
        trend.add_point(datetime(2024, 1, 3), 25.0)  # Max
        trend.add_point(datetime(2024, 1, 4), 10.0)
        
        min_val, max_val = trend.get_value_range()
        assert min_val == 5.0
        assert max_val == 25.0
    
    def test_get_value_range_empty_data(self) -> None:
        """Test getting value range when no data points exist."""
        trend = TrendAnalysis(metric_name="test", data_points=[])
        
        min_val, max_val = trend.get_value_range()
        assert min_val is None
        assert max_val is None
    
    def test_get_value_range_single_point(self) -> None:
        """Test getting value range with single data point."""
        trend = TrendAnalysis(metric_name="test", data_points=[])
        trend.add_point(datetime(2024, 1, 1), 42.0)
        
        min_val, max_val = trend.get_value_range()
        assert min_val == 42.0
        assert max_val == 42.0
    
    def test_trend_direction_values(self) -> None:
        """Test valid trend direction values."""
        valid_directions = ["up", "down", "stable"]
        
        for direction in valid_directions:
            trend = TrendAnalysis(
                metric_name="test",
                data_points=[],
                trend_direction=direction
            )
            assert trend.trend_direction == direction
    
    def test_edge_case_negative_values(self) -> None:
        """Test handling of negative values in trend points."""
        trend = TrendAnalysis(metric_name="test", data_points=[])
        
        trend.add_point(datetime(2024, 1, 1), -10.0)
        trend.add_point(datetime(2024, 1, 2), -5.0)
        trend.add_point(datetime(2024, 1, 3), 0.0)
        trend.add_point(datetime(2024, 1, 4), 5.0)
        
        min_val, max_val = trend.get_value_range()
        assert min_val == -10.0
        assert max_val == 5.0
        
        latest = trend.get_latest_value()
        assert latest == 5.0
    
    def test_edge_case_zero_values(self) -> None:
        """Test handling of zero values in trend points."""
        trend = TrendAnalysis(metric_name="test", data_points=[])
        
        trend.add_point(datetime(2024, 1, 1), 0.0)
        trend.add_point(datetime(2024, 1, 2), 0.0)
        
        min_val, max_val = trend.get_value_range()
        assert min_val == 0.0
        assert max_val == 0.0
        
        latest = trend.get_latest_value()
        assert latest == 0.0
    
    def test_edge_case_very_large_values(self) -> None:
        """Test handling of very large values."""
        trend = TrendAnalysis(metric_name="test", data_points=[])
        
        large_value = 1e10
        trend.add_point(datetime(2024, 1, 1), large_value)
        
        latest = trend.get_latest_value()
        assert latest == large_value
        
        min_val, max_val = trend.get_value_range()
        assert min_val == large_value
        assert max_val == large_value
    
    def test_edge_case_same_timestamps(self) -> None:
        """Test handling of data points with same timestamps."""
        trend = TrendAnalysis(metric_name="test", data_points=[])
        
        same_time = datetime(2024, 1, 1, 10, 0, 0)
        trend.add_point(same_time, 10.0)
        trend.add_point(same_time, 20.0)  # Same timestamp, different value
        
        # Should return the last added value for same timestamp
        latest = trend.get_latest_value()
        assert latest in [10.0, 20.0]  # Either could be "latest" with same timestamp
        
        min_val, max_val = trend.get_value_range()
        assert min_val == 10.0
        assert max_val == 20.0
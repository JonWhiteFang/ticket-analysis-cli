"""Tests for trend analysis module.

This module contains comprehensive tests for the TrendAnalyzer class,
covering time-series analysis, pattern recognition, and statistical
forecasting according to the testing standards.
"""

from __future__ import annotations
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch

import pandas as pd

from ticket_analyzer.analysis.trends import TrendAnalyzer
from ticket_analyzer.models.ticket import Ticket, TicketStatus, TicketSeverity
from ticket_analyzer.models.exceptions import AnalysisError


class TestTrendAnalyzer:
    """Test cases for TrendAnalyzer class."""
    
    def test_analyzer_initialization(self):
        """Test trend analyzer initialization."""
        analyzer = TrendAnalyzer()
        
        assert analyzer._default_period_days == 30
        assert analyzer._min_data_points == 3
    
    def test_analyzer_initialization_with_custom_params(self):
        """Test trend analyzer initialization with custom parameters."""
        analyzer = TrendAnalyzer(period_days=60, min_data_points=5)
        
        assert analyzer._default_period_days == 60
        assert analyzer._min_data_points == 5
    
    def test_analyze_trends_success(self):
        """Test successful trend analysis."""
        analyzer = TrendAnalyzer()
        
        # Create DataFrame with time-series data
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(10)]
        df = pd.DataFrame({
            'created_date': dates,
            'status': ['Open'] * 5 + ['Resolved'] * 5,
            'severity': ['HIGH'] * 10
        })
        
        # Create corresponding tickets
        tickets = []
        for i, date in enumerate(dates):
            tickets.append(Ticket(
                id=f"T{i+1}",
                title=f"Ticket {i+1}",
                status=TicketStatus.OPEN if i < 5 else TicketStatus.RESOLVED,
                severity=TicketSeverity.HIGH,
                created_date=date
            ))
        
        result = analyzer.analyze_trends(df, tickets)
        
        assert isinstance(result, dict)
        assert "daily_trends" in result
        assert "weekly_trends" in result
        assert "monthly_trends" in result
        assert "trend_summary" in result
    
    def test_analyze_trends_empty_dataframe(self):
        """Test trend analysis with empty DataFrame."""
        analyzer = TrendAnalyzer()
        df = pd.DataFrame()
        tickets = []
        
        result = analyzer.analyze_trends(df, tickets)
        
        assert result["daily_trends"] == {}
        assert result["weekly_trends"] == {}
        assert result["monthly_trends"] == {}
        assert "no_data" in result["trend_summary"]
    
    def test_analyze_trends_insufficient_data(self):
        """Test trend analysis with insufficient data points."""
        analyzer = TrendAnalyzer(min_data_points=5)
        
        # Create DataFrame with only 2 data points
        df = pd.DataFrame({
            'created_date': [datetime(2024, 1, 1), datetime(2024, 1, 2)],
            'status': ['Open', 'Resolved'],
            'severity': ['HIGH', 'MEDIUM']
        })
        
        tickets = [
            Ticket(id="T1", title="Test 1", status=TicketStatus.OPEN,
                  severity=TicketSeverity.HIGH, created_date=datetime(2024, 1, 1)),
            Ticket(id="T2", title="Test 2", status=TicketStatus.RESOLVED,
                  severity=TicketSeverity.MEDIUM, created_date=datetime(2024, 1, 2))
        ]
        
        result = analyzer.analyze_trends(df, tickets)
        
        assert "insufficient_data" in result["trend_summary"]
    
    def test_calculate_daily_trends(self):
        """Test daily trend calculation."""
        analyzer = TrendAnalyzer()
        
        # Create data spanning multiple days
        dates = []
        for day in range(1, 8):  # Week of data
            for hour in [9, 12, 15]:  # 3 tickets per day
                dates.append(datetime(2024, 1, day, hour))
        
        df = pd.DataFrame({
            'created_date': dates,
            'status': ['Open'] * len(dates)
        })
        
        daily_trends = analyzer._calculate_daily_trends(df)
        
        assert isinstance(daily_trends, dict)
        assert len(daily_trends) == 7  # 7 days
        
        # Each day should have 3 tickets
        for date_str, count in daily_trends.items():
            assert count == 3
    
    def test_calculate_weekly_trends(self):
        """Test weekly trend calculation."""
        analyzer = TrendAnalyzer()
        
        # Create data spanning multiple weeks
        dates = []
        base_date = datetime(2024, 1, 1)  # Monday
        
        # 3 weeks of data, 5 tickets per week
        for week in range(3):
            for day in range(5):
                dates.append(base_date + timedelta(weeks=week, days=day))
        
        df = pd.DataFrame({
            'created_date': dates,
            'status': ['Open'] * len(dates)
        })
        
        weekly_trends = analyzer._calculate_weekly_trends(df)
        
        assert isinstance(weekly_trends, dict)
        assert len(weekly_trends) == 3  # 3 weeks
        
        # Each week should have 5 tickets
        for week_str, count in weekly_trends.items():
            assert count == 5
    
    def test_calculate_monthly_trends(self):
        """Test monthly trend calculation."""
        analyzer = TrendAnalyzer()
        
        # Create data spanning multiple months
        dates = []
        for month in [1, 2, 3]:
            for day in range(1, 11):  # 10 days per month
                dates.append(datetime(2024, month, day))
        
        df = pd.DataFrame({
            'created_date': dates,
            'status': ['Open'] * len(dates)
        })
        
        monthly_trends = analyzer._calculate_monthly_trends(df)
        
        assert isinstance(monthly_trends, dict)
        assert len(monthly_trends) == 3  # 3 months
        
        # Each month should have 10 tickets
        for month_str, count in monthly_trends.items():
            assert count == 10
    
    def test_detect_patterns_increasing_trend(self):
        """Test pattern detection for increasing trends."""
        analyzer = TrendAnalyzer()
        
        # Create increasing trend data
        trend_data = {
            '2024-01-01': 5,
            '2024-01-02': 7,
            '2024-01-03': 9,
            '2024-01-04': 11,
            '2024-01-05': 13
        }
        
        patterns = analyzer._detect_patterns(trend_data)
        
        assert "trend_direction" in patterns
        assert patterns["trend_direction"] == "increasing"
        assert "trend_strength" in patterns
    
    def test_detect_patterns_decreasing_trend(self):
        """Test pattern detection for decreasing trends."""
        analyzer = TrendAnalyzer()
        
        # Create decreasing trend data
        trend_data = {
            '2024-01-01': 15,
            '2024-01-02': 12,
            '2024-01-03': 9,
            '2024-01-04': 6,
            '2024-01-05': 3
        }
        
        patterns = analyzer._detect_patterns(trend_data)
        
        assert patterns["trend_direction"] == "decreasing"
        assert "trend_strength" in patterns
    
    def test_detect_patterns_stable_trend(self):
        """Test pattern detection for stable trends."""
        analyzer = TrendAnalyzer()
        
        # Create stable trend data
        trend_data = {
            '2024-01-01': 10,
            '2024-01-02': 11,
            '2024-01-03': 9,
            '2024-01-04': 10,
            '2024-01-05': 10
        }
        
        patterns = analyzer._detect_patterns(trend_data)
        
        assert patterns["trend_direction"] == "stable"
    
    def test_detect_anomalies(self):
        """Test anomaly detection in trend data."""
        analyzer = TrendAnalyzer()
        
        # Create data with clear anomaly
        trend_data = {
            '2024-01-01': 10,
            '2024-01-02': 12,
            '2024-01-03': 50,  # Anomaly
            '2024-01-04': 11,
            '2024-01-05': 9
        }
        
        anomalies = analyzer._detect_anomalies(trend_data)
        
        assert isinstance(anomalies, list)
        assert len(anomalies) > 0
        
        # Should detect the anomaly on 2024-01-03
        anomaly_dates = [anomaly['date'] for anomaly in anomalies]
        assert '2024-01-03' in anomaly_dates
    
    def test_detect_anomalies_no_anomalies(self):
        """Test anomaly detection with normal data."""
        analyzer = TrendAnalyzer()
        
        # Create normal data without anomalies
        trend_data = {
            '2024-01-01': 10,
            '2024-01-02': 12,
            '2024-01-03': 11,
            '2024-01-04': 13,
            '2024-01-05': 9
        }
        
        anomalies = analyzer._detect_anomalies(trend_data)
        
        assert isinstance(anomalies, list)
        assert len(anomalies) == 0
    
    def test_calculate_trend_statistics(self):
        """Test trend statistics calculation."""
        analyzer = TrendAnalyzer()
        
        trend_data = {
            '2024-01-01': 10,
            '2024-01-02': 15,
            '2024-01-03': 12,
            '2024-01-04': 18,
            '2024-01-05': 14
        }
        
        stats = analyzer._calculate_trend_statistics(trend_data)
        
        assert "mean" in stats
        assert "median" in stats
        assert "std_dev" in stats
        assert "min_value" in stats
        assert "max_value" in stats
        assert "total" in stats
        
        assert stats["mean"] == 13.8  # (10+15+12+18+14)/5
        assert stats["min_value"] == 10
        assert stats["max_value"] == 18
        assert stats["total"] == 69
    
    def test_calculate_trend_statistics_empty_data(self):
        """Test trend statistics with empty data."""
        analyzer = TrendAnalyzer()
        
        stats = analyzer._calculate_trend_statistics({})
        
        assert stats["mean"] == 0
        assert stats["median"] == 0
        assert stats["std_dev"] == 0
        assert stats["min_value"] == 0
        assert stats["max_value"] == 0
        assert stats["total"] == 0
    
    def test_generate_forecast(self):
        """Test trend forecasting."""
        analyzer = TrendAnalyzer()
        
        # Create trend data with clear pattern
        trend_data = {
            '2024-01-01': 10,
            '2024-01-02': 12,
            '2024-01-03': 14,
            '2024-01-04': 16,
            '2024-01-05': 18
        }
        
        forecast = analyzer._generate_forecast(trend_data, days=3)
        
        assert isinstance(forecast, dict)
        assert len(forecast) == 3
        
        # Forecast should continue the increasing trend
        forecast_values = list(forecast.values())
        assert all(isinstance(val, (int, float)) for val in forecast_values)
    
    def test_generate_forecast_insufficient_data(self):
        """Test forecasting with insufficient data."""
        analyzer = TrendAnalyzer()
        
        # Only 2 data points
        trend_data = {
            '2024-01-01': 10,
            '2024-01-02': 12
        }
        
        forecast = analyzer._generate_forecast(trend_data, days=3)
        
        # Should return empty forecast or simple projection
        assert isinstance(forecast, dict)
    
    def test_analyze_seasonal_patterns(self):
        """Test seasonal pattern analysis."""
        analyzer = TrendAnalyzer()
        
        # Create data with weekly pattern (more tickets on weekdays)
        dates = []
        values = []
        base_date = datetime(2024, 1, 1)  # Monday
        
        for week in range(4):  # 4 weeks
            for day in range(7):  # 7 days per week
                date = base_date + timedelta(weeks=week, days=day)
                dates.append(date)
                # More tickets on weekdays (Mon-Fri)
                values.append(15 if day < 5 else 5)
        
        df = pd.DataFrame({
            'created_date': dates,
            'count': values
        })
        
        seasonal_patterns = analyzer._analyze_seasonal_patterns(df)
        
        assert isinstance(seasonal_patterns, dict)
        assert "day_of_week_pattern" in seasonal_patterns
        
        # Should detect higher activity on weekdays
        dow_pattern = seasonal_patterns["day_of_week_pattern"]
        weekday_avg = sum(dow_pattern[str(i)] for i in range(5)) / 5  # Mon-Fri
        weekend_avg = sum(dow_pattern[str(i)] for i in range(5, 7)) / 2  # Sat-Sun
        
        assert weekday_avg > weekend_avg
    
    def test_filter_data_by_period(self):
        """Test data filtering by time period."""
        analyzer = TrendAnalyzer(period_days=7)
        
        # Create data spanning 14 days
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(14)]
        df = pd.DataFrame({
            'created_date': dates,
            'status': ['Open'] * 14
        })
        
        filtered_df = analyzer._filter_data_by_period(df)
        
        # Should only include last 7 days
        assert len(filtered_df) == 7
        
        # Check that it's the most recent 7 days
        min_date = filtered_df['created_date'].min()
        max_date = filtered_df['created_date'].max()
        expected_min = datetime(2024, 1, 8)  # 7 days before the last date
        
        assert min_date >= expected_min
        assert max_date == datetime(2024, 1, 14)
    
    def test_create_trend_summary(self):
        """Test trend summary creation."""
        analyzer = TrendAnalyzer()
        
        daily_trends = {'2024-01-01': 10, '2024-01-02': 15, '2024-01-03': 12}
        patterns = {'trend_direction': 'increasing', 'trend_strength': 'moderate'}
        anomalies = [{'date': '2024-01-02', 'value': 15, 'expected': 11}]
        
        summary = analyzer._create_trend_summary(daily_trends, patterns, anomalies)
        
        assert isinstance(summary, dict)
        assert "period_summary" in summary
        assert "trend_analysis" in summary
        assert "anomaly_count" in summary
        assert "key_insights" in summary
        
        assert summary["anomaly_count"] == 1
        assert summary["trend_analysis"]["direction"] == "increasing"


class TestTrendAnalyzerEdgeCases:
    """Test edge cases and error conditions for TrendAnalyzer."""
    
    def test_analyze_trends_invalid_dataframe(self):
        """Test trend analysis with invalid DataFrame."""
        analyzer = TrendAnalyzer()
        
        with pytest.raises((ValueError, TypeError)):
            analyzer.analyze_trends(None, [])
    
    def test_analyze_trends_missing_created_date_column(self):
        """Test trend analysis with DataFrame missing created_date column."""
        analyzer = TrendAnalyzer()
        
        df = pd.DataFrame({
            'status': ['Open', 'Resolved'],
            'severity': ['HIGH', 'MEDIUM']
            # Missing 'created_date' column
        })
        
        tickets = []
        
        with pytest.raises(AnalysisError):
            analyzer.analyze_trends(df, tickets)
    
    def test_analyze_trends_invalid_date_format(self):
        """Test trend analysis with invalid date formats."""
        analyzer = TrendAnalyzer()
        
        df = pd.DataFrame({
            'created_date': ['invalid_date', 'another_invalid'],
            'status': ['Open', 'Resolved']
        })
        
        tickets = []
        
        # Should handle gracefully or raise appropriate error
        result = analyzer.analyze_trends(df, tickets)
        assert isinstance(result, dict)
    
    def test_detect_patterns_empty_data(self):
        """Test pattern detection with empty data."""
        analyzer = TrendAnalyzer()
        
        patterns = analyzer._detect_patterns({})
        
        assert patterns["trend_direction"] == "no_data"
        assert patterns["trend_strength"] == "none"
    
    def test_detect_patterns_single_data_point(self):
        """Test pattern detection with single data point."""
        analyzer = TrendAnalyzer()
        
        patterns = analyzer._detect_patterns({'2024-01-01': 10})
        
        assert patterns["trend_direction"] == "insufficient_data"
    
    def test_performance_with_large_dataset(self):
        """Test performance with large dataset."""
        analyzer = TrendAnalyzer()
        
        # Create large dataset (1000 data points)
        dates = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(1000)]
        df = pd.DataFrame({
            'created_date': dates,
            'status': ['Open'] * 1000
        })
        
        tickets = []  # Empty for performance test
        
        # Should complete without timeout or memory issues
        result = analyzer.analyze_trends(df, tickets)
        
        assert isinstance(result, dict)
        assert "daily_trends" in result


class TestTrendAnalyzerIntegration:
    """Integration tests for TrendAnalyzer with real data scenarios."""
    
    def test_full_trend_analysis_workflow(self, sample_tickets_with_dates):
        """Test complete trend analysis workflow with realistic data."""
        analyzer = TrendAnalyzer()
        
        # Create DataFrame from sample tickets
        df_data = []
        for ticket in sample_tickets_with_dates:
            df_data.append({
                'created_date': ticket.created_date,
                'status': ticket.status.value,
                'severity': ticket.severity.value,
                'id': ticket.id
            })
        
        df = pd.DataFrame(df_data)
        
        result = analyzer.analyze_trends(df, sample_tickets_with_dates)
        
        # Verify complete result structure
        assert isinstance(result, dict)
        assert all(key in result for key in [
            "daily_trends", "weekly_trends", "monthly_trends", "trend_summary"
        ])
        
        # Verify trend summary contains expected insights
        summary = result["trend_summary"]
        assert "period_summary" in summary
        assert "trend_analysis" in summary
        assert "key_insights" in summary
    
    def test_trend_analysis_with_mixed_statuses(self):
        """Test trend analysis with tickets of different statuses."""
        analyzer = TrendAnalyzer()
        
        # Create tickets with different statuses over time
        tickets = []
        base_date = datetime(2024, 1, 1)
        
        for i in range(20):
            status = TicketStatus.OPEN if i % 3 == 0 else TicketStatus.RESOLVED
            tickets.append(Ticket(
                id=f"T{i+1}",
                title=f"Ticket {i+1}",
                status=status,
                severity=TicketSeverity.MEDIUM,
                created_date=base_date + timedelta(days=i)
            ))
        
        df_data = []
        for ticket in tickets:
            df_data.append({
                'created_date': ticket.created_date,
                'status': ticket.status.value,
                'severity': ticket.severity.value
            })
        
        df = pd.DataFrame(df_data)
        
        result = analyzer.analyze_trends(df, tickets)
        
        # Should handle mixed statuses without errors
        assert isinstance(result, dict)
        assert len(result["daily_trends"]) > 0
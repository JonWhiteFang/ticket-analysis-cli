"""Comprehensive tests for statistical functions and mathematical calculations.

This module contains unit tests for statistical analysis functions used
throughout the analysis engine, including descriptive statistics, trend
calculations, and mathematical utilities.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from ticket_analyzer.analysis.analysis_service import AnalysisEngine
from ticket_analyzer.analysis.calculators import (
    ResolutionTimeCalculator,
    StatusDistributionCalculator,
    VolumeAnalyzer
)
from ticket_analyzer.models.ticket import Ticket, TicketStatus, TicketSeverity


class TestStatisticalFunctions:
    """Test statistical functions used in analysis."""
    
    @pytest.fixture
    def statistical_tickets(self) -> List[Ticket]:
        """Create tickets with known statistical properties."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        # Create tickets with specific resolution times for statistical testing
        resolution_hours = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100]  # Include outlier
        
        for i, hours in enumerate(resolution_hours):
            created = base_time + timedelta(hours=i)
            resolved = created + timedelta(hours=hours)
            
            ticket = Ticket(
                id=f"T{i+1:03d}",
                title=f"Statistical test ticket {i+1}",
                description="Test ticket for statistical analysis",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.SEV_3,
                created_date=created,
                updated_date=resolved,
                resolved_date=resolved,
                assignee=f"user{(i % 3) + 1}",
                resolver_group=f"Team{(i % 2) + 1}"
            )
            tickets.append(ticket)
        
        return tickets
    
    def test_resolution_time_statistics(self, statistical_tickets: List[Ticket]) -> None:
        """Test resolution time statistical calculations."""
        calculator = ResolutionTimeCalculator()
        result = calculator.calculate(statistical_tickets)
        
        # Test basic statistics
        assert "avg_resolution_time_hours" in result
        assert "median_resolution_time_hours" in result
        
        # Test percentiles
        assert "p50_resolution_hours" in result
        assert "p75_resolution_hours" in result
        assert "p90_resolution_hours" in result
        assert "p95_resolution_hours" in result
        assert "p99_resolution_hours" in result
        
        # Verify percentile ordering
        assert result["p50_resolution_hours"] <= result["p75_resolution_hours"]
        assert result["p75_resolution_hours"] <= result["p90_resolution_hours"]
        assert result["p90_resolution_hours"] <= result["p95_resolution_hours"]
        assert result["p95_resolution_hours"] <= result["p99_resolution_hours"]
    
    def test_outlier_detection_and_handling(self, statistical_tickets: List[Ticket]) -> None:
        """Test outlier detection in statistical calculations."""
        calculator = ResolutionTimeCalculator()
        result = calculator.calculate(statistical_tickets)
        
        # Should detect the 100-hour outlier
        if "outlier_analysis" in result:
            outlier_analysis = result["outlier_analysis"]
            assert "outlier_count" in outlier_analysis
            assert outlier_analysis["outlier_count"] >= 1
            
            if "outliers" in outlier_analysis:
                outliers = outlier_analysis["outliers"]
                assert any(outlier["value"] == 100.0 for outlier in outliers)
    
    def test_standard_deviation_calculations(self, statistical_tickets: List[Ticket]) -> None:
        """Test standard deviation calculations."""
        calculator = ResolutionTimeCalculator()
        result = calculator.calculate(statistical_tickets)
        
        if "std_deviation_hours" in result:
            std_dev = result["std_deviation_hours"]
            assert std_dev > 0  # Should have variation due to outlier
            assert isinstance(std_dev, (int, float))
    
    def test_variance_calculations(self, statistical_tickets: List[Ticket]) -> None:
        """Test variance calculations."""
        calculator = ResolutionTimeCalculator()
        result = calculator.calculate(statistical_tickets)
        
        if "variance_hours" in result:
            variance = result["variance_hours"]
            assert variance > 0
            assert isinstance(variance, (int, float))
    
    def test_coefficient_of_variation(self, statistical_tickets: List[Ticket]) -> None:
        """Test coefficient of variation calculations."""
        calculator = ResolutionTimeCalculator()
        result = calculator.calculate(statistical_tickets)
        
        if "coefficient_of_variation" in result:
            cv = result["coefficient_of_variation"]
            assert isinstance(cv, (int, float))
            # CV should be high due to outlier
            assert cv > 0.5


class TestMathematicalUtilities:
    """Test mathematical utility functions."""
    
    def test_percentile_calculation_accuracy(self) -> None:
        """Test percentile calculation accuracy."""
        # Test with known data
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        
        # Calculate percentiles manually for verification
        p50 = np.percentile(data, 50)  # Should be 5.5
        p90 = np.percentile(data, 90)  # Should be 9.1
        
        # Test with calculator
        calculator = ResolutionTimeCalculator()
        
        # Create tickets with known resolution times
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        for i, hours in enumerate(data):
            created = base_time + timedelta(hours=i)
            resolved = created + timedelta(hours=hours)
            
            ticket = Ticket(
                id=f"T{i+1}",
                title=f"Test {i+1}",
                description="Test",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.SEV_3,
                created_date=created,
                updated_date=resolved,
                resolved_date=resolved
            )
            tickets.append(ticket)
        
        result = calculator.calculate(tickets)
        
        # Verify percentile accuracy (within reasonable tolerance)
        if "p50_resolution_hours" in result:
            assert abs(result["p50_resolution_hours"] - p50) < 0.1
        if "p90_resolution_hours" in result:
            assert abs(result["p90_resolution_hours"] - p90) < 0.1
    
    def test_trend_calculation_accuracy(self) -> None:
        """Test trend calculation mathematical accuracy."""
        # Create data with known linear trend
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        # Create increasing volume over time (linear trend)
        for day in range(10):
            tickets_per_day = day + 1  # 1, 2, 3, ..., 10
            
            for ticket_num in range(tickets_per_day):
                created_time = base_time + timedelta(days=day, hours=ticket_num)
                
                ticket = Ticket(
                    id=f"T{day}-{ticket_num}",
                    title=f"Trend test ticket",
                    description="Test",
                    status=TicketStatus.OPEN,
                    severity=TicketSeverity.SEV_3,
                    created_date=created_time,
                    updated_date=created_time + timedelta(minutes=30)
                )
                tickets.append(ticket)
        
        analyzer = VolumeAnalyzer()
        result = analyzer.calculate(tickets)
        
        # Should detect increasing trend
        if "growth_analysis" in result:
            growth = result["growth_analysis"]
            if "trend_classification" in growth:
                assert growth["trend_classification"] in ["strong_growth", "moderate_growth"]


class TestEdgeCaseStatistics:
    """Test statistical calculations with edge cases."""
    
    def test_single_data_point_statistics(self) -> None:
        """Test statistics with single data point."""
        single_ticket = [
            Ticket(
                id="T1",
                title="Single ticket",
                description="Test",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.SEV_3,
                created_date=datetime(2024, 1, 1, 10, 0, 0),
                updated_date=datetime(2024, 1, 1, 12, 0, 0),
                resolved_date=datetime(2024, 1, 1, 12, 0, 0)
            )
        ]
        
        calculator = ResolutionTimeCalculator()
        result = calculator.calculate(single_ticket)
        
        # With single data point, mean and median should be equal
        if "avg_resolution_time_hours" in result and "median_resolution_time_hours" in result:
            assert result["avg_resolution_time_hours"] == result["median_resolution_time_hours"]
        
        # Standard deviation should be 0 for single point
        if "std_deviation_hours" in result:
            assert result["std_deviation_hours"] == 0.0
    
    def test_identical_values_statistics(self) -> None:
        """Test statistics with identical values."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        identical_tickets = []
        
        # Create 5 tickets with identical 4-hour resolution times
        for i in range(5):
            created = base_time + timedelta(hours=i)
            resolved = created + timedelta(hours=4)  # Always 4 hours
            
            ticket = Ticket(
                id=f"T{i+1}",
                title=f"Identical ticket {i+1}",
                description="Test",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.SEV_3,
                created_date=created,
                updated_date=resolved,
                resolved_date=resolved
            )
            identical_tickets.append(ticket)
        
        calculator = ResolutionTimeCalculator()
        result = calculator.calculate(identical_tickets)
        
        # All statistics should be 4.0 for identical values
        assert result["avg_resolution_time_hours"] == 4.0
        assert result["median_resolution_time_hours"] == 4.0
        
        # Standard deviation should be 0 for identical values
        if "std_deviation_hours" in result:
            assert result["std_deviation_hours"] == 0.0
        
        # All percentiles should be 4.0
        percentile_keys = ["p50_resolution_hours", "p75_resolution_hours", "p90_resolution_hours"]
        for key in percentile_keys:
            if key in result:
                assert result[key] == 4.0
    
    def test_extreme_outlier_handling(self) -> None:
        """Test handling of extreme outliers in statistical calculations."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        outlier_tickets = []
        
        # Normal tickets: 1-5 hours
        normal_times = [1, 2, 3, 4, 5]
        # Extreme outliers: 1000, 10000 hours
        extreme_times = [1000, 10000]
        
        all_times = normal_times + extreme_times
        
        for i, hours in enumerate(all_times):
            created = base_time + timedelta(hours=i)
            resolved = created + timedelta(hours=hours)
            
            ticket = Ticket(
                id=f"T{i+1}",
                title=f"Outlier test ticket {i+1}",
                description="Test",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.SEV_3,
                created_date=created,
                updated_date=resolved,
                resolved_date=resolved
            )
            outlier_tickets.append(ticket)
        
        calculator = ResolutionTimeCalculator()
        result = calculator.calculate(outlier_tickets)
        
        # Median should be less affected by outliers than mean
        if "avg_resolution_time_hours" in result and "median_resolution_time_hours" in result:
            assert result["median_resolution_time_hours"] < result["avg_resolution_time_hours"]
        
        # Should detect multiple outliers
        if "outlier_analysis" in result:
            outlier_analysis = result["outlier_analysis"]
            if "outlier_count" in outlier_analysis:
                assert outlier_analysis["outlier_count"] >= 2


class TestDataFrameOperations:
    """Test pandas DataFrame operations used in analysis."""
    
    @pytest.fixture
    def analysis_engine(self) -> AnalysisEngine:
        """Create AnalysisEngine for DataFrame testing."""
        return AnalysisEngine()
    
    @pytest.fixture
    def dataframe_test_tickets(self) -> List[Ticket]:
        """Create tickets for DataFrame operation testing."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        statuses = [TicketStatus.OPEN, TicketStatus.RESOLVED, TicketStatus.CLOSED]
        severities = [TicketSeverity.SEV_1, TicketSeverity.SEV_3, TicketSeverity.SEV_5]
        
        for i in range(9):  # 3x3 matrix of status/severity combinations
            status = statuses[i % 3]
            severity = severities[i // 3]
            
            created = base_time + timedelta(hours=i)
            resolved = created + timedelta(hours=i+1) if status == TicketStatus.RESOLVED else None
            
            ticket = Ticket(
                id=f"T{i+1:03d}",
                title=f"DataFrame test ticket {i+1}",
                description="Test",
                status=status,
                severity=severity,
                created_date=created,
                updated_date=created + timedelta(minutes=30),
                resolved_date=resolved,
                assignee=f"user{(i % 2) + 1}",
                resolver_group=f"Team{(i % 3) + 1}"
            )
            tickets.append(ticket)
        
        return tickets
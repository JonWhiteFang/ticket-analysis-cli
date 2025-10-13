"""Tests for metrics calculator implementations.

This module contains comprehensive tests for all calculator classes,
covering metrics calculation, edge cases, and error handling according
to the testing standards.
"""

from __future__ import annotations
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import Counter

from ticket_analyzer.analysis.calculators import (
    ResolutionTimeCalculator,
    StatusDistributionCalculator,
    VolumeAnalyzer,
    SeverityAnalyzer,
    TeamPerformanceCalculator
)
from ticket_analyzer.models.ticket import Ticket, TicketStatus, TicketSeverity
from ticket_analyzer.models.exceptions import AnalysisError


class TestResolutionTimeCalculator:
    """Test cases for ResolutionTimeCalculator."""
    
    def test_calculate_with_resolved_tickets(self):
        """Test resolution time calculation with resolved tickets."""
        calculator = ResolutionTimeCalculator()
        
        # Create tickets with known resolution times
        tickets = [
            Ticket(
                id="T1",
                title="Test 1",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.HIGH,
                created_date=datetime(2024, 1, 1, 10, 0),
                resolved_date=datetime(2024, 1, 2, 14, 0)  # 28 hours
            ),
            Ticket(
                id="T2", 
                title="Test 2",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime(2024, 1, 1, 12, 0),
                resolved_date=datetime(2024, 1, 1, 16, 0)  # 4 hours
            ),
            Ticket(
                id="T3",
                title="Test 3", 
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.LOW,
                created_date=datetime(2024, 1, 1, 9, 0),
                resolved_date=datetime(2024, 1, 3, 9, 0)  # 48 hours
            )
        ]
        
        result = calculator.calculate(tickets)
        
        # Check basic statistics
        assert "avg_resolution_time_hours" in result
        assert "median_resolution_time_hours" in result
        assert "total_resolved_tickets" in result
        
        # Verify calculations
        expected_avg = (28 + 4 + 48) / 3  # 26.67 hours
        assert abs(result["avg_resolution_time_hours"] - expected_avg) < 0.1
        assert result["median_resolution_time_hours"] == 28.0
        assert result["total_resolved_tickets"] == 3
    
    def test_calculate_with_no_resolved_tickets(self):
        """Test resolution time calculation with no resolved tickets."""
        calculator = ResolutionTimeCalculator()
        
        tickets = [
            Ticket(
                id="T1",
                title="Open ticket",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime(2024, 1, 1)
            )
        ]
        
        result = calculator.calculate(tickets)
        
        assert result["avg_resolution_time_hours"] == 0
        assert result["median_resolution_time_hours"] == 0
        assert result["total_resolved_tickets"] == 0
    
    def test_calculate_with_empty_list(self):
        """Test resolution time calculation with empty ticket list."""
        calculator = ResolutionTimeCalculator()
        
        result = calculator.calculate([])
        
        assert result["avg_resolution_time_hours"] == 0
        assert result["median_resolution_time_hours"] == 0
        assert result["total_resolved_tickets"] == 0
    
    def test_calculate_by_severity_breakdown(self):
        """Test resolution time breakdown by severity."""
        calculator = ResolutionTimeCalculator()
        
        tickets = [
            Ticket(
                id="T1",
                title="High severity",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.HIGH,
                created_date=datetime(2024, 1, 1, 10, 0),
                resolved_date=datetime(2024, 1, 1, 12, 0)  # 2 hours
            ),
            Ticket(
                id="T2",
                title="High severity 2",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.HIGH,
                created_date=datetime(2024, 1, 1, 10, 0),
                resolved_date=datetime(2024, 1, 1, 14, 0)  # 4 hours
            ),
            Ticket(
                id="T3",
                title="Medium severity",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime(2024, 1, 1, 10, 0),
                resolved_date=datetime(2024, 1, 1, 18, 0)  # 8 hours
            )
        ]
        
        result = calculator.calculate(tickets)
        
        assert "resolution_time_by_severity" in result
        severity_breakdown = result["resolution_time_by_severity"]
        
        assert "HIGH" in severity_breakdown
        assert "MEDIUM" in severity_breakdown
        assert severity_breakdown["HIGH"] == 3.0  # Average of 2 and 4 hours
        assert severity_breakdown["MEDIUM"] == 8.0
    
    def test_calculate_with_invalid_dates(self):
        """Test handling of tickets with invalid resolution dates."""
        calculator = ResolutionTimeCalculator()
        
        tickets = [
            Ticket(
                id="T1",
                title="Invalid resolution date",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime(2024, 1, 2),  # Created after resolved
                resolved_date=datetime(2024, 1, 1)
            ),
            Ticket(
                id="T2",
                title="Valid ticket",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime(2024, 1, 1, 10, 0),
                resolved_date=datetime(2024, 1, 1, 12, 0)
            )
        ]
        
        result = calculator.calculate(tickets)
        
        # Should only count valid tickets
        assert result["total_resolved_tickets"] == 1
        assert result["avg_resolution_time_hours"] == 2.0
    
    def test_get_metric_names(self):
        """Test getting list of metric names."""
        calculator = ResolutionTimeCalculator()
        
        metric_names = calculator.get_metric_names()
        
        expected_metrics = [
            "avg_resolution_time_hours",
            "median_resolution_time_hours", 
            "total_resolved_tickets",
            "resolution_time_by_severity"
        ]
        
        for metric in expected_metrics:
            assert metric in metric_names


class TestStatusDistributionCalculator:
    """Test cases for StatusDistributionCalculator."""
    
    def test_calculate_status_distribution(self):
        """Test status distribution calculation."""
        calculator = StatusDistributionCalculator()
        
        tickets = [
            Ticket(id="T1", title="Open 1", status=TicketStatus.OPEN, 
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
            Ticket(id="T2", title="Open 2", status=TicketStatus.OPEN,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
            Ticket(id="T3", title="Resolved", status=TicketStatus.RESOLVED,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
            Ticket(id="T4", title="In Progress", status=TicketStatus.IN_PROGRESS,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
        ]
        
        result = calculator.calculate(tickets)
        
        assert "status_counts" in result
        assert "status_percentages" in result
        
        status_counts = result["status_counts"]
        status_percentages = result["status_percentages"]
        
        assert status_counts["OPEN"] == 2
        assert status_counts["RESOLVED"] == 1
        assert status_counts["IN_PROGRESS"] == 1
        
        assert status_percentages["OPEN"] == 50.0
        assert status_percentages["RESOLVED"] == 25.0
        assert status_percentages["IN_PROGRESS"] == 25.0
    
    def test_calculate_with_empty_list(self):
        """Test status distribution with empty ticket list."""
        calculator = StatusDistributionCalculator()
        
        result = calculator.calculate([])
        
        assert result["status_counts"] == {}
        assert result["status_percentages"] == {}
    
    def test_calculate_single_status(self):
        """Test status distribution with single status type."""
        calculator = StatusDistributionCalculator()
        
        tickets = [
            Ticket(id="T1", title="Open 1", status=TicketStatus.OPEN,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
            Ticket(id="T2", title="Open 2", status=TicketStatus.OPEN,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
        ]
        
        result = calculator.calculate(tickets)
        
        assert result["status_counts"]["OPEN"] == 2
        assert result["status_percentages"]["OPEN"] == 100.0
        assert len(result["status_counts"]) == 1
    
    def test_get_metric_names(self):
        """Test getting list of metric names."""
        calculator = StatusDistributionCalculator()
        
        metric_names = calculator.get_metric_names()
        
        expected_metrics = ["status_counts", "status_percentages"]
        for metric in expected_metrics:
            assert metric in metric_names


class TestVolumeAnalyzer:
    """Test cases for VolumeAnalyzer."""
    
    def test_calculate_volume_metrics(self):
        """Test volume metrics calculation."""
        calculator = VolumeAnalyzer()
        
        # Create tickets across different time periods
        base_date = datetime(2024, 1, 1)
        tickets = []
        
        # Week 1: 5 tickets
        for i in range(5):
            tickets.append(Ticket(
                id=f"T{i+1}",
                title=f"Ticket {i+1}",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.MEDIUM,
                created_date=base_date + timedelta(days=i)
            ))
        
        # Week 2: 3 tickets  
        for i in range(3):
            tickets.append(Ticket(
                id=f"T{i+6}",
                title=f"Ticket {i+6}",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.MEDIUM,
                created_date=base_date + timedelta(days=7+i)
            ))
        
        result = calculator.calculate(tickets)
        
        assert "total_tickets" in result
        assert "daily_average" in result
        assert "weekly_volumes" in result
        
        assert result["total_tickets"] == 8
        assert result["daily_average"] > 0
        assert len(result["weekly_volumes"]) >= 1
    
    def test_calculate_with_empty_list(self):
        """Test volume calculation with empty ticket list."""
        calculator = VolumeAnalyzer()
        
        result = calculator.calculate([])
        
        assert result["total_tickets"] == 0
        assert result["daily_average"] == 0
        assert result["weekly_volumes"] == {}
    
    def test_get_metric_names(self):
        """Test getting list of metric names."""
        calculator = VolumeAnalyzer()
        
        metric_names = calculator.get_metric_names()
        
        expected_metrics = ["total_tickets", "daily_average", "weekly_volumes"]
        for metric in expected_metrics:
            assert metric in metric_names


class TestSeverityAnalyzer:
    """Test cases for SeverityAnalyzer."""
    
    def test_calculate_severity_distribution(self):
        """Test severity distribution calculation."""
        calculator = SeverityAnalyzer()
        
        tickets = [
            Ticket(id="T1", title="High 1", status=TicketStatus.OPEN,
                  severity=TicketSeverity.HIGH, created_date=datetime.now()),
            Ticket(id="T2", title="High 2", status=TicketStatus.OPEN,
                  severity=TicketSeverity.HIGH, created_date=datetime.now()),
            Ticket(id="T3", title="Medium", status=TicketStatus.OPEN,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
            Ticket(id="T4", title="Low", status=TicketStatus.OPEN,
                  severity=TicketSeverity.LOW, created_date=datetime.now()),
        ]
        
        result = calculator.calculate(tickets)
        
        assert "severity_counts" in result
        assert "severity_percentages" in result
        
        severity_counts = result["severity_counts"]
        severity_percentages = result["severity_percentages"]
        
        assert severity_counts["HIGH"] == 2
        assert severity_counts["MEDIUM"] == 1
        assert severity_counts["LOW"] == 1
        
        assert severity_percentages["HIGH"] == 50.0
        assert severity_percentages["MEDIUM"] == 25.0
        assert severity_percentages["LOW"] == 25.0
    
    def test_calculate_with_empty_list(self):
        """Test severity analysis with empty ticket list."""
        calculator = SeverityAnalyzer()
        
        result = calculator.calculate([])
        
        assert result["severity_counts"] == {}
        assert result["severity_percentages"] == {}
    
    def test_get_metric_names(self):
        """Test getting list of metric names."""
        calculator = SeverityAnalyzer()
        
        metric_names = calculator.get_metric_names()
        
        expected_metrics = ["severity_counts", "severity_percentages"]
        for metric in expected_metrics:
            assert metric in metric_names


class TestTeamPerformanceCalculator:
    """Test cases for TeamPerformanceCalculator."""
    
    def test_calculate_team_performance(self):
        """Test team performance calculation."""
        calculator = TeamPerformanceCalculator()
        
        tickets = [
            Ticket(
                id="T1", title="Team A ticket 1", status=TicketStatus.RESOLVED,
                severity=TicketSeverity.MEDIUM, created_date=datetime(2024, 1, 1, 10, 0),
                resolved_date=datetime(2024, 1, 1, 12, 0), assignee="team_a_user1"
            ),
            Ticket(
                id="T2", title="Team A ticket 2", status=TicketStatus.RESOLVED,
                severity=TicketSeverity.MEDIUM, created_date=datetime(2024, 1, 1, 10, 0),
                resolved_date=datetime(2024, 1, 1, 14, 0), assignee="team_a_user2"
            ),
            Ticket(
                id="T3", title="Team B ticket", status=TicketStatus.RESOLVED,
                severity=TicketSeverity.MEDIUM, created_date=datetime(2024, 1, 1, 10, 0),
                resolved_date=datetime(2024, 1, 1, 16, 0), assignee="team_b_user1"
            ),
        ]
        
        result = calculator.calculate(tickets)
        
        assert "assignee_workload" in result
        assert "assignee_resolution_times" in result
        
        workload = result["assignee_workload"]
        resolution_times = result["assignee_resolution_times"]
        
        assert workload["team_a_user1"] == 1
        assert workload["team_a_user2"] == 1
        assert workload["team_b_user1"] == 1
        
        assert resolution_times["team_a_user1"] == 2.0  # 2 hours
        assert resolution_times["team_a_user2"] == 4.0  # 4 hours
        assert resolution_times["team_b_user1"] == 6.0  # 6 hours
    
    def test_calculate_with_unassigned_tickets(self):
        """Test team performance with unassigned tickets."""
        calculator = TeamPerformanceCalculator()
        
        tickets = [
            Ticket(
                id="T1", title="Assigned", status=TicketStatus.RESOLVED,
                severity=TicketSeverity.MEDIUM, created_date=datetime(2024, 1, 1, 10, 0),
                resolved_date=datetime(2024, 1, 1, 12, 0), assignee="user1"
            ),
            Ticket(
                id="T2", title="Unassigned", status=TicketStatus.OPEN,
                severity=TicketSeverity.MEDIUM, created_date=datetime(2024, 1, 1, 10, 0)
                # No assignee
            ),
        ]
        
        result = calculator.calculate(tickets)
        
        workload = result["assignee_workload"]
        
        assert workload["user1"] == 1
        assert "unassigned" in workload
        assert workload["unassigned"] == 1
    
    def test_calculate_with_empty_list(self):
        """Test team performance with empty ticket list."""
        calculator = TeamPerformanceCalculator()
        
        result = calculator.calculate([])
        
        assert result["assignee_workload"] == {}
        assert result["assignee_resolution_times"] == {}
    
    def test_get_metric_names(self):
        """Test getting list of metric names."""
        calculator = TeamPerformanceCalculator()
        
        metric_names = calculator.get_metric_names()
        
        expected_metrics = ["assignee_workload", "assignee_resolution_times"]
        for metric in expected_metrics:
            assert metric in metric_names


class TestCalculatorErrorHandling:
    """Test error handling across all calculators."""
    
    @pytest.mark.parametrize("calculator_class", [
        ResolutionTimeCalculator,
        StatusDistributionCalculator, 
        VolumeAnalyzer,
        SeverityAnalyzer,
        TeamPerformanceCalculator
    ])
    def test_calculator_handles_none_input(self, calculator_class):
        """Test that calculators handle None input gracefully."""
        calculator = calculator_class()
        
        with pytest.raises((ValueError, TypeError)):
            calculator.calculate(None)
    
    @pytest.mark.parametrize("calculator_class", [
        ResolutionTimeCalculator,
        StatusDistributionCalculator,
        VolumeAnalyzer, 
        SeverityAnalyzer,
        TeamPerformanceCalculator
    ])
    def test_calculator_handles_invalid_input_type(self, calculator_class):
        """Test that calculators handle invalid input types."""
        calculator = calculator_class()
        
        with pytest.raises((ValueError, TypeError)):
            calculator.calculate("not a list")
    
    @pytest.mark.parametrize("calculator_class", [
        ResolutionTimeCalculator,
        StatusDistributionCalculator,
        VolumeAnalyzer,
        SeverityAnalyzer, 
        TeamPerformanceCalculator
    ])
    def test_calculator_metric_names_not_empty(self, calculator_class):
        """Test that all calculators return non-empty metric names."""
        calculator = calculator_class()
        
        metric_names = calculator.get_metric_names()
        
        assert isinstance(metric_names, list)
        assert len(metric_names) > 0
        assert all(isinstance(name, str) for name in metric_names)


class TestCalculatorIntegration:
    """Integration tests for calculator combinations."""
    
    def test_multiple_calculators_same_data(self, sample_tickets):
        """Test multiple calculators on the same dataset."""
        calculators = [
            ResolutionTimeCalculator(),
            StatusDistributionCalculator(),
            VolumeAnalyzer(),
            SeverityAnalyzer(),
            TeamPerformanceCalculator()
        ]
        
        results = {}
        for calculator in calculators:
            calc_result = calculator.calculate(sample_tickets)
            results.update(calc_result)
        
        # Verify no metric name conflicts
        all_metric_names = []
        for calculator in calculators:
            all_metric_names.extend(calculator.get_metric_names())
        
        # Check for duplicates
        metric_counts = Counter(all_metric_names)
        duplicates = [name for name, count in metric_counts.items() if count > 1]
        assert len(duplicates) == 0, f"Duplicate metric names found: {duplicates}"
    
    def test_calculator_consistency_across_runs(self, sample_tickets):
        """Test that calculators produce consistent results across multiple runs."""
        calculator = ResolutionTimeCalculator()
        
        result1 = calculator.calculate(sample_tickets)
        result2 = calculator.calculate(sample_tickets)
        
        # Results should be identical
        assert result1 == result2
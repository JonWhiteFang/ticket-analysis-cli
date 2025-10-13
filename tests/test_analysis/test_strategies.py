"""Tests for analysis strategies module.

This module contains comprehensive tests for the MetricsCalculator base class
and strategy pattern implementation according to the testing standards.
"""

from __future__ import annotations
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from abc import ABC, abstractmethod

from ticket_analyzer.analysis.strategies import MetricsCalculator
from ticket_analyzer.models.ticket import Ticket, TicketStatus, TicketSeverity
from ticket_analyzer.models.exceptions import AnalysisError


class TestMetricsCalculator:
    """Test cases for MetricsCalculator base class."""
    
    def test_metrics_calculator_is_abstract(self):
        """Test that MetricsCalculator cannot be instantiated directly."""
        with pytest.raises(TypeError):
            MetricsCalculator()
    
    def test_metrics_calculator_interface_methods(self):
        """Test that MetricsCalculator defines required abstract methods."""
        # Check that abstract methods are defined
        assert hasattr(MetricsCalculator, 'calculate')
        assert hasattr(MetricsCalculator, 'get_metric_names')
        
        # Check that methods are abstract
        assert getattr(MetricsCalculator.calculate, '__isabstractmethod__', False)
        assert getattr(MetricsCalculator.get_metric_names, '__isabstractmethod__', False)


class ConcreteTestCalculator(MetricsCalculator):
    """Concrete implementation of MetricsCalculator for testing."""
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Test implementation of calculate method."""
        if not isinstance(tickets, list):
            raise ValueError("Tickets must be a list")
        
        return {
            "total_tickets": len(tickets),
            "test_metric": 42.0,
            "calculated_at": datetime.now().isoformat()
        }
    
    def get_metric_names(self) -> List[str]:
        """Test implementation of get_metric_names method."""
        return ["total_tickets", "test_metric", "calculated_at"]


class TestConcreteCalculatorImplementation:
    """Test concrete implementation of MetricsCalculator."""
    
    def test_concrete_calculator_instantiation(self):
        """Test that concrete calculator can be instantiated."""
        calculator = ConcreteTestCalculator()
        
        assert isinstance(calculator, MetricsCalculator)
        assert isinstance(calculator, ConcreteTestCalculator)
    
    def test_concrete_calculator_calculate_method(self, sample_tickets):
        """Test calculate method implementation."""
        calculator = ConcreteTestCalculator()
        
        result = calculator.calculate(sample_tickets)
        
        assert isinstance(result, dict)
        assert "total_tickets" in result
        assert "test_metric" in result
        assert "calculated_at" in result
        assert result["total_tickets"] == len(sample_tickets)
        assert result["test_metric"] == 42.0
    
    def test_concrete_calculator_get_metric_names(self):
        """Test get_metric_names method implementation."""
        calculator = ConcreteTestCalculator()
        
        metric_names = calculator.get_metric_names()
        
        assert isinstance(metric_names, list)
        assert len(metric_names) == 3
        assert "total_tickets" in metric_names
        assert "test_metric" in metric_names
        assert "calculated_at" in metric_names
    
    def test_concrete_calculator_calculate_empty_list(self):
        """Test calculate method with empty ticket list."""
        calculator = ConcreteTestCalculator()
        
        result = calculator.calculate([])
        
        assert result["total_tickets"] == 0
        assert result["test_metric"] == 42.0  # Should still return test value
    
    def test_concrete_calculator_calculate_invalid_input(self):
        """Test calculate method with invalid input."""
        calculator = ConcreteTestCalculator()
        
        with pytest.raises(ValueError, match="Tickets must be a list"):
            calculator.calculate("not a list")
    
    def test_concrete_calculator_calculate_none_input(self):
        """Test calculate method with None input."""
        calculator = ConcreteTestCalculator()
        
        with pytest.raises(ValueError, match="Tickets must be a list"):
            calculator.calculate(None)


class FailingTestCalculator(MetricsCalculator):
    """Calculator that always fails for testing error handling."""
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Implementation that always raises an exception."""
        raise AnalysisError("Test calculator failure")
    
    def get_metric_names(self) -> List[str]:
        """Return metric names for failing calculator."""
        return ["failing_metric"]


class TestFailingCalculatorImplementation:
    """Test calculator that fails for error handling scenarios."""
    
    def test_failing_calculator_instantiation(self):
        """Test that failing calculator can be instantiated."""
        calculator = FailingTestCalculator()
        
        assert isinstance(calculator, MetricsCalculator)
        assert isinstance(calculator, FailingTestCalculator)
    
    def test_failing_calculator_raises_exception(self, sample_tickets):
        """Test that failing calculator raises expected exception."""
        calculator = FailingTestCalculator()
        
        with pytest.raises(AnalysisError, match="Test calculator failure"):
            calculator.calculate(sample_tickets)
    
    def test_failing_calculator_get_metric_names(self):
        """Test get_metric_names works even when calculate fails."""
        calculator = FailingTestCalculator()
        
        metric_names = calculator.get_metric_names()
        
        assert isinstance(metric_names, list)
        assert "failing_metric" in metric_names


class ComplexTestCalculator(MetricsCalculator):
    """More complex calculator for testing advanced scenarios."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with optional configuration."""
        self._config = config or {}
        self._calculation_count = 0
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Complex calculation with configuration and state."""
        if not isinstance(tickets, list):
            raise ValueError("Tickets must be a list")
        
        self._calculation_count += 1
        
        # Filter tickets based on configuration
        min_severity = self._config.get('min_severity', TicketSeverity.LOW)
        filtered_tickets = [
            ticket for ticket in tickets 
            if ticket.severity.value >= min_severity.value
        ]
        
        # Calculate metrics
        total_tickets = len(filtered_tickets)
        open_tickets = len([t for t in filtered_tickets if t.status == TicketStatus.OPEN])
        resolved_tickets = len([t for t in filtered_tickets if t.status == TicketStatus.RESOLVED])
        
        # Calculate resolution rate
        resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0
        
        return {
            "total_filtered_tickets": total_tickets,
            "open_tickets": open_tickets,
            "resolved_tickets": resolved_tickets,
            "resolution_rate_percent": resolution_rate,
            "calculation_count": self._calculation_count,
            "config_applied": bool(self._config)
        }
    
    def get_metric_names(self) -> List[str]:
        """Return list of metrics this calculator provides."""
        return [
            "total_filtered_tickets",
            "open_tickets", 
            "resolved_tickets",
            "resolution_rate_percent",
            "calculation_count",
            "config_applied"
        ]
    
    def reset_calculation_count(self) -> None:
        """Reset the calculation counter."""
        self._calculation_count = 0
    
    def get_calculation_count(self) -> int:
        """Get current calculation count."""
        return self._calculation_count


class TestComplexCalculatorImplementation:
    """Test complex calculator with configuration and state."""
    
    def test_complex_calculator_default_initialization(self):
        """Test complex calculator with default configuration."""
        calculator = ComplexTestCalculator()
        
        assert calculator._config == {}
        assert calculator._calculation_count == 0
    
    def test_complex_calculator_custom_configuration(self):
        """Test complex calculator with custom configuration."""
        config = {"min_severity": TicketSeverity.HIGH}
        calculator = ComplexTestCalculator(config)
        
        assert calculator._config == config
    
    def test_complex_calculator_calculate_with_filtering(self):
        """Test calculation with severity filtering."""
        config = {"min_severity": TicketSeverity.HIGH}
        calculator = ComplexTestCalculator(config)
        
        tickets = [
            Ticket(id="T1", title="High", status=TicketStatus.OPEN, 
                  severity=TicketSeverity.HIGH, created_date=datetime.now()),
            Ticket(id="T2", title="Medium", status=TicketStatus.RESOLVED,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
            Ticket(id="T3", title="High 2", status=TicketStatus.RESOLVED,
                  severity=TicketSeverity.HIGH, created_date=datetime.now()),
        ]
        
        result = calculator.calculate(tickets)
        
        # Should only count HIGH severity tickets (2 out of 3)
        assert result["total_filtered_tickets"] == 2
        assert result["open_tickets"] == 1
        assert result["resolved_tickets"] == 1
        assert result["resolution_rate_percent"] == 50.0
        assert result["calculation_count"] == 1
        assert result["config_applied"] is True
    
    def test_complex_calculator_state_tracking(self):
        """Test calculation count state tracking."""
        calculator = ComplexTestCalculator()
        
        tickets = [
            Ticket(id="T1", title="Test", status=TicketStatus.OPEN,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now())
        ]
        
        # First calculation
        result1 = calculator.calculate(tickets)
        assert result1["calculation_count"] == 1
        
        # Second calculation
        result2 = calculator.calculate(tickets)
        assert result2["calculation_count"] == 2
        
        # Reset counter
        calculator.reset_calculation_count()
        assert calculator.get_calculation_count() == 0
        
        # Third calculation after reset
        result3 = calculator.calculate(tickets)
        assert result3["calculation_count"] == 1
    
    def test_complex_calculator_resolution_rate_calculation(self):
        """Test resolution rate calculation accuracy."""
        calculator = ComplexTestCalculator()
        
        tickets = [
            Ticket(id="T1", title="Open 1", status=TicketStatus.OPEN,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
            Ticket(id="T2", title="Open 2", status=TicketStatus.OPEN,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
            Ticket(id="T3", title="Resolved 1", status=TicketStatus.RESOLVED,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
            Ticket(id="T4", title="Resolved 2", status=TicketStatus.RESOLVED,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
            Ticket(id="T5", title="Resolved 3", status=TicketStatus.RESOLVED,
                  severity=TicketSeverity.MEDIUM, created_date=datetime.now()),
        ]
        
        result = calculator.calculate(tickets)
        
        # 3 resolved out of 5 total = 60%
        assert result["total_filtered_tickets"] == 5
        assert result["open_tickets"] == 2
        assert result["resolved_tickets"] == 3
        assert result["resolution_rate_percent"] == 60.0
    
    def test_complex_calculator_empty_tickets_resolution_rate(self):
        """Test resolution rate calculation with empty ticket list."""
        calculator = ComplexTestCalculator()
        
        result = calculator.calculate([])
        
        assert result["total_filtered_tickets"] == 0
        assert result["open_tickets"] == 0
        assert result["resolved_tickets"] == 0
        assert result["resolution_rate_percent"] == 0
    
    def test_complex_calculator_get_metric_names(self):
        """Test get_metric_names returns all expected metrics."""
        calculator = ComplexTestCalculator()
        
        metric_names = calculator.get_metric_names()
        
        expected_metrics = [
            "total_filtered_tickets",
            "open_tickets",
            "resolved_tickets", 
            "resolution_rate_percent",
            "calculation_count",
            "config_applied"
        ]
        
        assert len(metric_names) == len(expected_metrics)
        for metric in expected_metrics:
            assert metric in metric_names


class TestStrategyPatternImplementation:
    """Test strategy pattern implementation with multiple calculators."""
    
    def test_multiple_calculator_types(self, sample_tickets):
        """Test using multiple different calculator implementations."""
        calculators = [
            ConcreteTestCalculator(),
            ComplexTestCalculator(),
            ComplexTestCalculator({"min_severity": TicketSeverity.HIGH})
        ]
        
        results = {}
        for calculator in calculators:
            calc_result = calculator.calculate(sample_tickets)
            calc_name = calculator.__class__.__name__
            results[calc_name] = calc_result
        
        # All calculators should return results
        assert len(results) == 3
        assert "ConcreteTestCalculator" in results
        assert "ComplexTestCalculator" in results
        
        # Results should be different based on implementation
        concrete_result = results["ConcreteTestCalculator"]
        complex_result = list(results.values())[1]  # First ComplexTestCalculator
        
        assert concrete_result["test_metric"] == 42.0
        assert "resolution_rate_percent" in complex_result
    
    def test_calculator_polymorphism(self, sample_tickets):
        """Test polymorphic behavior of calculator implementations."""
        calculators: List[MetricsCalculator] = [
            ConcreteTestCalculator(),
            ComplexTestCalculator()
        ]
        
        # Should be able to call calculate on all calculators polymorphically
        for calculator in calculators:
            result = calculator.calculate(sample_tickets)
            metric_names = calculator.get_metric_names()
            
            assert isinstance(result, dict)
            assert isinstance(metric_names, list)
            assert len(metric_names) > 0
    
    def test_calculator_interface_consistency(self):
        """Test that all calculator implementations follow interface consistently."""
        calculator_classes = [
            ConcreteTestCalculator,
            ComplexTestCalculator,
            FailingTestCalculator
        ]
        
        for calc_class in calculator_classes:
            calculator = calc_class()
            
            # All should have calculate method
            assert hasattr(calculator, 'calculate')
            assert callable(getattr(calculator, 'calculate'))
            
            # All should have get_metric_names method
            assert hasattr(calculator, 'get_metric_names')
            assert callable(getattr(calculator, 'get_metric_names'))
            
            # get_metric_names should work without exceptions
            metric_names = calculator.get_metric_names()
            assert isinstance(metric_names, list)


class TestCalculatorErrorHandling:
    """Test error handling across calculator implementations."""
    
    def test_calculator_input_validation(self):
        """Test input validation across different calculators."""
        calculators = [
            ConcreteTestCalculator(),
            ComplexTestCalculator()
        ]
        
        invalid_inputs = [None, "not a list", 123, {"not": "list"}]
        
        for calculator in calculators:
            for invalid_input in invalid_inputs:
                with pytest.raises((ValueError, TypeError)):
                    calculator.calculate(invalid_input)
    
    def test_calculator_exception_propagation(self, sample_tickets):
        """Test that calculator exceptions are properly propagated."""
        calculator = FailingTestCalculator()
        
        with pytest.raises(AnalysisError, match="Test calculator failure"):
            calculator.calculate(sample_tickets)
    
    def test_calculator_graceful_degradation(self):
        """Test calculator behavior with edge case inputs."""
        calculator = ComplexTestCalculator()
        
        # Test with tickets having None values
        edge_case_tickets = [
            Ticket(
                id="T1",
                title="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime.now(),
                assignee=None  # None assignee
            )
        ]
        
        # Should handle gracefully without exceptions
        result = calculator.calculate(edge_case_tickets)
        
        assert isinstance(result, dict)
        assert result["total_filtered_tickets"] == 1


class TestCalculatorPerformance:
    """Test performance aspects of calculator implementations."""
    
    def test_calculator_performance_large_dataset(self):
        """Test calculator performance with large dataset."""
        calculator = ComplexTestCalculator()
        
        # Create large dataset
        large_tickets = []
        for i in range(1000):
            ticket = Ticket(
                id=f"T{i:06d}",
                title=f"Ticket {i}",
                status=TicketStatus.OPEN if i % 2 == 0 else TicketStatus.RESOLVED,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime.now() - timedelta(days=i % 30)
            )
            large_tickets.append(ticket)
        
        # Should complete without timeout
        result = calculator.calculate(large_tickets)
        
        assert result["total_filtered_tickets"] == 1000
        assert isinstance(result["resolution_rate_percent"], (int, float))
    
    def test_calculator_memory_efficiency(self):
        """Test calculator memory efficiency."""
        calculator = ComplexTestCalculator()
        
        # Process tickets in batches to test memory usage
        for batch in range(10):
            batch_tickets = []
            for i in range(100):
                ticket = Ticket(
                    id=f"T{batch:02d}{i:03d}",
                    title=f"Batch {batch} Ticket {i}",
                    status=TicketStatus.OPEN,
                    severity=TicketSeverity.MEDIUM,
                    created_date=datetime.now()
                )
                batch_tickets.append(ticket)
            
            result = calculator.calculate(batch_tickets)
            assert result["total_filtered_tickets"] == 100
        
        # Should complete without memory issues
        assert calculator.get_calculation_count() == 10
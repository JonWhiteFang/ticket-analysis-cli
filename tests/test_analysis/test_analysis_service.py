"""Tests for the analysis service module.

This module contains comprehensive tests for the AnalysisEngine class,
covering metrics calculation, data processing, error handling, and
edge cases according to the testing standards.
"""

from __future__ import annotations
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

import pandas as pd

from ticket_analyzer.analysis.analysis_service import AnalysisEngine
from ticket_analyzer.analysis.strategies import MetricsCalculator
from ticket_analyzer.models.ticket import Ticket, TicketStatus, TicketSeverity
from ticket_analyzer.models.analysis import AnalysisResult
from ticket_analyzer.models.exceptions import AnalysisError, DataProcessingError


class TestAnalysisEngine:
    """Test cases for AnalysisEngine class."""
    
    def test_engine_initialization(self):
        """Test analysis engine initialization."""
        engine = AnalysisEngine()
        
        assert engine._calculators == []
        assert engine._data_processor is not None
        assert engine._performance_monitor is not None
    
    def test_add_calculator_success(self):
        """Test successful calculator addition."""
        engine = AnalysisEngine()
        calculator = Mock(spec=MetricsCalculator)
        
        engine.add_calculator(calculator)
        
        assert len(engine._calculators) == 1
        assert calculator in engine._calculators
    
    def test_add_calculator_none_raises_error(self):
        """Test adding None calculator raises ValueError."""
        engine = AnalysisEngine()
        
        with pytest.raises(ValueError, match="Calculator cannot be None"):
            engine.add_calculator(None)
    
    def test_add_calculator_invalid_type_raises_error(self):
        """Test adding invalid calculator type raises ValueError."""
        engine = AnalysisEngine()
        invalid_calculator = "not a calculator"
        
        with pytest.raises(ValueError, match="Calculator must implement MetricsCalculator interface"):
            engine.add_calculator(invalid_calculator)
    
    def test_remove_calculator_success(self):
        """Test successful calculator removal."""
        engine = AnalysisEngine()
        calculator = Mock(spec=MetricsCalculator)
        engine.add_calculator(calculator)
        
        result = engine.remove_calculator(type(calculator))
        
        assert result is True
        assert len(engine._calculators) == 0
    
    def test_remove_calculator_not_found(self):
        """Test removing non-existent calculator returns False."""
        engine = AnalysisEngine()
        
        result = engine.remove_calculator(Mock)
        
        assert result is False
    
    def test_get_calculators_empty(self):
        """Test getting calculators when none are registered."""
        engine = AnalysisEngine()
        
        calculators = engine.get_calculators()
        
        assert calculators == []
    
    def test_get_calculators_with_registered(self):
        """Test getting calculators when some are registered."""
        engine = AnalysisEngine()
        calculator1 = Mock(spec=MetricsCalculator)
        calculator1.__class__.__name__ = "TestCalculator1"
        calculator2 = Mock(spec=MetricsCalculator)
        calculator2.__class__.__name__ = "TestCalculator2"
        
        engine.add_calculator(calculator1)
        engine.add_calculator(calculator2)
        
        calculators = engine.get_calculators()
        
        assert "TestCalculator1" in calculators
        assert "TestCalculator2" in calculators
        assert len(calculators) == 2
    
    def test_analyze_tickets_invalid_input_type(self):
        """Test analyze_tickets with invalid input type raises ValueError."""
        engine = AnalysisEngine()
        
        with pytest.raises(ValueError, match="Tickets must be a list"):
            engine.analyze_tickets("not a list")
    
    def test_analyze_tickets_empty_list(self):
        """Test analyze_tickets with empty list returns empty result."""
        engine = AnalysisEngine()
        
        result = engine.analyze_tickets([])
        
        assert isinstance(result, AnalysisResult)
        assert result.ticket_count == 0
        assert result.metrics == {}
    
    @patch('ticket_analyzer.analysis.analysis_service.logger')
    def test_analyze_tickets_no_valid_tickets(self, mock_logger):
        """Test analyze_tickets when no tickets pass validation."""
        engine = AnalysisEngine()
        invalid_tickets = [Mock()]  # Mock tickets that will fail validation
        
        with patch.object(engine, '_validate_and_process_tickets', return_value=[]):
            result = engine.analyze_tickets(invalid_tickets)
        
        assert isinstance(result, AnalysisResult)
        assert result.ticket_count == 0
        mock_logger.warning.assert_called_once_with("No valid tickets found for analysis")
    
    def test_analyze_tickets_success_with_calculators(self, sample_tickets):
        """Test successful ticket analysis with registered calculators."""
        engine = AnalysisEngine()
        
        # Mock calculator
        calculator = Mock(spec=MetricsCalculator)
        calculator.calculate.return_value = {"test_metric": 42.0}
        calculator.get_metric_names.return_value = ["test_metric"]
        engine.add_calculator(calculator)
        
        # Mock internal methods
        with patch.object(engine, '_validate_and_process_tickets', return_value=sample_tickets), \
             patch.object(engine, '_create_dataframe') as mock_df, \
             patch.object(engine, '_generate_trends_analysis', return_value={}), \
             patch.object(engine, '_generate_summary_insights', return_value={}):
            
            result = engine.analyze_tickets(sample_tickets)
        
        assert isinstance(result, AnalysisResult)
        assert result.ticket_count == len(sample_tickets)
        assert "test_metric" in result.metrics
        assert result.metrics["test_metric"] == 42.0
        calculator.calculate.assert_called_once_with(sample_tickets)
    
    def test_analyze_tickets_calculator_error_handling(self, sample_tickets):
        """Test error handling when calculator fails."""
        engine = AnalysisEngine()
        
        # Mock calculator that raises exception
        calculator = Mock(spec=MetricsCalculator)
        calculator.calculate.side_effect = Exception("Calculator error")
        calculator.get_metric_names.return_value = ["test_metric"]
        engine.add_calculator(calculator)
        
        with patch.object(engine, '_validate_and_process_tickets', return_value=sample_tickets), \
             patch.object(engine, '_create_dataframe'), \
             patch.object(engine, '_generate_trends_analysis', return_value={}), \
             patch.object(engine, '_generate_summary_insights', return_value={}):
            
            with pytest.raises(AnalysisError):
                engine.analyze_tickets(sample_tickets)
    
    def test_create_dataframe_from_tickets(self, sample_tickets):
        """Test DataFrame creation from ticket data."""
        engine = AnalysisEngine()
        
        df = engine._create_dataframe(sample_tickets)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(sample_tickets)
        assert "id" in df.columns
        assert "status" in df.columns
        assert "created_date" in df.columns
    
    def test_create_dataframe_empty_tickets(self):
        """Test DataFrame creation with empty ticket list."""
        engine = AnalysisEngine()
        
        df = engine._create_dataframe([])
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
    
    def test_validate_and_process_tickets_success(self, sample_tickets):
        """Test successful ticket validation and processing."""
        engine = AnalysisEngine()
        
        with patch.object(engine._data_processor, 'validate_ticket', return_value=True), \
             patch.object(engine._data_processor, 'process_ticket', side_effect=lambda x: x):
            
            result = engine._validate_and_process_tickets(sample_tickets)
        
        assert len(result) == len(sample_tickets)
        assert all(isinstance(ticket, Ticket) for ticket in result)
    
    def test_validate_and_process_tickets_filters_invalid(self, sample_tickets):
        """Test ticket validation filters out invalid tickets."""
        engine = AnalysisEngine()
        
        # Mock validation to fail for some tickets
        def mock_validate(ticket):
            return ticket.id != "T123456"  # Fail validation for specific ticket
        
        with patch.object(engine._data_processor, 'validate_ticket', side_effect=mock_validate), \
             patch.object(engine._data_processor, 'process_ticket', side_effect=lambda x: x):
            
            result = engine._validate_and_process_tickets(sample_tickets)
        
        # Should filter out the invalid ticket
        assert len(result) < len(sample_tickets)
        assert all(ticket.id != "T123456" for ticket in result)
    
    def test_calculate_all_metrics_success(self, sample_tickets):
        """Test successful metrics calculation with multiple calculators."""
        engine = AnalysisEngine()
        
        # Add multiple calculators
        calc1 = Mock(spec=MetricsCalculator)
        calc1.calculate.return_value = {"metric1": 10.0, "metric2": 20.0}
        calc2 = Mock(spec=MetricsCalculator)
        calc2.calculate.return_value = {"metric3": 30.0}
        
        engine.add_calculator(calc1)
        engine.add_calculator(calc2)
        
        result = engine._calculate_all_metrics(sample_tickets)
        
        assert result["metric1"] == 10.0
        assert result["metric2"] == 20.0
        assert result["metric3"] == 30.0
        calc1.calculate.assert_called_once_with(sample_tickets)
        calc2.calculate.assert_called_once_with(sample_tickets)
    
    def test_calculate_all_metrics_no_calculators(self, sample_tickets):
        """Test metrics calculation with no registered calculators."""
        engine = AnalysisEngine()
        
        result = engine._calculate_all_metrics(sample_tickets)
        
        assert result == {}
    
    def test_calculate_all_metrics_calculator_exception(self, sample_tickets):
        """Test metrics calculation when calculator raises exception."""
        engine = AnalysisEngine()
        
        calculator = Mock(spec=MetricsCalculator)
        calculator.calculate.side_effect = Exception("Calculation failed")
        calculator.__class__.__name__ = "FailingCalculator"
        engine.add_calculator(calculator)
        
        with pytest.raises(AnalysisError, match="Metrics calculation failed"):
            engine._calculate_all_metrics(sample_tickets)
    
    def test_generate_trends_analysis_success(self, sample_tickets):
        """Test successful trends analysis generation."""
        engine = AnalysisEngine()
        df = pd.DataFrame([
            {"created_date": datetime(2024, 1, 1), "status": "Open"},
            {"created_date": datetime(2024, 1, 2), "status": "Resolved"},
        ])
        
        with patch('ticket_analyzer.analysis.trends.TrendAnalyzer') as mock_analyzer:
            mock_instance = Mock()
            mock_instance.analyze_trends.return_value = {"trend_data": "test"}
            mock_analyzer.return_value = mock_instance
            
            result = engine._generate_trends_analysis(df, sample_tickets)
        
        assert "trend_data" in result
        mock_instance.analyze_trends.assert_called_once()
    
    def test_generate_summary_insights_success(self, sample_tickets):
        """Test successful summary insights generation."""
        engine = AnalysisEngine()
        metrics = {"avg_resolution_time": 24.5, "total_tickets": 100}
        
        result = engine._generate_summary_insights(metrics, sample_tickets)
        
        assert isinstance(result, dict)
        assert "total_tickets" in result
        assert "analysis_period" in result
        assert "key_insights" in result
    
    def test_create_empty_result(self):
        """Test creation of empty analysis result."""
        engine = AnalysisEngine()
        tickets = []
        
        result = engine._create_empty_result(tickets)
        
        assert isinstance(result, AnalysisResult)
        assert result.ticket_count == 0
        assert result.metrics == {}
        assert result.trends == {}
        assert result.summary == {}
    
    @patch('ticket_analyzer.analysis.analysis_service.logger')
    def test_performance_monitoring_integration(self, mock_logger, sample_tickets):
        """Test performance monitoring during analysis."""
        engine = AnalysisEngine()
        
        with patch.object(engine._performance_monitor, 'start_timing') as mock_start, \
             patch.object(engine._performance_monitor, 'end_timing') as mock_end, \
             patch.object(engine, '_validate_and_process_tickets', return_value=sample_tickets), \
             patch.object(engine, '_create_dataframe'), \
             patch.object(engine, '_calculate_all_metrics', return_value={}), \
             patch.object(engine, '_generate_trends_analysis', return_value={}), \
             patch.object(engine, '_generate_summary_insights', return_value={}):
            
            engine.analyze_tickets(sample_tickets)
        
        mock_start.assert_called()
        mock_end.assert_called()
    
    def test_memory_efficiency_large_dataset(self):
        """Test memory efficiency with large datasets."""
        engine = AnalysisEngine()
        
        # Create large dataset
        large_tickets = []
        for i in range(1000):
            ticket = Ticket(
                id=f"T{i:06d}",
                title=f"Test ticket {i}",
                status=TicketStatus.OPEN if i % 2 == 0 else TicketStatus.RESOLVED,
                severity=TicketSeverity.MEDIUM,
                created_date=datetime.now() - timedelta(days=i % 365)
            )
            large_tickets.append(ticket)
        
        # Mock processing to avoid actual heavy computation
        with patch.object(engine, '_validate_and_process_tickets', return_value=large_tickets[:100]), \
             patch.object(engine, '_create_dataframe') as mock_df, \
             patch.object(engine, '_calculate_all_metrics', return_value={}), \
             patch.object(engine, '_generate_trends_analysis', return_value={}), \
             patch.object(engine, '_generate_summary_insights', return_value={}):
            
            result = engine.analyze_tickets(large_tickets)
        
        assert isinstance(result, AnalysisResult)
        mock_df.assert_called_once()


class TestAnalysisEngineIntegration:
    """Integration tests for AnalysisEngine with real calculators."""
    
    def test_full_analysis_workflow_with_real_calculators(self, sample_tickets):
        """Test complete analysis workflow with actual calculator implementations."""
        from ticket_analyzer.analysis.calculators import (
            ResolutionTimeCalculator, 
            StatusDistributionCalculator
        )
        
        engine = AnalysisEngine()
        engine.add_calculator(ResolutionTimeCalculator())
        engine.add_calculator(StatusDistributionCalculator())
        
        # Mock only the data processor to avoid external dependencies
        with patch.object(engine._data_processor, 'validate_ticket', return_value=True), \
             patch.object(engine._data_processor, 'process_ticket', side_effect=lambda x: x):
            
            result = engine.analyze_tickets(sample_tickets)
        
        assert isinstance(result, AnalysisResult)
        assert result.ticket_count > 0
        assert len(result.metrics) > 0
        
        # Check for expected metrics from calculators
        assert any("resolution" in key.lower() for key in result.metrics.keys())
        assert any("status" in key.lower() for key in result.metrics.keys())
    
    def test_error_recovery_with_partial_calculator_failure(self, sample_tickets):
        """Test error recovery when some calculators fail."""
        from ticket_analyzer.analysis.calculators import StatusDistributionCalculator
        
        engine = AnalysisEngine()
        
        # Add working calculator
        engine.add_calculator(StatusDistributionCalculator())
        
        # Add failing calculator
        failing_calc = Mock(spec=MetricsCalculator)
        failing_calc.calculate.side_effect = Exception("Calculator failed")
        failing_calc.__class__.__name__ = "FailingCalculator"
        engine.add_calculator(failing_calc)
        
        with patch.object(engine._data_processor, 'validate_ticket', return_value=True), \
             patch.object(engine._data_processor, 'process_ticket', side_effect=lambda x: x):
            
            # Should raise AnalysisError due to failing calculator
            with pytest.raises(AnalysisError):
                engine.analyze_tickets(sample_tickets)
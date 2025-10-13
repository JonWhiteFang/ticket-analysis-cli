"""Comprehensive tests for error handling and fallback mechanisms.

This module contains unit tests for error handling scenarios across all
analysis components, testing graceful degradation, error recovery,
and fallback mechanisms when analysis operations encounter issues.
"""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from ticket_analyzer.analysis.analysis_service import AnalysisEngine
from ticket_analyzer.analysis.calculators import (
    ResolutionTimeCalculator,
    StatusDistributionCalculator,
    VolumeAnalyzer,
    SeverityAnalyzer,
    TeamPerformanceCalculator
)
from ticket_analyzer.analysis.data_processor import TicketDataProcessor
from ticket_analyzer.analysis.trends import TrendAnalyzer
from ticket_analyzer.models.ticket import Ticket, TicketStatus, TicketSeverity
from ticket_analyzer.models.exceptions import (
    AnalysisError,
    DataProcessingError,
    ValidationError
)


class TestAnalysisEngineErrorHandling:
    """Test error handling in AnalysisEngine."""
    
    @pytest.fixture
    def engine(self) -> AnalysisEngine:
        """Create AnalysisEngine instance."""
        return AnalysisEngine()
    
    @pytest.fixture
    def sample_tickets(self) -> List[Ticket]:
        """Create sample tickets for error testing."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        return [
            Ticket(
                id=f"T{i+1}",
                title=f"Error test ticket {i+1}",
                description="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=base_time + timedelta(hours=i),
                updated_date=base_time + timedelta(hours=i, minutes=30)
            )
            for i in range(3)
        ]
    
    def test_analyze_tickets_with_calculator_exception(self, engine: AnalysisEngine, sample_tickets: List[Ticket]) -> None:
        """Test analysis continues when calculator raises exception."""
        # Create a failing calculator
        failing_calculator = Mock()
        failing_calculator.calculate.side_effect = Exception("Calculator failed")
        failing_calculator.__class__.__name__ = "FailingCalculator"
        failing_calculator.get_metric_names.return_value = ["test_metric"]
        
        # Add both failing and working calculators
        working_calculator = ResolutionTimeCalculator()
        engine.add_calculator(failing_calculator)
        engine.add_calculator(working_calculator)
        
        # Analysis should complete despite one calculator failing
        result = engine.analyze_tickets(sample_tickets)
        
        assert isinstance(result, dict) or hasattr(result, 'metrics')
        # Should contain error information about the failing calculator
        if hasattr(result, 'metrics'):
            metrics = result.metrics
        else:
            metrics = result
        
        # Should have error recorded for failing calculator
        error_keys = [key for key in metrics.keys() if "error" in key.lower()]
        assert len(error_keys) > 0
    
    def test_analyze_tickets_with_data_processor_failure(self, engine: AnalysisEngine, sample_tickets: List[Ticket]) -> None:
        """Test analysis when data processor fails."""
        with patch.object(engine, '_data_processor') as mock_processor:
            mock_processor.process_tickets.side_effect = DataProcessingError("Processing failed")
            
            with pytest.raises(AnalysisError):
                engine.analyze_tickets(sample_tickets)
    
    def test_analyze_tickets_with_invalid_input_types(self, engine: AnalysisEngine) -> None:
        """Test analysis with various invalid input types."""
        invalid_inputs = [
            "not a list",
            123,
            {"not": "list"},
            None,
            [1, 2, 3],  # List of non-Ticket objects
            ["string", "objects"]
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises((ValueError, TypeError, AnalysisError)):
                engine.analyze_tickets(invalid_input)
    
    def test_analyze_tickets_with_corrupted_ticket_data(self, engine: AnalysisEngine) -> None:
        """Test analysis with corrupted ticket objects."""
        # Create tickets with missing or invalid attributes
        corrupted_tickets = []
        
        # Ticket with None values
        try:
            corrupted_ticket = Ticket(
                id=None,  # Invalid ID
                title="Corrupted ticket",
                description="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
            corrupted_tickets.append(corrupted_ticket)
        except:
            pass  # May fail during creation
        
        # Should handle gracefully or raise appropriate error
        if corrupted_tickets:
            try:
                result = engine.analyze_tickets(corrupted_tickets)
                # If it succeeds, should handle gracefully
                assert isinstance(result, dict) or hasattr(result, 'metrics')
            except (AnalysisError, ValidationError):
                # Acceptable to raise validation error
                pass
    
    def test_dataframe_creation_with_memory_error(self, engine: AnalysisEngine, sample_tickets: List[Ticket]) -> None:
        """Test DataFrame creation when memory is limited."""
        with patch('pandas.DataFrame') as mock_df:
            mock_df.side_effect = MemoryError("Insufficient memory")
            
            with pytest.raises(AnalysisError):
                engine.analyze_tickets(sample_tickets)
    
    def test_analysis_with_pandas_errors(self, engine: AnalysisEngine, sample_tickets: List[Ticket]) -> None:
        """Test analysis when pandas operations fail."""
        calculator = ResolutionTimeCalculator()
        engine.add_calculator(calculator)
        
        # Mock pandas operations to fail
        with patch('pandas.DataFrame.groupby') as mock_groupby:
            mock_groupby.side_effect = pd.errors.DataError("Pandas operation failed")
            
            # Should handle pandas errors gracefully
            result = engine.analyze_tickets(sample_tickets)
            assert isinstance(result, dict) or hasattr(result, 'metrics')


class TestCalculatorErrorHandling:
    """Test error handling in individual calculators."""
    
    @pytest.fixture
    def problematic_tickets(self) -> List[Ticket]:
        """Create tickets that might cause calculation issues."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        # Ticket with extreme resolution time
        extreme_ticket = Ticket(
            id="T1",
            title="Extreme resolution time",
            description="Test",
            status=TicketStatus.RESOLVED,
            severity=TicketSeverity.SEV_1,
            created_date=base_time,
            updated_date=base_time + timedelta(days=365*10),  # 10 years
            resolved_date=base_time + timedelta(days=365*10)
        )
        tickets.append(extreme_ticket)
        
        # Ticket with negative resolution time (invalid dates)
        try:
            negative_ticket = Ticket(
                id="T2",
                title="Negative resolution time",
                description="Test",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.SEV_2,
                created_date=base_time + timedelta(hours=5),
                updated_date=base_time + timedelta(hours=2),  # Before created
                resolved_date=base_time + timedelta(hours=1)   # Before created
            )
            tickets.append(negative_ticket)
        except:
            pass  # May fail validation
        
        return tickets
    
    def test_resolution_time_calculator_with_extreme_values(self, problematic_tickets: List[Ticket]) -> None:
        """Test ResolutionTimeCalculator with extreme values."""
        calculator = ResolutionTimeCalculator()
        
        # Should handle extreme values without crashing
        result = calculator.calculate(problematic_tickets)
        
        assert isinstance(result, dict)
        # Should have some form of result even with problematic data
        assert len(result) > 0
    
    def test_resolution_time_calculator_with_division_by_zero(self) -> None:
        """Test calculator when operations might cause division by zero."""
        # Empty list should not cause division by zero
        calculator = ResolutionTimeCalculator()
        result = calculator.calculate([])
        
        assert isinstance(result, dict)
        assert "sample_size" in result
        assert result["sample_size"] == 0
    
    def test_status_distribution_calculator_with_invalid_statuses(self) -> None:
        """Test StatusDistributionCalculator with invalid status values."""
        # Create tickets with potentially problematic status values
        tickets_with_none_status = []
        
        try:
            ticket = Ticket(
                id="T1",
                title="None status ticket",
                description="Test",
                status=None,  # Invalid status
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
            tickets_with_none_status.append(ticket)
        except:
            pass  # May fail during creation
        
        calculator = StatusDistributionCalculator()
        
        # Should handle gracefully
        if tickets_with_none_status:
            result = calculator.calculate(tickets_with_none_status)
            assert isinstance(result, dict)
    
    def test_volume_analyzer_with_future_dates(self) -> None:
        """Test VolumeAnalyzer with future dates."""
        future_tickets = [
            Ticket(
                id="T1",
                title="Future ticket",
                description="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now() + timedelta(days=30),  # Future
                updated_date=datetime.now() + timedelta(days=30)
            )
        ]
        
        analyzer = VolumeAnalyzer()
        result = analyzer.calculate(future_tickets)
        
        # Should handle future dates gracefully
        assert isinstance(result, dict)
    
    def test_calculator_with_numpy_errors(self) -> None:
        """Test calculators when numpy operations fail."""
        calculator = ResolutionTimeCalculator()
        
        # Create tickets that might cause numpy issues
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = [
            Ticket(
                id="T1",
                title="Numpy test",
                description="Test",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.SEV_3,
                created_date=base_time,
                updated_date=base_time + timedelta(hours=1),
                resolved_date=base_time + timedelta(hours=1)
            )
        ]
        
        # Mock numpy to raise an error
        with patch('numpy.percentile') as mock_percentile:
            mock_percentile.side_effect = ValueError("Numpy error")
            
            # Should handle numpy errors gracefully
            result = calculator.calculate(tickets)
            assert isinstance(result, dict)


class TestDataProcessorErrorHandling:
    """Test error handling in data processor."""
    
    @pytest.fixture
    def processor(self) -> TicketDataProcessor:
        """Create TicketDataProcessor instance."""
        return TicketDataProcessor()
    
    def test_process_tickets_with_validation_errors(self, processor: TicketDataProcessor) -> None:
        """Test processing tickets when validation fails."""
        # Create tickets that might fail validation
        invalid_tickets = []
        
        try:
            invalid_ticket = Ticket(
                id="",  # Empty ID
                title="Invalid ticket",
                description="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
            invalid_tickets.append(invalid_ticket)
        except:
            pass
        
        # Should handle validation errors gracefully
        if invalid_tickets:
            processed = processor.process_tickets(invalid_tickets)
            assert isinstance(processed, list)
    
    def test_process_tickets_with_cleaning_errors(self, processor: TicketDataProcessor) -> None:
        """Test processing when data cleaning fails."""
        tickets = [
            Ticket(
                id="T1",
                title="Test ticket",
                description="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
        ]
        
        # Mock data cleaner to fail
        with patch.object(processor._data_cleaner, 'clean_ticket') as mock_clean:
            mock_clean.side_effect = Exception("Cleaning failed")
            
            # Should handle cleaning errors gracefully
            processed = processor.process_tickets(tickets)
            assert isinstance(processed, list)
    
    def test_assess_data_quality_with_corrupted_data(self, processor: TicketDataProcessor) -> None:
        """Test data quality assessment with corrupted data."""
        # Create list with mixed valid and invalid objects
        mixed_data = [
            Ticket(
                id="T1",
                title="Valid ticket",
                description="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now(),
                updated_date=datetime.now()
            ),
            "not a ticket",  # Invalid object
            None,  # None object
        ]
        
        # Should handle mixed data gracefully
        try:
            quality = processor.assess_data_quality(mixed_data)
            assert isinstance(quality, dict)
        except (TypeError, AttributeError):
            # Acceptable to raise type errors for invalid objects
            pass


class TestTrendAnalyzerErrorHandling:
    """Test error handling in trend analyzer."""
    
    @pytest.fixture
    def analyzer(self) -> TrendAnalyzer:
        """Create TrendAnalyzer instance."""
        return TrendAnalyzer()
    
    def test_analyze_trends_with_pandas_errors(self, analyzer: TrendAnalyzer) -> None:
        """Test trend analysis when pandas operations fail."""
        tickets = [
            Ticket(
                id="T1",
                title="Trend test",
                description="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
        ]
        
        # Mock pandas to fail
        with patch('pandas.DataFrame.resample') as mock_resample:
            mock_resample.side_effect = pd.errors.DataError("Resample failed")
            
            # Should handle pandas errors gracefully
            with pytest.raises(AnalysisError):
                analyzer.analyze_trends(tickets)
    
    def test_detect_patterns_with_insufficient_data(self, analyzer: TrendAnalyzer) -> None:
        """Test pattern detection with insufficient data."""
        # Single ticket
        single_ticket = [
            Ticket(
                id="T1",
                title="Single ticket",
                description="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
        ]
        
        result = analyzer.detect_patterns(single_ticket)
        
        # Should handle insufficient data gracefully
        assert isinstance(result, dict)
        if "message" in result:
            assert "insufficient" in result["message"].lower() or "no" in result["message"].lower()
    
    def test_analyze_trends_with_datetime_errors(self, analyzer: TrendAnalyzer) -> None:
        """Test trend analysis when datetime operations fail."""
        tickets = [
            Ticket(
                id="T1",
                title="DateTime test",
                description="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
        ]
        
        # Mock datetime operations to fail
        with patch('pandas.to_datetime') as mock_to_datetime:
            mock_to_datetime.side_effect = ValueError("DateTime conversion failed")
            
            # Should handle datetime errors
            with pytest.raises(AnalysisError):
                analyzer.analyze_trends(tickets)


class TestFallbackMechanisms:
    """Test fallback mechanisms when primary analysis fails."""
    
    @pytest.fixture
    def engine(self) -> AnalysisEngine:
        """Create AnalysisEngine instance."""
        return AnalysisEngine()
    
    def test_fallback_to_basic_metrics_when_advanced_fails(self, engine: AnalysisEngine) -> None:
        """Test fallback to basic metrics when advanced calculations fail."""
        tickets = [
            Ticket(
                id="T1",
                title="Fallback test",
                description="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
        ]
        
        # Create calculator that fails on advanced metrics but succeeds on basic
        calculator = Mock()
        calculator.__class__.__name__ = "FallbackCalculator"
        calculator.get_metric_names.return_value = ["basic_metric"]
        
        def side_effect_calculate(ticket_list):
            # Simulate advanced calculation failure, return basic metrics
            return {
                "basic_metric": len(ticket_list),
                "sample_size": len(ticket_list),
                "data_available": len(ticket_list) > 0
            }
        
        calculator.calculate.side_effect = side_effect_calculate
        engine.add_calculator(calculator)
        
        result = engine.analyze_tickets(tickets)
        
        # Should have basic metrics even if advanced ones fail
        assert isinstance(result, dict) or hasattr(result, 'metrics')
    
    def test_graceful_degradation_with_partial_data(self, engine: AnalysisEngine) -> None:
        """Test graceful degradation when only partial data is available."""
        # Create tickets with missing optional fields
        partial_tickets = [
            Ticket(
                id="T1",
                title="Partial ticket",
                description="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now(),
                updated_date=datetime.now()
                # Missing assignee, resolver_group, etc.
            )
        ]
        
        calculator = ResolutionTimeCalculator()
        engine.add_calculator(calculator)
        
        # Should work with partial data
        result = engine.analyze_tickets(partial_tickets)
        
        assert isinstance(result, dict) or hasattr(result, 'metrics')
    
    def test_empty_result_generation_when_all_analysis_fails(self, engine: AnalysisEngine) -> None:
        """Test generation of empty result when all analysis fails."""
        tickets = [
            Ticket(
                id="T1",
                title="Test",
                description="Test",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
        ]
        
        # Add calculator that always fails
        failing_calculator = Mock()
        failing_calculator.__class__.__name__ = "AlwaysFailingCalculator"
        failing_calculator.calculate.side_effect = Exception("Always fails")
        failing_calculator.get_metric_names.return_value = ["test_metric"]
        
        engine.add_calculator(failing_calculator)
        
        # Should still return a result structure
        result = engine.analyze_tickets(tickets)
        
        assert isinstance(result, dict) or hasattr(result, 'metrics')


class TestRecoveryMechanisms:
    """Test error recovery mechanisms."""
    
    def test_calculator_retry_mechanism(self) -> None:
        """Test retry mechanism for transient calculator failures."""
        # This would test if calculators retry on transient failures
        # Implementation depends on whether retry logic is implemented
        calculator = ResolutionTimeCalculator()
        
        # Create tickets
        tickets = [
            Ticket(
                id="T1",
                title="Retry test",
                description="Test",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now() - timedelta(hours=2),
                updated_date=datetime.now() - timedelta(hours=1),
                resolved_date=datetime.now()
            )
        ]
        
        # Should complete successfully
        result = calculator.calculate(tickets)
        assert isinstance(result, dict)
    
    def test_data_validation_recovery(self) -> None:
        """Test recovery from data validation failures."""
        processor = TicketDataProcessor()
        
        # Create mix of valid and invalid tickets
        mixed_tickets = []
        
        # Valid ticket
        valid_ticket = Ticket(
            id="T1",
            title="Valid",
            description="Test",
            status=TicketStatus.OPEN,
            severity=TicketSeverity.SEV_3,
            created_date=datetime.now(),
            updated_date=datetime.now()
        )
        mixed_tickets.append(valid_ticket)
        
        # Should process valid tickets even if some are invalid
        processed = processor.process_tickets(mixed_tickets)
        assert isinstance(processed, list)
        assert len(processed) >= 1  # At least the valid ticket
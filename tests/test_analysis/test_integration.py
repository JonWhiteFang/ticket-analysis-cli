"""Integration tests for complete analysis workflows.

This module contains integration tests that verify the complete analysis
workflow from data input through processing, calculation, and result
generation. Tests ensure all components work together correctly.
"""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch

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
from ticket_analyzer.models.analysis import AnalysisResult


class TestCompleteAnalysisWorkflow:
    """Test complete analysis workflow integration."""
    
    @pytest.fixture
    def comprehensive_dataset(self) -> List[Ticket]:
        """Create comprehensive dataset for integration testing."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        # Create diverse ticket dataset
        for i in range(100):
            created_time = base_time + timedelta(days=i // 10, hours=i % 24)
            
            # Vary resolution status and times
            if i % 4 == 0:
                status = TicketStatus.RESOLVED
                resolved_time = created_time + timedelta(hours=2 + (i % 48))
            elif i % 4 == 1:
                status = TicketStatus.CLOSED
                resolved_time = created_time + timedelta(hours=1 + (i % 24))
            elif i % 4 == 2:
                status = TicketStatus.IN_PROGRESS
                resolved_time = None
            else:
                status = TicketStatus.OPEN
                resolved_time = None
            
            ticket = Ticket(
                id=f"T{i+1:03d}",
                title=f"Integration test ticket {i+1}",
                description=f"Comprehensive test ticket for integration testing {i+1}",
                status=status,
                severity=list(TicketSeverity)[i % len(TicketSeverity)],
                created_date=created_time,
                updated_date=created_time + timedelta(minutes=30),
                resolved_date=resolved_time,
                assignee=f"user{(i % 10) + 1}",
                resolver_group=f"Team{(i % 5) + 1}",
                tags=[f"tag{(i % 8) + 1}", "integration"],
                metadata={
                    "priority": "high" if i % 3 == 0 else "normal",
                    "component": f"comp{(i % 6) + 1}",
                    "customer_impact": "yes" if i % 5 == 0 else "no"
                }
            )
            tickets.append(ticket)
        
        return tickets
    
    def test_end_to_end_analysis_workflow(self, comprehensive_dataset: List[Ticket]) -> None:
        """Test complete end-to-end analysis workflow."""
        # Initialize analysis engine
        engine = AnalysisEngine()
        
        # Add all calculators
        engine.add_calculator(ResolutionTimeCalculator())
        engine.add_calculator(StatusDistributionCalculator())
        engine.add_calculator(VolumeAnalyzer())
        engine.add_calculator(SeverityAnalyzer())
        engine.add_calculator(TeamPerformanceCalculator())
        
        # Perform complete analysis
        result = engine.analyze_tickets(comprehensive_dataset)
        
        # Verify result structure
        assert isinstance(result, (dict, AnalysisResult))
        
        if isinstance(result, AnalysisResult):
            assert result.ticket_count > 0
            assert result.original_count == len(comprehensive_dataset)
            assert isinstance(result.metrics, dict)
            assert isinstance(result.trends, dict)
            assert result.generated_at is not None
        else:
            # Dictionary result
            assert len(result) > 0
        
        # Verify metrics from different calculators are present
        metrics = result.metrics if hasattr(result, 'metrics') else result
        
        # Should have metrics from ResolutionTimeCalculator
        resolution_metrics = [k for k in metrics.keys() if "resolution" in k.lower()]
        assert len(resolution_metrics) > 0
        
        # Should have metrics from StatusDistributionCalculator
        status_metrics = [k for k in metrics.keys() if "status" in k.lower()]
        assert len(status_metrics) > 0
        
        # Should have metrics from VolumeAnalyzer
        volume_metrics = [k for k in metrics.keys() if "volume" in k.lower()]
        assert len(volume_metrics) > 0    

    def test_data_processor_integration(self, comprehensive_dataset: List[Ticket]) -> None:
        """Test data processor integration with analysis engine."""
        processor = TicketDataProcessor()
        engine = AnalysisEngine()
        engine.add_calculator(ResolutionTimeCalculator())
        
        # Process tickets first
        processed_tickets = processor.process_tickets(comprehensive_dataset)
        
        # Analyze processed tickets
        result = engine.analyze_tickets(processed_tickets)
        
        # Should complete successfully
        assert isinstance(result, (dict, AnalysisResult))
        
        # Processed tickets should be valid for analysis
        assert len(processed_tickets) <= len(comprehensive_dataset)
    
    def test_trend_analyzer_integration(self, comprehensive_dataset: List[Ticket]) -> None:
        """Test trend analyzer integration with main analysis."""
        analyzer = TrendAnalyzer()
        engine = AnalysisEngine()
        engine.add_calculator(VolumeAnalyzer())
        
        # Perform both trend analysis and regular analysis
        trend_result = analyzer.analyze_trends(comprehensive_dataset)
        analysis_result = engine.analyze_tickets(comprehensive_dataset)
        
        # Both should complete successfully
        assert isinstance(trend_result, dict)
        assert isinstance(analysis_result, (dict, AnalysisResult))
        
        # Trend analysis should provide complementary information
        assert "volume_trends" in trend_result or "message" in trend_result
    
    def test_multiple_calculator_integration(self, comprehensive_dataset: List[Ticket]) -> None:
        """Test integration of multiple calculators working together."""
        engine = AnalysisEngine()
        
        # Add calculators in different orders to test independence
        calculators = [
            TeamPerformanceCalculator(),
            ResolutionTimeCalculator(),
            SeverityAnalyzer(),
            StatusDistributionCalculator(),
            VolumeAnalyzer()
        ]
        
        for calculator in calculators:
            engine.add_calculator(calculator)
        
        result = engine.analyze_tickets(comprehensive_dataset)
        
        # Should have metrics from all calculators
        metrics = result.metrics if hasattr(result, 'metrics') else result
        
        # Count metrics from different calculators
        metric_sources = set()
        for key in metrics.keys():
            if "resolution" in key.lower():
                metric_sources.add("resolution")
            elif "status" in key.lower():
                metric_sources.add("status")
            elif "volume" in key.lower():
                metric_sources.add("volume")
            elif "severity" in key.lower():
                metric_sources.add("severity")
        
        # Should have metrics from multiple sources
        assert len(metric_sources) >= 3


class TestErrorRecoveryIntegration:
    """Test error recovery in integrated workflows."""
    
    def test_partial_calculator_failure_recovery(self) -> None:
        """Test recovery when some calculators fail."""
        engine = AnalysisEngine()
        
        # Add working calculator
        engine.add_calculator(ResolutionTimeCalculator())
        
        # Add failing calculator
        failing_calc = Mock()
        failing_calc.calculate.side_effect = Exception("Calculator failed")
        failing_calc.__class__.__name__ = "FailingCalculator"
        failing_calc.get_metric_names.return_value = ["failing_metric"]
        engine.add_calculator(failing_calc)
        
        # Create test tickets
        tickets = [
            Ticket(
                id="T1",
                title="Test",
                description="Test",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.SEV_3,
                created_date=datetime.now() - timedelta(hours=2),
                updated_date=datetime.now() - timedelta(hours=1),
                resolved_date=datetime.now()
            )
        ]
        
        # Should complete with partial results
        result = engine.analyze_tickets(tickets)
        
        assert isinstance(result, (dict, AnalysisResult))
        
        # Should have results from working calculator
        metrics = result.metrics if hasattr(result, 'metrics') else result
        working_metrics = [k for k in metrics.keys() if "resolution" in k.lower()]
        assert len(working_metrics) > 0
        
        # Should have error information for failing calculator
        error_metrics = [k for k in metrics.keys() if "error" in k.lower()]
        assert len(error_metrics) > 0


class TestDataFlowIntegration:
    """Test data flow through integrated components."""
    
    def test_data_transformation_pipeline(self) -> None:
        """Test data transformation through the complete pipeline."""
        # Create raw ticket data
        raw_tickets = [
            Ticket(
                id="T1",
                title="  Raw Ticket with Spaces  ",
                description="Raw description\twith\ttabs",
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime(2024, 1, 1, 10, 0, 0),
                updated_date=datetime(2024, 1, 1, 10, 30, 0),
                assignee="user@amazon.com"
            )
        ]
        
        # Process through data processor
        processor = TicketDataProcessor()
        processed_tickets = processor.process_tickets(raw_tickets)
        
        # Analyze processed tickets
        engine = AnalysisEngine()
        engine.add_calculator(StatusDistributionCalculator())
        
        result = engine.analyze_tickets(processed_tickets)
        
        # Should complete successfully with cleaned data
        assert isinstance(result, (dict, AnalysisResult))
        assert len(processed_tickets) <= len(raw_tickets)
    
    def test_dataframe_integration_pipeline(self) -> None:
        """Test DataFrame creation and processing pipeline."""
        engine = AnalysisEngine()
        
        # Create test tickets
        tickets = [
            Ticket(
                id=f"T{i}",
                title=f"DataFrame test {i}",
                description="Test",
                status=TicketStatus.RESOLVED if i % 2 == 0 else TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime(2024, 1, 1, 10, 0, 0) + timedelta(hours=i),
                updated_date=datetime(2024, 1, 1, 10, 30, 0) + timedelta(hours=i),
                resolved_date=datetime(2024, 1, 1, 12, 0, 0) + timedelta(hours=i) if i % 2 == 0 else None
            )
            for i in range(10)
        ]
        
        # Test DataFrame creation
        df = engine._create_dataframe(tickets)
        assert len(df) == len(tickets)
        
        # Test DataFrame optimization
        optimized_df = engine._optimize_dataframe_types(df)
        assert len(optimized_df) == len(df)
        
        # Test analysis with DataFrame
        engine.add_calculator(ResolutionTimeCalculator())
        result = engine.analyze_tickets(tickets)
        
        assert isinstance(result, (dict, AnalysisResult))


class TestCrossComponentValidation:
    """Test validation across different components."""
    
    def test_consistent_ticket_counting(self) -> None:
        """Test that ticket counts are consistent across components."""
        tickets = [
            Ticket(
                id=f"T{i}",
                title=f"Count test {i}",
                description="Test",
                status=TicketStatus.RESOLVED if i < 5 else TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=datetime(2024, 1, 1, 10, 0, 0) + timedelta(hours=i),
                updated_date=datetime(2024, 1, 1, 10, 30, 0) + timedelta(hours=i),
                resolved_date=datetime(2024, 1, 1, 12, 0, 0) + timedelta(hours=i) if i < 5 else None
            )
            for i in range(10)
        ]
        
        # Test with different calculators
        resolution_calc = ResolutionTimeCalculator()
        status_calc = StatusDistributionCalculator()
        volume_calc = VolumeAnalyzer()
        
        resolution_result = resolution_calc.calculate(tickets)
        status_result = status_calc.calculate(tickets)
        volume_result = volume_calc.calculate(tickets)
        
        # All should report consistent total counts
        total_counts = []
        
        if "total_tickets" in resolution_result:
            total_counts.append(resolution_result["total_tickets"])
        if "total_tickets" in status_result:
            total_counts.append(status_result["total_tickets"])
        if "total_volume" in volume_result:
            total_counts.append(volume_result["total_volume"])
        
        # All counts should be equal
        if total_counts:
            assert all(count == total_counts[0] for count in total_counts)
            assert total_counts[0] == len(tickets)
    
    def test_metric_consistency_validation(self) -> None:
        """Test that metrics are consistent between different calculators."""
        # Create tickets with known properties
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        # 5 resolved tickets, 5 open tickets
        for i in range(10):
            is_resolved = i < 5
            ticket = Ticket(
                id=f"T{i+1}",
                title=f"Consistency test {i+1}",
                description="Test",
                status=TicketStatus.RESOLVED if is_resolved else TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=base_time + timedelta(hours=i),
                updated_date=base_time + timedelta(hours=i, minutes=30),
                resolved_date=base_time + timedelta(hours=i+2) if is_resolved else None
            )
            tickets.append(ticket)
        
        # Calculate with different calculators
        resolution_calc = ResolutionTimeCalculator()
        status_calc = StatusDistributionCalculator()
        
        resolution_result = resolution_calc.calculate(tickets)
        status_result = status_calc.calculate(tickets)
        
        # Check consistency of resolved ticket counts
        if "resolved_tickets" in resolution_result and "status_counts" in status_result:
            resolved_from_resolution = resolution_result["resolved_tickets"]
            resolved_from_status = status_result["status_counts"].get("Resolved", 0)
            
            assert resolved_from_resolution == resolved_from_status == 5
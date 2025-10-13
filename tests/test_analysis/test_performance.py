"""Performance tests for analysis engine components.

This module contains performance tests to ensure analysis operations
complete within acceptable time limits and handle large datasets
efficiently without memory issues or excessive processing time.
"""

import pytest
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch
import psutil
import os

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


class TestAnalysisPerformance:
    """Test performance of analysis operations."""
    
    @pytest.fixture
    def large_dataset(self) -> List[Ticket]:
        """Create large dataset for performance testing."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        # Create 10,000 tickets for performance testing
        for i in range(10000):
            created_time = base_time + timedelta(
                days=i // 100,  # Spread over ~100 days
                hours=i % 24,
                minutes=(i * 7) % 60  # Some variation
            )
            
            is_resolved = i % 3 == 0  # 1/3 resolved
            resolved_time = created_time + timedelta(
                hours=2 + (i % 48)  # 2-50 hour resolution times
            ) if is_resolved else None
            
            ticket = Ticket(
                id=f"T{i+1:06d}",
                title=f"Performance test ticket {i+1}",
                description=f"Description for performance testing {i+1}",
                status=TicketStatus.RESOLVED if is_resolved else TicketStatus.OPEN,
                severity=list(TicketSeverity)[i % len(TicketSeverity)],
                created_date=created_time,
                updated_date=created_time + timedelta(minutes=30),
                resolved_date=resolved_time,
                assignee=f"user{(i % 50) + 1}",  # 50 different users
                resolver_group=f"Team{(i % 10) + 1}",  # 10 different teams
                tags=[f"tag{(i % 20) + 1}", "performance"],
                metadata={"priority": "normal" if i % 2 == 0 else "high"}
            )
            tickets.append(ticket)
        
        return tickets
    
    @pytest.fixture
    def medium_dataset(self) -> List[Ticket]:
        """Create medium dataset for performance testing."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        # Create 1,000 tickets
        for i in range(1000):
            created_time = base_time + timedelta(hours=i, minutes=(i * 3) % 60)
            
            ticket = Ticket(
                id=f"T{i+1:04d}",
                title=f"Medium test ticket {i+1}",
                description="Performance test",
                status=TicketStatus.OPEN if i % 2 == 0 else TicketStatus.RESOLVED,
                severity=list(TicketSeverity)[i % len(TicketSeverity)],
                created_date=created_time,
                updated_date=created_time + timedelta(minutes=15),
                resolved_date=created_time + timedelta(hours=4) if i % 2 == 1 else None
            )
            tickets.append(ticket)
        
        return tickets
    
    @pytest.mark.performance
    def test_analysis_engine_performance_large_dataset(self, large_dataset: List[Ticket]) -> None:
        """Test AnalysisEngine performance with large dataset."""
        engine = AnalysisEngine()
        
        # Add all calculators
        engine.add_calculator(ResolutionTimeCalculator())
        engine.add_calculator(StatusDistributionCalculator())
        engine.add_calculator(VolumeAnalyzer())
        engine.add_calculator(SeverityAnalyzer())
        engine.add_calculator(TeamPerformanceCalculator())
        
        # Measure performance
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        result = engine.analyze_tickets(large_dataset)
        
        end_time = time.time()
        end_memory = self._get_memory_usage()
        
        processing_time = end_time - start_time
        memory_increase = end_memory - start_memory
        
        # Performance assertions
        assert processing_time < 30.0, f"Analysis took {processing_time:.2f}s, should be < 30s"
        assert memory_increase < 500, f"Memory increased by {memory_increase}MB, should be < 500MB"
        
        # Verify result completeness
        assert isinstance(result, dict) or hasattr(result, 'metrics')
        
        print(f"Large dataset analysis: {processing_time:.2f}s, {memory_increase}MB memory")
    
    @pytest.mark.performance
    def test_resolution_time_calculator_performance(self, large_dataset: List[Ticket]) -> None:
        """Test ResolutionTimeCalculator performance."""
        calculator = ResolutionTimeCalculator()
        
        start_time = time.time()
        result = calculator.calculate(large_dataset)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should complete within reasonable time
        assert processing_time < 10.0, f"Resolution time calculation took {processing_time:.2f}s"
        assert isinstance(result, dict)
        
        print(f"Resolution time calculation: {processing_time:.2f}s")
    
    @pytest.mark.performance
    def test_status_distribution_calculator_performance(self, large_dataset: List[Ticket]) -> None:
        """Test StatusDistributionCalculator performance."""
        calculator = StatusDistributionCalculator()
        
        start_time = time.time()
        result = calculator.calculate(large_dataset)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert processing_time < 5.0, f"Status distribution calculation took {processing_time:.2f}s"
        assert isinstance(result, dict)
        
        print(f"Status distribution calculation: {processing_time:.2f}s")
    
    @pytest.mark.performance
    def test_volume_analyzer_performance(self, large_dataset: List[Ticket]) -> None:
        """Test VolumeAnalyzer performance."""
        analyzer = VolumeAnalyzer()
        
        start_time = time.time()
        result = analyzer.calculate(large_dataset)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert processing_time < 8.0, f"Volume analysis took {processing_time:.2f}s"
        assert isinstance(result, dict)
        
        print(f"Volume analysis: {processing_time:.2f}s")
    
    @pytest.mark.performance
    def test_trend_analyzer_performance(self, medium_dataset: List[Ticket]) -> None:
        """Test TrendAnalyzer performance."""
        analyzer = TrendAnalyzer()
        
        start_time = time.time()
        result = analyzer.analyze_trends(medium_dataset)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Trend analysis is more complex, allow more time
        assert processing_time < 15.0, f"Trend analysis took {processing_time:.2f}s"
        assert isinstance(result, dict)
        
        print(f"Trend analysis: {processing_time:.2f}s")
    
    @pytest.mark.performance
    def test_data_processor_performance(self, large_dataset: List[Ticket]) -> None:
        """Test TicketDataProcessor performance."""
        processor = TicketDataProcessor()
        
        start_time = time.time()
        processed = processor.process_tickets(large_dataset)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert processing_time < 12.0, f"Data processing took {processing_time:.2f}s"
        assert isinstance(processed, list)
        assert len(processed) <= len(large_dataset)
        
        print(f"Data processing: {processing_time:.2f}s")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # Convert to MB


class TestMemoryEfficiency:
    """Test memory efficiency of analysis operations."""
    
    @pytest.fixture
    def memory_test_tickets(self) -> List[Ticket]:
        """Create tickets for memory testing."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        # Create 5,000 tickets with larger descriptions for memory testing
        for i in range(5000):
            # Large description to test memory handling
            large_description = f"Memory test ticket {i+1}. " * 50  # ~1KB description
            
            ticket = Ticket(
                id=f"T{i+1:05d}",
                title=f"Memory test ticket {i+1}",
                description=large_description,
                status=TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=base_time + timedelta(hours=i),
                updated_date=base_time + timedelta(hours=i, minutes=30),
                tags=[f"tag{j}" for j in range(10)],  # Multiple tags
                metadata={f"key{j}": f"value{j}" for j in range(20)}  # Large metadata
            )
            tickets.append(ticket)
        
        return tickets
    
    @pytest.mark.performance
    def test_memory_usage_during_analysis(self, memory_test_tickets: List[Ticket]) -> None:
        """Test memory usage during analysis operations."""
        engine = AnalysisEngine()
        engine.add_calculator(ResolutionTimeCalculator())
        
        initial_memory = self._get_memory_usage()
        
        # Perform analysis
        result = engine.analyze_tickets(memory_test_tickets)
        
        peak_memory = self._get_memory_usage()
        memory_increase = peak_memory - initial_memory
        
        # Memory increase should be reasonable
        assert memory_increase < 1000, f"Memory increased by {memory_increase}MB during analysis"
        
        # Clean up and check memory is released
        del result
        del memory_test_tickets
        
        # Force garbage collection
        import gc
        gc.collect()
        
        final_memory = self._get_memory_usage()
        memory_retained = final_memory - initial_memory
        
        # Most memory should be released
        assert memory_retained < 200, f"Retained {memory_retained}MB after cleanup"
        
        print(f"Memory usage: +{memory_increase}MB peak, +{memory_retained}MB retained")
    
    @pytest.mark.performance
    def test_dataframe_memory_efficiency(self) -> None:
        """Test pandas DataFrame memory efficiency."""
        engine = AnalysisEngine()
        
        # Create tickets with various data types
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        for i in range(1000):
            ticket = Ticket(
                id=f"T{i+1:04d}",
                title=f"DataFrame test {i+1}",
                description="Test",
                status=TicketStatus.OPEN if i % 2 == 0 else TicketStatus.RESOLVED,
                severity=list(TicketSeverity)[i % len(TicketSeverity)],
                created_date=base_time + timedelta(hours=i),
                updated_date=base_time + timedelta(hours=i, minutes=30)
            )
            tickets.append(ticket)
        
        initial_memory = self._get_memory_usage()
        
        # Create DataFrame
        df = engine._create_dataframe(tickets)
        
        dataframe_memory = self._get_memory_usage()
        memory_for_df = dataframe_memory - initial_memory
        
        # DataFrame should not use excessive memory
        assert memory_for_df < 100, f"DataFrame used {memory_for_df}MB for 1000 tickets"
        
        # Test DataFrame optimization
        optimized_df = engine._optimize_dataframe_types(df)
        
        optimized_memory = self._get_memory_usage()
        
        # Optimization should not significantly increase memory
        optimization_overhead = optimized_memory - dataframe_memory
        assert optimization_overhead < 50, f"Optimization added {optimization_overhead}MB overhead"
        
        print(f"DataFrame memory: {memory_for_df}MB, optimization overhead: {optimization_overhead}MB")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024


class TestScalabilityLimits:
    """Test scalability limits and behavior at boundaries."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_maximum_dataset_size(self) -> None:
        """Test analysis with maximum reasonable dataset size."""
        # Create very large dataset (50,000 tickets)
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        large_tickets = []
        
        print("Creating 50,000 tickets for scalability test...")
        
        for i in range(50000):
            if i % 10000 == 0:
                print(f"Created {i} tickets...")
            
            ticket = Ticket(
                id=f"T{i+1:06d}",
                title=f"Scalability test {i+1}",
                description="Scalability test",
                status=TicketStatus.OPEN if i % 3 == 0 else TicketStatus.RESOLVED,
                severity=list(TicketSeverity)[i % len(TicketSeverity)],
                created_date=base_time + timedelta(hours=i // 100),
                updated_date=base_time + timedelta(hours=i // 100, minutes=30)
            )
            large_tickets.append(ticket)
        
        print("Starting analysis of 50,000 tickets...")
        
        engine = AnalysisEngine()
        engine.add_calculator(ResolutionTimeCalculator())
        
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            result = engine.analyze_tickets(large_tickets)
            
            end_time = time.time()
            end_memory = self._get_memory_usage()
            
            processing_time = end_time - start_time
            memory_usage = end_memory - start_memory
            
            # Should complete within reasonable limits
            assert processing_time < 120.0, f"50K ticket analysis took {processing_time:.2f}s"
            assert memory_usage < 2000, f"50K ticket analysis used {memory_usage}MB"
            
            assert isinstance(result, dict) or hasattr(result, 'metrics')
            
            print(f"50K ticket analysis: {processing_time:.2f}s, {memory_usage}MB")
            
        except MemoryError:
            pytest.skip("Insufficient memory for 50K ticket test")
        except Exception as e:
            pytest.fail(f"50K ticket analysis failed: {e}")
    
    @pytest.mark.performance
    def test_time_complexity_scaling(self) -> None:
        """Test that analysis time scales reasonably with dataset size."""
        engine = AnalysisEngine()
        engine.add_calculator(ResolutionTimeCalculator())
        
        dataset_sizes = [100, 500, 1000, 2000]
        processing_times = []
        
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        
        for size in dataset_sizes:
            # Create dataset of specified size
            tickets = []
            for i in range(size):
                ticket = Ticket(
                    id=f"T{i+1:04d}",
                    title=f"Scaling test {i+1}",
                    description="Test",
                    status=TicketStatus.RESOLVED,
                    severity=TicketSeverity.SEV_3,
                    created_date=base_time + timedelta(hours=i),
                    updated_date=base_time + timedelta(hours=i, minutes=30),
                    resolved_date=base_time + timedelta(hours=i+1)
                )
                tickets.append(ticket)
            
            # Measure processing time
            start_time = time.time()
            result = engine.analyze_tickets(tickets)
            end_time = time.time()
            
            processing_time = end_time - start_time
            processing_times.append(processing_time)
            
            print(f"Size {size}: {processing_time:.3f}s")
        
        # Check that time complexity is reasonable (should be roughly linear or better)
        # Time for 2000 tickets should not be more than 20x time for 100 tickets
        time_ratio = processing_times[-1] / processing_times[0]
        size_ratio = dataset_sizes[-1] / dataset_sizes[0]  # 20x
        
        assert time_ratio <= size_ratio * 2, f"Time scaling is poor: {time_ratio:.2f}x for {size_ratio}x data"
        
        print(f"Time scaling: {time_ratio:.2f}x for {size_ratio}x data")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024


class TestConcurrencyPerformance:
    """Test performance under concurrent operations."""
    
    @pytest.mark.performance
    def test_concurrent_calculator_performance(self) -> None:
        """Test performance when multiple calculators run concurrently."""
        import threading
        import concurrent.futures
        
        # Create test dataset
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        for i in range(1000):
            ticket = Ticket(
                id=f"T{i+1:04d}",
                title=f"Concurrent test {i+1}",
                description="Test",
                status=TicketStatus.RESOLVED if i % 2 == 0 else TicketStatus.OPEN,
                severity=TicketSeverity.SEV_3,
                created_date=base_time + timedelta(hours=i),
                updated_date=base_time + timedelta(hours=i, minutes=30),
                resolved_date=base_time + timedelta(hours=i+2) if i % 2 == 0 else None
            )
            tickets.append(ticket)
        
        # Test sequential execution
        calculators = [
            ResolutionTimeCalculator(),
            StatusDistributionCalculator(),
            VolumeAnalyzer(),
            SeverityAnalyzer()
        ]
        
        start_time = time.time()
        sequential_results = []
        for calculator in calculators:
            result = calculator.calculate(tickets)
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        # Test concurrent execution (simulated)
        start_time = time.time()
        
        def calculate_metrics(calculator):
            return calculator.calculate(tickets)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(calculate_metrics, calc) for calc in calculators]
            concurrent_results = [future.result() for future in futures]
        
        concurrent_time = time.time() - start_time
        
        # Concurrent execution should not be significantly slower
        # (Note: Due to GIL, it might not be faster, but shouldn't be much slower)
        assert concurrent_time <= sequential_time * 1.5, f"Concurrent execution too slow: {concurrent_time:.2f}s vs {sequential_time:.2f}s"
        
        # Results should be equivalent
        assert len(concurrent_results) == len(sequential_results)
        
        print(f"Sequential: {sequential_time:.3f}s, Concurrent: {concurrent_time:.3f}s")
    
    def test_thread_safety_performance(self) -> None:
        """Test that calculators are thread-safe and performant."""
        import threading
        
        calculator = ResolutionTimeCalculator()
        
        # Create test tickets
        base_time = datetime(2024, 1, 1, 10, 0, 0)
        tickets = []
        
        for i in range(500):
            ticket = Ticket(
                id=f"T{i+1:03d}",
                title=f"Thread safety test {i+1}",
                description="Test",
                status=TicketStatus.RESOLVED,
                severity=TicketSeverity.SEV_3,
                created_date=base_time + timedelta(hours=i),
                updated_date=base_time + timedelta(hours=i, minutes=30),
                resolved_date=base_time + timedelta(hours=i+2)
            )
            tickets.append(ticket)
        
        results = []
        errors = []
        
        def worker():
            try:
                result = calculator.calculate(tickets)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads
        threads = []
        start_time = time.time()
        
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Should complete without errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"
        
        # All results should be identical (deterministic calculation)
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, "Results differ between threads"
        
        total_time = end_time - start_time
        print(f"Thread safety test: {total_time:.3f}s for 5 concurrent calculations")
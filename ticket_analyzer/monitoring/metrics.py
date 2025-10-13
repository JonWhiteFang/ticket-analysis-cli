"""Performance monitoring and metrics collection system.

This module provides comprehensive performance monitoring, timing metrics,
memory usage tracking, and diagnostic information collection for the
ticket analyzer application.
"""

from __future__ import annotations
import gc
import os
import psutil
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from statistics import mean, median

from ..logging.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class PerformanceMetric:
    """Individual performance metric data."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class SystemResourceSnapshot:
    """Snapshot of system resource usage."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    process_memory_mb: float
    process_cpu_percent: float
    thread_count: int
    file_descriptors: int


@dataclass
class OperationTiming:
    """Timing information for an operation."""
    operation_name: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.duration * 1000


class MetricsCollector:
    """Thread-safe metrics collection and aggregation."""
    
    def __init__(self, max_metrics: int = 10000) -> None:
        self._metrics: deque = deque(maxlen=max_metrics)
        self._operation_timings: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._lock = threading.RLock()
        
    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric."""
        with self._lock:
            self._metrics.append(metric)
            logger.debug(f"Recorded metric: {metric.name} = {metric.value} {metric.unit}")
    
    def record_timing(self, timing: OperationTiming) -> None:
        """Record operation timing."""
        with self._lock:
            self._operation_timings[timing.operation_name].append(timing)
            
            # Update counters
            self._counters[f"{timing.operation_name}_total"] += 1
            if timing.success:
                self._counters[f"{timing.operation_name}_success"] += 1
            else:
                self._counters[f"{timing.operation_name}_error"] += 1
            
            logger.debug(f"Recorded timing: {timing.operation_name} took {timing.duration_ms:.2f}ms")
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        with self._lock:
            counter_key = self._build_metric_key(name, tags)
            self._counters[counter_key] += value
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value."""
        with self._lock:
            gauge_key = self._build_metric_key(name, tags)
            self._gauges[gauge_key] = value
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        with self._lock:
            timings = list(self._operation_timings.get(operation_name, []))
            
            if not timings:
                return {"operation": operation_name, "count": 0}
            
            durations = [t.duration for t in timings]
            success_count = sum(1 for t in timings if t.success)
            error_count = len(timings) - success_count
            
            return {
                "operation": operation_name,
                "count": len(timings),
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": success_count / len(timings) if timings else 0,
                "avg_duration_ms": mean(durations) * 1000 if durations else 0,
                "median_duration_ms": median(durations) * 1000 if durations else 0,
                "min_duration_ms": min(durations) * 1000 if durations else 0,
                "max_duration_ms": max(durations) * 1000 if durations else 0,
                "p95_duration_ms": self._percentile(durations, 0.95) * 1000 if durations else 0,
                "p99_duration_ms": self._percentile(durations, 0.99) * 1000 if durations else 0,
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "operations": {
                    name: self.get_operation_stats(name)
                    for name in self._operation_timings.keys()
                },
                "total_metrics": len(self._metrics)
            }
    
    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        with self._lock:
            self._metrics.clear()
            self._operation_timings.clear()
            self._counters.clear()
            self._gauges.clear()
            logger.info("Cleared all metrics")
    
    def _build_metric_key(self, name: str, tags: Optional[Dict[str, str]]) -> str:
        """Build metric key with tags."""
        if not tags:
            return name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(percentile * len(sorted_data))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        
        return sorted_data[index]


class SystemResourceMonitor:
    """Monitor system resource usage and performance."""
    
    def __init__(self, collection_interval: float = 60.0) -> None:
        self._collection_interval = collection_interval
        self._snapshots: deque = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self._process = psutil.Process()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
    
    def start_monitoring(self) -> None:
        """Start continuous resource monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Started system resource monitoring")
    
    def stop_monitoring(self) -> None:
        """Stop resource monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Stopped system resource monitoring")
    
    def get_current_snapshot(self) -> SystemResourceSnapshot:
        """Get current system resource snapshot."""
        try:
            # System-wide metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Process-specific metrics
            process_memory = self._process.memory_info()
            process_cpu = self._process.cpu_percent()
            
            # Thread and file descriptor counts
            thread_count = self._process.num_threads()
            try:
                fd_count = self._process.num_fds() if hasattr(self._process, 'num_fds') else 0
            except (psutil.AccessDenied, AttributeError):
                fd_count = 0
            
            return SystemResourceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_usage_percent=disk.percent,
                process_memory_mb=process_memory.rss / (1024 * 1024),
                process_cpu_percent=process_cpu,
                thread_count=thread_count,
                file_descriptors=fd_count
            )
        
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            # Return minimal snapshot on error
            return SystemResourceSnapshot(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                process_memory_mb=0.0,
                process_cpu_percent=0.0,
                thread_count=0,
                file_descriptors=0
            )
    
    def get_resource_stats(self, duration: timedelta = timedelta(hours=1)) -> Dict[str, Any]:
        """Get resource usage statistics for the specified duration."""
        with self._lock:
            cutoff_time = datetime.now() - duration
            recent_snapshots = [
                s for s in self._snapshots 
                if s.timestamp >= cutoff_time
            ]
            
            if not recent_snapshots:
                return {"error": "No data available for the specified duration"}
            
            return {
                "duration_minutes": duration.total_seconds() / 60,
                "sample_count": len(recent_snapshots),
                "cpu": {
                    "avg_percent": mean(s.cpu_percent for s in recent_snapshots),
                    "max_percent": max(s.cpu_percent for s in recent_snapshots),
                    "min_percent": min(s.cpu_percent for s in recent_snapshots),
                },
                "memory": {
                    "avg_percent": mean(s.memory_percent for s in recent_snapshots),
                    "max_percent": max(s.memory_percent for s in recent_snapshots),
                    "avg_used_mb": mean(s.memory_used_mb for s in recent_snapshots),
                    "max_used_mb": max(s.memory_used_mb for s in recent_snapshots),
                },
                "process": {
                    "avg_memory_mb": mean(s.process_memory_mb for s in recent_snapshots),
                    "max_memory_mb": max(s.process_memory_mb for s in recent_snapshots),
                    "avg_cpu_percent": mean(s.process_cpu_percent for s in recent_snapshots),
                    "max_cpu_percent": max(s.process_cpu_percent for s in recent_snapshots),
                    "avg_threads": mean(s.thread_count for s in recent_snapshots),
                    "max_threads": max(s.thread_count for s in recent_snapshots),
                }
            }
    
    def check_resource_thresholds(self) -> List[Dict[str, Any]]:
        """Check if resource usage exceeds thresholds."""
        current = self.get_current_snapshot()
        alerts = []
        
        # Define thresholds
        thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_usage_percent": 90.0,
            "process_memory_mb": 1024.0,  # 1GB
        }
        
        for metric, threshold in thresholds.items():
            current_value = getattr(current, metric)
            if current_value > threshold:
                alerts.append({
                    "metric": metric,
                    "current_value": current_value,
                    "threshold": threshold,
                    "severity": "warning" if current_value < threshold * 1.2 else "critical",
                    "timestamp": current.timestamp.isoformat()
                })
        
        return alerts
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                snapshot = self.get_current_snapshot()
                with self._lock:
                    self._snapshots.append(snapshot)
                
                # Check for resource alerts
                alerts = self.check_resource_thresholds()
                for alert in alerts:
                    logger.warning(f"Resource threshold exceeded: {alert}")
                
                time.sleep(self._collection_interval)
                
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                time.sleep(self._collection_interval)


class PerformanceMonitor:
    """Main performance monitoring system."""
    
    def __init__(self, enable_resource_monitoring: bool = True) -> None:
        self._metrics_collector = MetricsCollector()
        self._resource_monitor = SystemResourceMonitor()
        self._operation_stack: List[str] = []
        self._stack_lock = threading.RLock()
        
        if enable_resource_monitoring:
            self._resource_monitor.start_monitoring()
    
    @contextmanager
    def time_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """Context manager for timing operations."""
        start_time = time.perf_counter()
        success = True
        error_message = None
        
        # Track operation stack for nested operations
        with self._stack_lock:
            self._operation_stack.append(operation_name)
        
        try:
            yield
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time
            
            # Remove from operation stack
            with self._stack_lock:
                if self._operation_stack and self._operation_stack[-1] == operation_name:
                    self._operation_stack.pop()
            
            # Record timing
            timing = OperationTiming(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=success,
                error_message=error_message,
                metadata=metadata or {}
            )
            
            self._metrics_collector.record_timing(timing)
            
            # Log performance metric
            logger.debug(
                f"Operation '{operation_name}' completed in {duration*1000:.2f}ms "
                f"(success: {success})"
            )
    
    def record_custom_metric(self, name: str, value: float, unit: str = "",
                           tags: Optional[Dict[str, str]] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a custom performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            metadata=metadata or {},
            tags=tags or {}
        )
        
        self._metrics_collector.record_metric(metric)
    
    def increment_counter(self, name: str, value: int = 1, 
                         tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        self._metrics_collector.increment_counter(name, value, tags)
    
    def set_gauge(self, name: str, value: float, 
                  tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value."""
        self._metrics_collector.set_gauge(name, value, tags)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        metrics = self._metrics_collector.get_all_metrics()
        resource_stats = self._resource_monitor.get_resource_stats()
        current_snapshot = self._resource_monitor.get_current_snapshot()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "resources": {
                "current": {
                    "cpu_percent": current_snapshot.cpu_percent,
                    "memory_percent": current_snapshot.memory_percent,
                    "process_memory_mb": current_snapshot.process_memory_mb,
                    "thread_count": current_snapshot.thread_count,
                },
                "stats": resource_stats
            },
            "active_operations": list(self._operation_stack),
            "gc_stats": {
                "collections": gc.get_stats(),
                "counts": gc.get_count(),
            }
        }
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        return self._metrics_collector.get_operation_stats(operation_name)
    
    def force_garbage_collection(self) -> Dict[str, Any]:
        """Force garbage collection and return statistics."""
        before_counts = gc.get_count()
        
        # Force full garbage collection
        collected = []
        for generation in range(3):
            collected.append(gc.collect(generation))
        
        after_counts = gc.get_count()
        
        gc_stats = {
            "before_counts": before_counts,
            "after_counts": after_counts,
            "collected_objects": collected,
            "total_collected": sum(collected)
        }
        
        logger.info(f"Forced garbage collection: {gc_stats}")
        return gc_stats
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get detailed memory usage information."""
        snapshot = self._resource_monitor.get_current_snapshot()
        
        # Get garbage collection info
        gc_info = {
            "counts": gc.get_count(),
            "stats": gc.get_stats(),
            "thresholds": gc.get_threshold(),
        }
        
        return {
            "system_memory_mb": snapshot.memory_used_mb,
            "system_memory_percent": snapshot.memory_percent,
            "process_memory_mb": snapshot.process_memory_mb,
            "available_memory_mb": snapshot.memory_available_mb,
            "garbage_collection": gc_info,
            "timestamp": snapshot.timestamp.isoformat()
        }
    
    def shutdown(self) -> None:
        """Shutdown the performance monitor."""
        self._resource_monitor.stop_monitoring()
        logger.info("Performance monitor shutdown complete")


def timed_operation(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Decorator for timing function operations."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Get or create performance monitor
            monitor = getattr(wrapper, '_performance_monitor', None)
            if monitor is None:
                monitor = PerformanceMonitor()
                wrapper._performance_monitor = monitor
            
            with monitor.time_operation(operation_name, metadata):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def count_calls(counter_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for counting function calls."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Get or create performance monitor
            monitor = getattr(wrapper, '_performance_monitor', None)
            if monitor is None:
                monitor = PerformanceMonitor()
                wrapper._performance_monitor = monitor
            
            monitor.increment_counter(counter_name, tags=tags)
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def shutdown_monitoring() -> None:
    """Shutdown global monitoring."""
    global _global_monitor
    if _global_monitor is not None:
        _global_monitor.shutdown()
        _global_monitor = None
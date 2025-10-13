# Performance Tuning and Optimization

## Overview

This document provides comprehensive guidance for optimizing the performance of the Ticket Analysis CLI tool. It covers system-level optimizations, application tuning, database performance, and monitoring strategies to ensure optimal performance across different deployment scenarios.

## Performance Architecture

### Performance Goals

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| Response Time | < 2 seconds | < 5 seconds | > 10 seconds |
| Throughput | > 1000 tickets/min | > 500 tickets/min | < 100 tickets/min |
| Memory Usage | < 512MB | < 1GB | > 2GB |
| CPU Usage | < 50% | < 80% | > 90% |
| Concurrent Users | > 50 | > 20 | < 10 |

### Performance Bottlenecks

Common performance bottlenecks and their solutions:

```
┌─────────────────────────────────────────────────────────────┐
│                    Performance Bottlenecks                  │
├─────────────────────────────────────────────────────────────┤
│  Network I/O                                                │
│  ├── MCP API calls                                          │
│  ├── Authentication requests                                │
│  └── Data transfer overhead                                 │
├─────────────────────────────────────────────────────────────┤
│  Memory Usage                                               │
│  ├── Large dataset processing                               │
│  ├── Memory leaks                                           │
│  └── Inefficient data structures                           │
├─────────────────────────────────────────────────────────────┤
│  CPU Processing                                             │
│  ├── Data parsing and validation                            │
│  ├── Complex calculations                                   │
│  └── Regex operations                                       │
├─────────────────────────────────────────────────────────────┤
│  Disk I/O                                                  │
│  ├── Log file operations                                    │
│  ├── Report generation                                      │
│  └── Temporary file handling                               │
└─────────────────────────────────────────────────────────────┘
```

## System-Level Optimizations

### Operating System Tuning

#### Linux System Optimization

```bash
# /etc/sysctl.d/99-ticket-analyzer-performance.conf

# Network performance
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.rmem_default = 262144
net.core.wmem_default = 262144
net.ipv4.tcp_rmem = 4096 65536 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.netdev_max_backlog = 5000
net.core.somaxconn = 1024

# Memory management
vm.swappiness = 1
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.vfs_cache_pressure = 50

# File descriptor limits
fs.file-max = 65536
fs.nr_open = 1048576

# Process limits
kernel.pid_max = 32768
```

#### Process Limits Configuration

```bash
# /etc/security/limits.d/ticket-analyzer.conf
ticket-analyzer soft nofile 65536
ticket-analyzer hard nofile 65536
ticket-analyzer soft nproc 32768
ticket-analyzer hard nproc 32768
ticket-analyzer soft memlock unlimited
ticket-analyzer hard memlock unlimited
```

#### CPU Affinity and Scheduling

```bash
# Set CPU affinity for better performance
#!/bin/bash
TICKET_ANALYZER_PID=$(pgrep -f ticket-analyzer)

if [ -n "$TICKET_ANALYZER_PID" ]; then
    # Bind to specific CPU cores (adjust based on system)
    taskset -cp 0-3 $TICKET_ANALYZER_PID
    
    # Set high priority scheduling
    chrt -p 10 $TICKET_ANALYZER_PID
    
    # Set I/O scheduling priority
    ionice -c 1 -n 4 -p $TICKET_ANALYZER_PID
fi
```

### Memory Optimization

#### Memory Configuration

```python
# Memory optimization configuration
MEMORY_CONFIG = {
    "max_memory_usage": "2GB",
    "gc_threshold": "1.5GB",
    "batch_size_memory_limit": "500MB",
    "cache_size_limit": "256MB",
    "temp_file_memory_limit": "100MB"
}

class MemoryOptimizer:
    """Optimize memory usage for large datasets."""
    
    def __init__(self, config: Dict[str, str]) -> None:
        self._config = config
        self._memory_monitor = MemoryMonitor()
    
    def optimize_data_processing(self, data_processor) -> None:
        """Optimize data processing for memory efficiency."""
        # Enable garbage collection optimization
        import gc
        gc.set_threshold(700, 10, 10)
        
        # Set memory limits
        self._set_memory_limits()
        
        # Configure batch processing
        self._configure_batch_processing(data_processor)
    
    def _set_memory_limits(self) -> None:
        """Set memory limits for the application."""
        try:
            import resource
            
            # Convert memory limit to bytes
            memory_limit = self._parse_memory_size(self._config["max_memory_usage"])
            
            # Set virtual memory limit
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            
        except ImportError:
            logger.warning("Resource module not available - memory limits not set")
    
    def _parse_memory_size(self, size_str: str) -> int:
        """Parse memory size string to bytes."""
        size_str = size_str.upper()
        if size_str.endswith('GB'):
            return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
        elif size_str.endswith('MB'):
            return int(float(size_str[:-2]) * 1024 * 1024)
        elif size_str.endswith('KB'):
            return int(float(size_str[:-2]) * 1024)
        else:
            return int(size_str)

class MemoryMonitor:
    """Monitor memory usage and trigger optimization."""
    
    def __init__(self) -> None:
        self._peak_memory = 0
        self._gc_count = 0
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """Check current memory usage."""
        import psutil
        import gc
        
        process = psutil.Process()
        memory_info = process.memory_info()
        
        current_memory = memory_info.rss
        if current_memory > self._peak_memory:
            self._peak_memory = current_memory
        
        return {
            "current_memory_mb": current_memory / (1024 * 1024),
            "peak_memory_mb": self._peak_memory / (1024 * 1024),
            "memory_percent": process.memory_percent(),
            "gc_collections": sum(gc.get_stats()),
        }
    
    def trigger_gc_if_needed(self, threshold_mb: int = 1024) -> bool:
        """Trigger garbage collection if memory usage is high."""
        memory_info = self.check_memory_usage()
        
        if memory_info["current_memory_mb"] > threshold_mb:
            import gc
            collected = gc.collect()
            self._gc_count += 1
            
            logger.info(f"Garbage collection triggered: {collected} objects collected")
            return True
        
        return False
```

### Disk I/O Optimization

#### File System Optimization

```bash
# Mount options for better performance
# /etc/fstab entry for data directory
/dev/sdb1 /var/lib/ticket-analyzer ext4 defaults,noatime,nodiratime,data=writeback 0 2

# Temporary file system for better performance
tmpfs /tmp tmpfs defaults,size=2G,mode=1777 0 0
tmpfs /var/tmp tmpfs defaults,size=1G,mode=1777 0 0
```

#### I/O Scheduling Optimization

```bash
#!/bin/bash
# Optimize I/O scheduler for SSDs
echo noop > /sys/block/sda/queue/scheduler

# Optimize read-ahead for better sequential performance
echo 4096 > /sys/block/sda/queue/read_ahead_kb

# Optimize queue depth
echo 32 > /sys/block/sda/queue/nr_requests
```

## Application-Level Optimizations

### Configuration Optimization

#### Performance Configuration

```json
{
  "performance": {
    "batch_size": 2000,
    "max_concurrent_requests": 20,
    "connection_pool_size": 10,
    "cache_enabled": true,
    "cache_ttl_seconds": 7200,
    "worker_threads": 8,
    "memory_limit_mb": 2048,
    "gc_threshold_mb": 1536,
    "async_processing": true,
    "compression_enabled": true,
    "lazy_loading": true
  },
  "mcp": {
    "timeout_seconds": 30,
    "retry_attempts": 5,
    "circuit_breaker_threshold": 10,
    "connection_pool_size": 15,
    "keep_alive": true,
    "compression": true,
    "batch_requests": true
  },
  "data_processing": {
    "streaming_enabled": true,
    "chunk_size": 10000,
    "parallel_processing": true,
    "memory_mapped_files": true,
    "index_caching": true
  }
}
```

### Data Processing Optimization

#### Efficient Data Structures

```python
from typing import Iterator, List, Dict, Any
import pandas as pd
from collections import deque
import numpy as np

class OptimizedDataProcessor:
    """Optimized data processor for large datasets."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._chunk_size = config.get("chunk_size", 10000)
        self._use_streaming = config.get("streaming_enabled", True)
        self._parallel_processing = config.get("parallel_processing", True)
    
    def process_tickets_streaming(self, ticket_iterator: Iterator[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        """Process tickets using streaming for memory efficiency."""
        chunk = []
        
        for ticket in ticket_iterator:
            chunk.append(ticket)
            
            if len(chunk) >= self._chunk_size:
                # Process chunk
                processed_chunk = self._process_chunk_optimized(chunk)
                
                # Yield results
                for result in processed_chunk:
                    yield result
                
                # Clear chunk to free memory
                chunk.clear()
        
        # Process remaining tickets
        if chunk:
            processed_chunk = self._process_chunk_optimized(chunk)
            for result in processed_chunk:
                yield result
    
    def _process_chunk_optimized(self, chunk: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process chunk with optimized operations."""
        if not chunk:
            return []
        
        # Convert to DataFrame for efficient operations
        df = pd.DataFrame(chunk)
        
        # Optimize data types
        df = self._optimize_dtypes(df)
        
        # Perform vectorized operations
        df = self._apply_vectorized_operations(df)
        
        # Convert back to list of dicts
        return df.to_dict('records')
    
    def _optimize_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame data types for memory efficiency."""
        # Convert string columns to categories if they have few unique values
        for col in df.select_dtypes(include=['object']):
            if df[col].nunique() / len(df) < 0.5:  # Less than 50% unique values
                df[col] = df[col].astype('category')
        
        # Optimize numeric columns
        for col in df.select_dtypes(include=['int64']):
            if df[col].min() >= 0:
                if df[col].max() < 255:
                    df[col] = df[col].astype('uint8')
                elif df[col].max() < 65535:
                    df[col] = df[col].astype('uint16')
                elif df[col].max() < 4294967295:
                    df[col] = df[col].astype('uint32')
        
        return df
    
    def _apply_vectorized_operations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply vectorized operations for better performance."""
        # Use vectorized string operations
        if 'status' in df.columns:
            df['is_resolved'] = df['status'].isin(['Resolved', 'Closed'])
        
        # Use vectorized datetime operations
        if 'created_date' in df.columns:
            df['created_date'] = pd.to_datetime(df['created_date'])
            df['age_days'] = (pd.Timestamp.now() - df['created_date']).dt.days
        
        return df

class ParallelProcessor:
    """Parallel processing for CPU-intensive operations."""
    
    def __init__(self, num_workers: int = None) -> None:
        import multiprocessing
        self._num_workers = num_workers or multiprocessing.cpu_count()
    
    def process_parallel(self, data_chunks: List[List[Dict[str, Any]]], 
                        process_func: callable) -> List[Dict[str, Any]]:
        """Process data chunks in parallel."""
        from concurrent.futures import ProcessPoolExecutor, as_completed
        
        results = []
        
        with ProcessPoolExecutor(max_workers=self._num_workers) as executor:
            # Submit all chunks for processing
            future_to_chunk = {
                executor.submit(process_func, chunk): chunk 
                for chunk in data_chunks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                try:
                    chunk_result = future.result()
                    results.extend(chunk_result)
                except Exception as e:
                    logger.error(f"Parallel processing error: {e}")
        
        return results
```

### Caching Strategies

#### Multi-Level Caching

```python
import time
from typing import Optional, Any, Dict
from functools import wraps
import pickle
import hashlib

class MultiLevelCache:
    """Multi-level caching system for performance optimization."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._memory_cache = {}
        self._disk_cache_dir = Path(config.get("cache_directory", "/tmp/ticket-analyzer-cache"))
        self._max_memory_items = config.get("max_memory_items", 1000)
        self._disk_cache_enabled = config.get("disk_cache_enabled", True)
        
        # Create cache directory
        if self._disk_cache_enabled:
            self._disk_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (memory first, then disk)."""
        # Try memory cache first
        if key in self._memory_cache:
            cache_entry = self._memory_cache[key]
            if not self._is_expired(cache_entry):
                return cache_entry['value']
            else:
                del self._memory_cache[key]
        
        # Try disk cache
        if self._disk_cache_enabled:
            disk_value = self._get_from_disk(key)
            if disk_value is not None:
                # Promote to memory cache
                self._set_memory(key, disk_value)
                return disk_value
        
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set value in cache."""
        # Set in memory cache
        self._set_memory(key, value, ttl_seconds)
        
        # Set in disk cache if enabled
        if self._disk_cache_enabled:
            self._set_disk(key, value, ttl_seconds)
    
    def _set_memory(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set value in memory cache."""
        # Evict old entries if cache is full
        if len(self._memory_cache) >= self._max_memory_items:
            self._evict_lru()
        
        self._memory_cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl_seconds,
            'access_time': time.time()
        }
    
    def _set_disk(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set value in disk cache."""
        try:
            cache_file = self._disk_cache_dir / f"{self._hash_key(key)}.cache"
            cache_data = {
                'value': value,
                'expires_at': time.time() + ttl_seconds
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
                
        except Exception as e:
            logger.warning(f"Failed to write disk cache: {e}")
    
    def _get_from_disk(self, key: str) -> Optional[Any]:
        """Get value from disk cache."""
        try:
            cache_file = self._disk_cache_dir / f"{self._hash_key(key)}.cache"
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            if not self._is_expired(cache_data):
                return cache_data['value']
            else:
                # Remove expired file
                cache_file.unlink()
                return None
                
        except Exception as e:
            logger.warning(f"Failed to read disk cache: {e}")
            return None
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        return time.time() > cache_entry['expires_at']
    
    def _evict_lru(self) -> None:
        """Evict least recently used item from memory cache."""
        if not self._memory_cache:
            return
        
        lru_key = min(self._memory_cache.keys(), 
                     key=lambda k: self._memory_cache[k]['access_time'])
        del self._memory_cache[lru_key]
    
    def _hash_key(self, key: str) -> str:
        """Generate hash for cache key."""
        return hashlib.md5(key.encode()).hexdigest()

def cached(ttl_seconds: int = 3600, cache_instance: MultiLevelCache = None):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"
            
            # Try to get from cache
            if cache_instance:
                cached_result = cache_instance.get(cache_key)
                if cached_result is not None:
                    return cached_result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            if cache_instance:
                cache_instance.set(cache_key, result, ttl_seconds)
            
            return result
        return wrapper
    return decorator
```

### Database and API Optimization

#### Connection Pooling

```python
from typing import Optional, Dict, Any, List
import threading
from queue import Queue, Empty
import time

class ConnectionPool:
    """Connection pool for MCP clients."""
    
    def __init__(self, max_connections: int = 10, 
                 connection_factory: callable = None) -> None:
        self._max_connections = max_connections
        self._connection_factory = connection_factory
        self._pool = Queue(maxsize=max_connections)
        self._created_connections = 0
        self._lock = threading.Lock()
        self._stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'active_connections': 0
        }
    
    def get_connection(self, timeout: float = 30.0) -> Any:
        """Get connection from pool."""
        self._stats['total_requests'] += 1
        
        try:
            # Try to get existing connection
            connection = self._pool.get(timeout=timeout)
            self._stats['cache_hits'] += 1
            return connection
        except Empty:
            # Create new connection if under limit
            with self._lock:
                if self._created_connections < self._max_connections:
                    connection = self._connection_factory()
                    self._created_connections += 1
                    self._stats['active_connections'] += 1
                    return connection
                else:
                    raise RuntimeError("Connection pool exhausted")
    
    def return_connection(self, connection: Any) -> None:
        """Return connection to pool."""
        try:
            self._pool.put_nowait(connection)
        except:
            # Pool is full, close connection
            if hasattr(connection, 'close'):
                connection.close()
            with self._lock:
                self._stats['active_connections'] -= 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        return self._stats.copy()

class OptimizedMCPClient:
    """Optimized MCP client with connection pooling and batching."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._connection_pool = ConnectionPool(
            max_connections=config.get("connection_pool_size", 10),
            connection_factory=self._create_connection
        )
        self._batch_enabled = config.get("batch_requests", True)
        self._batch_size = config.get("batch_size", 100)
        self._request_queue = []
        self._batch_lock = threading.Lock()
    
    def search_tickets_batch(self, queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Search tickets in batches for better performance."""
        if not self._batch_enabled or len(queries) <= 1:
            return [self._search_tickets_single(query) for query in queries]
        
        results = []
        
        # Process in batches
        for i in range(0, len(queries), self._batch_size):
            batch = queries[i:i + self._batch_size]
            batch_results = self._process_batch(batch)
            results.extend(batch_results)
        
        return results
    
    def _process_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of requests."""
        connection = self._connection_pool.get_connection()
        
        try:
            # Combine requests into single batch request
            batch_request = {
                'method': 'batch_search_tickets',
                'params': {'queries': batch}
            }
            
            response = connection.send_request(batch_request)
            return response.get('results', [])
            
        finally:
            self._connection_pool.return_connection(connection)
    
    def _create_connection(self) -> Any:
        """Create new MCP connection."""
        # Implementation would create actual MCP connection
        pass
```

## Monitoring and Profiling

### Performance Monitoring

#### Real-time Performance Metrics

```python
import time
import psutil
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = None

class PerformanceMonitor:
    """Real-time performance monitoring."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._metrics_history = []
        self._alert_thresholds = config.get("alert_thresholds", {})
        self._monitoring_enabled = config.get("monitoring_enabled", True)
    
    def collect_system_metrics(self) -> List[PerformanceMetric]:
        """Collect system performance metrics."""
        if not self._monitoring_enabled:
            return []
        
        metrics = []
        now = datetime.now()
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        metrics.append(PerformanceMetric(
            name="cpu_usage_percent",
            value=cpu_percent,
            unit="percent",
            timestamp=now
        ))
        
        # Memory metrics
        memory = psutil.virtual_memory()
        metrics.append(PerformanceMetric(
            name="memory_usage_percent",
            value=memory.percent,
            unit="percent",
            timestamp=now
        ))
        
        metrics.append(PerformanceMetric(
            name="memory_usage_mb",
            value=memory.used / (1024 * 1024),
            unit="megabytes",
            timestamp=now
        ))
        
        # Disk I/O metrics
        disk_io = psutil.disk_io_counters()
        if disk_io:
            metrics.append(PerformanceMetric(
                name="disk_read_mb_per_sec",
                value=disk_io.read_bytes / (1024 * 1024),
                unit="megabytes_per_second",
                timestamp=now
            ))
            
            metrics.append(PerformanceMetric(
                name="disk_write_mb_per_sec",
                value=disk_io.write_bytes / (1024 * 1024),
                unit="megabytes_per_second",
                timestamp=now
            ))
        
        # Network I/O metrics
        network_io = psutil.net_io_counters()
        if network_io:
            metrics.append(PerformanceMetric(
                name="network_sent_mb_per_sec",
                value=network_io.bytes_sent / (1024 * 1024),
                unit="megabytes_per_second",
                timestamp=now
            ))
            
            metrics.append(PerformanceMetric(
                name="network_recv_mb_per_sec",
                value=network_io.bytes_recv / (1024 * 1024),
                unit="megabytes_per_second",
                timestamp=now
            ))
        
        # Store metrics history
        self._metrics_history.extend(metrics)
        
        # Clean old metrics (keep last hour)
        cutoff_time = now - timedelta(hours=1)
        self._metrics_history = [
            m for m in self._metrics_history 
            if m.timestamp > cutoff_time
        ]
        
        return metrics
    
    def collect_application_metrics(self, operation_name: str, 
                                  duration: float, success: bool) -> PerformanceMetric:
        """Collect application-specific metrics."""
        tags = {
            "operation": operation_name,
            "status": "success" if success else "failure"
        }
        
        metric = PerformanceMetric(
            name="operation_duration",
            value=duration,
            unit="seconds",
            timestamp=datetime.now(),
            tags=tags
        )
        
        self._metrics_history.append(metric)
        return metric
    
    def check_performance_alerts(self) -> List[str]:
        """Check for performance alerts based on thresholds."""
        alerts = []
        
        if not self._metrics_history:
            return alerts
        
        # Get recent metrics (last 5 minutes)
        recent_time = datetime.now() - timedelta(minutes=5)
        recent_metrics = [
            m for m in self._metrics_history 
            if m.timestamp > recent_time
        ]
        
        # Check CPU usage
        cpu_metrics = [m for m in recent_metrics if m.name == "cpu_usage_percent"]
        if cpu_metrics:
            avg_cpu = sum(m.value for m in cpu_metrics) / len(cpu_metrics)
            cpu_threshold = self._alert_thresholds.get("cpu_percent", 80)
            if avg_cpu > cpu_threshold:
                alerts.append(f"High CPU usage: {avg_cpu:.1f}% (threshold: {cpu_threshold}%)")
        
        # Check memory usage
        memory_metrics = [m for m in recent_metrics if m.name == "memory_usage_percent"]
        if memory_metrics:
            avg_memory = sum(m.value for m in memory_metrics) / len(memory_metrics)
            memory_threshold = self._alert_thresholds.get("memory_percent", 85)
            if avg_memory > memory_threshold:
                alerts.append(f"High memory usage: {avg_memory:.1f}% (threshold: {memory_threshold}%)")
        
        return alerts

def performance_timer(monitor: PerformanceMonitor, operation_name: str):
    """Decorator for timing operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                monitor.collect_application_metrics(operation_name, duration, success)
        
        return wrapper
    return decorator
```

### Profiling and Debugging

#### Performance Profiling

```python
import cProfile
import pstats
import io
from typing import Dict, Any, Optional
import tracemalloc
import linecache

class PerformanceProfiler:
    """Performance profiler for identifying bottlenecks."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._profiling_enabled = config.get("profiling_enabled", False)
        self._memory_profiling = config.get("memory_profiling", False)
        self._profile_output_dir = Path(config.get("profile_output_dir", "/tmp/profiles"))
        
        # Create output directory
        self._profile_output_dir.mkdir(parents=True, exist_ok=True)
    
    def profile_function(self, func: callable, *args, **kwargs) -> Any:
        """Profile a function execution."""
        if not self._profiling_enabled:
            return func(*args, **kwargs)
        
        # CPU profiling
        profiler = cProfile.Profile()
        
        # Memory profiling
        if self._memory_profiling:
            tracemalloc.start()
        
        try:
            profiler.enable()
            result = func(*args, **kwargs)
            profiler.disable()
            
            # Save CPU profile
            self._save_cpu_profile(profiler, func.__name__)
            
            # Save memory profile
            if self._memory_profiling:
                self._save_memory_profile(func.__name__)
            
            return result
            
        finally:
            if self._memory_profiling:
                tracemalloc.stop()
    
    def _save_cpu_profile(self, profiler: cProfile.Profile, func_name: str) -> None:
        """Save CPU profiling results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_file = self._profile_output_dir / f"cpu_profile_{func_name}_{timestamp}.prof"
        
        # Save binary profile
        profiler.dump_stats(str(profile_file))
        
        # Save human-readable report
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(50)  # Top 50 functions
        
        report_file = self._profile_output_dir / f"cpu_report_{func_name}_{timestamp}.txt"
        with open(report_file, 'w') as f:
            f.write(s.getvalue())
    
    def _save_memory_profile(self, func_name: str) -> None:
        """Save memory profiling results."""
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self._profile_output_dir / f"memory_report_{func_name}_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write(f"Memory Profile for {func_name}\n")
            f.write("=" * 50 + "\n\n")
            
            for index, stat in enumerate(top_stats[:20], 1):
                f.write(f"{index}. {stat}\n")
                
                # Get source code context
                frame = stat.traceback.format()[0]
                f.write(f"   {frame}\n\n")

class MemoryProfiler:
    """Detailed memory profiling and leak detection."""
    
    def __init__(self) -> None:
        self._snapshots = []
        self._baseline_snapshot = None
    
    def start_monitoring(self) -> None:
        """Start memory monitoring."""
        tracemalloc.start()
        self._baseline_snapshot = tracemalloc.take_snapshot()
    
    def take_snapshot(self, label: str = None) -> None:
        """Take a memory snapshot."""
        if not tracemalloc.is_tracing():
            return
        
        snapshot = tracemalloc.take_snapshot()
        self._snapshots.append({
            'snapshot': snapshot,
            'label': label or f"snapshot_{len(self._snapshots)}",
            'timestamp': datetime.now()
        })
    
    def analyze_memory_growth(self) -> Dict[str, Any]:
        """Analyze memory growth between snapshots."""
        if len(self._snapshots) < 2:
            return {"error": "Need at least 2 snapshots for comparison"}
        
        current = self._snapshots[-1]['snapshot']
        previous = self._snapshots[-2]['snapshot']
        
        top_stats = current.compare_to(previous, 'lineno')
        
        analysis = {
            "total_snapshots": len(self._snapshots),
            "current_label": self._snapshots[-1]['label'],
            "previous_label": self._snapshots[-2]['label'],
            "top_memory_increases": []
        }
        
        for stat in top_stats[:10]:
            if stat.size_diff > 0:
                analysis["top_memory_increases"].append({
                    "file": stat.traceback.format()[0],
                    "size_diff_mb": stat.size_diff / (1024 * 1024),
                    "count_diff": stat.count_diff
                })
        
        return analysis
    
    def detect_memory_leaks(self) -> List[Dict[str, Any]]:
        """Detect potential memory leaks."""
        if not self._baseline_snapshot or len(self._snapshots) < 1:
            return []
        
        current = self._snapshots[-1]['snapshot']
        top_stats = current.compare_to(self._baseline_snapshot, 'lineno')
        
        potential_leaks = []
        
        for stat in top_stats:
            # Consider it a potential leak if:
            # 1. Memory usage increased significantly
            # 2. Object count increased significantly
            if (stat.size_diff > 1024 * 1024 and  # > 1MB increase
                stat.count_diff > 100):  # > 100 objects increase
                
                potential_leaks.append({
                    "file": stat.traceback.format()[0],
                    "size_increase_mb": stat.size_diff / (1024 * 1024),
                    "object_count_increase": stat.count_diff,
                    "current_size_mb": stat.size / (1024 * 1024)
                })
        
        return potential_leaks
```

## Load Testing and Benchmarking

### Load Testing Framework

```python
import asyncio
import aiohttp
import time
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import statistics

@dataclass
class LoadTestResult:
    """Load test result data structure."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    errors: List[str]

class LoadTester:
    """Load testing framework for performance validation."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._max_concurrent_users = config.get("max_concurrent_users", 50)
        self._test_duration_seconds = config.get("test_duration_seconds", 60)
        self._ramp_up_seconds = config.get("ramp_up_seconds", 10)
    
    async def run_load_test(self, test_function: Callable, 
                           test_data: List[Any]) -> LoadTestResult:
        """Run load test with specified parameters."""
        start_time = time.time()
        end_time = start_time + self._test_duration_seconds
        
        response_times = []
        successful_requests = 0
        failed_requests = 0
        errors = []
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self._max_concurrent_users)
        
        async def execute_request(data):
            nonlocal successful_requests, failed_requests
            
            async with semaphore:
                request_start = time.time()
                
                try:
                    await test_function(data)
                    successful_requests += 1
                except Exception as e:
                    failed_requests += 1
                    errors.append(str(e))
                finally:
                    response_time = time.time() - request_start
                    response_times.append(response_time)
        
        # Generate load
        tasks = []
        data_index = 0
        
        while time.time() < end_time:
            # Ramp up gradually
            current_time = time.time()
            if current_time - start_time < self._ramp_up_seconds:
                ramp_factor = (current_time - start_time) / self._ramp_up_seconds
                current_max_users = int(self._max_concurrent_users * ramp_factor)
            else:
                current_max_users = self._max_concurrent_users
            
            # Create tasks up to current limit
            while len(tasks) < current_max_users and time.time() < end_time:
                data = test_data[data_index % len(test_data)]
                task = asyncio.create_task(execute_request(data))
                tasks.append(task)
                data_index += 1
            
            # Clean up completed tasks
            tasks = [task for task in tasks if not task.done()]
            
            await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
        
        # Wait for remaining tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate results
        total_requests = successful_requests + failed_requests
        test_duration = time.time() - start_time
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            
            sorted_times = sorted(response_times)
            p95_index = int(0.95 * len(sorted_times))
            p99_index = int(0.99 * len(sorted_times))
            
            p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]
            p99_response_time = sorted_times[p99_index] if p99_index < len(sorted_times) else sorted_times[-1]
        else:
            avg_response_time = median_response_time = p95_response_time = p99_response_time = 0
        
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0
        
        return LoadTestResult(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_response_time=avg_response_time,
            median_response_time=median_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            errors=errors[:100]  # Limit error list size
        )

# Example load test
async def example_load_test():
    """Example load test for ticket analysis."""
    
    async def test_ticket_analysis(test_data):
        """Test function for ticket analysis."""
        # Simulate ticket analysis operation
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Add some randomness to simulate real conditions
        import random
        if random.random() < 0.05:  # 5% failure rate
            raise Exception("Simulated error")
    
    # Test data
    test_data = [
        {"ticket_id": f"T{i:06d}", "status": "Open"} 
        for i in range(1000)
    ]
    
    # Load test configuration
    config = {
        "max_concurrent_users": 20,
        "test_duration_seconds": 30,
        "ramp_up_seconds": 5
    }
    
    # Run load test
    load_tester = LoadTester(config)
    result = await load_tester.run_load_test(test_ticket_analysis, test_data)
    
    # Print results
    print(f"Load Test Results:")
    print(f"Total Requests: {result.total_requests}")
    print(f"Successful: {result.successful_requests}")
    print(f"Failed: {result.failed_requests}")
    print(f"Average Response Time: {result.average_response_time:.3f}s")
    print(f"95th Percentile: {result.p95_response_time:.3f}s")
    print(f"Requests/Second: {result.requests_per_second:.1f}")
    
    if result.errors:
        print(f"Sample Errors: {result.errors[:5]}")

# Run the example
# asyncio.run(example_load_test())
```

This comprehensive performance guide provides the foundation for optimizing the Ticket Analysis CLI tool across all deployment scenarios. Regular performance monitoring, profiling, and optimization are essential for maintaining optimal performance as the system scales.
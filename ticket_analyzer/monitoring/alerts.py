"""Monitoring and alerting system for ticket analyzer.

This module provides threshold-based alerting, performance monitoring,
health checks, and system resource monitoring with capacity planning metrics.
"""

from __future__ import annotations
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from ..logging.logger import get_logger
from .metrics import PerformanceMonitor, SystemResourceSnapshot

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """Alert status states."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Alert:
    """Individual alert instance."""
    id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    timestamp: datetime
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    def acknowledge(self, acknowledged_by: str = "system") -> None:
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = acknowledged_by
    
    def resolve(self) -> None:
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now()
    
    def suppress(self) -> None:
        """Suppress the alert."""
        self.status = AlertStatus.SUPPRESSED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "metadata": self.metadata,
            "tags": self.tags,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
        }


@dataclass
class AlertRule:
    """Base class for alert rules."""
    name: str
    description: str
    severity: AlertSeverity
    enabled: bool = True
    cooldown_minutes: int = 5
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ThresholdRule(AlertRule):
    """Threshold-based alert rule."""
    metric_name: str = ""
    threshold_value: float = 0.0
    comparison: str = "greater_than"  # greater_than, less_than, equals
    duration_minutes: int = 1  # How long condition must persist
    
    def evaluate(self, current_value: float, timestamp: datetime) -> bool:
        """Evaluate if the threshold condition is met."""
        if self.comparison == "greater_than":
            return current_value > self.threshold_value
        elif self.comparison == "less_than":
            return current_value < self.threshold_value
        elif self.comparison == "equals":
            return abs(current_value - self.threshold_value) < 0.001
        else:
            return False


@dataclass
class PerformanceRule(AlertRule):
    """Performance-based alert rule."""
    operation_name: str = ""
    max_duration_ms: float = 0.0
    max_error_rate: float = 0.1  # 10% error rate threshold
    min_sample_size: int = 10
    
    def evaluate(self, operation_stats: Dict[str, Any]) -> bool:
        """Evaluate performance conditions."""
        if operation_stats.get("count", 0) < self.min_sample_size:
            return False
        
        # Check duration threshold
        avg_duration = operation_stats.get("avg_duration_ms", 0)
        if avg_duration > self.max_duration_ms:
            return True
        
        # Check error rate threshold
        error_rate = 1.0 - operation_stats.get("success_rate", 1.0)
        if error_rate > self.max_error_rate:
            return True
        
        return False


class AlertHandler(ABC):
    """Abstract base class for alert handlers."""
    
    @abstractmethod
    def handle_alert(self, alert: Alert) -> bool:
        """Handle an alert. Return True if handled successfully."""
        pass


class LoggingAlertHandler(AlertHandler):
    """Alert handler that logs alerts."""
    
    def handle_alert(self, alert: Alert) -> bool:
        """Log the alert."""
        try:
            log_level = {
                AlertSeverity.INFO: logger.info,
                AlertSeverity.WARNING: logger.warning,
                AlertSeverity.CRITICAL: logger.error,
                AlertSeverity.EMERGENCY: logger.critical,
            }.get(alert.severity, logger.warning)
            
            log_level(
                f"ALERT [{alert.severity.value.upper()}] {alert.name}: {alert.message}",
                alert_id=alert.id,
                source=alert.source,
                metadata=alert.metadata,
                tags=alert.tags
            )
            return True
        except Exception as e:
            logger.error(f"Failed to log alert {alert.id}: {e}")
            return False


class CallbackAlertHandler(AlertHandler):
    """Alert handler that calls a callback function."""
    
    def __init__(self, callback: Callable[[Alert], None]) -> None:
        self._callback = callback
    
    def handle_alert(self, alert: Alert) -> bool:
        """Call the callback with the alert."""
        try:
            self._callback(alert)
            return True
        except Exception as e:
            logger.error(f"Alert callback failed for {alert.id}: {e}")
            return False


class AlertManager:
    """Main alert management system."""
    
    def __init__(self, performance_monitor: Optional[PerformanceMonitor] = None) -> None:
        self._performance_monitor = performance_monitor
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: deque = deque(maxlen=10000)
        self._handlers: List[AlertHandler] = []
        self._rule_states: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._suppressed_alerts: Set[str] = set()
        
        # Threading
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Default handlers
        self.add_handler(LoggingAlertHandler())
        
        # Health check metrics
        self._health_checks: Dict[str, Callable[[], bool]] = {}
        self._last_health_check: Optional[datetime] = None
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        with self._lock:
            self._rules[rule.name] = rule
            logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str) -> None:
        """Remove an alert rule."""
        with self._lock:
            if rule_name in self._rules:
                del self._rules[rule_name]
                # Clean up rule state
                if rule_name in self._rule_states:
                    del self._rule_states[rule_name]
                logger.info(f"Removed alert rule: {rule_name}")
    
    def add_handler(self, handler: AlertHandler) -> None:
        """Add an alert handler."""
        with self._lock:
            self._handlers.append(handler)
    
    def remove_handler(self, handler: AlertHandler) -> None:
        """Remove an alert handler."""
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)
    
    def start_monitoring(self, check_interval: float = 30.0) -> None:
        """Start continuous alert monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(check_interval,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("Started alert monitoring")
    
    def stop_monitoring(self) -> None:
        """Stop alert monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Stopped alert monitoring")
    
    def fire_alert(self, name: str, message: str, severity: AlertSeverity,
                   source: str = "manual", metadata: Optional[Dict[str, Any]] = None,
                   tags: Optional[Dict[str, str]] = None) -> Alert:
        """Manually fire an alert."""
        alert_id = f"{name}_{int(time.time() * 1000)}"
        
        alert = Alert(
            id=alert_id,
            name=name,
            severity=severity,
            status=AlertStatus.ACTIVE,
            message=message,
            timestamp=datetime.now(),
            source=source,
            metadata=metadata or {},
            tags=tags or {}
        )
        
        return self._process_alert(alert)
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "user") -> bool:
        """Acknowledge an active alert."""
        with self._lock:
            if alert_id in self._active_alerts:
                self._active_alerts[alert_id].acknowledge(acknowledged_by)
                logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                return True
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert."""
        with self._lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.resolve()
                del self._active_alerts[alert_id]
                self._alert_history.append(alert)
                logger.info(f"Alert {alert_id} resolved")
                return True
            return False
    
    def suppress_alert(self, alert_name: str, duration_minutes: int = 60) -> None:
        """Suppress alerts for a specific rule."""
        with self._lock:
            self._suppressed_alerts.add(alert_name)
            
            # Schedule unsuppression
            def unsuppress():
                time.sleep(duration_minutes * 60)
                with self._lock:
                    self._suppressed_alerts.discard(alert_name)
                logger.info(f"Alert suppression lifted for {alert_name}")
            
            threading.Thread(target=unsuppress, daemon=True).start()
            logger.info(f"Suppressed alerts for {alert_name} for {duration_minutes} minutes")
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get list of active alerts."""
        with self._lock:
            alerts = list(self._active_alerts.values())
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        with self._lock:
            history = list(self._alert_history)
            return sorted(history, key=lambda a: a.timestamp, reverse=True)[:limit]
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics."""
        with self._lock:
            active_by_severity = defaultdict(int)
            for alert in self._active_alerts.values():
                active_by_severity[alert.severity.value] += 1
            
            total_history = len(self._alert_history)
            resolved_count = sum(1 for a in self._alert_history if a.status == AlertStatus.RESOLVED)
            
            return {
                "active_alerts": len(self._active_alerts),
                "active_by_severity": dict(active_by_severity),
                "total_rules": len(self._rules),
                "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
                "suppressed_rules": len(self._suppressed_alerts),
                "total_history": total_history,
                "resolved_count": resolved_count,
                "handlers": len(self._handlers),
            }
    
    def add_health_check(self, name: str, check_func: Callable[[], bool]) -> None:
        """Add a health check function."""
        self._health_checks[name] = check_func
        logger.info(f"Added health check: {name}")
    
    def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks and return results."""
        results = {}
        failed_checks = []
        
        for name, check_func in self._health_checks.items():
            try:
                result = check_func()
                results[name] = {"status": "healthy" if result else "unhealthy", "success": result}
                
                if not result:
                    failed_checks.append(name)
                    # Fire alert for failed health check
                    self.fire_alert(
                        name=f"health_check_{name}",
                        message=f"Health check '{name}' failed",
                        severity=AlertSeverity.WARNING,
                        source="health_check",
                        tags={"check_name": name}
                    )
            
            except Exception as e:
                results[name] = {"status": "error", "error": str(e), "success": False}
                failed_checks.append(name)
                logger.error(f"Health check '{name}' raised exception: {e}")
        
        self._last_health_check = datetime.now()
        
        return {
            "timestamp": self._last_health_check.isoformat(),
            "total_checks": len(self._health_checks),
            "passed": len(self._health_checks) - len(failed_checks),
            "failed": len(failed_checks),
            "failed_checks": failed_checks,
            "results": results,
            "overall_status": "healthy" if not failed_checks else "unhealthy"
        }
    
    def _monitoring_loop(self, check_interval: float) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                self._evaluate_rules()
                self._run_periodic_health_checks()
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}")
                time.sleep(check_interval)
    
    def _evaluate_rules(self) -> None:
        """Evaluate all alert rules."""
        current_time = datetime.now()
        
        with self._lock:
            for rule_name, rule in self._rules.items():
                if not rule.enabled or rule_name in self._suppressed_alerts:
                    continue
                
                try:
                    should_alert = False
                    alert_metadata = {}
                    
                    if isinstance(rule, ThresholdRule):
                        should_alert, alert_metadata = self._evaluate_threshold_rule(rule, current_time)
                    elif isinstance(rule, PerformanceRule):
                        should_alert, alert_metadata = self._evaluate_performance_rule(rule, current_time)
                    
                    if should_alert:
                        self._handle_rule_violation(rule, alert_metadata, current_time)
                    else:
                        self._handle_rule_recovery(rule, current_time)
                
                except Exception as e:
                    logger.error(f"Error evaluating rule {rule_name}: {e}")
    
    def _evaluate_threshold_rule(self, rule: ThresholdRule, current_time: datetime) -> tuple[bool, Dict[str, Any]]:
        """Evaluate a threshold rule."""
        if not self._performance_monitor:
            return False, {}
        
        # Get current system snapshot for resource metrics
        resource_snapshot = self._performance_monitor._resource_monitor.get_current_snapshot()
        
        # Map metric names to values
        metric_values = {
            "cpu_percent": resource_snapshot.cpu_percent,
            "memory_percent": resource_snapshot.memory_percent,
            "process_memory_mb": resource_snapshot.process_memory_mb,
            "disk_usage_percent": resource_snapshot.disk_usage_percent,
            "thread_count": resource_snapshot.thread_count,
        }
        
        current_value = metric_values.get(rule.metric_name)
        if current_value is None:
            return False, {}
        
        # Check if threshold is violated
        threshold_violated = rule.evaluate(current_value, current_time)
        
        if threshold_violated:
            # Check duration requirement
            rule_state = self._rule_states[rule.name]
            violation_start = rule_state.get("violation_start")
            
            if violation_start is None:
                rule_state["violation_start"] = current_time
                return False, {}  # Wait for duration
            
            violation_duration = (current_time - violation_start).total_seconds() / 60
            if violation_duration >= rule.duration_minutes:
                return True, {
                    "current_value": current_value,
                    "threshold_value": rule.threshold_value,
                    "violation_duration_minutes": violation_duration
                }
        else:
            # Clear violation state
            self._rule_states[rule.name].pop("violation_start", None)
        
        return False, {}
    
    def _evaluate_performance_rule(self, rule: PerformanceRule, current_time: datetime) -> tuple[bool, Dict[str, Any]]:
        """Evaluate a performance rule."""
        if not self._performance_monitor:
            return False, {}
        
        operation_stats = self._performance_monitor.get_operation_stats(rule.operation_name)
        
        if rule.evaluate(operation_stats):
            return True, {
                "operation_stats": operation_stats,
                "max_duration_ms": rule.max_duration_ms,
                "max_error_rate": rule.max_error_rate
            }
        
        return False, {}
    
    def _handle_rule_violation(self, rule: AlertRule, metadata: Dict[str, Any], current_time: datetime) -> None:
        """Handle a rule violation."""
        rule_state = self._rule_states[rule.name]
        last_alert_time = rule_state.get("last_alert_time")
        
        # Check cooldown period
        if last_alert_time:
            cooldown_elapsed = (current_time - last_alert_time).total_seconds() / 60
            if cooldown_elapsed < rule.cooldown_minutes:
                return  # Still in cooldown
        
        # Create and fire alert
        alert_id = f"{rule.name}_{int(time.time() * 1000)}"
        alert = Alert(
            id=alert_id,
            name=rule.name,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            message=f"Alert rule '{rule.name}' violated: {rule.description}",
            timestamp=current_time,
            source="alert_manager",
            metadata=metadata,
            tags=rule.tags
        )
        
        self._process_alert(alert)
        rule_state["last_alert_time"] = current_time
    
    def _handle_rule_recovery(self, rule: AlertRule, current_time: datetime) -> None:
        """Handle rule recovery (condition no longer violated)."""
        # Auto-resolve alerts for this rule if they exist
        alerts_to_resolve = [
            alert_id for alert_id, alert in self._active_alerts.items()
            if alert.name == rule.name
        ]
        
        for alert_id in alerts_to_resolve:
            self.resolve_alert(alert_id)
    
    def _process_alert(self, alert: Alert) -> Alert:
        """Process and handle an alert."""
        with self._lock:
            # Add to active alerts
            self._active_alerts[alert.id] = alert
            
            # Send to handlers
            for handler in self._handlers:
                try:
                    handler.handle_alert(alert)
                except Exception as e:
                    logger.error(f"Alert handler failed: {e}")
            
            logger.info(f"Processed alert: {alert.name} [{alert.severity.value}]")
            return alert
    
    def _run_periodic_health_checks(self) -> None:
        """Run health checks periodically."""
        if not self._health_checks:
            return
        
        # Run health checks every 5 minutes
        if (self._last_health_check is None or 
            (datetime.now() - self._last_health_check).total_seconds() > 300):
            
            try:
                self.run_health_checks()
            except Exception as e:
                logger.error(f"Error running health checks: {e}")


# Predefined alert rules
class ThresholdAlert:
    """Factory for common threshold alerts."""
    
    @staticmethod
    def high_cpu_usage(threshold: float = 80.0) -> ThresholdRule:
        """Alert for high CPU usage."""
        return ThresholdRule(
            name="high_cpu_usage",
            description=f"CPU usage exceeds {threshold}%",
            severity=AlertSeverity.WARNING,
            metric_name="cpu_percent",
            threshold_value=threshold,
            comparison="greater_than",
            duration_minutes=2,
            tags={"category": "system", "resource": "cpu"}
        )
    
    @staticmethod
    def high_memory_usage(threshold: float = 85.0) -> ThresholdRule:
        """Alert for high memory usage."""
        return ThresholdRule(
            name="high_memory_usage",
            description=f"Memory usage exceeds {threshold}%",
            severity=AlertSeverity.WARNING,
            metric_name="memory_percent",
            threshold_value=threshold,
            comparison="greater_than",
            duration_minutes=2,
            tags={"category": "system", "resource": "memory"}
        )
    
    @staticmethod
    def high_disk_usage(threshold: float = 90.0) -> ThresholdRule:
        """Alert for high disk usage."""
        return ThresholdRule(
            name="high_disk_usage",
            description=f"Disk usage exceeds {threshold}%",
            severity=AlertSeverity.CRITICAL,
            metric_name="disk_usage_percent",
            threshold_value=threshold,
            comparison="greater_than",
            duration_minutes=1,
            tags={"category": "system", "resource": "disk"}
        )


class PerformanceAlert:
    """Factory for common performance alerts."""
    
    @staticmethod
    def slow_operation(operation_name: str, max_duration_ms: float = 5000.0) -> PerformanceRule:
        """Alert for slow operations."""
        return PerformanceRule(
            name=f"slow_{operation_name}",
            description=f"Operation '{operation_name}' is taking too long",
            severity=AlertSeverity.WARNING,
            operation_name=operation_name,
            max_duration_ms=max_duration_ms,
            max_error_rate=0.05,  # 5% error rate
            tags={"category": "performance", "operation": operation_name}
        )
    
    @staticmethod
    def high_error_rate(operation_name: str, max_error_rate: float = 0.1) -> PerformanceRule:
        """Alert for high error rates."""
        return PerformanceRule(
            name=f"high_error_rate_{operation_name}",
            description=f"Operation '{operation_name}' has high error rate",
            severity=AlertSeverity.CRITICAL,
            operation_name=operation_name,
            max_duration_ms=float('inf'),  # Don't check duration
            max_error_rate=max_error_rate,
            tags={"category": "reliability", "operation": operation_name}
        )


# Global alert manager instance
_global_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    global _global_alert_manager
    if _global_alert_manager is None:
        from .metrics import get_performance_monitor
        _global_alert_manager = AlertManager(get_performance_monitor())
    return _global_alert_manager


def setup_default_alerts() -> None:
    """Set up default system alerts."""
    manager = get_alert_manager()
    
    # System resource alerts
    manager.add_rule(ThresholdAlert.high_cpu_usage(80.0))
    manager.add_rule(ThresholdAlert.high_memory_usage(85.0))
    manager.add_rule(ThresholdAlert.high_disk_usage(90.0))
    
    # Performance alerts for common operations
    manager.add_rule(PerformanceAlert.slow_operation("ticket_search", 10000.0))
    manager.add_rule(PerformanceAlert.slow_operation("data_analysis", 30000.0))
    manager.add_rule(PerformanceAlert.high_error_rate("authentication", 0.05))
    
    logger.info("Default alerts configured")


def shutdown_alerting() -> None:
    """Shutdown global alerting."""
    global _global_alert_manager
    if _global_alert_manager is not None:
        _global_alert_manager.stop_monitoring()
        _global_alert_manager = None
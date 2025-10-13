"""Service integration and coordination for ticket analyzer.

This module provides service integration, lifecycle management, and coordination
between all application services. It handles service wiring, health monitoring,
performance tracking, and graceful degradation scenarios.
"""

from __future__ import annotations
import logging
import time
from typing import Dict, Any, Optional, List, Type
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from contextlib import contextmanager

from .container import DependencyContainer
from .interfaces import (
    AuthenticationInterface,
    DataRetrievalInterface,
    AnalysisInterface,
    ReportingInterface,
    ConfigurationInterface,
    MCPClientInterface,
    DataSanitizerInterface,
    ProgressInterface
)
from .models import (
    ApplicationConfig,
    AuthConfig,
    MCPConfig,
    LoggingConfig,
    ConfigurationError,
    AuthenticationError,
    DataRetrievalError
)

# Import concrete implementations
from .auth import SecureMidwayAuthenticator, SecureAuthenticationSession
from .data_retrieval import MCPTicketRepository, InputValidator
from .analysis import AnalysisEngine, TicketDataProcessor
from .reporting import CLIReporter, HTMLReporter, ProgressManager
from .config import ConfigurationManager
from .external import MCPClient, ResilienceManager
from .security import TicketDataSanitizer, SecureLogger

logger = logging.getLogger(__name__)


@dataclass
class ServiceHealth:
    """Service health information."""
    service_name: str
    healthy: bool
    last_check: datetime
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    check_count: int = 0
    failure_count: int = 0


@dataclass
class PerformanceMetrics:
    """Performance metrics for service operations."""
    operation_name: str
    total_calls: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    error_count: int = 0
    last_call: Optional[datetime] = None
    
    @property
    def avg_time_ms(self) -> float:
        """Calculate average execution time."""
        return self.total_time_ms / self.total_calls if self.total_calls > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        return ((self.total_calls - self.error_count) / self.total_calls * 100) if self.total_calls > 0 else 0.0


class ServiceIntegrator:
    """Service integration and coordination manager.
    
    This class handles the wiring of all application services, manages their
    lifecycle, monitors health, and provides coordination between services.
    It ensures proper initialization order, dependency resolution, and
    graceful degradation when services fail.
    """
    
    def __init__(self, container: DependencyContainer, 
                 config: Optional[ApplicationConfig] = None) -> None:
        """Initialize service integrator.
        
        Args:
            container: Dependency injection container.
            config: Optional application configuration.
        """
        self._container = container
        self._config = config or ApplicationConfig()
        self._services: Dict[str, Any] = {}
        self._health_status: Dict[str, ServiceHealth] = {}
        self._performance_metrics: Dict[str, PerformanceMetrics] = {}
        self._lock = Lock()
        self._monitoring_enabled = True
        self._health_check_interval = timedelta(minutes=5)
        self._last_health_check = datetime.now()
        
        logger.info("Service integrator initialized")
    
    def wire_services(self) -> None:
        """Wire all application services with proper dependencies.
        
        This method registers all concrete service implementations with
        the dependency container and establishes their dependencies.
        
        Raises:
            ConfigurationError: If service wiring fails.
        """
        logger.info("Wiring application services")
        
        try:
            # Register configuration service first (no dependencies)
            self._register_configuration_service()
            
            # Register security services (minimal dependencies)
            self._register_security_services()
            
            # Register external services (depends on config and security)
            self._register_external_services()
            
            # Register authentication service (depends on config and external)
            self._register_authentication_service()
            
            # Register data retrieval service (depends on auth, external, security)
            self._register_data_retrieval_service()
            
            # Register analysis service (depends on security)
            self._register_analysis_service()
            
            # Register reporting services (depends on config)
            self._register_reporting_services()
            
            # Register progress service (no dependencies)
            self._register_progress_service()
            
            logger.info("All services wired successfully")
            
        except Exception as e:
            logger.error(f"Service wiring failed: {e}")
            raise ConfigurationError(f"Failed to wire services: {e}")
    
    def initialize_services(self) -> None:
        """Initialize all services in proper dependency order.
        
        Raises:
            ConfigurationError: If service initialization fails.
        """
        logger.info("Initializing services")
        
        try:
            # Initialize container services
            self._container.initialize_services()
            
            # Resolve and cache service instances
            self._resolve_service_instances()
            
            # Perform initial health checks
            self._perform_initial_health_checks()
            
            # Setup performance monitoring
            self._setup_performance_monitoring()
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise ConfigurationError(f"Failed to initialize services: {e}")
    
    def get_service_health(self) -> Dict[str, ServiceHealth]:
        """Get current health status of all services.
        
        Returns:
            Dictionary mapping service names to health information.
        """
        with self._lock:
            # Perform health check if needed
            if (datetime.now() - self._last_health_check) > self._health_check_interval:
                self._check_all_services_health()
            
            return self._health_status.copy()
    
    def get_performance_metrics(self) -> Dict[str, PerformanceMetrics]:
        """Get performance metrics for all services.
        
        Returns:
            Dictionary mapping service names to performance metrics.
        """
        with self._lock:
            return self._performance_metrics.copy()
    
    def monitor_service_call(self, service_name: str, operation_name: str):
        """Context manager for monitoring service calls.
        
        Args:
            service_name: Name of the service being called.
            operation_name: Name of the operation being performed.
        """
        return self._ServiceCallMonitor(self, service_name, operation_name)
    
    def handle_service_failure(self, service_name: str, error: Exception) -> bool:
        """Handle service failure with graceful degradation.
        
        Args:
            service_name: Name of the failed service.
            error: The error that occurred.
            
        Returns:
            True if failure was handled gracefully, False otherwise.
        """
        logger.warning(f"Handling failure for service {service_name}: {error}")
        
        with self._lock:
            # Update health status
            if service_name in self._health_status:
                health = self._health_status[service_name]
                health.healthy = False
                health.error_message = str(error)
                health.failure_count += 1
                health.last_check = datetime.now()
            
            # Update performance metrics
            if service_name in self._performance_metrics:
                self._performance_metrics[service_name].error_count += 1
        
        # Attempt graceful degradation based on service type
        return self._attempt_graceful_degradation(service_name, error)
    
    def cleanup_services(self) -> None:
        """Cleanup all services and resources.
        
        This method should be called during application shutdown to
        properly cleanup resources and close connections.
        """
        logger.info("Cleaning up services")
        
        # Cleanup services in reverse dependency order
        cleanup_order = [
            'progress', 'reporting', 'analysis', 'data_retrieval',
            'authentication', 'external', 'security', 'configuration'
        ]
        
        for service_name in cleanup_order:
            if service_name in self._services:
                try:
                    service = self._services[service_name]
                    if hasattr(service, 'cleanup'):
                        service.cleanup()
                    logger.debug(f"Cleaned up service: {service_name}")
                except Exception as e:
                    logger.error(f"Error cleaning up {service_name}: {e}")
        
        # Clear all cached data
        with self._lock:
            self._services.clear()
            self._health_status.clear()
            self._performance_metrics.clear()
        
        logger.info("Service cleanup completed")
    
    def _register_configuration_service(self) -> None:
        """Register configuration service."""
        def config_factory(container: DependencyContainer) -> ConfigurationInterface:
            return ConfigurationManager(self._config)
        
        self._container.register_factory(
            ConfigurationInterface,
            config_factory,
            dependencies=[]
        )
        logger.debug("Registered configuration service")
    
    def _register_security_services(self) -> None:
        """Register security and sanitization services."""
        def sanitizer_factory(container: DependencyContainer) -> DataSanitizerInterface:
            return TicketDataSanitizer()
        
        self._container.register_factory(
            DataSanitizerInterface,
            sanitizer_factory,
            dependencies=[]
        )
        logger.debug("Registered security services")
    
    def _register_external_services(self) -> None:
        """Register external service clients."""
        def mcp_client_factory(container: DependencyContainer) -> MCPClientInterface:
            config_service = container.resolve(ConfigurationInterface)
            mcp_config = config_service.get_setting('mcp', MCPConfig())
            return MCPClient(mcp_config)
        
        self._container.register_factory(
            MCPClientInterface,
            mcp_client_factory,
            dependencies=[self._get_service_name(ConfigurationInterface)]
        )
        logger.debug("Registered external services")
    
    def _register_authentication_service(self) -> None:
        """Register authentication service."""
        def auth_factory(container: DependencyContainer) -> AuthenticationInterface:
            config_service = container.resolve(ConfigurationInterface)
            auth_config = config_service.get_setting('authentication', AuthConfig())
            
            session = SecureAuthenticationSession()
            return SecureMidwayAuthenticator(auth_config, session)
        
        self._container.register_factory(
            AuthenticationInterface,
            auth_factory,
            dependencies=[self._get_service_name(ConfigurationInterface)]
        )
        logger.debug("Registered authentication service")
    
    def _register_data_retrieval_service(self) -> None:
        """Register data retrieval service."""
        def data_factory(container: DependencyContainer) -> DataRetrievalInterface:
            mcp_client = container.resolve(MCPClientInterface)
            auth_service = container.resolve(AuthenticationInterface)
            sanitizer = container.resolve(DataSanitizerInterface)
            validator = InputValidator()
            
            return MCPTicketRepository(mcp_client, auth_service, validator, sanitizer)
        
        self._container.register_factory(
            DataRetrievalInterface,
            data_factory,
            dependencies=[
                self._get_service_name(MCPClientInterface),
                self._get_service_name(AuthenticationInterface),
                self._get_service_name(DataSanitizerInterface)
            ]
        )
        logger.debug("Registered data retrieval service")
    
    def _register_analysis_service(self) -> None:
        """Register analysis service."""
        def analysis_factory(container: DependencyContainer) -> AnalysisInterface:
            sanitizer = container.resolve(DataSanitizerInterface)
            processor = TicketDataProcessor(sanitizer)
            return AnalysisEngine(processor)
        
        self._container.register_factory(
            AnalysisInterface,
            analysis_factory,
            dependencies=[self._get_service_name(DataSanitizerInterface)]
        )
        logger.debug("Registered analysis service")
    
    def _register_reporting_services(self) -> None:
        """Register reporting services."""
        def reporting_factory(container: DependencyContainer) -> ReportingInterface:
            config_service = container.resolve(ConfigurationInterface)
            output_config = config_service.get_setting('output', {})
            
            # Return CLI reporter by default, can be extended for multiple formats
            return CLIReporter(output_config)
        
        self._container.register_factory(
            ReportingInterface,
            reporting_factory,
            dependencies=[self._get_service_name(ConfigurationInterface)]
        )
        logger.debug("Registered reporting services")
    
    def _register_progress_service(self) -> None:
        """Register progress indication service."""
        def progress_factory(container: DependencyContainer) -> ProgressInterface:
            return ProgressManager()
        
        self._container.register_factory(
            ProgressInterface,
            progress_factory,
            dependencies=[]
        )
        logger.debug("Registered progress service")
    
    def _resolve_service_instances(self) -> None:
        """Resolve and cache service instances."""
        service_types = [
            (ConfigurationInterface, 'configuration'),
            (DataSanitizerInterface, 'security'),
            (MCPClientInterface, 'external'),
            (AuthenticationInterface, 'authentication'),
            (DataRetrievalInterface, 'data_retrieval'),
            (AnalysisInterface, 'analysis'),
            (ReportingInterface, 'reporting'),
            (ProgressInterface, 'progress')
        ]
        
        for service_type, service_name in service_types:
            try:
                if self._container.is_registered(service_type):
                    self._services[service_name] = self._container.resolve(service_type)
                    logger.debug(f"Resolved service: {service_name}")
            except Exception as e:
                logger.error(f"Failed to resolve {service_name}: {e}")
                # Continue with other services
    
    def _perform_initial_health_checks(self) -> None:
        """Perform initial health checks on all services."""
        logger.debug("Performing initial health checks")
        
        for service_name, service in self._services.items():
            try:
                health = ServiceHealth(
                    service_name=service_name,
                    healthy=True,
                    last_check=datetime.now(),
                    check_count=1
                )
                
                # Perform health check if service supports it
                start_time = time.time()
                
                if hasattr(service, 'health_check'):
                    result = service.health_check()
                    health.healthy = result.get('healthy', True)
                    health.error_message = result.get('error_message')
                elif hasattr(service, 'validate_connection'):
                    health.healthy = service.validate_connection()
                
                health.response_time_ms = (time.time() - start_time) * 1000
                
                with self._lock:
                    self._health_status[service_name] = health
                
                logger.debug(f"Health check for {service_name}: {'OK' if health.healthy else 'FAILED'}")
                
            except Exception as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                with self._lock:
                    self._health_status[service_name] = ServiceHealth(
                        service_name=service_name,
                        healthy=False,
                        last_check=datetime.now(),
                        error_message=str(e),
                        check_count=1,
                        failure_count=1
                    )
    
    def _check_all_services_health(self) -> None:
        """Check health of all services."""
        for service_name in self._services:
            self._check_service_health(service_name)
        
        self._last_health_check = datetime.now()
    
    def _check_service_health(self, service_name: str) -> None:
        """Check health of a specific service.
        
        Args:
            service_name: Name of service to check.
        """
        if service_name not in self._services:
            return
        
        service = self._services[service_name]
        health = self._health_status.get(service_name)
        
        if not health:
            health = ServiceHealth(
                service_name=service_name,
                healthy=True,
                last_check=datetime.now()
            )
        
        try:
            start_time = time.time()
            
            if hasattr(service, 'health_check'):
                result = service.health_check()
                health.healthy = result.get('healthy', True)
                health.error_message = result.get('error_message')
            elif hasattr(service, 'validate_connection'):
                health.healthy = service.validate_connection()
                health.error_message = None
            else:
                # Assume healthy if no health check available
                health.healthy = True
                health.error_message = None
            
            health.response_time_ms = (time.time() - start_time) * 1000
            health.last_check = datetime.now()
            health.check_count += 1
            
            if not health.healthy:
                health.failure_count += 1
            
        except Exception as e:
            health.healthy = False
            health.error_message = str(e)
            health.last_check = datetime.now()
            health.check_count += 1
            health.failure_count += 1
        
        with self._lock:
            self._health_status[service_name] = health
    
    def _setup_performance_monitoring(self) -> None:
        """Setup performance monitoring for all services."""
        if not self._monitoring_enabled:
            return
        
        logger.debug("Setting up performance monitoring")
        
        for service_name in self._services:
            with self._lock:
                self._performance_metrics[service_name] = PerformanceMetrics(
                    operation_name=service_name
                )
    
    def _attempt_graceful_degradation(self, service_name: str, error: Exception) -> bool:
        """Attempt graceful degradation for failed service.
        
        Args:
            service_name: Name of failed service.
            error: The error that occurred.
            
        Returns:
            True if degradation was successful, False otherwise.
        """
        logger.info(f"Attempting graceful degradation for {service_name}")
        
        # Service-specific degradation strategies
        if service_name == 'authentication':
            # For auth failures, we can't continue safely
            logger.error("Authentication service failed - cannot continue")
            return False
        
        elif service_name == 'data_retrieval':
            # For data retrieval failures, we might use cached data
            logger.warning("Data retrieval failed - check for cached data")
            return False  # No caching implemented yet
        
        elif service_name == 'reporting':
            # For reporting failures, we can still provide basic output
            logger.warning("Reporting service failed - using basic output")
            return True
        
        elif service_name == 'progress':
            # Progress service failure is not critical
            logger.warning("Progress service failed - continuing without progress indicators")
            return True
        
        else:
            # Default: assume failure is not recoverable
            return False
    
    def _get_service_name(self, service_type: Type) -> str:
        """Get service name from type.
        
        Args:
            service_type: Service type.
            
        Returns:
            Service name string.
        """
        return f"{service_type.__module__}.{service_type.__name__}"
    
    class _ServiceCallMonitor:
        """Context manager for monitoring service calls."""
        
        def __init__(self, integrator: 'ServiceIntegrator', 
                     service_name: str, operation_name: str) -> None:
            self._integrator = integrator
            self._service_name = service_name
            self._operation_name = operation_name
            self._start_time: Optional[float] = None
        
        def __enter__(self):
            self._start_time = time.time()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self._start_time is None:
                return
            
            execution_time = (time.time() - self._start_time) * 1000
            
            with self._integrator._lock:
                if self._service_name in self._integrator._performance_metrics:
                    metrics = self._integrator._performance_metrics[self._service_name]
                    metrics.total_calls += 1
                    metrics.total_time_ms += execution_time
                    metrics.min_time_ms = min(metrics.min_time_ms, execution_time)
                    metrics.max_time_ms = max(metrics.max_time_ms, execution_time)
                    metrics.last_call = datetime.now()
                    
                    if exc_type is not None:
                        metrics.error_count += 1
                        # Handle the service failure
                        self._integrator.handle_service_failure(
                            self._service_name, exc_val or Exception("Unknown error")
                        )


def create_service_integrator(container: DependencyContainer,
                            config: Optional[ApplicationConfig] = None) -> ServiceIntegrator:
    """Factory function to create and configure service integrator.
    
    Args:
        container: Dependency injection container.
        config: Optional application configuration.
        
    Returns:
        Configured service integrator.
    """
    integrator = ServiceIntegrator(container, config)
    logger.info("Created service integrator")
    return integrator
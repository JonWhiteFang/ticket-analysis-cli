"""Main application orchestrator for ticket analyzer.

This module provides the main application class that coordinates all services,
manages the application lifecycle, and handles the overall workflow for
ticket analysis operations. It serves as the central orchestrator that
wires together authentication, data retrieval, analysis, and reporting.
"""

from __future__ import annotations
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from contextlib import contextmanager

from .container import DependencyContainer, create_container
from .interfaces import (
    AuthenticationInterface,
    DataRetrievalInterface,
    AnalysisInterface,
    ReportingInterface,
    ConfigurationInterface,
    ProgressInterface
)
from .models import (
    ApplicationConfig,
    SearchCriteria,
    AnalysisResult,
    ReportConfig,
    TicketAnalysisError,
    ConfigurationError,
    AuthenticationError,
    DataRetrievalError,
    AnalysisError,
    create_error_context
)

logger = logging.getLogger(__name__)


@dataclass
class WorkflowContext:
    """Context information for workflow execution."""
    start_time: datetime
    operation_id: str
    user_id: Optional[str] = None
    request_params: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    success: bool
    result: Optional[Any] = None
    error: Optional[Exception] = None
    context: Optional[WorkflowContext] = None
    execution_time_ms: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None


class TicketAnalyzerApp:
    """Main application orchestrator for ticket analysis.
    
    This class coordinates all application services and manages the complete
    workflow from authentication through data retrieval, analysis, and reporting.
    It provides error handling, recovery mechanisms, and graceful degradation
    when services are unavailable.
    
    Example:
        >>> app = TicketAnalyzerApp()
        >>> app.initialize()
        >>> result = app.analyze_tickets(criteria)
        >>> app.shutdown()
    """
    
    def __init__(self, config: Optional[ApplicationConfig] = None,
                 container: Optional[DependencyContainer] = None) -> None:
        """Initialize the ticket analyzer application.
        
        Args:
            config: Optional application configuration.
            container: Optional dependency injection container.
        """
        self._config = config
        self._container = container or create_container(config)
        self._initialized = False
        self._services: Dict[str, Any] = {}
        self._health_status: Dict[str, bool] = {}
        self._performance_metrics: Dict[str, List[float]] = {}
        
        # Setup logging
        self._setup_logging()
        
        logger.info("Ticket analyzer application created")
    
    def initialize(self) -> None:
        """Initialize the application and all services.
        
        This method sets up all services, validates configuration,
        and prepares the application for operation.
        
        Raises:
            ConfigurationError: If initialization fails.
        """
        if self._initialized:
            logger.warning("Application already initialized")
            return
        
        logger.info("Initializing ticket analyzer application")
        
        try:
            # Initialize dependency container
            self._container.initialize_services()
            
            # Resolve core services
            self._resolve_services()
            
            # Validate service health
            self._validate_service_health()
            
            # Setup performance monitoring
            self._setup_performance_monitoring()
            
            self._initialized = True
            logger.info("Application initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Application initialization failed: {e}")
            raise ConfigurationError(f"Failed to initialize application: {e}")
    
    def analyze_tickets(self, criteria: SearchCriteria, 
                       report_config: Optional[ReportConfig] = None) -> WorkflowResult:
        """Execute complete ticket analysis workflow.
        
        This method orchestrates the entire workflow from authentication
        through data retrieval, analysis, and report generation.
        
        Args:
            criteria: Search criteria for ticket analysis.
            report_config: Optional report configuration.
            
        Returns:
            Workflow result containing analysis results or error information.
        """
        if not self._initialized:
            raise ConfigurationError("Application not initialized")
        
        # Create workflow context
        context = WorkflowContext(
            start_time=datetime.now(),
            operation_id=self._generate_operation_id(),
            request_params=criteria.to_dict() if hasattr(criteria, 'to_dict') else {}
        )
        
        logger.info(f"Starting ticket analysis workflow: {context.operation_id}")
        
        try:
            with self._workflow_timing(context):
                # Step 1: Authentication
                self._ensure_authentication(context)
                
                # Step 2: Data Retrieval
                tickets = self._retrieve_tickets(criteria, context)
                
                # Step 3: Analysis
                analysis_result = self._analyze_tickets(tickets, context)
                
                # Step 4: Report Generation (if requested)
                report_output = None
                if report_config:
                    report_output = self._generate_report(analysis_result, report_config, context)
                
                # Create successful result
                result = WorkflowResult(
                    success=True,
                    result={
                        'analysis': analysis_result,
                        'report': report_output
                    },
                    context=context,
                    execution_time_ms=self._calculate_execution_time(context),
                    metrics=self._collect_workflow_metrics(context)
                )
                
                logger.info(f"Workflow completed successfully: {context.operation_id}")
                return result
                
        except Exception as e:
            logger.error(f"Workflow failed: {context.operation_id} - {e}")
            
            # Create error result with recovery information
            result = WorkflowResult(
                success=False,
                error=e,
                context=context,
                execution_time_ms=self._calculate_execution_time(context),
                metrics=self._collect_workflow_metrics(context)
            )
            
            # Attempt graceful degradation
            self._handle_workflow_error(e, context, result)
            
            return result
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of all services.
        
        Returns:
            Dictionary containing health status for each service.
        """
        if not self._initialized:
            return {"status": "not_initialized"}
        
        health_info = {
            "status": "healthy" if all(self._health_status.values()) else "degraded",
            "services": self._health_status.copy(),
            "last_check": datetime.now().isoformat(),
            "performance_metrics": self._get_performance_summary()
        }
        
        return health_info
    
    def shutdown(self) -> None:
        """Shutdown the application and cleanup resources.
        
        This method performs graceful shutdown of all services,
        cleanup of resources, and final logging.
        """
        if not self._initialized:
            logger.warning("Application not initialized, nothing to shutdown")
            return
        
        logger.info("Shutting down ticket analyzer application")
        
        try:
            # Cleanup services in reverse order
            self._cleanup_services()
            
            # Cleanup dependency container
            self._container.cleanup()
            
            # Final performance metrics
            self._log_final_metrics()
            
            self._initialized = False
            logger.info("Application shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")
    
    def _resolve_services(self) -> None:
        """Resolve and cache core services from container."""
        try:
            # Resolve core services
            if self._container.is_registered(AuthenticationInterface):
                self._services['auth'] = self._container.resolve(AuthenticationInterface)
            
            if self._container.is_registered(DataRetrievalInterface):
                self._services['data'] = self._container.resolve(DataRetrievalInterface)
            
            if self._container.is_registered(AnalysisInterface):
                self._services['analysis'] = self._container.resolve(AnalysisInterface)
            
            if self._container.is_registered(ReportingInterface):
                self._services['reporting'] = self._container.resolve(ReportingInterface)
            
            if self._container.is_registered(ConfigurationInterface):
                self._services['config'] = self._container.resolve(ConfigurationInterface)
            
            if self._container.is_registered(ProgressInterface):
                self._services['progress'] = self._container.resolve(ProgressInterface)
            
            logger.debug(f"Resolved {len(self._services)} core services")
            
        except Exception as e:
            logger.error(f"Failed to resolve services: {e}")
            raise ConfigurationError(f"Service resolution failed: {e}")
    
    def _validate_service_health(self) -> None:
        """Validate health of all resolved services."""
        logger.debug("Validating service health")
        
        for service_name, service in self._services.items():
            try:
                # Check if service has health check method
                if hasattr(service, 'health_check'):
                    health_result = service.health_check()
                    self._health_status[service_name] = health_result.get('healthy', True)
                elif hasattr(service, 'validate_connection'):
                    self._health_status[service_name] = service.validate_connection()
                else:
                    # Assume healthy if no health check available
                    self._health_status[service_name] = True
                
                logger.debug(f"Service {service_name} health: {self._health_status[service_name]}")
                
            except Exception as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                self._health_status[service_name] = False
    
    def _ensure_authentication(self, context: WorkflowContext) -> None:
        """Ensure user is authenticated for the workflow.
        
        Args:
            context: Workflow context.
            
        Raises:
            AuthenticationError: If authentication fails.
        """
        if 'auth' not in self._services:
            logger.warning("Authentication service not available, skipping authentication")
            return
        
        auth_service = self._services['auth']
        
        try:
            logger.debug(f"Ensuring authentication for workflow: {context.operation_id}")
            auth_service.ensure_authenticated()
            
            # Update context with user info
            if hasattr(auth_service, 'get_session_info'):
                session_info = auth_service.get_session_info()
                context.user_id = session_info.get('user_id')
            
        except Exception as e:
            logger.error(f"Authentication failed for workflow {context.operation_id}: {e}")
            raise AuthenticationError(f"Authentication required: {e}")
    
    def _retrieve_tickets(self, criteria: SearchCriteria, 
                         context: WorkflowContext) -> List[Any]:
        """Retrieve tickets based on search criteria.
        
        Args:
            criteria: Search criteria.
            context: Workflow context.
            
        Returns:
            List of retrieved tickets.
            
        Raises:
            DataRetrievalError: If data retrieval fails.
        """
        if 'data' not in self._services:
            raise DataRetrievalError("Data retrieval service not available")
        
        data_service = self._services['data']
        
        try:
            logger.debug(f"Retrieving tickets for workflow: {context.operation_id}")
            
            # Show progress if available
            if 'progress' in self._services:
                self._services['progress'].start_operation("Retrieving ticket data")
            
            start_time = time.time()
            tickets = data_service.search_tickets(criteria)
            retrieval_time = (time.time() - start_time) * 1000
            
            # Update performance metrics
            self._record_performance_metric('data_retrieval_ms', retrieval_time)
            
            # Complete progress
            if 'progress' in self._services:
                self._services['progress'].complete_operation(
                    True, f"Retrieved {len(tickets)} tickets"
                )
            
            logger.info(f"Retrieved {len(tickets)} tickets in {retrieval_time:.2f}ms")
            return tickets
            
        except Exception as e:
            if 'progress' in self._services:
                self._services['progress'].complete_operation(False, f"Data retrieval failed: {e}")
            
            logger.error(f"Data retrieval failed for workflow {context.operation_id}: {e}")
            raise DataRetrievalError(f"Failed to retrieve tickets: {e}")
    
    def _analyze_tickets(self, tickets: List[Any], 
                        context: WorkflowContext) -> AnalysisResult:
        """Analyze retrieved tickets.
        
        Args:
            tickets: List of tickets to analyze.
            context: Workflow context.
            
        Returns:
            Analysis results.
            
        Raises:
            AnalysisError: If analysis fails.
        """
        if 'analysis' not in self._services:
            raise AnalysisError("Analysis service not available")
        
        analysis_service = self._services['analysis']
        
        try:
            logger.debug(f"Analyzing {len(tickets)} tickets for workflow: {context.operation_id}")
            
            # Show progress if available
            if 'progress' in self._services:
                self._services['progress'].start_operation("Analyzing ticket data")
            
            start_time = time.time()
            analysis_result = analysis_service.analyze_tickets(tickets)
            analysis_time = (time.time() - start_time) * 1000
            
            # Update performance metrics
            self._record_performance_metric('analysis_ms', analysis_time)
            
            # Complete progress
            if 'progress' in self._services:
                self._services['progress'].complete_operation(
                    True, f"Analysis completed for {len(tickets)} tickets"
                )
            
            logger.info(f"Analysis completed in {analysis_time:.2f}ms")
            return analysis_result
            
        except Exception as e:
            if 'progress' in self._services:
                self._services['progress'].complete_operation(False, f"Analysis failed: {e}")
            
            logger.error(f"Analysis failed for workflow {context.operation_id}: {e}")
            raise AnalysisError(f"Failed to analyze tickets: {e}")
    
    def _generate_report(self, analysis_result: AnalysisResult, 
                        report_config: ReportConfig,
                        context: WorkflowContext) -> Optional[str]:
        """Generate report from analysis results.
        
        Args:
            analysis_result: Analysis results.
            report_config: Report configuration.
            context: Workflow context.
            
        Returns:
            Report output path or content.
        """
        if 'reporting' not in self._services:
            logger.warning("Reporting service not available, skipping report generation")
            return None
        
        reporting_service = self._services['reporting']
        
        try:
            logger.debug(f"Generating report for workflow: {context.operation_id}")
            
            # Show progress if available
            if 'progress' in self._services:
                self._services['progress'].start_operation("Generating report")
            
            start_time = time.time()
            report_output = reporting_service.generate_report(analysis_result, report_config)
            report_time = (time.time() - start_time) * 1000
            
            # Update performance metrics
            self._record_performance_metric('report_generation_ms', report_time)
            
            # Complete progress
            if 'progress' in self._services:
                self._services['progress'].complete_operation(
                    True, f"Report generated: {report_output}"
                )
            
            logger.info(f"Report generated in {report_time:.2f}ms: {report_output}")
            return report_output
            
        except Exception as e:
            if 'progress' in self._services:
                self._services['progress'].complete_operation(False, f"Report generation failed: {e}")
            
            logger.error(f"Report generation failed for workflow {context.operation_id}: {e}")
            # Don't raise error for report generation - it's not critical
            return None
    
    def _handle_workflow_error(self, error: Exception, 
                              context: WorkflowContext,
                              result: WorkflowResult) -> None:
        """Handle workflow errors with graceful degradation.
        
        Args:
            error: The error that occurred.
            context: Workflow context.
            result: Workflow result to update.
        """
        logger.info(f"Attempting graceful degradation for workflow: {context.operation_id}")
        
        # Add error context
        error_context = create_error_context(
            operation=f"workflow_{context.operation_id}",
            user_id=context.user_id,
            timestamp=datetime.now(),
            additional_info={
                'request_params': context.request_params,
                'execution_time_ms': self._calculate_execution_time(context)
            }
        )
        
        # Update result with error context
        if hasattr(result, 'error_context'):
            result.error_context = error_context
    
    @contextmanager
    def _workflow_timing(self, context: WorkflowContext):
        """Context manager for workflow timing.
        
        Args:
            context: Workflow context to update with timing.
        """
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = (time.time() - start_time) * 1000
            if not hasattr(context, 'execution_time_ms'):
                context.execution_time_ms = execution_time
    
    def _calculate_execution_time(self, context: WorkflowContext) -> float:
        """Calculate workflow execution time.
        
        Args:
            context: Workflow context.
            
        Returns:
            Execution time in milliseconds.
        """
        if hasattr(context, 'execution_time_ms'):
            return context.execution_time_ms
        
        return (datetime.now() - context.start_time).total_seconds() * 1000
    
    def _collect_workflow_metrics(self, context: WorkflowContext) -> Dict[str, Any]:
        """Collect workflow performance metrics.
        
        Args:
            context: Workflow context.
            
        Returns:
            Dictionary of collected metrics.
        """
        return {
            'operation_id': context.operation_id,
            'execution_time_ms': self._calculate_execution_time(context),
            'service_health': self._health_status.copy(),
            'performance_metrics': self._get_performance_summary()
        }
    
    def _record_performance_metric(self, metric_name: str, value: float) -> None:
        """Record a performance metric.
        
        Args:
            metric_name: Name of the metric.
            value: Metric value.
        """
        if metric_name not in self._performance_metrics:
            self._performance_metrics[metric_name] = []
        
        self._performance_metrics[metric_name].append(value)
        
        # Keep only last 100 measurements
        if len(self._performance_metrics[metric_name]) > 100:
            self._performance_metrics[metric_name] = self._performance_metrics[metric_name][-100:]
    
    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of performance metrics.
        
        Returns:
            Dictionary containing performance summary.
        """
        summary = {}
        
        for metric_name, values in self._performance_metrics.items():
            if values:
                summary[metric_name] = {
                    'count': len(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'latest': values[-1]
                }
        
        return summary
    
    def _setup_logging(self) -> None:
        """Setup application logging configuration."""
        # Logging setup will be handled by the logging configuration
        pass
    
    def _setup_performance_monitoring(self) -> None:
        """Setup performance monitoring for the application."""
        logger.debug("Performance monitoring initialized")
        # Initialize performance metrics storage
        self._performance_metrics = {
            'data_retrieval_ms': [],
            'analysis_ms': [],
            'report_generation_ms': []
        }
    
    def _cleanup_services(self) -> None:
        """Cleanup all application services."""
        for service_name, service in self._services.items():
            try:
                if hasattr(service, 'cleanup'):
                    service.cleanup()
                    logger.debug(f"Cleaned up service: {service_name}")
            except Exception as e:
                logger.error(f"Error cleaning up service {service_name}: {e}")
        
        self._services.clear()
        self._health_status.clear()
    
    def _log_final_metrics(self) -> None:
        """Log final performance metrics before shutdown."""
        if self._performance_metrics:
            summary = self._get_performance_summary()
            logger.info(f"Final performance metrics: {summary}")
    
    def _generate_operation_id(self) -> str:
        """Generate unique operation ID for workflow tracking.
        
        Returns:
            Unique operation identifier.
        """
        import uuid
        return f"op_{int(time.time())}_{str(uuid.uuid4())[:8]}"


def create_app(config: Optional[ApplicationConfig] = None) -> TicketAnalyzerApp:
    """Factory function to create and configure the application.
    
    Args:
        config: Optional application configuration.
        
    Returns:
        Configured ticket analyzer application.
    """
    app = TicketAnalyzerApp(config)
    logger.info("Created ticket analyzer application")
    return app
"""Dependency injection container for ticket analyzer application.

This module provides a dependency injection container that manages service
registration, dependency resolution, and lifecycle management for all
application services. It follows the dependency injection pattern to
ensure loose coupling and testability.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional, Type, TypeVar, Callable, Union
from enum import Enum
from dataclasses import dataclass
from threading import Lock

from .interfaces import (
    AuthenticationInterface,
    DataRetrievalInterface,
    AnalysisInterface,
    ReportingInterface,
    ConfigurationInterface,
    MCPClientInterface,
    DataSanitizerInterface
)
from .models import ApplicationConfig, ConfigurationError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceLifecycle(Enum):
    """Service lifecycle management types."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


@dataclass
class ServiceRegistration:
    """Service registration information."""
    service_type: Type
    implementation: Union[Type, Callable[..., Any]]
    lifecycle: ServiceLifecycle
    dependencies: list[str]
    factory: Optional[Callable[..., Any]] = None
    instance: Optional[Any] = None
    initialized: bool = False


class DependencyContainer:
    """Dependency injection container for service management.
    
    This container manages service registration, dependency resolution,
    and lifecycle management. It supports singleton, transient, and
    scoped service lifecycles with automatic dependency injection.
    
    Example:
        >>> container = DependencyContainer()
        >>> container.register_singleton(AuthenticationInterface, MidwayAuthenticator)
        >>> auth_service = container.resolve(AuthenticationInterface)
    """
    
    def __init__(self, config: Optional[ApplicationConfig] = None) -> None:
        """Initialize dependency container.
        
        Args:
            config: Optional application configuration for service setup.
        """
        self._services: Dict[str, ServiceRegistration] = {}
        self._instances: Dict[str, Any] = {}
        self._lock = Lock()
        self._config = config
        self._initialized = False
        
        # Register core services
        self._register_core_services()
    
    def register_singleton(self, service_type: Type[T], 
                          implementation: Union[Type[T], Callable[..., T]],
                          dependencies: Optional[list[str]] = None) -> None:
        """Register a singleton service.
        
        Args:
            service_type: Interface or base class type.
            implementation: Concrete implementation class or factory function.
            dependencies: List of dependency service names.
        """
        self._register_service(
            service_type, 
            implementation, 
            ServiceLifecycle.SINGLETON,
            dependencies or []
        )
    
    def register_transient(self, service_type: Type[T], 
                          implementation: Union[Type[T], Callable[..., T]],
                          dependencies: Optional[list[str]] = None) -> None:
        """Register a transient service (new instance each time).
        
        Args:
            service_type: Interface or base class type.
            implementation: Concrete implementation class or factory function.
            dependencies: List of dependency service names.
        """
        self._register_service(
            service_type, 
            implementation, 
            ServiceLifecycle.TRANSIENT,
            dependencies or []
        )
    
    def register_scoped(self, service_type: Type[T], 
                       implementation: Union[Type[T], Callable[..., T]],
                       dependencies: Optional[list[str]] = None) -> None:
        """Register a scoped service (one instance per scope).
        
        Args:
            service_type: Interface or base class type.
            implementation: Concrete implementation class or factory function.
            dependencies: List of dependency service names.
        """
        self._register_service(
            service_type, 
            implementation, 
            ServiceLifecycle.SCOPED,
            dependencies or []
        )
    
    def register_factory(self, service_type: Type[T], 
                        factory: Callable[..., T],
                        lifecycle: ServiceLifecycle = ServiceLifecycle.SINGLETON,
                        dependencies: Optional[list[str]] = None) -> None:
        """Register a service with custom factory method.
        
        Args:
            service_type: Interface or base class type.
            factory: Factory function that creates service instances.
            lifecycle: Service lifecycle management type.
            dependencies: List of dependency service names.
        """
        service_name = self._get_service_name(service_type)
        
        with self._lock:
            self._services[service_name] = ServiceRegistration(
                service_type=service_type,
                implementation=factory,
                lifecycle=lifecycle,
                dependencies=dependencies or [],
                factory=factory
            )
        
        logger.debug(f"Registered factory for {service_name} with {lifecycle.value} lifecycle")
    
    def register_instance(self, service_type: Type[T], instance: T) -> None:
        """Register a pre-created service instance.
        
        Args:
            service_type: Interface or base class type.
            instance: Pre-created service instance.
        """
        service_name = self._get_service_name(service_type)
        
        with self._lock:
            self._services[service_name] = ServiceRegistration(
                service_type=service_type,
                implementation=type(instance),
                lifecycle=ServiceLifecycle.SINGLETON,
                dependencies=[],
                instance=instance,
                initialized=True
            )
            self._instances[service_name] = instance
        
        logger.debug(f"Registered instance for {service_name}")
    
    def resolve(self, service_type: Type[T]) -> T:
        """Resolve a service instance with dependency injection.
        
        Args:
            service_type: Interface or base class type to resolve.
            
        Returns:
            Service instance with all dependencies injected.
            
        Raises:
            ConfigurationError: If service is not registered or cannot be resolved.
        """
        service_name = self._get_service_name(service_type)
        
        if service_name not in self._services:
            raise ConfigurationError(f"Service {service_name} is not registered")
        
        return self._resolve_service(service_name)
    
    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered.
        
        Args:
            service_type: Interface or base class type to check.
            
        Returns:
            True if service is registered, False otherwise.
        """
        service_name = self._get_service_name(service_type)
        return service_name in self._services
    
    def get_registered_services(self) -> list[str]:
        """Get list of all registered service names.
        
        Returns:
            List of registered service names.
        """
        return list(self._services.keys())
    
    def initialize_services(self) -> None:
        """Initialize all registered services and resolve dependencies.
        
        This method should be called after all services are registered
        to ensure proper initialization order and dependency resolution.
        
        Raises:
            ConfigurationError: If service initialization fails.
        """
        if self._initialized:
            return
        
        logger.info("Initializing dependency container services")
        
        try:
            # Initialize services in dependency order
            for service_name in self._get_initialization_order():
                if not self._services[service_name].initialized:
                    self._resolve_service(service_name)
            
            self._initialized = True
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise ConfigurationError(f"Failed to initialize services: {e}")
    
    def cleanup(self) -> None:
        """Cleanup all service instances and resources.
        
        This method should be called during application shutdown
        to properly cleanup resources and close connections.
        """
        logger.info("Cleaning up dependency container")
        
        with self._lock:
            # Cleanup services in reverse order
            for service_name in reversed(list(self._instances.keys())):
                instance = self._instances.get(service_name)
                if instance and hasattr(instance, 'cleanup'):
                    try:
                        instance.cleanup()
                        logger.debug(f"Cleaned up service: {service_name}")
                    except Exception as e:
                        logger.error(f"Error cleaning up {service_name}: {e}")
            
            # Clear all instances and registrations
            self._instances.clear()
            self._services.clear()
            self._initialized = False
        
        logger.info("Dependency container cleanup completed")
    
    def _register_service(self, service_type: Type, 
                         implementation: Union[Type, Callable],
                         lifecycle: ServiceLifecycle,
                         dependencies: list[str]) -> None:
        """Internal method to register a service.
        
        Args:
            service_type: Interface or base class type.
            implementation: Concrete implementation or factory.
            lifecycle: Service lifecycle type.
            dependencies: List of dependency service names.
        """
        service_name = self._get_service_name(service_type)
        
        with self._lock:
            self._services[service_name] = ServiceRegistration(
                service_type=service_type,
                implementation=implementation,
                lifecycle=lifecycle,
                dependencies=dependencies
            )
        
        logger.debug(f"Registered {service_name} with {lifecycle.value} lifecycle")
    
    def _resolve_service(self, service_name: str) -> Any:
        """Internal method to resolve a service instance.
        
        Args:
            service_name: Name of service to resolve.
            
        Returns:
            Service instance.
            
        Raises:
            ConfigurationError: If service cannot be resolved.
        """
        registration = self._services[service_name]
        
        # Return existing singleton instance
        if (registration.lifecycle == ServiceLifecycle.SINGLETON and 
            registration.instance is not None):
            return registration.instance
        
        # Check for circular dependencies
        if hasattr(self, '_resolving') and service_name in self._resolving:
            raise ConfigurationError(f"Circular dependency detected for {service_name}")
        
        # Track services being resolved
        if not hasattr(self, '_resolving'):
            self._resolving = set()
        self._resolving.add(service_name)
        
        try:
            # Resolve dependencies first
            dependencies = {}
            for dep_name in registration.dependencies:
                if dep_name in self._services:
                    dependencies[dep_name] = self._resolve_service(dep_name)
                else:
                    logger.warning(f"Dependency {dep_name} not found for {service_name}")
            
            # Create service instance
            if registration.factory:
                instance = registration.factory(self, **dependencies)
            elif callable(registration.implementation):
                if dependencies:
                    instance = registration.implementation(**dependencies)
                else:
                    instance = registration.implementation()
            else:
                raise ConfigurationError(f"Invalid implementation for {service_name}")
            
            # Store singleton instances
            if registration.lifecycle == ServiceLifecycle.SINGLETON:
                with self._lock:
                    registration.instance = instance
                    registration.initialized = True
                    self._instances[service_name] = instance
            
            logger.debug(f"Resolved service: {service_name}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to resolve service {service_name}: {e}")
            raise ConfigurationError(f"Cannot resolve service {service_name}: {e}")
        
        finally:
            self._resolving.discard(service_name)
    
    def _get_service_name(self, service_type: Type) -> str:
        """Get service name from type.
        
        Args:
            service_type: Service type.
            
        Returns:
            Service name string.
        """
        return f"{service_type.__module__}.{service_type.__name__}"
    
    def _get_initialization_order(self) -> list[str]:
        """Get service initialization order based on dependencies.
        
        Returns:
            List of service names in initialization order.
            
        Raises:
            ConfigurationError: If circular dependencies are detected.
        """
        # Topological sort for dependency order
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(service_name: str) -> None:
            if service_name in temp_visited:
                raise ConfigurationError(f"Circular dependency detected involving {service_name}")
            
            if service_name not in visited:
                temp_visited.add(service_name)
                
                # Visit dependencies first
                registration = self._services.get(service_name)
                if registration:
                    for dep_name in registration.dependencies:
                        if dep_name in self._services:
                            visit(dep_name)
                
                temp_visited.remove(service_name)
                visited.add(service_name)
                order.append(service_name)
        
        # Visit all services
        for service_name in self._services:
            if service_name not in visited:
                visit(service_name)
        
        return order
    
    def _register_core_services(self) -> None:
        """Register core application services.
        
        This method registers the essential services that are always
        needed by the application. Specific implementations will be
        registered by the application setup.
        """
        logger.debug("Registering core service interfaces")
        
        # Core services will be registered by the application
        # This method can be extended to register default implementations
        pass


def create_container(config: Optional[ApplicationConfig] = None) -> DependencyContainer:
    """Factory function to create and configure dependency container.
    
    Args:
        config: Optional application configuration.
        
    Returns:
        Configured dependency container.
    """
    container = DependencyContainer(config)
    
    # Additional container setup can be done here
    logger.info("Created dependency injection container")
    
    return container
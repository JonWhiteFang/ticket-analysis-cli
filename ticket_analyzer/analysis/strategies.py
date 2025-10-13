"""Analysis strategy patterns for ticket metrics calculation.

This module implements the Strategy pattern for different types of metrics
calculations. Each strategy encapsulates a specific algorithm for calculating
metrics from ticket data, allowing for extensible and maintainable analysis
capabilities.

The MetricsCalculator base class defines the interface that all concrete
strategy implementations must follow, ensuring consistency and enabling
easy addition of new metrics calculation strategies.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..models.ticket import Ticket
from ..models.exceptions import AnalysisError


class MetricsCalculator(ABC):
    """Abstract base class for metrics calculation strategies.
    
    This class defines the interface for all metrics calculation strategies
    using the Strategy pattern. Each concrete implementation should focus on
    calculating specific types of metrics from ticket data.
    
    All implementations must be thread-safe and handle edge cases gracefully,
    including empty datasets and missing data fields.
    """
    
    @abstractmethod
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate specific metrics from ticket data.
        
        This method performs the core calculation logic for the specific
        metrics this calculator is responsible for. Implementations should
        handle edge cases such as empty datasets, missing fields, and
        invalid data gracefully.
        
        Args:
            tickets: List of tickets to analyze. May be empty.
            
        Returns:
            Dictionary containing calculated metrics with descriptive keys.
            The structure should be consistent across calls and include
            metadata about the calculation (e.g., sample size, date range).
            
        Raises:
            AnalysisError: If calculation fails due to data issues or
                processing errors that cannot be handled gracefully.
            
        Example:
            >>> calculator = ResolutionTimeCalculator()
            >>> tickets = [ticket1, ticket2, ticket3]
            >>> result = calculator.calculate(tickets)
            >>> print(result)
            {
                'avg_resolution_time_hours': 24.5,
                'median_resolution_time_hours': 18.0,
                'total_resolved': 2,
                'sample_size': 3
            }
        """
        pass
    
    @abstractmethod
    def get_metric_names(self) -> List[str]:
        """Get list of metric names this calculator provides.
        
        This method returns the names of all metrics that this calculator
        can produce. These names should match the keys in the dictionary
        returned by the calculate() method.
        
        Returns:
            List of metric names as strings. Names should be descriptive
            and follow a consistent naming convention (e.g., snake_case).
            
        Example:
            >>> calculator = ResolutionTimeCalculator()
            >>> names = calculator.get_metric_names()
            >>> print(names)
            ['avg_resolution_time_hours', 'median_resolution_time_hours', 'total_resolved']
        """
        pass
    
    def validate_input(self, tickets: List[Ticket]) -> bool:
        """Validate input tickets for calculation requirements.
        
        This method provides a default validation that can be overridden
        by concrete implementations if they have specific requirements.
        
        Args:
            tickets: List of tickets to validate.
            
        Returns:
            True if tickets are valid for this calculator, False otherwise.
        """
        if not isinstance(tickets, list):
            return False
        
        # Allow empty lists - calculators should handle this case
        if not tickets:
            return True
        
        # Validate that all items are Ticket instances
        return all(isinstance(ticket, Ticket) for ticket in tickets)
    
    def get_calculator_info(self) -> Dict[str, Any]:
        """Get information about this calculator.
        
        Returns:
            Dictionary containing calculator metadata including name,
            description, and supported metrics.
        """
        return {
            'name': self.__class__.__name__,
            'description': self.__class__.__doc__ or 'No description available',
            'metrics': self.get_metric_names(),
            'version': '1.0.0'
        }
    
    def supports_metric(self, metric_name: str) -> bool:
        """Check if this calculator supports a specific metric.
        
        Args:
            metric_name: Name of the metric to check.
            
        Returns:
            True if the metric is supported, False otherwise.
        """
        return metric_name in self.get_metric_names()
    
    def _handle_empty_dataset(self) -> Dict[str, Any]:
        """Handle empty dataset case with appropriate default values.
        
        This method provides a default implementation for handling empty
        datasets. Concrete implementations can override this method to
        provide calculator-specific default values.
        
        Returns:
            Dictionary with default values for empty datasets.
        """
        return {
            'sample_size': 0,
            'data_available': False,
            'message': 'No data available for calculation'
        }
    
    def _validate_ticket_data(self, ticket: Ticket) -> bool:
        """Validate individual ticket data for calculation requirements.
        
        This method provides basic validation that can be extended by
        concrete implementations for their specific needs.
        
        Args:
            ticket: Ticket to validate.
            
        Returns:
            True if ticket data is valid, False otherwise.
        """
        if not ticket or not ticket.id:
            return False
        
        # Basic validation - ticket has required fields
        return (
            hasattr(ticket, 'created_date') and 
            ticket.created_date is not None and
            hasattr(ticket, 'status') and 
            ticket.status is not None
        )
    
    def _filter_valid_tickets(self, tickets: List[Ticket]) -> List[Ticket]:
        """Filter tickets to include only those valid for calculation.
        
        This method removes tickets that don't meet the basic requirements
        for calculation, helping to ensure data quality.
        
        Args:
            tickets: List of tickets to filter.
            
        Returns:
            List of tickets that pass validation.
        """
        return [
            ticket for ticket in tickets 
            if self._validate_ticket_data(ticket)
        ]
    
    def _get_date_range(self, tickets: List[Ticket]) -> Optional[Dict[str, datetime]]:
        """Get the date range covered by the ticket dataset.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with 'start' and 'end' datetime objects, or None if
            no valid dates are found.
        """
        if not tickets:
            return None
        
        valid_dates = [
            ticket.created_date for ticket in tickets 
            if ticket.created_date is not None
        ]
        
        if not valid_dates:
            return None
        
        return {
            'start': min(valid_dates),
            'end': max(valid_dates)
        }
    
    def _add_metadata(self, metrics: Dict[str, Any], tickets: List[Ticket]) -> Dict[str, Any]:
        """Add metadata to metrics results.
        
        This method adds common metadata that's useful for all calculators,
        such as sample size and date range information.
        
        Args:
            metrics: Calculated metrics dictionary.
            tickets: Original tickets used for calculation.
            
        Returns:
            Metrics dictionary with added metadata.
        """
        metadata = {
            'sample_size': len(tickets),
            'calculation_timestamp': datetime.now().isoformat(),
            'calculator': self.__class__.__name__
        }
        
        date_range = self._get_date_range(tickets)
        if date_range:
            metadata['date_range'] = {
                'start': date_range['start'].isoformat(),
                'end': date_range['end'].isoformat()
            }
        
        # Add metadata to the metrics dictionary
        result = metrics.copy()
        result['_metadata'] = metadata
        
        return result


class TrendAnalysisStrategy(ABC):
    """Abstract base class for trend analysis strategies.
    
    This class defines the interface for trend analysis calculations,
    which focus on time-series data and pattern recognition in ticket
    metrics over time.
    """
    
    @abstractmethod
    def analyze_trends(self, tickets: List[Ticket], 
                      time_period: timedelta = timedelta(days=30)) -> Dict[str, Any]:
        """Analyze trends in ticket data over specified time period.
        
        Args:
            tickets: List of tickets to analyze.
            time_period: Time period for trend analysis (default: 30 days).
            
        Returns:
            Dictionary containing trend analysis results.
            
        Raises:
            AnalysisError: If trend analysis fails.
        """
        pass
    
    @abstractmethod
    def detect_patterns(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Detect patterns in ticket data.
        
        Args:
            tickets: List of tickets to analyze for patterns.
            
        Returns:
            Dictionary containing detected patterns and anomalies.
        """
        pass
    
    @abstractmethod
    def get_trend_names(self) -> List[str]:
        """Get list of trend analysis types this strategy provides.
        
        Returns:
            List of trend analysis names.
        """
        pass


class StatisticalAnalysisStrategy(ABC):
    """Abstract base class for statistical analysis strategies.
    
    This class defines the interface for statistical calculations
    on ticket data, including distributions, correlations, and
    statistical summaries.
    """
    
    @abstractmethod
    def calculate_statistics(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate statistical measures from ticket data.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing statistical measures.
            
        Raises:
            AnalysisError: If statistical calculation fails.
        """
        pass
    
    @abstractmethod
    def calculate_distributions(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate distributions of ticket attributes.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing distribution data.
        """
        pass
    
    @abstractmethod
    def get_statistical_measures(self) -> List[str]:
        """Get list of statistical measures this strategy provides.
        
        Returns:
            List of statistical measure names.
        """
        pass
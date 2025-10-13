"""Core analysis service for ticket data processing and metrics calculation.

This module implements the AnalysisEngine class which serves as the main
orchestrator for ticket analysis operations. It uses pandas DataFrames for
efficient data manipulation and coordinates multiple metrics calculators
using the Strategy pattern.

The service handles data validation, processing, and aggregation of results
from various analysis strategies while providing comprehensive error handling
and performance optimization.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import logging

import pandas as pd

from ..interfaces import AnalysisInterface, MetricsCalculatorInterface
from ..models.ticket import Ticket
from ..models.analysis import AnalysisResult, SearchCriteria
from ..models.exceptions import AnalysisError, DataProcessingError
from .strategies import MetricsCalculator

logger = logging.getLogger(__name__)


class AnalysisEngine(AnalysisInterface):
    """Core analysis engine for comprehensive ticket analysis.
    
    This class implements the main analysis workflow using the Strategy pattern
    to coordinate multiple metrics calculators. It provides efficient data
    processing using pandas DataFrames and handles edge cases gracefully.
    
    The engine supports:
    - Multiple metrics calculation strategies
    - Pandas DataFrame processing for performance
    - Comprehensive error handling and recovery
    - Data validation and cleaning
    - Statistical summaries and insights generation
    
    Example:
        >>> engine = AnalysisEngine()
        >>> engine.add_calculator(ResolutionTimeCalculator())
        >>> engine.add_calculator(StatusDistributionCalculator())
        >>> result = engine.analyze_tickets(tickets)
        >>> print(result.metrics['avg_resolution_time_hours'])
        24.5
    """
    
    def __init__(self) -> None:
        """Initialize the analysis engine with empty calculator registry."""
        self._calculators: List[MetricsCalculator] = []
        self._data_processor = TicketDataProcessor()
        self._performance_monitor = AnalysisPerformanceMonitor()
    
    def add_calculator(self, calculator: MetricsCalculator) -> None:
        """Add a metrics calculator strategy to the engine.
        
        Args:
            calculator: Metrics calculator implementing MetricsCalculator interface.
            
        Raises:
            ValueError: If calculator is None or invalid.
        """
        if not calculator:
            raise ValueError("Calculator cannot be None")
        
        if not isinstance(calculator, MetricsCalculator):
            raise ValueError("Calculator must implement MetricsCalculator interface")
        
        self._calculators.append(calculator)
        logger.debug(f"Added calculator: {calculator.__class__.__name__}")
    
    def remove_calculator(self, calculator_type: type) -> bool:
        """Remove a calculator by type.
        
        Args:
            calculator_type: Type of calculator to remove.
            
        Returns:
            True if calculator was removed, False if not found.
        """
        initial_count = len(self._calculators)
        self._calculators = [
            calc for calc in self._calculators 
            if not isinstance(calc, calculator_type)
        ]
        removed = len(self._calculators) < initial_count
        
        if removed:
            logger.debug(f"Removed calculator: {calculator_type.__name__}")
        
        return removed
    
    def get_calculators(self) -> List[str]:
        """Get list of registered calculator names.
        
        Returns:
            List of calculator class names.
        """
        return [calc.__class__.__name__ for calc in self._calculators]
    
    def analyze_tickets(self, tickets: List[Ticket]) -> AnalysisResult:
        """Perform comprehensive analysis on ticket data.
        
        This is the main entry point for ticket analysis. It validates input,
        processes data, runs all registered calculators, and aggregates results.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            AnalysisResult containing metrics, trends, and summary information.
            
        Raises:
            AnalysisError: If analysis fails due to data or processing issues.
            ValueError: If tickets parameter is invalid.
        """
        if not isinstance(tickets, list):
            raise ValueError("Tickets must be a list")
        
        logger.info(f"Starting analysis of {len(tickets)} tickets")
        start_time = datetime.now()
        
        try:
            # Validate and process input data
            validated_tickets = self._validate_and_process_tickets(tickets)
            
            if not validated_tickets:
                logger.warning("No valid tickets found for analysis")
                return self._create_empty_result(tickets)
            
            # Create DataFrame for efficient processing
            df = self._create_dataframe(validated_tickets)
            
            # Calculate metrics using all registered calculators
            metrics = self._calculate_all_metrics(validated_tickets)
            
            # Generate trends analysis
            trends = self._generate_trends_analysis(df, validated_tickets)
            
            # Create summary insights
            summary = self._generate_summary_insights(metrics, validated_tickets)
            
            # Create analysis result
            result = AnalysisResult(
                metrics=metrics,
                trends=trends,
                summary=summary,
                generated_at=datetime.now(),
                ticket_count=len(validated_tickets),
                original_count=len(tickets),
                date_range=self._get_analysis_date_range(validated_tickets)
            )
            
            # Log performance metrics
            duration = datetime.now() - start_time
            self._performance_monitor.record_analysis(
                ticket_count=len(tickets),
                duration=duration,
                calculators_used=len(self._calculators)
            )
            
            logger.info(f"Analysis completed in {duration.total_seconds():.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise AnalysisError(f"Ticket analysis failed: {e}") from e
    
    def calculate_metrics(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate metrics from ticket data using registered calculators.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing all calculated metrics.
            
        Raises:
            AnalysisError: If metrics calculation fails.
        """
        if not tickets:
            return {}
        
        validated_tickets = self._validate_and_process_tickets(tickets)
        return self._calculate_all_metrics(validated_tickets)
    
    def generate_trends(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Generate trend analysis from ticket data.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing trend analysis results.
            
        Raises:
            AnalysisError: If trend generation fails.
        """
        if not tickets:
            return {}
        
        validated_tickets = self._validate_and_process_tickets(tickets)
        df = self._create_dataframe(validated_tickets)
        return self._generate_trends_analysis(df, validated_tickets)
    
    def _validate_and_process_tickets(self, tickets: List[Ticket]) -> List[Ticket]:
        """Validate and process tickets for analysis.
        
        Args:
            tickets: Raw tickets to validate and process.
            
        Returns:
            List of validated and processed tickets.
        """
        if not tickets:
            return []
        
        # Use data processor for validation and cleaning
        processed_tickets = self._data_processor.process_tickets(tickets)
        
        logger.debug(f"Processed {len(processed_tickets)} valid tickets from {len(tickets)} input tickets")
        return processed_tickets
    
    def _create_dataframe(self, tickets: List[Ticket]) -> pd.DataFrame:
        """Create pandas DataFrame from ticket data for efficient processing.
        
        Args:
            tickets: List of validated tickets.
            
        Returns:
            DataFrame with ticket data optimized for analysis.
        """
        if not tickets:
            return pd.DataFrame()
        
        try:
            # Convert tickets to dictionary format
            ticket_data = []
            for ticket in tickets:
                ticket_dict = {
                    'id': ticket.id,
                    'title': ticket.title,
                    'status': ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                    'severity': ticket.severity.value if hasattr(ticket.severity, 'value') else str(ticket.severity),
                    'created_date': ticket.created_date,
                    'updated_date': ticket.updated_date,
                    'resolved_date': ticket.resolved_date,
                    'assignee': ticket.assignee,
                    'resolver_group': ticket.resolver_group,
                    'is_resolved': ticket.is_resolved(),
                    'age_hours': ticket.age().total_seconds() / 3600 if ticket.age() else None,
                    'resolution_time_hours': (
                        ticket.resolution_time().total_seconds() / 3600 
                        if ticket.resolution_time() else None
                    )
                }
                ticket_data.append(ticket_dict)
            
            # Create DataFrame with proper data types
            df = pd.DataFrame(ticket_data)
            
            # Optimize data types for performance
            df = self._optimize_dataframe_types(df)
            
            logger.debug(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
            return df
            
        except Exception as e:
            logger.error(f"Failed to create DataFrame: {e}")
            raise DataProcessingError(f"DataFrame creation failed: {e}") from e
    
    def _optimize_dataframe_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame data types for memory efficiency and performance.
        
        Args:
            df: DataFrame to optimize.
            
        Returns:
            Optimized DataFrame.
        """
        if df.empty:
            return df
        
        try:
            # Convert categorical columns
            categorical_columns = ['status', 'severity', 'assignee', 'resolver_group']
            for col in categorical_columns:
                if col in df.columns:
                    df[col] = df[col].astype('category')
            
            # Convert datetime columns
            datetime_columns = ['created_date', 'updated_date', 'resolved_date']
            for col in datetime_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            
            # Convert boolean columns
            boolean_columns = ['is_resolved']
            for col in boolean_columns:
                if col in df.columns:
                    df[col] = df[col].astype('bool')
            
            return df
            
        except Exception as e:
            logger.warning(f"DataFrame optimization failed: {e}")
            return df  # Return original if optimization fails
    
    def _calculate_all_metrics(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate metrics using all registered calculators.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing all calculated metrics.
        """
        if not self._calculators:
            logger.warning("No calculators registered for metrics calculation")
            return {}
        
        all_metrics = {}
        
        for calculator in self._calculators:
            try:
                calculator_metrics = calculator.calculate(tickets)
                
                # Add calculator name prefix to avoid conflicts
                calculator_name = calculator.__class__.__name__
                prefixed_metrics = {
                    f"{calculator_name}_{key}" if not key.startswith('_') else key: value
                    for key, value in calculator_metrics.items()
                }
                
                all_metrics.update(prefixed_metrics)
                
                logger.debug(f"Calculated metrics using {calculator_name}")
                
            except Exception as e:
                logger.error(f"Calculator {calculator.__class__.__name__} failed: {e}")
                # Continue with other calculators instead of failing completely
                all_metrics[f"{calculator.__class__.__name__}_error"] = str(e)
        
        return all_metrics
    
    def _generate_trends_analysis(self, df: pd.DataFrame, tickets: List[Ticket]) -> Dict[str, Any]:
        """Generate trend analysis from DataFrame and ticket data.
        
        Args:
            df: DataFrame containing ticket data.
            tickets: Original ticket objects.
            
        Returns:
            Dictionary containing trend analysis results.
        """
        if df.empty:
            return {'trends_available': False, 'message': 'No data for trend analysis'}
        
        trends = {}
        
        try:
            # Volume trends over time
            trends['volume_trends'] = self._calculate_volume_trends(df)
            
            # Resolution time trends
            trends['resolution_trends'] = self._calculate_resolution_trends(df)
            
            # Status distribution trends
            trends['status_trends'] = self._calculate_status_trends(df)
            
            # Severity distribution trends
            trends['severity_trends'] = self._calculate_severity_trends(df)
            
            logger.debug("Generated trend analysis")
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            trends['error'] = str(e)
        
        return trends
    
    def _calculate_volume_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate ticket volume trends over time.
        
        Args:
            df: DataFrame with ticket data.
            
        Returns:
            Dictionary containing volume trend data.
        """
        if 'created_date' not in df.columns:
            return {'error': 'No created_date column for volume analysis'}
        
        try:
            # Group by date and count tickets
            df_copy = df.copy()
            df_copy['date'] = df_copy['created_date'].dt.date
            daily_counts = df_copy.groupby('date').size()
            
            # Calculate weekly and monthly aggregations
            df_copy['week'] = df_copy['created_date'].dt.to_period('W')
            df_copy['month'] = df_copy['created_date'].dt.to_period('M')
            
            weekly_counts = df_copy.groupby('week').size()
            monthly_counts = df_copy.groupby('month').size()
            
            return {
                'daily_volume': daily_counts.to_dict(),
                'weekly_volume': {str(k): v for k, v in weekly_counts.to_dict().items()},
                'monthly_volume': {str(k): v for k, v in monthly_counts.to_dict().items()},
                'total_tickets': len(df),
                'date_range': {
                    'start': df['created_date'].min().isoformat() if not df['created_date'].isna().all() else None,
                    'end': df['created_date'].max().isoformat() if not df['created_date'].isna().all() else None
                }
            }
            
        except Exception as e:
            return {'error': f'Volume trend calculation failed: {e}'}
    
    def _calculate_resolution_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate resolution time trends.
        
        Args:
            df: DataFrame with ticket data.
            
        Returns:
            Dictionary containing resolution trend data.
        """
        if 'resolution_time_hours' not in df.columns:
            return {'error': 'No resolution time data available'}
        
        try:
            resolved_df = df[df['is_resolved'] == True].copy()
            
            if resolved_df.empty:
                return {'message': 'No resolved tickets for trend analysis'}
            
            # Group by week and calculate average resolution time
            resolved_df['week'] = resolved_df['resolved_date'].dt.to_period('W')
            weekly_avg = resolved_df.groupby('week')['resolution_time_hours'].mean()
            
            # Calculate monthly trends
            resolved_df['month'] = resolved_df['resolved_date'].dt.to_period('M')
            monthly_avg = resolved_df.groupby('month')['resolution_time_hours'].mean()
            
            return {
                'weekly_avg_resolution_hours': {str(k): v for k, v in weekly_avg.to_dict().items()},
                'monthly_avg_resolution_hours': {str(k): v for k, v in monthly_avg.to_dict().items()},
                'overall_avg_hours': resolved_df['resolution_time_hours'].mean(),
                'resolved_count': len(resolved_df)
            }
            
        except Exception as e:
            return {'error': f'Resolution trend calculation failed: {e}'}
    
    def _calculate_status_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate status distribution trends over time.
        
        Args:
            df: DataFrame with ticket data.
            
        Returns:
            Dictionary containing status trend data.
        """
        if 'status' not in df.columns or 'created_date' not in df.columns:
            return {'error': 'Missing required columns for status trends'}
        
        try:
            df_copy = df.copy()
            df_copy['month'] = df_copy['created_date'].dt.to_period('M')
            
            # Calculate status distribution by month
            status_by_month = df_copy.groupby(['month', 'status']).size().unstack(fill_value=0)
            
            return {
                'monthly_status_distribution': {
                    str(month): row.to_dict() 
                    for month, row in status_by_month.iterrows()
                },
                'overall_status_distribution': df['status'].value_counts().to_dict()
            }
            
        except Exception as e:
            return {'error': f'Status trend calculation failed: {e}'}
    
    def _calculate_severity_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate severity distribution trends over time.
        
        Args:
            df: DataFrame with ticket data.
            
        Returns:
            Dictionary containing severity trend data.
        """
        if 'severity' not in df.columns or 'created_date' not in df.columns:
            return {'error': 'Missing required columns for severity trends'}
        
        try:
            df_copy = df.copy()
            df_copy['month'] = df_copy['created_date'].dt.to_period('M')
            
            # Calculate severity distribution by month
            severity_by_month = df_copy.groupby(['month', 'severity']).size().unstack(fill_value=0)
            
            return {
                'monthly_severity_distribution': {
                    str(month): row.to_dict() 
                    for month, row in severity_by_month.iterrows()
                },
                'overall_severity_distribution': df['severity'].value_counts().to_dict()
            }
            
        except Exception as e:
            return {'error': f'Severity trend calculation failed: {e}'}
    
    def _generate_summary_insights(self, metrics: Dict[str, Any], tickets: List[Ticket]) -> Dict[str, Any]:
        """Generate high-level summary insights from metrics and tickets.
        
        Args:
            metrics: Calculated metrics dictionary.
            tickets: Original ticket data.
            
        Returns:
            Dictionary containing summary insights and recommendations.
        """
        summary = {
            'total_tickets_analyzed': len(tickets),
            'analysis_timestamp': datetime.now().isoformat(),
            'key_insights': [],
            'recommendations': [],
            'data_quality': self._assess_data_quality(tickets)
        }
        
        try:
            # Extract key insights from metrics
            insights = self._extract_key_insights(metrics, tickets)
            summary['key_insights'] = insights
            
            # Generate recommendations based on analysis
            recommendations = self._generate_recommendations(metrics, tickets)
            summary['recommendations'] = recommendations
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            summary['error'] = str(e)
        
        return summary
    
    def _extract_key_insights(self, metrics: Dict[str, Any], tickets: List[Ticket]) -> List[str]:
        """Extract key insights from calculated metrics.
        
        Args:
            metrics: Calculated metrics.
            tickets: Ticket data.
            
        Returns:
            List of insight strings.
        """
        insights = []
        
        # Analyze resolution time insights
        for key, value in metrics.items():
            if 'avg_resolution_time' in key and isinstance(value, (int, float)):
                if value > 48:  # More than 48 hours
                    insights.append(f"Average resolution time is high at {value:.1f} hours")
                elif value < 4:  # Less than 4 hours
                    insights.append(f"Excellent average resolution time of {value:.1f} hours")
        
        # Analyze volume insights
        resolved_count = sum(1 for ticket in tickets if ticket.is_resolved())
        if tickets:
            resolution_rate = (resolved_count / len(tickets)) * 100
            if resolution_rate > 90:
                insights.append(f"High resolution rate of {resolution_rate:.1f}%")
            elif resolution_rate < 50:
                insights.append(f"Low resolution rate of {resolution_rate:.1f}% needs attention")
        
        return insights
    
    def _generate_recommendations(self, metrics: Dict[str, Any], tickets: List[Ticket]) -> List[str]:
        """Generate actionable recommendations based on analysis.
        
        Args:
            metrics: Calculated metrics.
            tickets: Ticket data.
            
        Returns:
            List of recommendation strings.
        """
        recommendations = []
        
        # Resolution time recommendations
        for key, value in metrics.items():
            if 'avg_resolution_time' in key and isinstance(value, (int, float)):
                if value > 72:  # More than 3 days
                    recommendations.append("Consider reviewing resolution processes to reduce average resolution time")
        
        # Volume recommendations
        if len(tickets) > 1000:
            recommendations.append("High ticket volume detected - consider workload distribution analysis")
        
        return recommendations
    
    def _assess_data_quality(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Assess the quality of ticket data for analysis.
        
        Args:
            tickets: List of tickets to assess.
            
        Returns:
            Dictionary containing data quality metrics.
        """
        if not tickets:
            return {'quality_score': 0, 'issues': ['No data available']}
        
        quality_metrics = {
            'total_tickets': len(tickets),
            'complete_records': 0,
            'missing_fields': {},
            'quality_score': 0,
            'issues': []
        }
        
        # Check for missing critical fields
        for ticket in tickets:
            complete = True
            
            if not ticket.id:
                quality_metrics['missing_fields']['id'] = quality_metrics['missing_fields'].get('id', 0) + 1
                complete = False
            
            if not ticket.created_date:
                quality_metrics['missing_fields']['created_date'] = quality_metrics['missing_fields'].get('created_date', 0) + 1
                complete = False
            
            if not ticket.status:
                quality_metrics['missing_fields']['status'] = quality_metrics['missing_fields'].get('status', 0) + 1
                complete = False
            
            if complete:
                quality_metrics['complete_records'] += 1
        
        # Calculate quality score
        if tickets:
            quality_metrics['quality_score'] = (quality_metrics['complete_records'] / len(tickets)) * 100
        
        # Generate quality issues
        if quality_metrics['quality_score'] < 90:
            quality_metrics['issues'].append(f"Data completeness is {quality_metrics['quality_score']:.1f}%")
        
        return quality_metrics
    
    def _create_empty_result(self, original_tickets: List[Ticket]) -> AnalysisResult:
        """Create an empty analysis result for cases with no valid data.
        
        Args:
            original_tickets: Original ticket list (may be empty or invalid).
            
        Returns:
            AnalysisResult with empty/default values.
        """
        return AnalysisResult(
            metrics={'message': 'No valid tickets for analysis'},
            trends={'message': 'No data for trend analysis'},
            summary={
                'total_tickets_analyzed': 0,
                'original_ticket_count': len(original_tickets),
                'analysis_timestamp': datetime.now().isoformat(),
                'key_insights': ['No data available for analysis'],
                'recommendations': ['Ensure ticket data is available and properly formatted']
            },
            generated_at=datetime.now(),
            ticket_count=0,
            original_count=len(original_tickets),
            date_range=None
        )
    
    def _get_analysis_date_range(self, tickets: List[Ticket]) -> Optional[Dict[str, str]]:
        """Get the date range covered by the analyzed tickets.
        
        Args:
            tickets: List of analyzed tickets.
            
        Returns:
            Dictionary with start and end dates, or None if no valid dates.
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
            'start': min(valid_dates).isoformat(),
            'end': max(valid_dates).isoformat()
        }


class TicketDataProcessor:
    """Processor for cleaning and validating ticket data before analysis."""
    
    def process_tickets(self, tickets: List[Ticket]) -> List[Ticket]:
        """Process and validate tickets for analysis.
        
        Args:
            tickets: Raw tickets to process.
            
        Returns:
            List of validated and cleaned tickets.
        """
        if not tickets:
            return []
        
        processed = []
        
        for ticket in tickets:
            if self._is_valid_ticket(ticket):
                cleaned_ticket = self._clean_ticket_data(ticket)
                if cleaned_ticket:
                    processed.append(cleaned_ticket)
        
        logger.debug(f"Processed {len(processed)} valid tickets from {len(tickets)} input")
        return processed
    
    def _is_valid_ticket(self, ticket: Ticket) -> bool:
        """Check if ticket has minimum required data for analysis.
        
        Args:
            ticket: Ticket to validate.
            
        Returns:
            True if ticket is valid for analysis.
        """
        if not ticket or not ticket.id:
            return False
        
        # Must have creation date and status
        return (
            ticket.created_date is not None and
            ticket.status is not None
        )
    
    def _clean_ticket_data(self, ticket: Ticket) -> Optional[Ticket]:
        """Clean and normalize ticket data.
        
        Args:
            ticket: Ticket to clean.
            
        Returns:
            Cleaned ticket or None if cleaning fails.
        """
        try:
            # For now, return the ticket as-is
            # Future enhancements could include data normalization,
            # field validation, and data type conversions
            return ticket
        except Exception as e:
            logger.warning(f"Failed to clean ticket {ticket.id}: {e}")
            return None


class AnalysisPerformanceMonitor:
    """Monitor and track analysis performance metrics."""
    
    def __init__(self) -> None:
        """Initialize performance monitor."""
        self._analysis_history: List[Dict[str, Any]] = []
    
    def record_analysis(self, ticket_count: int, duration: timedelta, calculators_used: int) -> None:
        """Record analysis performance metrics.
        
        Args:
            ticket_count: Number of tickets analyzed.
            duration: Time taken for analysis.
            calculators_used: Number of calculators used.
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'ticket_count': ticket_count,
            'duration_seconds': duration.total_seconds(),
            'calculators_used': calculators_used,
            'tickets_per_second': ticket_count / duration.total_seconds() if duration.total_seconds() > 0 else 0
        }
        
        self._analysis_history.append(record)
        
        # Keep only last 100 records
        if len(self._analysis_history) > 100:
            self._analysis_history = self._analysis_history[-100:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics.
        
        Returns:
            Dictionary containing performance metrics.
        """
        if not self._analysis_history:
            return {'message': 'No performance data available'}
        
        durations = [record['duration_seconds'] for record in self._analysis_history]
        throughputs = [record['tickets_per_second'] for record in self._analysis_history]
        
        return {
            'total_analyses': len(self._analysis_history),
            'avg_duration_seconds': sum(durations) / len(durations),
            'avg_throughput_tickets_per_second': sum(throughputs) / len(throughputs),
            'last_analysis': self._analysis_history[-1] if self._analysis_history else None
        }
"""Trend analysis and time-series processing for ticket data.

This module implements comprehensive trend analysis capabilities including
time-series processing, pattern recognition, anomaly detection, and
statistical forecasting for ticket metrics over configurable time periods.

The TrendAnalyzer class provides methods for analyzing various temporal
patterns in ticket data, supporting weekly, monthly, and quarterly
trend calculations with configurable date ranges.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta, date
from collections import defaultdict, Counter
import statistics
import logging

import pandas as pd

from ..models.ticket import Ticket
from ..models.exceptions import AnalysisError
from .strategies import TrendAnalysisStrategy

logger = logging.getLogger(__name__)


class TrendAnalyzer(TrendAnalysisStrategy):
    """Comprehensive trend analyzer for ticket data time-series analysis.
    
    This class implements advanced trend analysis capabilities including:
    - Time-series analysis with configurable periods
    - Pattern recognition and seasonal analysis
    - Anomaly detection using statistical methods
    - Forecasting and prediction capabilities
    - Multi-dimensional trend analysis (volume, resolution time, etc.)
    
    The analyzer supports various time granularities from daily to quarterly
    analysis and provides both statistical and visual trend indicators.
    """
    
    def __init__(self, default_period: timedelta = timedelta(days=30)) -> None:
        """Initialize trend analyzer with default analysis period.
        
        Args:
            default_period: Default time period for trend analysis.
        """
        self._default_period = default_period
        self._anomaly_threshold = 2.0  # Standard deviations for anomaly detection
    
    def analyze_trends(self, tickets: List[Ticket], 
                      time_period: timedelta = None) -> Dict[str, Any]:
        """Analyze trends in ticket data over specified time period.
        
        Args:
            tickets: List of tickets to analyze.
            time_period: Time period for analysis (uses default if None).
            
        Returns:
            Dictionary containing comprehensive trend analysis results.
            
        Raises:
            AnalysisError: If trend analysis fails.
        """
        if not tickets:
            return {'message': 'No tickets available for trend analysis'}
        
        period = time_period or self._default_period
        
        try:
            # Filter tickets to the specified time period
            filtered_tickets = self._filter_tickets_by_period(tickets, period)
            
            if not filtered_tickets:
                return {'message': f'No tickets found in the last {period.days} days'}
            
            # Create time-series DataFrame for efficient processing
            df = self._create_time_series_dataframe(filtered_tickets)
            
            # Perform various trend analyses
            volume_trends = self._analyze_volume_trends(df, filtered_tickets)
            resolution_trends = self._analyze_resolution_time_trends(df, filtered_tickets)
            status_trends = self._analyze_status_trends(df, filtered_tickets)
            seasonal_patterns = self._analyze_seasonal_patterns(df, filtered_tickets)
            
            # Compile comprehensive results
            result = {
                'analysis_period': {
                    'days': period.days,
                    'start_date': (datetime.now() - period).isoformat(),
                    'end_date': datetime.now().isoformat()
                },
                'tickets_analyzed': len(filtered_tickets),
                'volume_trends': volume_trends,
                'resolution_trends': resolution_trends,
                'status_trends': status_trends,
                'seasonal_patterns': seasonal_patterns,
                'summary': self._generate_trend_summary(volume_trends, resolution_trends, status_trends)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            raise AnalysisError(f"Trend analysis failed: {e}") from e  
  
    def detect_patterns(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Detect patterns in ticket data using statistical analysis.
        
        Args:
            tickets: List of tickets to analyze for patterns.
            
        Returns:
            Dictionary containing detected patterns and anomalies.
        """
        if not tickets:
            return {'message': 'No tickets available for pattern detection'}
        
        try:
            # Create DataFrame for pattern analysis
            df = self._create_time_series_dataframe(tickets)
            
            # Detect various patterns
            cyclical_patterns = self._detect_cyclical_patterns(df, tickets)
            anomalies = self._detect_anomalies(df, tickets)
            growth_patterns = self._detect_growth_patterns(df, tickets)
            correlation_patterns = self._detect_correlation_patterns(df, tickets)
            
            return {
                'cyclical_patterns': cyclical_patterns,
                'anomalies': anomalies,
                'growth_patterns': growth_patterns,
                'correlation_patterns': correlation_patterns,
                'pattern_summary': self._summarize_patterns(cyclical_patterns, anomalies, growth_patterns)
            }
            
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            raise AnalysisError(f"Pattern detection failed: {e}") from e
    
    def get_trend_names(self) -> List[str]:
        """Get list of trend analysis types this strategy provides.
        
        Returns:
            List of trend analysis names.
        """
        return [
            'volume_trends',
            'resolution_trends', 
            'status_trends',
            'seasonal_patterns',
            'cyclical_patterns',
            'anomalies',
            'growth_patterns',
            'correlation_patterns'
        ]    
    d
ef _filter_tickets_by_period(self, tickets: List[Ticket], period: timedelta) -> List[Ticket]:
        """Filter tickets to those created within the specified time period.
        
        Args:
            tickets: List of tickets to filter.
            period: Time period to filter by.
            
        Returns:
            List of tickets within the time period.
        """
        cutoff_date = datetime.now() - period
        
        filtered = []
        for ticket in tickets:
            if (ticket.created_date and 
                ticket.created_date >= cutoff_date):
                filtered.append(ticket)
        
        return filtered
    
    def _create_time_series_dataframe(self, tickets: List[Ticket]) -> pd.DataFrame:
        """Create pandas DataFrame optimized for time-series analysis.
        
        Args:
            tickets: List of tickets to convert.
            
        Returns:
            DataFrame with time-series optimized structure.
        """
        if not tickets:
            return pd.DataFrame()
        
        # Convert tickets to time-series format
        data = []
        for ticket in tickets:
            if ticket.created_date:
                row = {
                    'date': ticket.created_date.date(),
                    'datetime': ticket.created_date,
                    'ticket_id': ticket.id,
                    'status': str(ticket.status),
                    'severity': str(ticket.severity),
                    'is_resolved': ticket.is_resolved(),
                    'resolution_hours': (
                        ticket.resolution_time().total_seconds() / 3600 
                        if ticket.resolution_time() else None
                    ),
                    'age_hours': (
                        ticket.age().total_seconds() / 3600 
                        if ticket.age() else None
                    ),
                    'assignee': ticket.assignee or 'Unassigned',
                    'resolver_group': ticket.resolver_group or 'Unassigned'
                }
                data.append(row)
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Optimize for time-series analysis
        df['date'] = pd.to_datetime(df['date'])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime')
        
        return df    

    def _analyze_volume_trends(self, df: pd.DataFrame, tickets: List[Ticket]) -> Dict[str, Any]:
        """Analyze volume trends over time with multiple granularities.
        
        Args:
            df: Time-series DataFrame.
            tickets: Original ticket list.
            
        Returns:
            Dictionary containing volume trend analysis.
        """
        if df.empty:
            return {'message': 'No data for volume trend analysis'}
        
        try:
            # Daily volume trends
            daily_volume = df.groupby('date').size()
            
            # Weekly volume trends
            df_copy = df.copy()
            df_copy['week'] = df_copy['date'].dt.to_period('W')
            weekly_volume = df_copy.groupby('week').size()
            
            # Monthly volume trends
            df_copy['month'] = df_copy['date'].dt.to_period('M')
            monthly_volume = df_copy.groupby('month').size()
            
            # Calculate trend statistics
            daily_values = daily_volume.values
            trend_direction = self._calculate_trend_direction(daily_values)
            volatility = self._calculate_volatility(daily_values)
            
            # Identify peak and low periods
            peak_analysis = self._analyze_peaks_and_lows(daily_volume)
            
            return {
                'daily_volume': {
                    'data': {str(date): int(count) for date, count in daily_volume.items()},
                    'trend_direction': trend_direction,
                    'volatility': volatility,
                    'average': float(daily_values.mean()) if len(daily_values) > 0 else 0,
                    'peak_analysis': peak_analysis
                },
                'weekly_volume': {
                    'data': {str(week): int(count) for week, count in weekly_volume.items()},
                    'average': float(weekly_volume.mean()) if len(weekly_volume) > 0 else 0
                },
                'monthly_volume': {
                    'data': {str(month): int(count) for month, count in monthly_volume.items()},
                    'average': float(monthly_volume.mean()) if len(monthly_volume) > 0 else 0
                },
                'total_tickets': len(tickets),
                'analysis_period_days': (df['date'].max() - df['date'].min()).days + 1
            }
            
        except Exception as e:
            logger.error(f"Volume trend analysis failed: {e}")
            return {'error': f'Volume trend analysis failed: {e}'}
    
    def _analyze_resolution_time_trends(self, df: pd.DataFrame, tickets: List[Ticket]) -> Dict[str, Any]:
        """Analyze resolution time trends over time.
        
        Args:
            df: Time-series DataFrame.
            tickets: Original ticket list.
            
        Returns:
            Dictionary containing resolution time trend analysis.
        """
        if df.empty:
            return {'message': 'No data for resolution time trend analysis'}
        
        # Filter to resolved tickets only
        resolved_df = df[df['is_resolved'] == True].copy()
        
        if resolved_df.empty:
            return {'message': 'No resolved tickets for trend analysis'}
        
        try:
            # Weekly resolution time trends
            resolved_df['week'] = resolved_df['date'].dt.to_period('W')
            weekly_avg_resolution = resolved_df.groupby('week')['resolution_hours'].mean()
            
            # Monthly resolution time trends
            resolved_df['month'] = resolved_df['date'].dt.to_period('M')
            monthly_avg_resolution = resolved_df.groupby('month')['resolution_hours'].mean()
            
            # Calculate trend statistics
            resolution_values = weekly_avg_resolution.values
            trend_direction = self._calculate_trend_direction(resolution_values)
            
            return {
                'weekly_avg_resolution': {
                    'data': {str(week): float(avg) for week, avg in weekly_avg_resolution.items()},
                    'trend_direction': trend_direction,
                    'overall_average': float(resolved_df['resolution_hours'].mean())
                },
                'monthly_avg_resolution': {
                    'data': {str(month): float(avg) for month, avg in monthly_avg_resolution.items()},
                    'overall_average': float(resolved_df['resolution_hours'].mean())
                },
                'resolved_ticket_count': len(resolved_df),
                'resolution_rate': (len(resolved_df) / len(df)) * 100 if len(df) > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Resolution time trend analysis failed: {e}")
            return {'error': f'Resolution time trend analysis failed: {e}'}   
 
    def _analyze_status_trends(self, df: pd.DataFrame, tickets: List[Ticket]) -> Dict[str, Any]:
        """Analyze status distribution trends over time.
        
        Args:
            df: Time-series DataFrame.
            tickets: Original ticket list.
            
        Returns:
            Dictionary containing status trend analysis.
        """
        if df.empty:
            return {'message': 'No data for status trend analysis'}
        
        try:
            # Monthly status distribution trends
            df_copy = df.copy()
            df_copy['month'] = df_copy['date'].dt.to_period('M')
            
            monthly_status = df_copy.groupby(['month', 'status']).size().unstack(fill_value=0)
            
            # Calculate status change rates
            status_changes = self._calculate_status_change_rates(monthly_status)
            
            return {
                'monthly_status_distribution': {
                    str(month): {status: int(count) for status, count in row.items()}
                    for month, row in monthly_status.iterrows()
                },
                'status_change_rates': status_changes,
                'overall_status_distribution': df['status'].value_counts().to_dict()
            }
            
        except Exception as e:
            logger.error(f"Status trend analysis failed: {e}")
            return {'error': f'Status trend analysis failed: {e}'}
    
    def _analyze_seasonal_patterns(self, df: pd.DataFrame, tickets: List[Ticket]) -> Dict[str, Any]:
        """Analyze seasonal patterns in ticket data.
        
        Args:
            df: Time-series DataFrame.
            tickets: Original ticket list.
            
        Returns:
            Dictionary containing seasonal pattern analysis.
        """
        if df.empty:
            return {'message': 'No data for seasonal pattern analysis'}
        
        try:
            # Day of week patterns
            df_copy = df.copy()
            df_copy['day_of_week'] = df_copy['date'].dt.day_name()
            dow_volume = df_copy.groupby('day_of_week').size()
            
            # Hour of day patterns (if datetime available)
            if 'datetime' in df_copy.columns:
                df_copy['hour'] = df_copy['datetime'].dt.hour
                hourly_volume = df_copy.groupby('hour').size()
            else:
                hourly_volume = pd.Series(dtype=int)
            
            # Monthly patterns
            df_copy['month_name'] = df_copy['date'].dt.month_name()
            monthly_volume = df_copy.groupby('month_name').size()
            
            # Quarterly patterns
            df_copy['quarter'] = df_copy['date'].dt.quarter
            quarterly_volume = df_copy.groupby('quarter').size()
            
            return {
                'day_of_week_patterns': {
                    'data': dow_volume.to_dict(),
                    'peak_day': dow_volume.idxmax() if not dow_volume.empty else None,
                    'low_day': dow_volume.idxmin() if not dow_volume.empty else None
                },
                'hourly_patterns': {
                    'data': hourly_volume.to_dict(),
                    'peak_hour': int(hourly_volume.idxmax()) if not hourly_volume.empty else None,
                    'low_hour': int(hourly_volume.idxmin()) if not hourly_volume.empty else None
                } if not hourly_volume.empty else {'message': 'No hourly data available'},
                'monthly_patterns': {
                    'data': monthly_volume.to_dict(),
                    'peak_month': monthly_volume.idxmax() if not monthly_volume.empty else None,
                    'low_month': monthly_volume.idxmin() if not monthly_volume.empty else None
                },
                'quarterly_patterns': {
                    'data': {f'Q{quarter}': int(count) for quarter, count in quarterly_volume.items()},
                    'peak_quarter': f'Q{quarterly_volume.idxmax()}' if not quarterly_volume.empty else None,
                    'low_quarter': f'Q{quarterly_volume.idxmin()}' if not quarterly_volume.empty else None
                }
            }
            
        except Exception as e:
            logger.error(f"Seasonal pattern analysis failed: {e}")
            return {'error': f'Seasonal pattern analysis failed: {e}'} 
   
    def _detect_cyclical_patterns(self, df: pd.DataFrame, tickets: List[Ticket]) -> Dict[str, Any]:
        """Detect cyclical patterns in ticket data.
        
        Args:
            df: Time-series DataFrame.
            tickets: Original ticket list.
            
        Returns:
            Dictionary containing cyclical pattern analysis.
        """
        if df.empty or len(df) < 14:  # Need at least 2 weeks of data
            return {'message': 'Insufficient data for cyclical pattern detection'}
        
        try:
            # Daily volume for cycle detection
            daily_volume = df.groupby('date').size()
            
            # Simple cycle detection using autocorrelation-like approach
            cycles = self._detect_simple_cycles(daily_volume.values)
            
            # Weekly cycle detection
            df_copy = df.copy()
            df_copy['day_of_week'] = df_copy['date'].dt.dayofweek
            weekly_pattern = df_copy.groupby('day_of_week').size()
            weekly_consistency = self._calculate_pattern_consistency(weekly_pattern.values)
            
            return {
                'detected_cycles': cycles,
                'weekly_pattern_consistency': weekly_consistency,
                'weekly_pattern_strength': 'strong' if weekly_consistency > 0.7 else 'moderate' if weekly_consistency > 0.4 else 'weak'
            }
            
        except Exception as e:
            logger.error(f"Cyclical pattern detection failed: {e}")
            return {'error': f'Cyclical pattern detection failed: {e}'}
    
    def _detect_anomalies(self, df: pd.DataFrame, tickets: List[Ticket]) -> Dict[str, Any]:
        """Detect anomalies in ticket data using statistical methods.
        
        Args:
            df: Time-series DataFrame.
            tickets: Original ticket list.
            
        Returns:
            Dictionary containing anomaly detection results.
        """
        if df.empty:
            return {'message': 'No data for anomaly detection'}
        
        try:
            # Daily volume anomalies
            daily_volume = df.groupby('date').size()
            volume_anomalies = self._detect_statistical_anomalies(
                daily_volume.values, 
                daily_volume.index.tolist()
            )
            
            # Resolution time anomalies (for resolved tickets)
            resolved_df = df[df['is_resolved'] == True]
            if not resolved_df.empty:
                resolution_anomalies = self._detect_statistical_anomalies(
                    resolved_df['resolution_hours'].dropna().values,
                    resolved_df[resolved_df['resolution_hours'].notna()]['ticket_id'].tolist()
                )
            else:
                resolution_anomalies = []
            
            return {
                'volume_anomalies': volume_anomalies,
                'resolution_time_anomalies': resolution_anomalies,
                'total_anomalies': len(volume_anomalies) + len(resolution_anomalies)
            }
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return {'error': f'Anomaly detection failed: {e}'}
    
    def _detect_growth_patterns(self, df: pd.DataFrame, tickets: List[Ticket]) -> Dict[str, Any]:
        """Detect growth patterns and trends in ticket data.
        
        Args:
            df: Time-series DataFrame.
            tickets: Original ticket list.
            
        Returns:
            Dictionary containing growth pattern analysis.
        """
        if df.empty:
            return {'message': 'No data for growth pattern detection'}
        
        try:
            # Weekly growth analysis
            df_copy = df.copy()
            df_copy['week'] = df_copy['date'].dt.to_period('W')
            weekly_volume = df_copy.groupby('week').size()
            
            if len(weekly_volume) < 2:
                return {'message': 'Insufficient data for growth analysis'}
            
            # Calculate week-over-week growth rates
            growth_rates = []
            for i in range(1, len(weekly_volume)):
                prev_volume = weekly_volume.iloc[i-1]
                curr_volume = weekly_volume.iloc[i]
                
                if prev_volume > 0:
                    growth_rate = ((curr_volume - prev_volume) / prev_volume) * 100
                    growth_rates.append({
                        'week': str(weekly_volume.index[i]),
                        'growth_rate': growth_rate,
                        'volume': int(curr_volume),
                        'previous_volume': int(prev_volume)
                    })
            
            # Calculate overall trend
            avg_growth_rate = statistics.mean([gr['growth_rate'] for gr in growth_rates]) if growth_rates else 0
            
            # Determine trend classification
            if avg_growth_rate > 5:
                trend_classification = 'strong_growth'
            elif avg_growth_rate > 0:
                trend_classification = 'moderate_growth'
            elif avg_growth_rate > -5:
                trend_classification = 'stable'
            else:
                trend_classification = 'declining'
            
            return {
                'weekly_growth_rates': growth_rates,
                'average_growth_rate': avg_growth_rate,
                'trend_classification': trend_classification,
                'total_weeks_analyzed': len(weekly_volume)
            }
            
        except Exception as e:
            logger.error(f"Growth pattern detection failed: {e}")
            return {'error': f'Growth pattern detection failed: {e}'}  
  
    def _detect_correlation_patterns(self, df: pd.DataFrame, tickets: List[Ticket]) -> Dict[str, Any]:
        """Detect correlation patterns between different metrics.
        
        Args:
            df: Time-series DataFrame.
            tickets: Original ticket list.
            
        Returns:
            Dictionary containing correlation analysis.
        """
        if df.empty:
            return {'message': 'No data for correlation analysis'}
        
        try:
            # Prepare data for correlation analysis
            daily_metrics = df.groupby('date').agg({
                'ticket_id': 'count',  # Daily volume
                'resolution_hours': 'mean',  # Average resolution time
                'is_resolved': 'sum'  # Number resolved per day
            }).rename(columns={
                'ticket_id': 'daily_volume',
                'resolution_hours': 'avg_resolution_hours',
                'is_resolved': 'daily_resolved'
            })
            
            # Calculate correlations
            correlations = {}
            
            if len(daily_metrics) > 3:  # Need at least 4 data points
                # Volume vs Resolution Time correlation
                volume_resolution_corr = self._calculate_correlation(
                    daily_metrics['daily_volume'].values,
                    daily_metrics['avg_resolution_hours'].dropna().values
                )
                
                if volume_resolution_corr is not None:
                    correlations['volume_vs_resolution_time'] = {
                        'correlation': volume_resolution_corr,
                        'strength': self._interpret_correlation_strength(volume_resolution_corr),
                        'interpretation': self._interpret_volume_resolution_correlation(volume_resolution_corr)
                    }
            
            return {
                'correlations': correlations,
                'data_points_analyzed': len(daily_metrics),
                'analysis_note': 'Correlation analysis requires sufficient data points for meaningful results'
            }
            
        except Exception as e:
            logger.error(f"Correlation pattern detection failed: {e}")
            return {'error': f'Correlation pattern detection failed: {e}'}
    
    # Helper methods for trend analysis
    
    def _calculate_trend_direction(self, values: List[float]) -> str:
        """Calculate overall trend direction from time series values.
        
        Args:
            values: List of numeric values in time order.
            
        Returns:
            String indicating trend direction.
        """
        if len(values) < 2:
            return 'insufficient_data'
        
        # Simple linear trend calculation
        n = len(values)
        x = list(range(n))
        
        # Calculate slope using least squares
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 'stable'
        
        slope = numerator / denominator
        
        if slope > 0.1:
            return 'increasing'
        elif slope < -0.1:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (coefficient of variation) for time series.
        
        Args:
            values: List of numeric values.
            
        Returns:
            Volatility measure (coefficient of variation).
        """
        if len(values) < 2:
            return 0.0
        
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 0.0
        
        std_dev = statistics.stdev(values)
        return std_dev / mean_val
    
    def _analyze_peaks_and_lows(self, series: pd.Series) -> Dict[str, Any]:
        """Analyze peaks and lows in a time series.
        
        Args:
            series: Pandas Series with time-indexed data.
            
        Returns:
            Dictionary with peak and low analysis.
        """
        if series.empty:
            return {}
        
        values = series.values
        mean_val = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        
        # Define thresholds for peaks and lows
        peak_threshold = mean_val + std_dev
        low_threshold = mean_val - std_dev
        
        peaks = []
        lows = []
        
        for date, value in series.items():
            if value > peak_threshold:
                peaks.append({'date': str(date), 'value': int(value)})
            elif value < low_threshold:
                lows.append({'date': str(date), 'value': int(value)})
        
        return {
            'peaks': peaks[:5],  # Limit to top 5
            'lows': lows[:5],   # Limit to top 5
            'peak_count': len(peaks),
            'low_count': len(lows),
            'mean_value': mean_val,
            'std_deviation': std_dev
        } 
   
    def _calculate_status_change_rates(self, monthly_status: pd.DataFrame) -> Dict[str, Any]:
        """Calculate rates of change for different status categories.
        
        Args:
            monthly_status: DataFrame with monthly status distributions.
            
        Returns:
            Dictionary with status change rate analysis.
        """
        if monthly_status.empty or len(monthly_status) < 2:
            return {'message': 'Insufficient data for status change rate calculation'}
        
        change_rates = {}
        
        for status in monthly_status.columns:
            values = monthly_status[status].values
            if len(values) >= 2:
                # Calculate month-over-month change rate
                changes = []
                for i in range(1, len(values)):
                    if values[i-1] > 0:
                        change_rate = ((values[i] - values[i-1]) / values[i-1]) * 100
                        changes.append(change_rate)
                
                if changes:
                    change_rates[status] = {
                        'avg_change_rate': statistics.mean(changes),
                        'trend': 'increasing' if statistics.mean(changes) > 0 else 'decreasing' if statistics.mean(changes) < 0 else 'stable'
                    }
        
        return change_rates
    
    def _detect_simple_cycles(self, values: List[float]) -> List[Dict[str, Any]]:
        """Detect simple cyclical patterns in time series data.
        
        Args:
            values: List of numeric values in time order.
            
        Returns:
            List of detected cycles with their characteristics.
        """
        if len(values) < 7:  # Need at least a week of data
            return []
        
        cycles = []
        
        # Check for weekly cycles (7-day pattern)
        if len(values) >= 14:  # Need at least 2 weeks
            weekly_correlation = self._calculate_weekly_autocorrelation(values)
            if weekly_correlation > 0.5:  # Threshold for significant correlation
                cycles.append({
                    'type': 'weekly',
                    'period_days': 7,
                    'strength': weekly_correlation,
                    'confidence': 'high' if weekly_correlation > 0.7 else 'moderate'
                })
        
        return cycles
    
    def _calculate_weekly_autocorrelation(self, values: List[float]) -> float:
        """Calculate autocorrelation at 7-day lag for weekly pattern detection.
        
        Args:
            values: List of numeric values.
            
        Returns:
            Autocorrelation coefficient.
        """
        if len(values) < 14:
            return 0.0
        
        # Simple correlation between values and values shifted by 7 days
        lag = 7
        if len(values) <= lag:
            return 0.0
        
        x = values[:-lag]
        y = values[lag:]
        
        return self._calculate_correlation(x, y) or 0.0
    
    def _calculate_pattern_consistency(self, pattern_values: List[float]) -> float:
        """Calculate consistency score for a pattern.
        
        Args:
            pattern_values: Values representing a pattern.
            
        Returns:
            Consistency score between 0 and 1.
        """
        if len(pattern_values) < 2:
            return 0.0
        
        # Calculate coefficient of variation (lower = more consistent)
        mean_val = statistics.mean(pattern_values)
        if mean_val == 0:
            return 0.0
        
        std_dev = statistics.stdev(pattern_values)
        cv = std_dev / mean_val
        
        # Convert to consistency score (1 - normalized CV)
        # Normalize CV to 0-1 range (assuming CV > 2 is very inconsistent)
        normalized_cv = min(cv / 2.0, 1.0)
        return 1.0 - normalized_cv
    
    def _detect_statistical_anomalies(self, values: List[float], identifiers: List[str]) -> List[Dict[str, Any]]:
        """Detect statistical anomalies using z-score method.
        
        Args:
            values: Numeric values to analyze.
            identifiers: Corresponding identifiers for the values.
            
        Returns:
            List of detected anomalies.
        """
        if len(values) < 3:  # Need at least 3 points for meaningful statistics
            return []
        
        mean_val = statistics.mean(values)
        std_dev = statistics.stdev(values)
        
        if std_dev == 0:  # No variation
            return []
        
        anomalies = []
        for i, value in enumerate(values):
            z_score = abs((value - mean_val) / std_dev)
            
            if z_score > self._anomaly_threshold:
                anomalies.append({
                    'identifier': identifiers[i] if i < len(identifiers) else f'index_{i}',
                    'value': value,
                    'z_score': z_score,
                    'type': 'high' if value > mean_val else 'low',
                    'severity': 'extreme' if z_score > 3 else 'moderate'
                })
        
        return sorted(anomalies, key=lambda x: x['z_score'], reverse=True)[:10]  # Top 10 anomalies
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> Optional[float]:
        """Calculate Pearson correlation coefficient between two series.
        
        Args:
            x: First series of values.
            y: Second series of values.
            
        Returns:
            Correlation coefficient or None if calculation fails.
        """
        if len(x) != len(y) or len(x) < 2:
            return None
        
        try:
            # Remove any NaN pairs
            valid_pairs = [(xi, yi) for xi, yi in zip(x, y) if xi is not None and yi is not None]
            
            if len(valid_pairs) < 2:
                return None
            
            x_clean, y_clean = zip(*valid_pairs)
            
            n = len(x_clean)
            x_mean = statistics.mean(x_clean)
            y_mean = statistics.mean(y_clean)
            
            numerator = sum((x_clean[i] - x_mean) * (y_clean[i] - y_mean) for i in range(n))
            
            x_var = sum((x_clean[i] - x_mean) ** 2 for i in range(n))
            y_var = sum((y_clean[i] - y_mean) ** 2 for i in range(n))
            
            denominator = (x_var * y_var) ** 0.5
            
            if denominator == 0:
                return None
            
            return numerator / denominator
            
        except Exception:
            return None    

    def _interpret_correlation_strength(self, correlation: float) -> str:
        """Interpret correlation coefficient strength.
        
        Args:
            correlation: Correlation coefficient.
            
        Returns:
            String describing correlation strength.
        """
        abs_corr = abs(correlation)
        
        if abs_corr >= 0.8:
            return 'very_strong'
        elif abs_corr >= 0.6:
            return 'strong'
        elif abs_corr >= 0.4:
            return 'moderate'
        elif abs_corr >= 0.2:
            return 'weak'
        else:
            return 'very_weak'
    
    def _interpret_volume_resolution_correlation(self, correlation: float) -> str:
        """Interpret volume vs resolution time correlation.
        
        Args:
            correlation: Correlation coefficient.
            
        Returns:
            String interpretation of the correlation.
        """
        if correlation > 0.3:
            return 'Higher ticket volume tends to correlate with longer resolution times'
        elif correlation < -0.3:
            return 'Higher ticket volume tends to correlate with shorter resolution times'
        else:
            return 'No significant correlation between ticket volume and resolution times'
    
    def _generate_trend_summary(self, volume_trends: Dict[str, Any], 
                               resolution_trends: Dict[str, Any], 
                               status_trends: Dict[str, Any]) -> Dict[str, Any]:
        """Generate high-level summary of trend analysis.
        
        Args:
            volume_trends: Volume trend analysis results.
            resolution_trends: Resolution time trend analysis results.
            status_trends: Status trend analysis results.
            
        Returns:
            Dictionary with trend summary.
        """
        summary = {
            'key_findings': [],
            'recommendations': [],
            'overall_health': 'unknown'
        }
        
        try:
            # Analyze volume trends
            if 'daily_volume' in volume_trends:
                trend_direction = volume_trends['daily_volume'].get('trend_direction', 'unknown')
                if trend_direction == 'increasing':
                    summary['key_findings'].append('Ticket volume is increasing over time')
                    summary['recommendations'].append('Monitor capacity and consider workload distribution')
                elif trend_direction == 'decreasing':
                    summary['key_findings'].append('Ticket volume is decreasing over time')
            
            # Analyze resolution trends
            if 'weekly_avg_resolution' in resolution_trends:
                resolution_trend = resolution_trends['weekly_avg_resolution'].get('trend_direction', 'unknown')
                if resolution_trend == 'increasing':
                    summary['key_findings'].append('Resolution times are increasing')
                    summary['recommendations'].append('Review resolution processes for potential improvements')
                elif resolution_trend == 'decreasing':
                    summary['key_findings'].append('Resolution times are improving')
            
            # Determine overall health
            health_indicators = []
            
            if volume_trends.get('daily_volume', {}).get('trend_direction') == 'stable':
                health_indicators.append('stable_volume')
            
            if resolution_trends.get('weekly_avg_resolution', {}).get('trend_direction') in ['stable', 'decreasing']:
                health_indicators.append('good_resolution_trend')
            
            if len(health_indicators) >= 1:
                summary['overall_health'] = 'good'
            else:
                summary['overall_health'] = 'needs_attention'
            
        except Exception as e:
            logger.error(f"Trend summary generation failed: {e}")
            summary['error'] = str(e)
        
        return summary
    
    def _summarize_patterns(self, cyclical_patterns: Dict[str, Any], 
                           anomalies: Dict[str, Any], 
                           growth_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize detected patterns for high-level insights.
        
        Args:
            cyclical_patterns: Cyclical pattern analysis results.
            anomalies: Anomaly detection results.
            growth_patterns: Growth pattern analysis results.
            
        Returns:
            Dictionary with pattern summary.
        """
        summary = {
            'pattern_count': 0,
            'anomaly_count': 0,
            'key_patterns': [],
            'attention_areas': []
        }
        
        try:
            # Count detected patterns
            if 'detected_cycles' in cyclical_patterns:
                summary['pattern_count'] += len(cyclical_patterns['detected_cycles'])
            
            # Count anomalies
            if 'total_anomalies' in anomalies:
                summary['anomaly_count'] = anomalies['total_anomalies']
            
            # Identify key patterns
            if cyclical_patterns.get('weekly_pattern_strength') == 'strong':
                summary['key_patterns'].append('Strong weekly pattern detected')
            
            if growth_patterns.get('trend_classification') == 'strong_growth':
                summary['key_patterns'].append('Strong growth trend identified')
                summary['attention_areas'].append('Monitor capacity for growing ticket volume')
            
            # Identify attention areas
            if summary['anomaly_count'] > 5:
                summary['attention_areas'].append('High number of anomalies detected - investigate unusual patterns')
            
        except Exception as e:
            logger.error(f"Pattern summary generation failed: {e}")
            summary['error'] = str(e)
        
        return summary


class ForecastingEngine:
    """Simple forecasting engine for ticket metrics prediction.
    
    This class provides basic forecasting capabilities using simple
    statistical methods for predicting future ticket volumes and trends.
    """
    
    def __init__(self) -> None:
        """Initialize forecasting engine."""
        pass
    
    def forecast_volume(self, historical_data: List[float], periods: int = 7) -> Dict[str, Any]:
        """Forecast future ticket volume using simple trend analysis.
        
        Args:
            historical_data: Historical volume data points.
            periods: Number of future periods to forecast.
            
        Returns:
            Dictionary containing forecast results.
        """
        if len(historical_data) < 3:
            return {'message': 'Insufficient historical data for forecasting'}
        
        try:
            # Simple linear trend forecasting
            n = len(historical_data)
            x = list(range(n))
            
            # Calculate trend line
            x_mean = statistics.mean(x)
            y_mean = statistics.mean(historical_data)
            
            numerator = sum((x[i] - x_mean) * (historical_data[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                slope = 0
                intercept = y_mean
            else:
                slope = numerator / denominator
                intercept = y_mean - slope * x_mean
            
            # Generate forecasts
            forecasts = []
            for i in range(periods):
                forecast_x = n + i
                forecast_y = intercept + slope * forecast_x
                forecasts.append(max(0, forecast_y))  # Ensure non-negative
            
            return {
                'forecasts': forecasts,
                'trend_slope': slope,
                'confidence': 'low',  # Simple method has low confidence
                'method': 'linear_trend',
                'periods_forecasted': periods
            }
            
        except Exception as e:
            return {'error': f'Forecasting failed: {e}'}
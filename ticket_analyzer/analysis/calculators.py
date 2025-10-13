"""Specific metrics calculator implementations using Strategy pattern.

This module contains concrete implementations of metrics calculators that
inherit from the MetricsCalculator base class. Each calculator focuses on
a specific type of analysis and provides detailed metrics calculation.

The calculators implement the Strategy pattern, allowing the analysis engine
to use different calculation strategies based on requirements. All calculators
handle edge cases gracefully and provide comprehensive error handling.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import statistics
import logging

import pandas as pd

from ..models.ticket import Ticket, TicketStatus, TicketSeverity
from ..models.exceptions import AnalysisError
from .strategies import MetricsCalculator

logger = logging.getLogger(__name__)


class ResolutionTimeCalculator(MetricsCalculator):
    """Calculator for resolution time metrics and statistics.
    
    This calculator analyzes ticket resolution times, providing comprehensive
    statistics including averages, medians, percentiles, and breakdowns by
    various ticket attributes like severity and assignee.
    
    Handles edge cases such as:
    - Tickets without resolution dates
    - Invalid date ranges
    - Empty datasets
    - Outlier detection and handling
    """
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate resolution time metrics from ticket data.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing resolution time metrics including:
            - Basic statistics (mean, median, std dev)
            - Percentile analysis (P50, P75, P90, P95, P99)
            - Breakdown by severity level
            - Breakdown by assignee/team
            - Outlier analysis
            - Time period analysis
        """
        if not self.validate_input(tickets):
            return self._handle_empty_dataset()
        
        # Filter to only resolved tickets with valid resolution times
        resolved_tickets = self._get_resolved_tickets_with_times(tickets)
        
        if not resolved_tickets:
            return {
                **self._handle_empty_dataset(),
                'total_tickets': len(tickets),
                'resolved_tickets': 0,
                'resolution_rate': 0.0
            }
        
        # Calculate basic resolution time statistics
        resolution_times = [ticket.resolution_time() for ticket in resolved_tickets]
        resolution_hours = [rt.total_seconds() / 3600 for rt in resolution_times if rt]
        
        if not resolution_hours:
            return self._handle_empty_dataset()
        
        # Basic statistics
        basic_stats = self._calculate_basic_statistics(resolution_hours)
        
        # Percentile analysis
        percentiles = self._calculate_percentiles(resolution_hours)
        
        # Breakdown by severity
        severity_breakdown = self._calculate_severity_breakdown(resolved_tickets)
        
        # Breakdown by assignee
        assignee_breakdown = self._calculate_assignee_breakdown(resolved_tickets)
        
        # Time period analysis
        time_analysis = self._calculate_time_period_analysis(resolved_tickets)
        
        # Outlier analysis
        outlier_analysis = self._calculate_outlier_analysis(resolution_hours, resolved_tickets)
        
        # Compile results
        result = {
            **basic_stats,
            **percentiles,
            'by_severity': severity_breakdown,
            'by_assignee': assignee_breakdown,
            'time_analysis': time_analysis,
            'outlier_analysis': outlier_analysis,
            'total_tickets': len(tickets),
            'resolved_tickets': len(resolved_tickets),
            'resolution_rate': (len(resolved_tickets) / len(tickets)) * 100 if tickets else 0.0
        }
        
        return self._add_metadata(result, tickets)
    
    def get_metric_names(self) -> List[str]:
        """Get list of metric names this calculator provides."""
        return [
            'avg_resolution_time_hours',
            'median_resolution_time_hours',
            'std_dev_resolution_hours',
            'min_resolution_hours',
            'max_resolution_hours',
            'p50_resolution_hours',
            'p75_resolution_hours',
            'p90_resolution_hours',
            'p95_resolution_hours',
            'p99_resolution_hours',
            'by_severity',
            'by_assignee',
            'time_analysis',
            'outlier_analysis',
            'total_tickets',
            'resolved_tickets',
            'resolution_rate'
        ]
    
    def _get_resolved_tickets_with_times(self, tickets: List[Ticket]) -> List[Ticket]:
        """Get tickets that are resolved and have valid resolution times.
        
        Args:
            tickets: List of tickets to filter.
            
        Returns:
            List of resolved tickets with valid resolution times.
        """
        resolved = []
        for ticket in tickets:
            if (ticket.is_resolved() and 
                ticket.resolution_time() is not None and
                ticket.resolution_time().total_seconds() > 0):
                resolved.append(ticket)
        
        return resolved
    
    def _calculate_basic_statistics(self, resolution_hours: List[float]) -> Dict[str, float]:
        """Calculate basic statistical measures for resolution times.
        
        Args:
            resolution_hours: List of resolution times in hours.
            
        Returns:
            Dictionary with basic statistics.
        """
        if not resolution_hours:
            return {}
        
        return {
            'avg_resolution_time_hours': statistics.mean(resolution_hours),
            'median_resolution_time_hours': statistics.median(resolution_hours),
            'std_dev_resolution_hours': statistics.stdev(resolution_hours) if len(resolution_hours) > 1 else 0.0,
            'min_resolution_hours': min(resolution_hours),
            'max_resolution_hours': max(resolution_hours)
        }
    
    def _calculate_percentiles(self, resolution_hours: List[float]) -> Dict[str, float]:
        """Calculate percentile analysis for resolution times.
        
        Args:
            resolution_hours: List of resolution times in hours.
            
        Returns:
            Dictionary with percentile values.
        """
        if not resolution_hours:
            return {}
        
        sorted_times = sorted(resolution_hours)
        
        return {
            'p50_resolution_hours': statistics.median(sorted_times),
            'p75_resolution_hours': self._percentile(sorted_times, 75),
            'p90_resolution_hours': self._percentile(sorted_times, 90),
            'p95_resolution_hours': self._percentile(sorted_times, 95),
            'p99_resolution_hours': self._percentile(sorted_times, 99)
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate specific percentile value.
        
        Args:
            data: Sorted list of values.
            percentile: Percentile to calculate (0-100).
            
        Returns:
            Percentile value.
        """
        if not data:
            return 0.0
        
        k = (len(data) - 1) * (percentile / 100)
        f = int(k)
        c = k - f
        
        if f + 1 < len(data):
            return data[f] + c * (data[f + 1] - data[f])
        else:
            return data[f]
    
    def _calculate_severity_breakdown(self, resolved_tickets: List[Ticket]) -> Dict[str, Dict[str, float]]:
        """Calculate resolution time breakdown by severity level.
        
        Args:
            resolved_tickets: List of resolved tickets.
            
        Returns:
            Dictionary with severity breakdown statistics.
        """
        severity_groups = defaultdict(list)
        
        for ticket in resolved_tickets:
            severity = str(ticket.severity)
            resolution_hours = ticket.resolution_time().total_seconds() / 3600
            severity_groups[severity].append(resolution_hours)
        
        breakdown = {}
        for severity, times in severity_groups.items():
            if times:
                breakdown[severity] = {
                    'avg_hours': statistics.mean(times),
                    'median_hours': statistics.median(times),
                    'count': len(times),
                    'min_hours': min(times),
                    'max_hours': max(times)
                }
        
        return breakdown
    
    def _calculate_assignee_breakdown(self, resolved_tickets: List[Ticket]) -> Dict[str, Dict[str, float]]:
        """Calculate resolution time breakdown by assignee.
        
        Args:
            resolved_tickets: List of resolved tickets.
            
        Returns:
            Dictionary with assignee breakdown statistics.
        """
        assignee_groups = defaultdict(list)
        
        for ticket in resolved_tickets:
            assignee = ticket.assignee or 'Unassigned'
            resolution_hours = ticket.resolution_time().total_seconds() / 3600
            assignee_groups[assignee].append(resolution_hours)
        
        breakdown = {}
        for assignee, times in assignee_groups.items():
            if times:
                breakdown[assignee] = {
                    'avg_hours': statistics.mean(times),
                    'median_hours': statistics.median(times),
                    'count': len(times),
                    'min_hours': min(times),
                    'max_hours': max(times)
                }
        
        return breakdown
    
    def _calculate_time_period_analysis(self, resolved_tickets: List[Ticket]) -> Dict[str, Any]:
        """Analyze resolution times by time periods (day of week, hour of day).
        
        Args:
            resolved_tickets: List of resolved tickets.
            
        Returns:
            Dictionary with time period analysis.
        """
        if not resolved_tickets:
            return {}
        
        # Group by day of week
        day_groups = defaultdict(list)
        hour_groups = defaultdict(list)
        
        for ticket in resolved_tickets:
            if ticket.resolved_date:
                day_of_week = ticket.resolved_date.strftime('%A')
                hour_of_day = ticket.resolved_date.hour
                resolution_hours = ticket.resolution_time().total_seconds() / 3600
                
                day_groups[day_of_week].append(resolution_hours)
                hour_groups[hour_of_day].append(resolution_hours)
        
        # Calculate averages by day
        day_averages = {
            day: statistics.mean(times) 
            for day, times in day_groups.items() if times
        }
        
        # Calculate averages by hour
        hour_averages = {
            hour: statistics.mean(times) 
            for hour, times in hour_groups.items() if times
        }
        
        return {
            'by_day_of_week': day_averages,
            'by_hour_of_day': hour_averages
        }
    
    def _calculate_outlier_analysis(self, resolution_hours: List[float], 
                                  resolved_tickets: List[Ticket]) -> Dict[str, Any]:
        """Analyze outliers in resolution times.
        
        Args:
            resolution_hours: List of resolution times in hours.
            resolved_tickets: List of resolved tickets.
            
        Returns:
            Dictionary with outlier analysis.
        """
        if len(resolution_hours) < 4:  # Need at least 4 data points for meaningful outlier analysis
            return {'message': 'Insufficient data for outlier analysis'}
        
        # Calculate IQR method outliers
        q1 = self._percentile(sorted(resolution_hours), 25)
        q3 = self._percentile(sorted(resolution_hours), 75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = []
        for i, hours in enumerate(resolution_hours):
            if hours < lower_bound or hours > upper_bound:
                outliers.append({
                    'ticket_id': resolved_tickets[i].id,
                    'resolution_hours': hours,
                    'type': 'fast' if hours < lower_bound else 'slow'
                })
        
        return {
            'outlier_count': len(outliers),
            'outlier_percentage': (len(outliers) / len(resolution_hours)) * 100,
            'outliers': outliers[:10],  # Limit to first 10 outliers
            'iqr_bounds': {
                'lower': lower_bound,
                'upper': upper_bound,
                'q1': q1,
                'q3': q3,
                'iqr': iqr
            }
        }


class StatusDistributionCalculator(MetricsCalculator):
    """Calculator for ticket status distribution metrics.
    
    This calculator analyzes the distribution of tickets across different
    status values, providing insights into workflow patterns and bottlenecks.
    """
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate status distribution metrics.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing status distribution metrics.
        """
        if not self.validate_input(tickets):
            return self._handle_empty_dataset()
        
        valid_tickets = self._filter_valid_tickets(tickets)
        
        if not valid_tickets:
            return self._handle_empty_dataset()
        
        # Calculate basic distribution
        status_counts = Counter(str(ticket.status) for ticket in valid_tickets)
        total = len(valid_tickets)
        
        # Calculate percentages
        status_percentages = {
            status: (count / total) * 100 
            for status, count in status_counts.items()
        }
        
        # Calculate trends over time
        time_trends = self._calculate_status_trends(valid_tickets)
        
        # Calculate transition analysis
        transition_analysis = self._calculate_status_transitions(valid_tickets)
        
        result = {
            'status_counts': dict(status_counts),
            'status_percentages': status_percentages,
            'total_tickets': total,
            'unique_statuses': len(status_counts),
            'most_common_status': status_counts.most_common(1)[0] if status_counts else None,
            'time_trends': time_trends,
            'transition_analysis': transition_analysis
        }
        
        return self._add_metadata(result, tickets)
    
    def get_metric_names(self) -> List[str]:
        """Get list of metric names this calculator provides."""
        return [
            'status_counts',
            'status_percentages',
            'total_tickets',
            'unique_statuses',
            'most_common_status',
            'time_trends',
            'transition_analysis'
        ]
    
    def _calculate_status_trends(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate status distribution trends over time.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with trend data.
        """
        if not tickets:
            return {}
        
        # Group tickets by month and status
        monthly_status = defaultdict(lambda: defaultdict(int))
        
        for ticket in tickets:
            if ticket.created_date:
                month_key = ticket.created_date.strftime('%Y-%m')
                status = str(ticket.status)
                monthly_status[month_key][status] += 1
        
        return {
            'monthly_distribution': {
                month: dict(statuses) 
                for month, statuses in monthly_status.items()
            }
        }
    
    def _calculate_status_transitions(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Analyze status transitions (placeholder for future enhancement).
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with transition analysis.
        """
        # This is a placeholder for future enhancement
        # Would require ticket history data to track status changes
        return {
            'message': 'Status transition analysis requires ticket history data',
            'available': False
        }


class VolumeAnalyzer(MetricsCalculator):
    """Calculator for ticket volume analysis and trends.
    
    This calculator analyzes ticket creation patterns, volume trends,
    and identifies peak periods and seasonal patterns.
    """
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate volume analysis metrics.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing volume analysis metrics.
        """
        if not self.validate_input(tickets):
            return self._handle_empty_dataset()
        
        valid_tickets = self._filter_valid_tickets(tickets)
        
        if not valid_tickets:
            return self._handle_empty_dataset()
        
        # Basic volume metrics
        basic_metrics = self._calculate_basic_volume_metrics(valid_tickets)
        
        # Time-based analysis
        time_analysis = self._calculate_time_based_volume(valid_tickets)
        
        # Peak analysis
        peak_analysis = self._calculate_peak_analysis(valid_tickets)
        
        # Growth analysis
        growth_analysis = self._calculate_growth_analysis(valid_tickets)
        
        result = {
            **basic_metrics,
            'time_analysis': time_analysis,
            'peak_analysis': peak_analysis,
            'growth_analysis': growth_analysis
        }
        
        return self._add_metadata(result, tickets)
    
    def get_metric_names(self) -> List[str]:
        """Get list of metric names this calculator provides."""
        return [
            'total_volume',
            'daily_average',
            'weekly_average',
            'monthly_average',
            'time_analysis',
            'peak_analysis',
            'growth_analysis'
        ]
    
    def _calculate_basic_volume_metrics(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate basic volume metrics.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with basic volume metrics.
        """
        total_volume = len(tickets)
        
        if not tickets:
            return {'total_volume': 0}
        
        # Calculate date range
        dates = [ticket.created_date for ticket in tickets if ticket.created_date]
        
        if not dates:
            return {'total_volume': total_volume}
        
        date_range = max(dates) - min(dates)
        days = max(1, date_range.days)
        weeks = max(1, days / 7)
        months = max(1, days / 30)
        
        return {
            'total_volume': total_volume,
            'daily_average': total_volume / days,
            'weekly_average': total_volume / weeks,
            'monthly_average': total_volume / months,
            'date_range_days': days
        }
    
    def _calculate_time_based_volume(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate volume analysis by time periods.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with time-based volume analysis.
        """
        if not tickets:
            return {}
        
        # Group by different time periods
        daily_counts = defaultdict(int)
        weekly_counts = defaultdict(int)
        monthly_counts = defaultdict(int)
        hourly_counts = defaultdict(int)
        dow_counts = defaultdict(int)  # Day of week
        
        for ticket in tickets:
            if ticket.created_date:
                date = ticket.created_date
                
                daily_counts[date.date()] += 1
                weekly_counts[date.strftime('%Y-W%U')] += 1
                monthly_counts[date.strftime('%Y-%m')] += 1
                hourly_counts[date.hour] += 1
                dow_counts[date.strftime('%A')] += 1
        
        return {
            'daily_volume': dict(daily_counts),
            'weekly_volume': dict(weekly_counts),
            'monthly_volume': dict(monthly_counts),
            'hourly_distribution': dict(hourly_counts),
            'day_of_week_distribution': dict(dow_counts)
        }
    
    def _calculate_peak_analysis(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Analyze peak periods and patterns.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with peak analysis.
        """
        if not tickets:
            return {}
        
        # Daily volume analysis
        daily_counts = defaultdict(int)
        for ticket in tickets:
            if ticket.created_date:
                daily_counts[ticket.created_date.date()] += 1
        
        if not daily_counts:
            return {}
        
        volumes = list(daily_counts.values())
        avg_volume = statistics.mean(volumes)
        
        # Find peak days (above average + 1 std dev)
        if len(volumes) > 1:
            std_dev = statistics.stdev(volumes)
            peak_threshold = avg_volume + std_dev
            
            peak_days = [
                {'date': str(date), 'volume': volume}
                for date, volume in daily_counts.items()
                if volume > peak_threshold
            ]
        else:
            peak_days = []
        
        return {
            'average_daily_volume': avg_volume,
            'peak_threshold': peak_threshold if len(volumes) > 1 else avg_volume,
            'peak_days': sorted(peak_days, key=lambda x: x['volume'], reverse=True)[:10],
            'peak_day_count': len(peak_days)
        }
    
    def _calculate_growth_analysis(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate growth trends and patterns.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with growth analysis.
        """
        if not tickets:
            return {}
        
        # Monthly growth analysis
        monthly_counts = defaultdict(int)
        for ticket in tickets:
            if ticket.created_date:
                month_key = ticket.created_date.strftime('%Y-%m')
                monthly_counts[month_key] += 1
        
        if len(monthly_counts) < 2:
            return {'message': 'Insufficient data for growth analysis'}
        
        # Calculate month-over-month growth
        sorted_months = sorted(monthly_counts.items())
        growth_rates = []
        
        for i in range(1, len(sorted_months)):
            prev_month, prev_count = sorted_months[i-1]
            curr_month, curr_count = sorted_months[i]
            
            if prev_count > 0:
                growth_rate = ((curr_count - prev_count) / prev_count) * 100
                growth_rates.append({
                    'month': curr_month,
                    'growth_rate': growth_rate,
                    'volume': curr_count,
                    'previous_volume': prev_count
                })
        
        avg_growth_rate = statistics.mean([gr['growth_rate'] for gr in growth_rates]) if growth_rates else 0
        
        return {
            'monthly_growth_rates': growth_rates,
            'average_growth_rate': avg_growth_rate,
            'total_months': len(monthly_counts),
            'growth_trend': 'increasing' if avg_growth_rate > 0 else 'decreasing' if avg_growth_rate < 0 else 'stable'
        }


class SeverityAnalyzer(MetricsCalculator):
    """Calculator for ticket severity analysis and distribution.
    
    This calculator analyzes ticket severity patterns, distributions,
    and relationships with resolution times and other metrics.
    """
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate severity analysis metrics.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing severity analysis metrics.
        """
        if not self.validate_input(tickets):
            return self._handle_empty_dataset()
        
        valid_tickets = self._filter_valid_tickets(tickets)
        
        if not valid_tickets:
            return self._handle_empty_dataset()
        
        # Basic severity distribution
        severity_distribution = self._calculate_severity_distribution(valid_tickets)
        
        # Severity trends over time
        severity_trends = self._calculate_severity_trends(valid_tickets)
        
        # Severity vs resolution time analysis
        severity_resolution_analysis = self._calculate_severity_resolution_analysis(valid_tickets)
        
        result = {
            'distribution': severity_distribution,
            'trends': severity_trends,
            'resolution_analysis': severity_resolution_analysis
        }
        
        return self._add_metadata(result, tickets)
    
    def get_metric_names(self) -> List[str]:
        """Get list of metric names this calculator provides."""
        return [
            'distribution',
            'trends',
            'resolution_analysis'
        ]
    
    def _calculate_severity_distribution(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate basic severity distribution.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with severity distribution data.
        """
        severity_counts = Counter(str(ticket.severity) for ticket in tickets)
        total = len(tickets)
        
        severity_percentages = {
            severity: (count / total) * 100 
            for severity, count in severity_counts.items()
        }
        
        return {
            'counts': dict(severity_counts),
            'percentages': severity_percentages,
            'total_tickets': total,
            'unique_severities': len(severity_counts),
            'most_common_severity': severity_counts.most_common(1)[0] if severity_counts else None
        }
    
    def _calculate_severity_trends(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate severity trends over time.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with severity trend data.
        """
        monthly_severity = defaultdict(lambda: defaultdict(int))
        
        for ticket in tickets:
            if ticket.created_date:
                month_key = ticket.created_date.strftime('%Y-%m')
                severity = str(ticket.severity)
                monthly_severity[month_key][severity] += 1
        
        return {
            'monthly_distribution': {
                month: dict(severities) 
                for month, severities in monthly_severity.items()
            }
        }
    
    def _calculate_severity_resolution_analysis(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Analyze relationship between severity and resolution times.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with severity-resolution analysis.
        """
        severity_resolution = defaultdict(list)
        
        for ticket in tickets:
            if ticket.is_resolved() and ticket.resolution_time():
                severity = str(ticket.severity)
                resolution_hours = ticket.resolution_time().total_seconds() / 3600
                severity_resolution[severity].append(resolution_hours)
        
        analysis = {}
        for severity, times in severity_resolution.items():
            if times:
                analysis[severity] = {
                    'avg_resolution_hours': statistics.mean(times),
                    'median_resolution_hours': statistics.median(times),
                    'count': len(times),
                    'min_hours': min(times),
                    'max_hours': max(times)
                }
        
        return analysis


class TeamPerformanceCalculator(MetricsCalculator):
    """Calculator for team and assignee performance metrics.
    
    This calculator analyzes performance metrics by team, assignee,
    and resolver group, providing insights into workload distribution
    and performance patterns.
    """
    
    def calculate(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate team performance metrics.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary containing team performance metrics.
        """
        if not self.validate_input(tickets):
            return self._handle_empty_dataset()
        
        valid_tickets = self._filter_valid_tickets(tickets)
        
        if not valid_tickets:
            return self._handle_empty_dataset()
        
        # Assignee performance analysis
        assignee_analysis = self._calculate_assignee_performance(valid_tickets)
        
        # Resolver group analysis
        resolver_group_analysis = self._calculate_resolver_group_performance(valid_tickets)
        
        # Workload distribution analysis
        workload_analysis = self._calculate_workload_distribution(valid_tickets)
        
        result = {
            'assignee_performance': assignee_analysis,
            'resolver_group_performance': resolver_group_analysis,
            'workload_distribution': workload_analysis
        }
        
        return self._add_metadata(result, tickets)
    
    def get_metric_names(self) -> List[str]:
        """Get list of metric names this calculator provides."""
        return [
            'assignee_performance',
            'resolver_group_performance',
            'workload_distribution'
        ]
    
    def _calculate_assignee_performance(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate performance metrics by assignee.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with assignee performance data.
        """
        assignee_metrics = defaultdict(lambda: {
            'total_tickets': 0,
            'resolved_tickets': 0,
            'resolution_times': []
        })
        
        for ticket in tickets:
            assignee = ticket.assignee or 'Unassigned'
            assignee_metrics[assignee]['total_tickets'] += 1
            
            if ticket.is_resolved():
                assignee_metrics[assignee]['resolved_tickets'] += 1
                if ticket.resolution_time():
                    resolution_hours = ticket.resolution_time().total_seconds() / 3600
                    assignee_metrics[assignee]['resolution_times'].append(resolution_hours)
        
        # Calculate performance statistics
        performance_data = {}
        for assignee, metrics in assignee_metrics.items():
            resolution_times = metrics['resolution_times']
            
            performance_data[assignee] = {
                'total_tickets': metrics['total_tickets'],
                'resolved_tickets': metrics['resolved_tickets'],
                'resolution_rate': (
                    (metrics['resolved_tickets'] / metrics['total_tickets']) * 100
                    if metrics['total_tickets'] > 0 else 0
                ),
                'avg_resolution_hours': (
                    statistics.mean(resolution_times) if resolution_times else None
                ),
                'median_resolution_hours': (
                    statistics.median(resolution_times) if resolution_times else None
                )
            }
        
        return performance_data
    
    def _calculate_resolver_group_performance(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate performance metrics by resolver group.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with resolver group performance data.
        """
        group_metrics = defaultdict(lambda: {
            'total_tickets': 0,
            'resolved_tickets': 0,
            'resolution_times': []
        })
        
        for ticket in tickets:
            group = ticket.resolver_group or 'Unassigned'
            group_metrics[group]['total_tickets'] += 1
            
            if ticket.is_resolved():
                group_metrics[group]['resolved_tickets'] += 1
                if ticket.resolution_time():
                    resolution_hours = ticket.resolution_time().total_seconds() / 3600
                    group_metrics[group]['resolution_times'].append(resolution_hours)
        
        # Calculate group performance statistics
        performance_data = {}
        for group, metrics in group_metrics.items():
            resolution_times = metrics['resolution_times']
            
            performance_data[group] = {
                'total_tickets': metrics['total_tickets'],
                'resolved_tickets': metrics['resolved_tickets'],
                'resolution_rate': (
                    (metrics['resolved_tickets'] / metrics['total_tickets']) * 100
                    if metrics['total_tickets'] > 0 else 0
                ),
                'avg_resolution_hours': (
                    statistics.mean(resolution_times) if resolution_times else None
                ),
                'median_resolution_hours': (
                    statistics.median(resolution_times) if resolution_times else None
                )
            }
        
        return performance_data
    
    def _calculate_workload_distribution(self, tickets: List[Ticket]) -> Dict[str, Any]:
        """Calculate workload distribution analysis.
        
        Args:
            tickets: List of tickets to analyze.
            
        Returns:
            Dictionary with workload distribution data.
        """
        # Assignee workload
        assignee_counts = Counter(ticket.assignee or 'Unassigned' for ticket in tickets)
        
        # Resolver group workload
        group_counts = Counter(ticket.resolver_group or 'Unassigned' for ticket in tickets)
        
        # Calculate distribution statistics
        assignee_volumes = list(assignee_counts.values())
        group_volumes = list(group_counts.values())
        
        return {
            'assignee_distribution': dict(assignee_counts),
            'resolver_group_distribution': dict(group_counts),
            'assignee_stats': {
                'total_assignees': len(assignee_counts),
                'avg_tickets_per_assignee': statistics.mean(assignee_volumes) if assignee_volumes else 0,
                'max_tickets_per_assignee': max(assignee_volumes) if assignee_volumes else 0,
                'min_tickets_per_assignee': min(assignee_volumes) if assignee_volumes else 0
            },
            'group_stats': {
                'total_groups': len(group_counts),
                'avg_tickets_per_group': statistics.mean(group_volumes) if group_volumes else 0,
                'max_tickets_per_group': max(group_volumes) if group_volumes else 0,
                'min_tickets_per_group': min(group_volumes) if group_volumes else 0
            }
        }
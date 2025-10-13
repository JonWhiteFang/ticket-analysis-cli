#!/usr/bin/env python3
"""
Python Integration Example for Ticket Analysis CLI

This example demonstrates how to integrate the ticket analyzer into Python applications,
including programmatic execution, result processing, and error handling.

Usage:
    python integration-example.py
"""

import subprocess
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TicketAnalyzerIntegration:
    """Integration wrapper for the Ticket Analysis CLI."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize the integration wrapper.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file
        self.base_command = ["ticket-analyzer"]
        
        # Verify CLI is available
        if not self._check_cli_available():
            raise RuntimeError("ticket-analyzer CLI not found")
    
    def _check_cli_available(self) -> bool:
        """Check if the CLI tool is available."""
        try:
            result = subprocess.run(
                ["ticket-analyzer", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def analyze_tickets(self, 
                       resolver_group: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       status_filter: Optional[List[str]] = None,
                       max_results: int = 1000,
                       output_format: str = "json") -> Dict[str, Any]:
        """Analyze tickets and return results.
        
        Args:
            resolver_group: Team resolver group name
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            status_filter: List of ticket statuses to include
            max_results: Maximum number of results
            output_format: Output format (json, csv, html)
            
        Returns:
            Dictionary containing analysis results
            
        Raises:
            RuntimeError: If analysis fails
        """
        # Build command
        cmd = self.base_command + ["analyze"]
        
        if self.config_file:
            cmd.extend(["--config", self.config_file])
        
        if resolver_group:
            cmd.extend(["--resolver-group", resolver_group])
        
        if start_date:
            cmd.extend(["--start-date", start_date])
        
        if end_date:
            cmd.extend(["--end-date", end_date])
        
        if status_filter:
            for status in status_filter:
                cmd.extend(["--status", status])
        
        cmd.extend([
            "--max-results", str(max_results),
            "--format", output_format
        ])
        
        # Execute command
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Analysis failed: {result.stderr}")
            
            # Parse results based on format
            if output_format == "json":
                return json.loads(result.stdout)
            else:
                return {"raw_output": result.stdout}
                
        except subprocess.TimeoutExpired:
            raise RuntimeError("Analysis timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse JSON output: {e}")
    
    def get_team_metrics(self, team_name: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive metrics for a specific team.
        
        Args:
            team_name: Team resolver group name
            days: Number of days to analyze
            
        Returns:
            Dictionary with team metrics
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        return self.analyze_tickets(
            resolver_group=team_name,
            start_date=start_date,
            end_date=end_date,
            output_format="json"
        )
    
    def compare_periods(self, team_name: str, days: int = 30) -> Dict[str, Any]:
        """Compare current period with previous period.
        
        Args:
            team_name: Team resolver group name
            days: Number of days per period
            
        Returns:
            Dictionary with comparison results
        """
        # Current period
        current_end = datetime.now().strftime('%Y-%m-%d')
        current_start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Previous period
        previous_end = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        previous_start = (datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')
        
        current_metrics = self.analyze_tickets(
            resolver_group=team_name,
            start_date=current_start,
            end_date=current_end,
            output_format="json"
        )
        
        previous_metrics = self.analyze_tickets(
            resolver_group=team_name,
            start_date=previous_start,
            end_date=previous_end,
            output_format="json"
        )
        
        return {
            "current_period": {
                "start_date": current_start,
                "end_date": current_end,
                "metrics": current_metrics
            },
            "previous_period": {
                "start_date": previous_start,
                "end_date": previous_end,
                "metrics": previous_metrics
            },
            "comparison": self._calculate_comparison(current_metrics, previous_metrics)
        }
    
    def _calculate_comparison(self, current: Dict[str, Any], 
                            previous: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comparison metrics between two periods."""
        comparison = {}
        
        # Extract key metrics for comparison
        current_total = current.get('total_tickets', 0)
        previous_total = previous.get('total_tickets', 0)
        
        if previous_total > 0:
            comparison['ticket_volume_change'] = (
                (current_total - previous_total) / previous_total * 100
            )
        else:
            comparison['ticket_volume_change'] = 0
        
        # Add more comparison logic as needed
        comparison['current_total'] = current_total
        comparison['previous_total'] = previous_total
        
        return comparison


def example_basic_usage():
    """Example: Basic ticket analysis."""
    print("=== Basic Usage Example ===")
    
    analyzer = TicketAnalyzerIntegration()
    
    try:
        # Analyze last 7 days for a specific team
        results = analyzer.analyze_tickets(
            resolver_group="Frontend Development",
            start_date=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            status_filter=["Open", "In Progress", "Resolved"]
        )
        
        print(f"Total tickets: {results.get('total_tickets', 0)}")
        print(f"Analysis period: {results.get('date_range', {})}")
        
        # Extract key metrics
        metrics = results.get('metrics', {})
        if 'resolution_time' in metrics:
            avg_resolution = metrics['resolution_time'].get('avg_resolution_time_hours', 0)
            print(f"Average resolution time: {avg_resolution:.1f} hours")
        
    except RuntimeError as e:
        print(f"Analysis failed: {e}")


def example_team_comparison():
    """Example: Compare team performance across periods."""
    print("\n=== Team Comparison Example ===")
    
    analyzer = TicketAnalyzerIntegration()
    
    try:
        comparison = analyzer.compare_periods("Backend Services", days=30)
        
        current = comparison['current_period']['metrics']
        previous = comparison['previous_period']['metrics']
        comp_metrics = comparison['comparison']
        
        print(f"Current period tickets: {comp_metrics['current_total']}")
        print(f"Previous period tickets: {comp_metrics['previous_total']}")
        print(f"Volume change: {comp_metrics['ticket_volume_change']:.1f}%")
        
    except RuntimeError as e:
        print(f"Comparison failed: {e}")


def example_batch_processing():
    """Example: Process multiple teams in batch."""
    print("\n=== Batch Processing Example ===")
    
    analyzer = TicketAnalyzerIntegration()
    teams = ["Frontend Development", "Backend Services", "DevOps", "QA Team"]
    
    results = {}
    for team in teams:
        try:
            team_metrics = analyzer.get_team_metrics(team, days=14)
            results[team] = {
                'total_tickets': team_metrics.get('total_tickets', 0),
                'success': True
            }
            print(f"✓ {team}: {results[team]['total_tickets']} tickets")
            
        except RuntimeError as e:
            results[team] = {'success': False, 'error': str(e)}
            print(f"✗ {team}: {e}")
    
    # Summary
    successful = sum(1 for r in results.values() if r.get('success', False))
    print(f"\nProcessed {successful}/{len(teams)} teams successfully")


def example_custom_analysis():
    """Example: Custom analysis with specific filters."""
    print("\n=== Custom Analysis Example ===")
    
    analyzer = TicketAnalyzerIntegration()
    
    try:
        # Analyze high-priority tickets for the last month
        results = analyzer.analyze_tickets(
            start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            end_date=datetime.now().strftime('%Y-%m-%d'),
            status_filter=["Open", "In Progress"],
            max_results=500
        )
        
        print(f"High-priority open tickets: {results.get('total_tickets', 0)}")
        
        # Process metrics
        metrics = results.get('metrics', {})
        if 'status_distribution' in metrics:
            status_dist = metrics['status_distribution']
            for status, count in status_dist.get('status_counts', {}).items():
                print(f"  {status}: {count}")
        
    except RuntimeError as e:
        print(f"Custom analysis failed: {e}")


def example_error_handling():
    """Example: Proper error handling and logging."""
    print("\n=== Error Handling Example ===")
    
    analyzer = TicketAnalyzerIntegration()
    
    # Test with invalid team name
    try:
        results = analyzer.analyze_tickets(
            resolver_group="Non-Existent Team",
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        print("Analysis completed (unexpected)")
        
    except RuntimeError as e:
        print(f"Expected error caught: {e}")
        logger.warning(f"Analysis failed for non-existent team: {e}")
    
    # Test with invalid date range
    try:
        results = analyzer.analyze_tickets(
            start_date="invalid-date",
            end_date="2024-01-31"
        )
        print("Analysis completed (unexpected)")
        
    except RuntimeError as e:
        print(f"Expected error caught: {e}")
        logger.error(f"Invalid date format: {e}")


def main():
    """Run all examples."""
    print("Ticket Analysis CLI Integration Examples")
    print("=" * 50)
    
    try:
        example_basic_usage()
        example_team_comparison()
        example_batch_processing()
        example_custom_analysis()
        example_error_handling()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"Example execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
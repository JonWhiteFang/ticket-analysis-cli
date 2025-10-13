#!/usr/bin/env python3
"""
Bulk Ticket Analysis Script

This script processes multiple date ranges, teams, or configurations in batch mode.
Useful for generating historical reports or analyzing multiple teams simultaneously.

Usage:
    python bulk-analysis.py [OPTIONS]

Examples:
    # Analyze multiple teams
    python bulk-analysis.py --teams "Team A" "Team B" "Team C"
    
    # Historical analysis (monthly reports for last 6 months)
    python bulk-analysis.py --historical --months 6
    
    # Custom date ranges
    python bulk-analysis.py --date-ranges "2024-01-01,2024-01-31" "2024-02-01,2024-02-29"
"""

import argparse
import subprocess
import sys
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BulkAnalyzer:
    """Bulk ticket analysis processor."""
    
    def __init__(self, output_dir: str = "./bulk-reports", 
                 max_workers: int = 3, verbose: bool = False):
        self.output_dir = Path(output_dir)
        self.max_workers = max_workers
        self.verbose = verbose
        self.results: List[Dict[str, Any]] = []
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if verbose:
            logger.setLevel(logging.DEBUG)
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        try:
            result = subprocess.run(
                ["ticket-analyzer", "--version"], 
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info("ticket-analyzer is available")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        logger.error("ticket-analyzer command not found")
        return False
    
    def check_authentication(self) -> bool:
        """Check authentication status."""
        try:
            result = subprocess.run(
                ["mwinit", "-s"], 
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Cannot verify authentication status")
            return True  # Assume OK if mwinit not available    
  
  def generate_date_ranges(self, months: int) -> List[tuple]:
        """Generate monthly date ranges for historical analysis."""
        ranges = []
        current_date = datetime.now().replace(day=1)
        
        for i in range(months):
            end_date = current_date - timedelta(days=1)
            start_date = (current_date - timedelta(days=32)).replace(day=1)
            ranges.append((start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            current_date = start_date
        
        return ranges
    
    def run_single_analysis(self, team: str, start_date: str, end_date: str, 
                          format_type: str = "json") -> Dict[str, Any]:
        """Run analysis for a single team and date range."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_team = team.replace(' ', '_').replace('/', '_')
        output_file = self.output_dir / f"{safe_team}_{start_date}_{end_date}_{timestamp}.{format_type}"
        
        cmd = [
            "ticket-analyzer", "analyze",
            "--resolver-group", team,
            "--start-date", start_date,
            "--end-date", end_date,
            "--format", format_type,
            "--output", str(output_file),
            "--progress"
        ]
        
        if self.verbose:
            cmd.append("--verbose")
        
        logger.info(f"Analyzing {team}: {start_date} to {end_date}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            analysis_result = {
                "team": team,
                "start_date": start_date,
                "end_date": end_date,
                "output_file": str(output_file),
                "success": result.returncode == 0,
                "timestamp": timestamp
            }
            
            if result.returncode == 0:
                logger.info(f"✓ Completed: {team} ({start_date} to {end_date})")
                analysis_result["file_size"] = output_file.stat().st_size if output_file.exists() else 0
            else:
                logger.error(f"✗ Failed: {team} ({start_date} to {end_date})")
                analysis_result["error"] = result.stderr
            
            return analysis_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"✗ Timeout: {team} ({start_date} to {end_date})")
            return {
                "team": team,
                "start_date": start_date,
                "end_date": end_date,
                "success": False,
                "error": "Analysis timed out",
                "timestamp": timestamp
            }
    
    def run_bulk_analysis(self, teams: List[str], date_ranges: List[tuple], 
                         format_type: str = "json") -> List[Dict[str, Any]]:
        """Run bulk analysis for multiple teams and date ranges."""
        tasks = []
        
        # Create all combinations of teams and date ranges
        for team in teams:
            for start_date, end_date in date_ranges:
                tasks.append((team, start_date, end_date, format_type))
        
        logger.info(f"Starting bulk analysis: {len(tasks)} tasks with {self.max_workers} workers")
        
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self.run_single_analysis, *task): task 
                for task in tasks
            }
            
            # Process completed tasks
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Task failed {task}: {e}")
                    results.append({
                        "team": task[0],
                        "start_date": task[1],
                        "end_date": task[2],
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().strftime('%Y%m%d_%H%M%S')
                    })
        
        return results
    
    def generate_summary_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate summary report of bulk analysis."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_file = self.output_dir / f"bulk_analysis_summary_{timestamp}.json"
        
        # Calculate statistics
        total_tasks = len(results)
        successful_tasks = sum(1 for r in results if r.get('success', False))
        failed_tasks = total_tasks - successful_tasks
        
        # Group by team
        teams_processed = set(r['team'] for r in results)
        
        summary = {
            "generated_at": datetime.now().isoformat(),
            "statistics": {
                "total_tasks": total_tasks,
                "successful_tasks": successful_tasks,
                "failed_tasks": failed_tasks,
                "success_rate": (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0,
                "teams_processed": len(teams_processed)
            },
            "teams": list(teams_processed),
            "results": results
        }
        
        # Save summary
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Summary report saved: {summary_file}")
        return str(summary_file)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Bulk Ticket Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--teams", nargs="+", 
        help="List of team resolver groups to analyze"
    )
    parser.add_argument(
        "--date-ranges", nargs="+",
        help="Custom date ranges in format 'YYYY-MM-DD,YYYY-MM-DD'"
    )
    parser.add_argument(
        "--historical", action="store_true",
        help="Generate historical monthly reports"
    )
    parser.add_argument(
        "--months", type=int, default=6,
        help="Number of months for historical analysis (default: 6)"
    )
    parser.add_argument(
        "--format", choices=["json", "csv", "html"], default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--output-dir", default="./bulk-reports",
        help="Output directory (default: ./bulk-reports)"
    )
    parser.add_argument(
        "--max-workers", type=int, default=3,
        help="Maximum parallel workers (default: 3)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.teams and not args.historical:
        parser.error("Must specify either --teams or --historical")
    
    # Initialize analyzer
    analyzer = BulkAnalyzer(
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        verbose=args.verbose
    )
    
    # Check dependencies
    if not analyzer.check_dependencies():
        sys.exit(1)
    
    if not analyzer.check_authentication():
        logger.warning("Authentication check failed, continuing anyway")
    
    # Determine teams and date ranges
    teams = args.teams or [""]  # Empty string for all teams
    
    if args.historical:
        date_ranges = analyzer.generate_date_ranges(args.months)
        logger.info(f"Generated {len(date_ranges)} monthly date ranges")
    elif args.date_ranges:
        date_ranges = []
        for range_str in args.date_ranges:
            try:
                start, end = range_str.split(',')
                date_ranges.append((start.strip(), end.strip()))
            except ValueError:
                logger.error(f"Invalid date range format: {range_str}")
                sys.exit(1)
    else:
        # Default: last 30 days
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        date_ranges = [(start_date, end_date)]
    
    logger.info(f"Processing {len(teams)} teams across {len(date_ranges)} date ranges")
    
    # Run bulk analysis
    start_time = time.time()
    results = analyzer.run_bulk_analysis(teams, date_ranges, args.format)
    end_time = time.time()
    
    # Generate summary
    summary_file = analyzer.generate_summary_report(results)
    
    # Print final statistics
    successful = sum(1 for r in results if r.get('success', False))
    total = len(results)
    
    print(f"\nBulk Analysis Complete!")
    print(f"Total tasks: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success rate: {successful/total*100:.1f}%")
    print(f"Total time: {end_time - start_time:.1f} seconds")
    print(f"Summary report: {summary_file}")
    print(f"Output directory: {args.output_dir}")


if __name__ == "__main__":
    main()
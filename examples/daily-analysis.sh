#!/bin/bash

# Daily Ticket Analysis Automation Script
# This script performs automated daily ticket analysis and generates reports
# 
# Usage: ./daily-analysis.sh [OPTIONS]
# Options:
#   -t, --team TEAM_NAME    Analyze specific team (default: all teams)
#   -f, --format FORMAT     Output format (default: html)
#   -o, --output DIR        Output directory (default: ./daily-reports)
#   -d, --days DAYS         Number of days to analyze (default: 7)
#   -v, --verbose           Enable verbose output
#   -h, --help              Show this help message
#
# Example:
#   ./daily-analysis.sh --team "My Team" --format html --days 30

set -euo pipefail

# Default configuration
TEAM_NAME=""
OUTPUT_FORMAT="html"
OUTPUT_DIR="./daily-reports"
DAYS=7
VERBOSE=false
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Daily Ticket Analysis Automation Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -t, --team TEAM_NAME    Analyze specific team (default: all teams)
    -f, --format FORMAT     Output format: table, json, csv, html (default: html)
    -o, --output DIR        Output directory (default: ./daily-reports)
    -d, --days DAYS         Number of days to analyze (default: 7)
    -v, --verbose           Enable verbose output
    -h, --help              Show this help message

EXAMPLES:
    # Basic daily analysis
    $0

    # Analyze specific team for last 30 days
    $0 --team "Frontend Team" --days 30

    # Generate JSON report with verbose output
    $0 --format json --verbose

    # Custom output directory
    $0 --output /shared/reports/daily

CONFIGURATION:
    The script uses the default ticket-analyzer configuration.
    To customize settings, create ~/.ticket-analyzer/config.json

SCHEDULING:
    To run this script daily via cron:
    0 8 * * * /path/to/daily-analysis.sh --team "Your Team" >> /var/log/daily-analysis.log 2>&1

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--team)
                TEAM_NAME="$2"
                shift 2
                ;;
            -f|--format)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -d|--days)
                DAYS="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Validate dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v ticket-analyzer &> /dev/null; then
        log_error "ticket-analyzer command not found. Please install the Ticket Analysis CLI."
        exit 1
    fi
    
    if ! command -v mwinit &> /dev/null; then
        log_warning "mwinit command not found. Authentication may fail."
    fi
    
    log_success "Dependencies check completed"
}

# Check authentication
check_authentication() {
    log_info "Checking authentication status..."
    
    if mwinit -s &> /dev/null; then
        log_success "Authentication is valid"
    else
        log_warning "Authentication may be expired. Attempting to refresh..."
        if ! mwinit -o; then
            log_error "Authentication failed. Please run 'mwinit -o' manually."
            exit 1
        fi
        log_success "Authentication refreshed"
    fi
}

# Create output directory
setup_output_directory() {
    log_info "Setting up output directory: $OUTPUT_DIR"
    
    mkdir -p "$OUTPUT_DIR"
    
    if [[ ! -w "$OUTPUT_DIR" ]]; then
        log_error "Output directory is not writable: $OUTPUT_DIR"
        exit 1
    fi
    
    log_success "Output directory ready"
}

# Build ticket-analyzer command
build_command() {
    local cmd="ticket-analyzer analyze"
    
    # Add date range
    local start_date=$(date -d "$DAYS days ago" +%Y-%m-%d)
    cmd="$cmd --start-date $start_date --end-date $DATE"
    
    # Add team filter if specified
    if [[ -n "$TEAM_NAME" ]]; then
        cmd="$cmd --resolver-group \"$TEAM_NAME\""
    fi
    
    # Add output format and file
    local output_file="$OUTPUT_DIR/daily-analysis-$TIMESTAMP.$OUTPUT_FORMAT"
    cmd="$cmd --format $OUTPUT_FORMAT --output \"$output_file\""
    
    # Add verbose flag if requested
    if [[ "$VERBOSE" == true ]]; then
        cmd="$cmd --verbose"
    fi
    
    # Add progress indicator
    cmd="$cmd --progress"
    
    echo "$cmd"
}

# Run analysis
run_analysis() {
    local cmd=$(build_command)
    
    log_info "Running ticket analysis..."
    log_info "Command: $cmd"
    
    if [[ "$VERBOSE" == true ]]; then
        log_info "Analysis parameters:"
        log_info "  Team: ${TEAM_NAME:-'All teams'}"
        log_info "  Date range: $(date -d "$DAYS days ago" +%Y-%m-%d) to $DATE"
        log_info "  Output format: $OUTPUT_FORMAT"
        log_info "  Output directory: $OUTPUT_DIR"
    fi
    
    # Execute the command
    if eval "$cmd"; then
        log_success "Analysis completed successfully"
        
        # Find the generated report file
        local report_file=$(find "$OUTPUT_DIR" -name "daily-analysis-$TIMESTAMP.*" -type f | head -1)
        if [[ -n "$report_file" ]]; then
            log_success "Report generated: $report_file"
            
            # Show file size
            local file_size=$(du -h "$report_file" | cut -f1)
            log_info "Report size: $file_size"
            
            # For HTML reports, show URL if applicable
            if [[ "$OUTPUT_FORMAT" == "html" ]]; then
                log_info "Open in browser: file://$(realpath "$report_file")"
            fi
        fi
    else
        log_error "Analysis failed"
        exit 1
    fi
}

# Generate summary
generate_summary() {
    log_info "Generating analysis summary..."
    
    local summary_file="$OUTPUT_DIR/daily-summary-$DATE.txt"
    
    cat > "$summary_file" << EOF
Daily Ticket Analysis Summary
Generated: $(date)
Script: $0
Parameters:
  Team: ${TEAM_NAME:-'All teams'}
  Date Range: $(date -d "$DAYS days ago" +%Y-%m-%d) to $DATE
  Output Format: $OUTPUT_FORMAT
  Output Directory: $OUTPUT_DIR

Reports Generated:
$(find "$OUTPUT_DIR" -name "*$TIMESTAMP*" -type f -exec basename {} \; | sed 's/^/  /')

EOF
    
    log_success "Summary saved: $summary_file"
}

# Cleanup old reports (keep last 30 days)
cleanup_old_reports() {
    if [[ "$VERBOSE" == true ]]; then
        log_info "Cleaning up old reports (keeping last 30 days)..."
    fi
    
    find "$OUTPUT_DIR" -name "daily-analysis-*" -type f -mtime +30 -delete 2>/dev/null || true
    find "$OUTPUT_DIR" -name "daily-summary-*" -type f -mtime +30 -delete 2>/dev/null || true
    
    if [[ "$VERBOSE" == true ]]; then
        log_success "Cleanup completed"
    fi
}

# Main execution
main() {
    log_info "Starting daily ticket analysis - $(date)"
    
    parse_args "$@"
    check_dependencies
    check_authentication
    setup_output_directory
    run_analysis
    generate_summary
    cleanup_old_reports
    
    log_success "Daily analysis completed successfully!"
    
    if [[ "$VERBOSE" == true ]]; then
        log_info "Check $OUTPUT_DIR for generated reports"
    fi
}

# Error handling
trap 'log_error "Script failed at line $LINENO"' ERR

# Run main function with all arguments
main "$@"
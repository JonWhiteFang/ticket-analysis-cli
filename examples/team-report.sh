#!/bin/bash

# Team Performance Report Generator
# Generates comprehensive team performance reports with multiple metrics
#
# Usage: ./team-report.sh [OPTIONS]
# Options:
#   -t, --team TEAM_NAME      Team resolver group name (required)
#   -p, --period PERIOD       Time period: weekly, monthly, quarterly (default: monthly)
#   -f, --format FORMAT       Output format: html, json, csv (default: html)
#   -o, --output DIR          Output directory (default: ./team-reports)
#   -c, --compare             Include comparison with previous period
#   -e, --email EMAIL         Email report to specified address
#   -v, --verbose             Enable verbose output
#   -h, --help                Show this help message

set -euo pipefail

# Default configuration
TEAM_NAME=""
PERIOD="monthly"
OUTPUT_FORMAT="html"
OUTPUT_DIR="./team-reports"
COMPARE=false
EMAIL=""
VERBOSE=false
DATE=$(date +%Y-%m-%d)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Help function
show_help() {
    cat << EOF
Team Performance Report Generator

USAGE:
    $0 -t TEAM_NAME [OPTIONS]

REQUIRED:
    -t, --team TEAM_NAME      Team resolver group name

OPTIONS:
    -p, --period PERIOD       Time period: weekly, monthly, quarterly (default: monthly)
    -f, --format FORMAT       Output format: html, json, csv (default: html)
    -o, --output DIR          Output directory (default: ./team-reports)
    -c, --compare             Include comparison with previous period
    -e, --email EMAIL         Email report to specified address
    -v, --verbose             Enable verbose output
    -h, --help                Show this help message

EXAMPLES:
    # Basic monthly report for a team
    $0 --team "Frontend Development"

    # Weekly report with comparison
    $0 --team "Backend Services" --period weekly --compare

    # Quarterly report in JSON format
    $0 --team "DevOps" --period quarterly --format json

    # Generate and email report
    $0 --team "Support Team" --email manager@company.com

PERIODS:
    weekly     - Last 7 days vs previous 7 days
    monthly    - Last 30 days vs previous 30 days  
    quarterly  - Last 90 days vs previous 90 days

OUTPUT:
    Reports include:
    - Ticket volume and trends
    - Resolution time metrics
    - Status distribution
    - Team workload analysis
    - Priority breakdown
    - Performance comparisons (if --compare used)

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
            -p|--period)
                PERIOD="$2"
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
            -c|--compare)
                COMPARE=true
                shift
                ;;
            -e|--email)
                EMAIL="$2"
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
    
    # Validate required arguments
    if [[ -z "$TEAM_NAME" ]]; then
        log_error "Team name is required. Use -t or --team option."
        show_help
        exit 1
    fi
    
    # Validate period
    if [[ ! "$PERIOD" =~ ^(weekly|monthly|quarterly)$ ]]; then
        log_error "Invalid period: $PERIOD. Must be weekly, monthly, or quarterly."
        exit 1
    fi
    
    # Validate format
    if [[ ! "$OUTPUT_FORMAT" =~ ^(html|json|csv)$ ]]; then
        log_error "Invalid format: $OUTPUT_FORMAT. Must be html, json, or csv."
        exit 1
    fi
}

# Calculate date ranges based on period
calculate_dates() {
    case $PERIOD in
        weekly)
            DAYS=7
            PERIOD_NAME="Weekly"
            ;;
        monthly)
            DAYS=30
            PERIOD_NAME="Monthly"
            ;;
        quarterly)
            DAYS=90
            PERIOD_NAME="Quarterly"
            ;;
    esac
    
    # Current period
    CURRENT_END=$(date +%Y-%m-%d)
    CURRENT_START=$(date -d "$DAYS days ago" +%Y-%m-%d)
    
    # Previous period (for comparison)
    if [[ "$COMPARE" == true ]]; then
        PREVIOUS_END=$(date -d "$DAYS days ago" +%Y-%m-%d)
        PREVIOUS_START=$(date -d "$((DAYS * 2)) days ago" +%Y-%m-%d)
    fi
    
    if [[ "$VERBOSE" == true ]]; then
        log_info "Date ranges calculated:"
        log_info "  Current period: $CURRENT_START to $CURRENT_END"
        if [[ "$COMPARE" == true ]]; then
            log_info "  Previous period: $PREVIOUS_START to $PREVIOUS_END"
        fi
    fi
}

# Generate current period report
generate_current_report() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local safe_team_name=$(echo "$TEAM_NAME" | tr ' ' '_' | tr -cd '[:alnum:]_-')
    local output_file="$OUTPUT_DIR/${safe_team_name}_${PERIOD}_${timestamp}.$OUTPUT_FORMAT"
    
    log_info "Generating $PERIOD_NAME report for '$TEAM_NAME'..."
    
    local cmd="ticket-analyzer analyze"
    cmd="$cmd --resolver-group \"$TEAM_NAME\""
    cmd="$cmd --start-date $CURRENT_START"
    cmd="$cmd --end-date $CURRENT_END"
    cmd="$cmd --format $OUTPUT_FORMAT"
    cmd="$cmd --output \"$output_file\""
    cmd="$cmd --progress"
    
    if [[ "$VERBOSE" == true ]]; then
        cmd="$cmd --verbose"
        log_info "Command: $cmd"
    fi
    
    if eval "$cmd"; then
        log_success "Current period report generated: $output_file"
        echo "$output_file"
    else
        log_error "Failed to generate current period report"
        return 1
    fi
}

# Generate comparison report
generate_comparison_report() {
    if [[ "$COMPARE" != true ]]; then
        return 0
    fi
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local safe_team_name=$(echo "$TEAM_NAME" | tr ' ' '_' | tr -cd '[:alnum:]_-')
    local output_file="$OUTPUT_DIR/${safe_team_name}_${PERIOD}_comparison_${timestamp}.$OUTPUT_FORMAT"
    
    log_info "Generating comparison report for previous $PERIOD_NAME period..."
    
    local cmd="ticket-analyzer analyze"
    cmd="$cmd --resolver-group \"$TEAM_NAME\""
    cmd="$cmd --start-date $PREVIOUS_START"
    cmd="$cmd --end-date $PREVIOUS_END"
    cmd="$cmd --format $OUTPUT_FORMAT"
    cmd="$cmd --output \"$output_file\""
    cmd="$cmd --progress"
    
    if [[ "$VERBOSE" == true ]]; then
        cmd="$cmd --verbose"
    fi
    
    if eval "$cmd"; then
        log_success "Comparison report generated: $output_file"
        echo "$output_file"
    else
        log_warning "Failed to generate comparison report"
        return 1
    fi
}

# Create summary report
create_summary() {
    local current_report="$1"
    local comparison_report="$2"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local safe_team_name=$(echo "$TEAM_NAME" | tr ' ' '_' | tr -cd '[:alnum:]_-')
    local summary_file="$OUTPUT_DIR/${safe_team_name}_${PERIOD}_summary_${timestamp}.txt"
    
    log_info "Creating summary report..."
    
    cat > "$summary_file" << EOF
Team Performance Report Summary
===============================

Team: $TEAM_NAME
Period: $PERIOD_NAME ($CURRENT_START to $CURRENT_END)
Generated: $(date)
Generated by: $0

Reports Generated:
- Current Period: $(basename "$current_report")
EOF
    
    if [[ -n "$comparison_report" ]]; then
        cat >> "$summary_file" << EOF
- Previous Period: $(basename "$comparison_report")
- Comparison: Enabled
EOF
    else
        cat >> "$summary_file" << EOF
- Comparison: Not requested
EOF
    fi
    
    cat >> "$summary_file" << EOF

Key Metrics to Review:
- Total ticket volume
- Average resolution time
- Status distribution
- Priority breakdown
- Team workload balance

Next Steps:
1. Review the generated reports
2. Identify trends and patterns
3. Discuss findings with team
4. Plan improvements if needed

EOF
    
    if [[ "$OUTPUT_FORMAT" == "html" ]]; then
        cat >> "$summary_file" << EOF
View Reports:
- Current: file://$(realpath "$current_report")
EOF
        if [[ -n "$comparison_report" ]]; then
            cat >> "$summary_file" << EOF
- Previous: file://$(realpath "$comparison_report")
EOF
        fi
    fi
    
    log_success "Summary created: $summary_file"
    echo "$summary_file"
}

# Email report if requested
email_report() {
    local current_report="$1"
    local summary_file="$2"
    
    if [[ -z "$EMAIL" ]]; then
        return 0
    fi
    
    log_info "Emailing report to $EMAIL..."
    
    if command -v mail &> /dev/null; then
        local subject="Team Performance Report - $TEAM_NAME ($PERIOD_NAME)"
        
        {
            echo "Team Performance Report"
            echo "======================"
            echo ""
            cat "$summary_file"
        } | mail -s "$subject" -a "$current_report" "$EMAIL"
        
        log_success "Report emailed to $EMAIL"
    else
        log_warning "Mail command not available. Cannot send email."
        log_info "Report files are available in: $OUTPUT_DIR"
    fi
}

# Main execution
main() {
    log_info "Starting team performance report generation - $(date)"
    
    parse_args "$@"
    
    # Check dependencies
    if ! command -v ticket-analyzer &> /dev/null; then
        log_error "ticket-analyzer command not found"
        exit 1
    fi
    
    # Check authentication
    if ! mwinit -s &> /dev/null; then
        log_warning "Authentication may be expired"
        if ! mwinit -o; then
            log_error "Authentication failed"
            exit 1
        fi
    fi
    
    # Setup
    calculate_dates
    mkdir -p "$OUTPUT_DIR"
    
    # Generate reports
    local current_report
    local comparison_report=""
    
    current_report=$(generate_current_report)
    
    if [[ "$COMPARE" == true ]]; then
        comparison_report=$(generate_comparison_report) || true
    fi
    
    # Create summary
    local summary_file
    summary_file=$(create_summary "$current_report" "$comparison_report")
    
    # Email if requested
    email_report "$current_report" "$summary_file"
    
    log_success "Team performance report generation completed!"
    log_info "Reports available in: $OUTPUT_DIR"
    
    if [[ "$VERBOSE" == true ]]; then
        log_info "Files generated:"
        find "$OUTPUT_DIR" -name "*$(date +%Y%m%d)*" -type f -exec basename {} \; | sed 's/^/  /'
    fi
}

# Error handling
trap 'log_error "Script failed at line $LINENO"' ERR

# Run main function
main "$@"
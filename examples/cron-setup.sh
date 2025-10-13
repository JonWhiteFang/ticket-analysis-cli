#!/bin/bash

# Cron Job Setup Script for Ticket Analysis CLI
# This script helps set up automated ticket analysis using cron jobs
#
# Usage: ./cron-setup.sh [OPTIONS]
# Options:
#   --install           Install cron jobs
#   --uninstall         Remove cron jobs
#   --list              List current cron jobs
#   --test              Test cron job execution
#   --help              Show this help

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_TAG="# TICKET_ANALYZER_CRON"
LOG_DIR="$HOME/.ticket-analyzer/logs"
REPORTS_DIR="$HOME/.ticket-analyzer/reports"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    cat << EOF
Cron Job Setup Script for Ticket Analysis CLI

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --install           Install cron jobs for automated analysis
    --uninstall         Remove all ticket analyzer cron jobs
    --list              List current ticket analyzer cron jobs
    --test              Test cron job execution
    --help              Show this help message

CRON JOBS INSTALLED:
    1. Daily Analysis    - Every day at 8:00 AM
    2. Weekly Report     - Every Monday at 9:00 AM  
    3. Monthly Report    - First day of month at 10:00 AM
    4. Log Cleanup       - Every Sunday at 2:00 AM

EXAMPLES:
    # Install all cron jobs
    $0 --install

    # Remove all cron jobs
    $0 --uninstall

    # Check current jobs
    $0 --list

    # Test execution
    $0 --test

CONFIGURATION:
    Edit the variables in this script to customize:
    - Teams to analyze
    - Report formats
    - Email recipients
    - Output directories

REQUIREMENTS:
    - ticket-analyzer CLI installed and in PATH
    - Valid Midway authentication setup
    - Write access to log and report directories

EOF
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check if ticket-analyzer is available
    if ! command -v ticket-analyzer &> /dev/null; then
        log_error "ticket-analyzer command not found"
        return 1
    fi
    
    # Check if crontab is available
    if ! command -v crontab &> /dev/null; then
        log_error "crontab command not found"
        return 1
    fi
    
    # Check directories
    mkdir -p "$LOG_DIR" "$REPORTS_DIR"
    
    log_success "Dependencies check passed"
    return 0
}

create_wrapper_scripts() {
    log_info "Creating wrapper scripts..."
    
    local scripts_dir="$HOME/.ticket-analyzer/scripts"
    mkdir -p "$scripts_dir"
    
    # Daily analysis script
    cat > "$scripts_dir/daily-analysis.sh" << 'EOF'
#!/bin/bash
# Daily ticket analysis wrapper script

LOG_FILE="$HOME/.ticket-analyzer/logs/daily-$(date +%Y%m%d).log"
REPORT_DIR="$HOME/.ticket-analyzer/reports/daily"

exec >> "$LOG_FILE" 2>&1

echo "=== Daily Analysis Started: $(date) ==="

# Ensure authentication
if ! mwinit -s; then
    echo "Authentication expired, attempting refresh..."
    if ! mwinit -o; then
        echo "ERROR: Authentication failed"
        exit 1
    fi
fi

# Create report directory
mkdir -p "$REPORT_DIR"

# Run analysis for key teams
TEAMS=("Frontend Development" "Backend Services" "DevOps" "QA Team")

for team in "${TEAMS[@]}"; do
    echo "Analyzing team: $team"
    
    safe_team=$(echo "$team" | tr ' ' '_')
    output_file="$REPORT_DIR/daily_${safe_team}_$(date +%Y%m%d).html"
    
    if ticket-analyzer analyze \
        --resolver-group "$team" \
        --start-date "$(date -d '7 days ago' +%Y-%m-%d)" \
        --end-date "$(date +%Y-%m-%d)" \
        --format html \
        --output "$output_file" \
        --progress; then
        echo "✓ Completed: $team"
    else
        echo "✗ Failed: $team"
    fi
done

echo "=== Daily Analysis Completed: $(date) ==="
EOF

    # Weekly report script
    cat > "$scripts_dir/weekly-report.sh" << 'EOF'
#!/bin/bash
# Weekly ticket analysis wrapper script

LOG_FILE="$HOME/.ticket-analyzer/logs/weekly-$(date +%Y%m%d).log"
REPORT_DIR="$HOME/.ticket-analyzer/reports/weekly"

exec >> "$LOG_FILE" 2>&1

echo "=== Weekly Report Started: $(date) ==="

# Ensure authentication
if ! mwinit -s; then
    echo "Authentication expired, attempting refresh..."
    if ! mwinit -o; then
        echo "ERROR: Authentication failed"
        exit 1
    fi
fi

# Create report directory
mkdir -p "$REPORT_DIR"

# Generate comprehensive weekly report
output_file="$REPORT_DIR/weekly_all_teams_$(date +%Y%m%d).html"

echo "Generating weekly report for all teams..."

if ticket-analyzer analyze \
    --start-date "$(date -d '7 days ago' +%Y-%m-%d)" \
    --end-date "$(date +%Y-%m-%d)" \
    --format html \
    --output "$output_file" \
    --progress \
    --verbose; then
    echo "✓ Weekly report completed: $output_file"
    
    # Email report if configured
    if [ -n "${WEEKLY_EMAIL_RECIPIENTS:-}" ]; then
        echo "Emailing weekly report..."
        mail -s "Weekly Ticket Analysis Report - $(date +%Y-%m-%d)" \
             -a "$output_file" \
             "$WEEKLY_EMAIL_RECIPIENTS" < /dev/null || echo "Email failed"
    fi
else
    echo "✗ Weekly report failed"
fi

echo "=== Weekly Report Completed: $(date) ==="
EOF

    # Monthly report script
    cat > "$scripts_dir/monthly-report.sh" << 'EOF'
#!/bin/bash
# Monthly ticket analysis wrapper script

LOG_FILE="$HOME/.ticket-analyzer/logs/monthly-$(date +%Y%m%d).log"
REPORT_DIR="$HOME/.ticket-analyzer/reports/monthly"

exec >> "$LOG_FILE" 2>&1

echo "=== Monthly Report Started: $(date) ==="

# Ensure authentication
if ! mwinit -s; then
    echo "Authentication expired, attempting refresh..."
    if ! mwinit -o; then
        echo "ERROR: Authentication failed"
        exit 1
    fi
fi

# Create report directory
mkdir -p "$REPORT_DIR"

# Generate monthly report
last_month_start=$(date -d "$(date +%Y-%m-01) -1 month" +%Y-%m-%d)
last_month_end=$(date -d "$(date +%Y-%m-01) -1 day" +%Y-%m-%d)
output_file="$REPORT_DIR/monthly_$(date -d "$last_month_start" +%Y%m)_$(date +%Y%m%d).html"

echo "Generating monthly report: $last_month_start to $last_month_end"

if ticket-analyzer analyze \
    --start-date "$last_month_start" \
    --end-date "$last_month_end" \
    --format html \
    --output "$output_file" \
    --progress \
    --verbose; then
    echo "✓ Monthly report completed: $output_file"
    
    # Email report if configured
    if [ -n "${MONTHLY_EMAIL_RECIPIENTS:-}" ]; then
        echo "Emailing monthly report..."
        mail -s "Monthly Ticket Analysis Report - $(date -d "$last_month_start" +%B\ %Y)" \
             -a "$output_file" \
             "$MONTHLY_EMAIL_RECIPIENTS" < /dev/null || echo "Email failed"
    fi
else
    echo "✗ Monthly report failed"
fi

echo "=== Monthly Report Completed: $(date) ==="
EOF

    # Log cleanup script
    cat > "$scripts_dir/cleanup-logs.sh" << 'EOF'
#!/bin/bash
# Log cleanup wrapper script

LOG_FILE="$HOME/.ticket-analyzer/logs/cleanup-$(date +%Y%m%d).log"

exec >> "$LOG_FILE" 2>&1

echo "=== Log Cleanup Started: $(date) ==="

# Clean up old log files (keep last 30 days)
find "$HOME/.ticket-analyzer/logs" -name "*.log" -mtime +30 -delete 2>/dev/null || true

# Clean up old reports (keep last 90 days)
find "$HOME/.ticket-analyzer/reports" -name "*.html" -mtime +90 -delete 2>/dev/null || true
find "$HOME/.ticket-analyzer/reports" -name "*.json" -mtime +90 -delete 2>/dev/null || true
find "$HOME/.ticket-analyzer/reports" -name "*.csv" -mtime +90 -delete 2>/dev/null || true

# Clean up empty directories
find "$HOME/.ticket-analyzer/reports" -type d -empty -delete 2>/dev/null || true

echo "=== Log Cleanup Completed: $(date) ==="
EOF

    # Make scripts executable
    chmod +x "$scripts_dir"/*.sh
    
    log_success "Wrapper scripts created in $scripts_dir"
}

install_cron_jobs() {
    log_info "Installing cron jobs..."
    
    # Create wrapper scripts first
    create_wrapper_scripts
    
    local scripts_dir="$HOME/.ticket-analyzer/scripts"
    
    # Get current crontab
    local temp_cron=$(mktemp)
    crontab -l 2>/dev/null | grep -v "$CRON_TAG" > "$temp_cron" || true
    
    # Add new cron jobs
    cat >> "$temp_cron" << EOF

$CRON_TAG - Ticket Analysis Automation
# Daily analysis at 8:00 AM
0 8 * * * $scripts_dir/daily-analysis.sh $CRON_TAG

# Weekly report every Monday at 9:00 AM
0 9 * * 1 $scripts_dir/weekly-report.sh $CRON_TAG

# Monthly report on first day of month at 10:00 AM
0 10 1 * * $scripts_dir/monthly-report.sh $CRON_TAG

# Log cleanup every Sunday at 2:00 AM
0 2 * * 0 $scripts_dir/cleanup-logs.sh $CRON_TAG

EOF

    # Install new crontab
    crontab "$temp_cron"
    rm "$temp_cron"
    
    log_success "Cron jobs installed successfully"
    log_info "Use 'crontab -l' to verify installation"
}

uninstall_cron_jobs() {
    log_info "Removing ticket analyzer cron jobs..."
    
    # Get current crontab without ticket analyzer jobs
    local temp_cron=$(mktemp)
    crontab -l 2>/dev/null | grep -v "$CRON_TAG" > "$temp_cron" || true
    
    # Install cleaned crontab
    crontab "$temp_cron"
    rm "$temp_cron"
    
    log_success "Cron jobs removed successfully"
}

list_cron_jobs() {
    log_info "Current ticket analyzer cron jobs:"
    
    if crontab -l 2>/dev/null | grep -q "$CRON_TAG"; then
        crontab -l 2>/dev/null | grep -A 10 -B 1 "$CRON_TAG"
    else
        log_warning "No ticket analyzer cron jobs found"
    fi
}

test_cron_execution() {
    log_info "Testing cron job execution..."
    
    local scripts_dir="$HOME/.ticket-analyzer/scripts"
    
    if [ ! -d "$scripts_dir" ]; then
        log_error "Wrapper scripts not found. Run --install first."
        return 1
    fi
    
    # Test daily analysis script
    log_info "Testing daily analysis script..."
    if bash -n "$scripts_dir/daily-analysis.sh"; then
        log_success "✓ Daily analysis script syntax OK"
    else
        log_error "✗ Daily analysis script has syntax errors"
    fi
    
    # Test authentication
    log_info "Testing authentication..."
    if mwinit -s &> /dev/null; then
        log_success "✓ Authentication is valid"
    else
        log_warning "⚠ Authentication may be expired"
    fi
    
    # Test ticket-analyzer command
    log_info "Testing ticket-analyzer command..."
    if ticket-analyzer --version &> /dev/null; then
        log_success "✓ ticket-analyzer is available"
    else
        log_error "✗ ticket-analyzer command failed"
    fi
    
    log_info "Test completed"
}

main() {
    case "${1:-}" in
        --install)
            check_dependencies && install_cron_jobs
            ;;
        --uninstall)
            uninstall_cron_jobs
            ;;
        --list)
            list_cron_jobs
            ;;
        --test)
            test_cron_execution
            ;;
        --help)
            show_help
            ;;
        *)
            log_error "Invalid option: ${1:-}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
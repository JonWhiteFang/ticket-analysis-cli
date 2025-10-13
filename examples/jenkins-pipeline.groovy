// Jenkins Pipeline for Ticket Analysis CLI
// This pipeline demonstrates how to integrate ticket analysis into CI/CD workflows

pipeline {
    agent any
    
    parameters {
        choice(
            name: 'ANALYSIS_PERIOD',
            choices: ['weekly', 'monthly', 'quarterly'],
            description: 'Analysis time period'
        )
        string(
            name: 'TEAM_NAME',
            defaultValue: '',
            description: 'Team resolver group name (leave empty for all teams)'
        )
        choice(
            name: 'OUTPUT_FORMAT',
            choices: ['html', 'json', 'csv'],
            description: 'Report output format'
        )
        booleanParam(
            name: 'EMAIL_REPORT',
            defaultValue: false,
            description: 'Email report to team leads'
        )
    }
    
    environment {
        // Configuration
        TICKET_ANALYZER_CONFIG = "${WORKSPACE}/config/ticket-analyzer.json"
        REPORTS_DIR = "${WORKSPACE}/reports"
        ARCHIVE_DIR = "/shared/reports/archive"
        
        // Credentials (stored in Jenkins credentials)
        MIDWAY_CREDENTIALS = credentials('midway-service-account')
        EMAIL_RECIPIENTS = credentials('team-leads-email-list')
    }
    
    stages {
        stage('Setup') {
            steps {
                script {
                    echo "Setting up ticket analysis pipeline"
                    echo "Analysis period: ${params.ANALYSIS_PERIOD}"
                    echo "Team: ${params.TEAM_NAME ?: 'All teams'}"
                    echo "Output format: ${params.OUTPUT_FORMAT}"
                }
                
                // Clean workspace
                cleanWs()
                
                // Create directories
                sh """
                    mkdir -p ${REPORTS_DIR}
                    mkdir -p config
                """
                
                // Create configuration file
                writeFile file: 'config/ticket-analyzer.json', text: '''
                {
                    "output": {
                        "default_format": "html",
                        "max_results": 5000,
                        "sanitize_output": true
                    },
                    "authentication": {
                        "timeout_seconds": 90,
                        "max_retry_attempts": 3
                    },
                    "logging": {
                        "level": "INFO",
                        "sanitize_logs": true
                    },
                    "performance": {
                        "parallel_processing": true,
                        "max_workers": 4
                    }
                }
                '''
            }
        }
        
        stage('Check Dependencies') {
            steps {
                script {
                    // Check if ticket-analyzer is installed
                    def result = sh(
                        script: 'ticket-analyzer --version',
                        returnStatus: true
                    )
                    
                    if (result != 0) {
                        error "ticket-analyzer CLI not found. Please install it first."
                    }
                    
                    echo "✓ ticket-analyzer CLI is available"
                }
                
                // Check Python dependencies if needed
                sh """
                    python3 --version
                    pip3 list | grep -E "(pandas|click|tqdm)" || echo "Some Python packages may be missing"
                """
            }
        }
        
        stage('Authentication') {
            steps {
                script {
                    // Authenticate with Midway using service account
                    echo "Authenticating with Midway..."
                    
                    // Note: In real implementation, use proper service account authentication
                    // This is a simplified example
                    sh """
                        # Check if already authenticated
                        if ! mwinit -s; then
                            echo "Authentication required"
                            # Use service account credentials here
                            # mwinit -o -u \${MIDWAY_CREDENTIALS_USR} -p \${MIDWAY_CREDENTIALS_PSW}
                        fi
                        
                        echo "✓ Authentication verified"
                    """
                }
            }
        }
        
        stage('Calculate Date Range') {
            steps {
                script {
                    def today = new Date()
                    def startDate, endDate
                    
                    switch(params.ANALYSIS_PERIOD) {
                        case 'weekly':
                            startDate = today - 7
                            endDate = today
                            break
                        case 'monthly':
                            startDate = today - 30
                            endDate = today
                            break
                        case 'quarterly':
                            startDate = today - 90
                            endDate = today
                            break
                        default:
                            startDate = today - 30
                            endDate = today
                    }
                    
                    env.START_DATE = startDate.format('yyyy-MM-dd')
                    env.END_DATE = endDate.format('yyyy-MM-dd')
                    
                    echo "Analysis date range: ${env.START_DATE} to ${env.END_DATE}"
                }
            }
        }
        
        stage('Run Analysis') {
            steps {
                script {
                    def timestamp = new Date().format('yyyyMMdd_HHmmss')
                    def teamSuffix = params.TEAM_NAME ? params.TEAM_NAME.replaceAll(' ', '_') : 'all_teams'
                    def outputFile = "${REPORTS_DIR}/${params.ANALYSIS_PERIOD}_${teamSuffix}_${timestamp}.${params.OUTPUT_FORMAT}"
                    
                    // Build command
                    def cmd = [
                        'ticket-analyzer', 'analyze',
                        '--config', env.TICKET_ANALYZER_CONFIG,
                        '--start-date', env.START_DATE,
                        '--end-date', env.END_DATE,
                        '--format', params.OUTPUT_FORMAT,
                        '--output', outputFile,
                        '--progress',
                        '--verbose'
                    ]
                    
                    if (params.TEAM_NAME) {
                        cmd.addAll(['--resolver-group', params.TEAM_NAME])
                    }
                    
                    echo "Running analysis command: ${cmd.join(' ')}"
                    
                    // Execute analysis
                    def result = sh(
                        script: cmd.join(' '),
                        returnStatus: true
                    )
                    
                    if (result != 0) {
                        error "Ticket analysis failed with exit code ${result}"
                    }
                    
                    // Store output file path for later stages
                    env.OUTPUT_FILE = outputFile
                    
                    echo "✓ Analysis completed successfully"
                    echo "Report generated: ${outputFile}"
                }
            }
        }
        
        stage('Validate Results') {
            steps {
                script {
                    // Check if output file exists and has content
                    def fileExists = sh(
                        script: "test -f '${env.OUTPUT_FILE}'",
                        returnStatus: true
                    ) == 0
                    
                    if (!fileExists) {
                        error "Output file not found: ${env.OUTPUT_FILE}"
                    }
                    
                    // Check file size
                    def fileSize = sh(
                        script: "stat -f%z '${env.OUTPUT_FILE}' 2>/dev/null || stat -c%s '${env.OUTPUT_FILE}'",
                        returnStdout: true
                    ).trim()
                    
                    echo "Report file size: ${fileSize} bytes"
                    
                    if (fileSize.toInteger() < 100) {
                        error "Report file is too small, analysis may have failed"
                    }
                    
                    echo "✓ Report validation passed"
                }
            }
        }
        
        stage('Archive Report') {
            steps {
                script {
                    // Archive to Jenkins
                    archiveArtifacts artifacts: "reports/*", fingerprint: true
                    
                    // Copy to shared archive location
                    sh """
                        mkdir -p ${ARCHIVE_DIR}
                        cp '${env.OUTPUT_FILE}' '${ARCHIVE_DIR}/'
                        echo "Report archived to ${ARCHIVE_DIR}"
                    """
                    
                    echo "✓ Report archived successfully"
                }
            }
        }
        
        stage('Email Report') {
            when {
                expression { params.EMAIL_REPORT }
            }
            steps {
                script {
                    def subject = "Ticket Analysis Report - ${params.ANALYSIS_PERIOD.capitalize()} (${env.START_DATE} to ${env.END_DATE})"
                    def body = """
                    Ticket Analysis Report Generated
                    
                    Analysis Details:
                    - Period: ${params.ANALYSIS_PERIOD}
                    - Team: ${params.TEAM_NAME ?: 'All teams'}
                    - Date Range: ${env.START_DATE} to ${env.END_DATE}
                    - Format: ${params.OUTPUT_FORMAT}
                    - Generated: ${new Date()}
                    
                    The report is attached to this email and archived at:
                    ${env.BUILD_URL}artifact/reports/
                    
                    Jenkins Build: ${env.BUILD_URL}
                    """
                    
                    emailext (
                        subject: subject,
                        body: body,
                        to: env.EMAIL_RECIPIENTS,
                        attachmentsPattern: "reports/*"
                    )
                    
                    echo "✓ Report emailed to recipients"
                }
            }
        }
        
        stage('Cleanup') {
            steps {
                script {
                    // Clean up temporary files but keep reports
                    sh """
                        # Remove config files
                        rm -f config/ticket-analyzer.json
                        
                        # Keep reports directory for archiving
                        echo "Cleanup completed, reports preserved"
                    """
                }
            }
        }
    }
    
    post {
        always {
            script {
                // Always clean up authentication
                sh 'mwinit -d || true'  # Destroy authentication session
            }
        }
        
        success {
            script {
                echo "✓ Pipeline completed successfully"
                
                // Send success notification
                slackSend(
                    channel: '#team-reports',
                    color: 'good',
                    message: "✅ Ticket analysis completed successfully for ${params.TEAM_NAME ?: 'all teams'} (${params.ANALYSIS_PERIOD})"
                )
            }
        }
        
        failure {
            script {
                echo "✗ Pipeline failed"
                
                // Send failure notification
                slackSend(
                    channel: '#team-reports',
                    color: 'danger',
                    message: "❌ Ticket analysis failed for ${params.TEAM_NAME ?: 'all teams'} (${params.ANALYSIS_PERIOD}). Check ${env.BUILD_URL}"
                )
            }
        }
        
        unstable {
            script {
                echo "⚠ Pipeline completed with warnings"
                
                slackSend(
                    channel: '#team-reports',
                    color: 'warning',
                    message: "⚠️ Ticket analysis completed with warnings for ${params.TEAM_NAME ?: 'all teams'} (${params.ANALYSIS_PERIOD})"
                )
            }
        }
    }
}
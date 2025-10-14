"""Tests for the analyze CLI command.

This module tests the analyze command functionality including argument parsing,
validation, error handling, and integration with analysis services.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from click.testing import CliRunner

from ticket_analyzer.cli.commands.analyze import analyze_command
from ticket_analyzer.models.ticket import TicketStatus, TicketSeverity
from ticket_analyzer.models.analysis import SearchCriteria
from ticket_analyzer.models.exceptions import (
    AuthenticationError,
    DataRetrievalError,
    TicketAnalysisError
)


class TestAnalyzeCommand:
    """Test cases for analyze command."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_container(self):
        """Mock dependency container with services."""
        with patch('ticket_analyzer.cli.commands.analyze.DependencyContainer') as mock:
            container = Mock()
            
            # Mock analysis service
            analysis_service = Mock()
            analysis_result = Mock()
            analysis_result.ticket_count = 50
            analysis_result.generated_at = datetime.now()
            analysis_result.date_range = (datetime.now() - timedelta(days=7), datetime.now())
            analysis_result.metrics = {
                'status_distribution': {'Open': 30, 'Resolved': 20},
                'avg_resolution_time': 24.5
            }
            analysis_result.summary = {
                'key_insights': ['Tickets are increasing', 'Resolution time improving']
            }
            analysis_service.analyze_tickets.return_value = analysis_result
            container.analysis_service = analysis_service
            
            # Mock output service
            output_service = Mock()
            container.output_service = output_service
            
            mock.return_value = container
            yield container
    
    @pytest.fixture
    def mock_cli_context(self):
        """Mock CLI context."""
        context = Mock()
        context.verbose = False
        context.config_file = None
        context.output_dir = "./reports"
        return context
    
    def test_analyze_help(self, runner):
        """Test analyze command help text."""
        result = runner.invoke(analyze_command, ['--help'])
        
        assert result.exit_code == 0
        assert "Analyze ticket data" in result.output
        assert "--status" in result.output
        assert "--severity" in result.output
        assert "--format" in result.output
        assert "Examples:" in result.output
    
    def test_analyze_basic_command(self, runner, mock_container, mock_cli_context):
        """Test basic analyze command execution."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--status', 'Open',
                '--days-back', '7'
            ])
            
            assert result.exit_code == 0
            assert "Analysis completed" in result.output
            mock_container.analysis_service.analyze_tickets.assert_called_once()
    
    def test_analyze_with_ticket_ids(self, runner, mock_container, mock_cli_context):
        """Test analyze command with specific ticket IDs."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--ticket-ids', 'T123456', 'T789012',
                '--format', 'json'
            ])
            
            assert result.exit_code == 0
            mock_container.analysis_service.analyze_tickets.assert_called_once()
            
            # Verify search criteria includes ticket IDs
            call_args = mock_container.analysis_service.analyze_tickets.call_args
            criteria = call_args[1]['criteria']
            assert criteria.ticket_ids == ['T123456', 'T789012']
    
    def test_analyze_with_status_filter(self, runner, mock_container, mock_cli_context):
        """Test analyze command with status filter."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--status', 'Open', 'In Progress',
                '--format', 'table'
            ])
            
            assert result.exit_code == 0
            
            # Verify search criteria includes status filter
            call_args = mock_container.analysis_service.analyze_tickets.call_args
            criteria = call_args[1]['criteria']
            assert 'Open' in criteria.status
            assert 'In Progress' in criteria.status
    
    def test_analyze_with_severity_filter(self, runner, mock_container, mock_cli_context):
        """Test analyze command with severity filter."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--severity', 'SEV_1', 'SEV_2',
                '--format', 'json'
            ])
            
            assert result.exit_code == 0
            
            # Verify search criteria includes severity filter
            call_args = mock_container.analysis_service.analyze_tickets.call_args
            criteria = call_args[1]['criteria']
            assert 'SEV_1' in criteria.severity
            assert 'SEV_2' in criteria.severity
    
    def test_analyze_with_date_range(self, runner, mock_container, mock_cli_context):
        """Test analyze command with date range."""
        start_date = '2024-01-01'
        end_date = '2024-01-31'
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--start-date', start_date,
                '--end-date', end_date
            ])
            
            assert result.exit_code == 0
            
            # Verify search criteria includes date range
            call_args = mock_container.analysis_service.analyze_tickets.call_args
            criteria = call_args[1]['criteria']
            assert criteria.created_after is not None
            assert criteria.created_before is not None
    
    def test_analyze_with_assignee_filter(self, runner, mock_container, mock_cli_context):
        """Test analyze command with assignee filter."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--assignee', 'user1', 'user2',
                '--format', 'csv'
            ])
            
            assert result.exit_code == 0
            
            # Verify search criteria includes assignee filter
            call_args = mock_container.analysis_service.analyze_tickets.call_args
            criteria = call_args[1]['criteria']
            assert 'user1' in criteria.assignee
            assert 'user2' in criteria.assignee
    
    def test_analyze_with_resolver_group_filter(self, runner, mock_container, mock_cli_context):
        """Test analyze command with resolver group filter."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--resolver-group', 'Team A', 'Team B'
            ])
            
            assert result.exit_code == 0
            
            # Verify search criteria includes resolver group filter
            call_args = mock_container.analysis_service.analyze_tickets.call_args
            criteria = call_args[1]['criteria']
            assert 'Team A' in criteria.resolver_group
            assert 'Team B' in criteria.resolver_group
    
    def test_analyze_with_tags_filter(self, runner, mock_container, mock_cli_context):
        """Test analyze command with tags filter."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--tags', 'urgent', 'bug', 'production'
            ])
            
            assert result.exit_code == 0
            
            # Verify search criteria includes tags filter
            call_args = mock_container.analysis_service.analyze_tickets.call_args
            criteria = call_args[1]['criteria']
            assert 'urgent' in criteria.tags
            assert 'bug' in criteria.tags
            assert 'production' in criteria.tags
    
    def test_analyze_with_search_term(self, runner, mock_container, mock_cli_context):
        """Test analyze command with search term."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--search-term', 'authentication error'
            ])
            
            assert result.exit_code == 0
            
            # Verify search criteria includes search term
            call_args = mock_container.analysis_service.analyze_tickets.call_args
            criteria = call_args[1]['criteria']
            assert criteria.search_term == 'authentication error'
    
    def test_analyze_with_analysis_options(self, runner, mock_container, mock_cli_context):
        """Test analyze command with analysis options."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--priority-analysis',
                '--trend-analysis',
                '--team-performance'
            ])
            
            assert result.exit_code == 0
            
            # Verify analysis options are passed
            call_args = mock_container.analysis_service.analyze_tickets.call_args
            assert call_args[1]['include_priority_analysis'] is True
            assert call_args[1]['include_trend_analysis'] is True
            assert call_args[1]['include_team_performance'] is True
    
    def test_analyze_output_formats(self, runner, mock_container, mock_cli_context):
        """Test analyze command with different output formats."""
        formats = ['table', 'json', 'csv', 'html']
        
        for format_type in formats:
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj = mock_cli_context
                
                result = runner.invoke(analyze_command, [
                    '--format', format_type,
                    '--status', 'Open'
                ])
                
                assert result.exit_code == 0
                
                if format_type == 'table':
                    # Table format should display results directly
                    assert "Analysis completed" in result.output
                else:
                    # File formats should save to file
                    mock_container.output_service.generate_output.assert_called()
    
    def test_analyze_with_output_file(self, runner, mock_container, mock_cli_context, tmp_path):
        """Test analyze command with output file."""
        output_file = tmp_path / "analysis_result.json"
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--format', 'json',
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            
            # Verify output service is called with correct path
            mock_container.output_service.generate_output.assert_called_once()
            call_args = mock_container.output_service.generate_output.call_args
            assert call_args[1]['output_path'] == output_file
    
    def test_analyze_with_charts(self, runner, mock_container, mock_cli_context):
        """Test analyze command with charts enabled."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--format', 'html',
                '--include-charts'
            ])
            
            assert result.exit_code == 0
            
            # Verify charts are included
            call_args = mock_container.output_service.generate_output.call_args
            assert call_args[1]['include_charts'] is True
    
    def test_analyze_verbose_output(self, runner, mock_container, mock_cli_context):
        """Test analyze command with verbose output."""
        mock_cli_context.verbose = True
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(analyze_command, [
                '--status', 'Open'
            ])
            
            assert result.exit_code == 0
            assert "Analysis Configuration:" in result.output
            assert "Format:" in result.output
            assert "Max Results:" in result.output


class TestAnalyzeCommandValidation:
    """Test cases for analyze command validation."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_invalid_ticket_id_format(self, runner):
        """Test validation of invalid ticket ID format."""
        result = runner.invoke(analyze_command, [
            '--ticket-ids', 'INVALID-ID-FORMAT'
        ])
        
        assert result.exit_code != 0
        assert "Invalid ticket ID format" in result.output
    
    def test_invalid_status_value(self, runner):
        """Test validation of invalid status value."""
        result = runner.invoke(analyze_command, [
            '--status', 'InvalidStatus'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output
    
    def test_invalid_severity_value(self, runner):
        """Test validation of invalid severity value."""
        result = runner.invoke(analyze_command, [
            '--severity', 'INVALID_SEV'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output
    
    def test_invalid_date_format(self, runner):
        """Test validation of invalid date format."""
        result = runner.invoke(analyze_command, [
            '--start-date', 'invalid-date-format'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output
    
    def test_invalid_date_range(self, runner):
        """Test validation of invalid date range."""
        with patch('ticket_analyzer.cli.shared.validate_date_range') as mock_validate:
            mock_validate.side_effect = Exception("Start date must be before end date")
            
            result = runner.invoke(analyze_command, [
                '--start-date', '2024-01-31',
                '--end-date', '2024-01-01'
            ])
            
            mock_validate.assert_called_once()
    
    def test_invalid_max_results(self, runner):
        """Test validation of invalid max results."""
        result = runner.invoke(analyze_command, [
            '--max-results', '0'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output
        
        result = runner.invoke(analyze_command, [
            '--max-results', '99999'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output
    
    def test_invalid_timeout(self, runner):
        """Test validation of invalid timeout values."""
        result = runner.invoke(analyze_command, [
            '--timeout', '5'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output
        
        result = runner.invoke(analyze_command, [
            '--timeout', '999'
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.output


class TestAnalyzeCommandErrorHandling:
    """Test cases for analyze command error handling."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_cli_context(self):
        """Mock CLI context."""
        context = Mock()
        context.verbose = False
        context.config_file = None
        context.output_dir = "./reports"
        return context
    
    def test_authentication_error(self, runner, mock_cli_context):
        """Test handling of authentication errors."""
        with patch('ticket_analyzer.cli.commands.analyze.DependencyContainer') as mock_container:
            container = Mock()
            container.analysis_service.analyze_tickets.side_effect = AuthenticationError("Auth failed")
            mock_container.return_value = container
            
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj = mock_cli_context
                
                result = runner.invoke(analyze_command, ['--status', 'Open'])
                
                assert result.exit_code == 1
                assert "Authentication failed" in result.output
    
    def test_data_retrieval_error(self, runner, mock_cli_context):
        """Test handling of data retrieval errors."""
        with patch('ticket_analyzer.cli.commands.analyze.DependencyContainer') as mock_container:
            container = Mock()
            container.analysis_service.analyze_tickets.side_effect = DataRetrievalError("Data error")
            mock_container.return_value = container
            
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj = mock_cli_context
                
                result = runner.invoke(analyze_command, ['--status', 'Open'])
                
                assert result.exit_code == 3
                assert "Data retrieval failed" in result.output
    
    def test_analysis_error(self, runner, mock_cli_context):
        """Test handling of analysis errors."""
        with patch('ticket_analyzer.cli.commands.analyze.DependencyContainer') as mock_container:
            container = Mock()
            container.analysis_service.analyze_tickets.side_effect = TicketAnalysisError("Analysis error")
            mock_container.return_value = container
            
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj = mock_cli_context
                
                result = runner.invoke(analyze_command, ['--status', 'Open'])
                
                assert result.exit_code == 4
                assert "Analysis failed" in result.output
    
    def test_verbose_error_output(self, runner, mock_cli_context):
        """Test verbose error output includes additional information."""
        mock_cli_context.verbose = True
        
        with patch('ticket_analyzer.cli.commands.analyze.DependencyContainer') as mock_container:
            container = Mock()
            container.analysis_service.analyze_tickets.side_effect = AuthenticationError("Auth failed")
            mock_container.return_value = container
            
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj = mock_cli_context
                
                result = runner.invoke(analyze_command, ['--status', 'Open'])
                
                assert result.exit_code == 1
                assert "Try running 'mwinit -o'" in result.output


class TestAnalyzeCommandProgressTracking:
    """Test cases for analyze command progress tracking."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_cli_context(self):
        """Mock CLI context."""
        context = Mock()
        context.verbose = False
        context.config_file = None
        context.output_dir = "./reports"
        return context
    
    def test_progress_bar_display(self, runner, mock_cli_context):
        """Test progress bar is displayed during analysis."""
        with patch('ticket_analyzer.cli.commands.analyze.DependencyContainer') as mock_container:
            container = Mock()
            
            # Mock analysis service with progress callback
            analysis_service = Mock()
            analysis_result = Mock()
            analysis_result.ticket_count = 100
            analysis_result.generated_at = datetime.now()
            analysis_result.date_range = (datetime.now() - timedelta(days=7), datetime.now())
            analysis_result.metrics = {}
            analysis_result.summary = {}
            
            def mock_analyze_tickets(*args, **kwargs):
                # Simulate progress callback
                progress_callback = kwargs.get('progress_callback')
                if progress_callback:
                    for i in range(10):
                        progress_callback(i, 10)
                return analysis_result
            
            analysis_service.analyze_tickets.side_effect = mock_analyze_tickets
            container.analysis_service = analysis_service
            container.output_service = Mock()
            mock_container.return_value = container
            
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj = mock_cli_context
                
                with patch('ticket_analyzer.cli.commands.analyze.tqdm') as mock_tqdm:
                    mock_pbar = Mock()
                    mock_tqdm.return_value.__enter__.return_value = mock_pbar
                    
                    result = runner.invoke(analyze_command, ['--status', 'Open'])
                    
                    assert result.exit_code == 0
                    mock_tqdm.assert_called_once()
    
    def test_progress_without_tqdm(self, runner, mock_cli_context):
        """Test progress handling when tqdm is not available."""
        with patch('ticket_analyzer.cli.commands.analyze.DependencyContainer') as mock_container:
            container = Mock()
            analysis_service = Mock()
            analysis_result = Mock()
            analysis_result.ticket_count = 50
            analysis_result.generated_at = datetime.now()
            analysis_result.date_range = (datetime.now() - timedelta(days=7), datetime.now())
            analysis_result.metrics = {}
            analysis_result.summary = {}
            analysis_service.analyze_tickets.return_value = analysis_result
            container.analysis_service = analysis_service
            container.output_service = Mock()
            mock_container.return_value = container
            
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj = mock_cli_context
                
                # Mock tqdm import error
                with patch('ticket_analyzer.cli.commands.analyze.tqdm', side_effect=ImportError):
                    result = runner.invoke(analyze_command, ['--status', 'Open'])
                    
                    assert result.exit_code == 0
                    # Should still work without progress bar


class TestAnalyzeCommandSearchCriteria:
    """Test cases for search criteria building."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_build_search_criteria_basic(self):
        """Test building basic search criteria."""
        from ticket_analyzer.cli.commands.analyze import _build_search_criteria
        
        criteria = _build_search_criteria(
            ticket_ids=('T123456',),
            status=('Open',),
            severity=('SEV_1',),
            assignee=('user1',),
            resolver_group=('Team A',),
            tags=('urgent',),
            search_term='error',
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            days_back=30,
            date_range=None,
            max_results=100,
            include_resolved=False,
            exclude_automated=True
        )
        
        assert criteria.ticket_ids == ['T123456']
        assert criteria.status == ['Open']
        assert criteria.severity == ['SEV_1']
        assert criteria.assignee == ['user1']
        assert criteria.resolver_group == ['Team A']
        assert criteria.tags == ['urgent']
        assert criteria.search_term == 'error'
        assert criteria.max_results == 100
        assert criteria.exclude_automated is True
    
    def test_build_search_criteria_date_range(self):
        """Test building search criteria with date range."""
        from ticket_analyzer.cli.commands.analyze import _build_search_criteria
        
        criteria = _build_search_criteria(
            ticket_ids=(),
            status=(),
            severity=(),
            assignee=(),
            resolver_group=(),
            tags=(),
            search_term=None,
            start_date=None,
            end_date=None,
            days_back=7,
            date_range=None,
            max_results=1000,
            include_resolved=True,
            exclude_automated=False
        )
        
        # Should calculate date range from days_back
        assert criteria.created_after is not None
        assert criteria.created_before is not None
        assert criteria.created_after < criteria.created_before
    
    def test_predefined_date_ranges(self):
        """Test predefined date range calculations."""
        from ticket_analyzer.cli.commands.analyze import _calculate_predefined_date_range
        
        # Test different predefined ranges
        ranges = ['today', 'yesterday', 'week', 'month', 'quarter']
        
        for range_name in ranges:
            start, end = _calculate_predefined_date_range(range_name)
            assert isinstance(start, datetime)
            assert isinstance(end, datetime)
            assert start < end
    
    def test_invalid_predefined_date_range(self):
        """Test invalid predefined date range raises error."""
        from ticket_analyzer.cli.commands.analyze import _calculate_predefined_date_range
        
        with pytest.raises(ValueError):
            _calculate_predefined_date_range('invalid_range')


class TestAnalyzeCommandSummaryDisplay:
    """Test cases for analysis summary display."""
    
    def test_display_analysis_summary_basic(self):
        """Test basic analysis summary display."""
        from ticket_analyzer.cli.commands.analyze import _display_analysis_summary
        
        analysis_result = Mock()
        analysis_result.ticket_count = 100
        analysis_result.date_range = (datetime(2024, 1, 1), datetime(2024, 1, 31))
        analysis_result.metrics = {
            'status_distribution': {'Open': 60, 'Resolved': 40},
            'avg_resolution_time': 24.5
        }
        analysis_result.summary = {
            'key_insights': ['Tickets increasing', 'Resolution time stable']
        }
        
        with patch('ticket_analyzer.cli.commands.analyze.info_message') as mock_info:
            _display_analysis_summary(analysis_result, verbose=False)
            
            # Should display basic summary information
            mock_info.assert_called()
            call_args = [call[0][0] for call in mock_info.call_args_list]
            
            # Check that summary information is displayed
            summary_text = ' '.join(call_args)
            assert 'Total Tickets: 100' in summary_text
            assert 'Average Resolution Time: 24.5' in summary_text
    
    def test_display_analysis_summary_verbose(self):
        """Test verbose analysis summary display."""
        from ticket_analyzer.cli.commands.analyze import _display_analysis_summary
        
        analysis_result = Mock()
        analysis_result.ticket_count = 50
        analysis_result.date_range = (datetime(2024, 1, 1), datetime(2024, 1, 15))
        analysis_result.metrics = {
            'status_distribution': {'Open': 30, 'Resolved': 20}
        }
        analysis_result.summary = {
            'key_insights': ['Performance improving', 'Volume stable']
        }
        
        with patch('ticket_analyzer.cli.commands.analyze.info_message') as mock_info:
            _display_analysis_summary(analysis_result, verbose=True)
            
            # Should display additional verbose information
            mock_info.assert_called()
            call_args = [call[0][0] for call in mock_info.call_args_list]
            
            # Check that insights are displayed in verbose mode
            summary_text = ' '.join(call_args)
            assert 'Key Insights:' in summary_text
            assert 'Performance improving' in summary_text
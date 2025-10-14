"""Tests for the report CLI command.

This module tests the report command functionality including list, convert,
merge, and clean subcommands with comprehensive validation and error handling.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from click.testing import CliRunner

from ticket_analyzer.cli.commands.report import (
    report_command, list_reports, convert_report, merge_reports, clean_reports
)
from ticket_analyzer.models.exceptions import TicketAnalysisError


class TestReportCommand:
    """Test cases for report command group."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_report_help(self, runner):
        """Test report command help text."""
        result = runner.invoke(report_command, ['--help'])
        
        assert result.exit_code == 0
        assert "Report generation and management commands" in result.output
        assert "list" in result.output
        assert "convert" in result.output
        assert "merge" in result.output
        assert "clean" in result.output
    
    def test_report_no_subcommand(self, runner):
        """Test report command without subcommand shows help."""
        result = runner.invoke(report_command, [])
        
        assert result.exit_code == 0
        assert "Usage:" in result.output


class TestListReportsCommand:
    """Test cases for report list command."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_cli_context(self):
        """Mock CLI context."""
        context = Mock()
        context.output_dir = "./reports"
        return context
    
    @pytest.fixture
    def sample_reports_dir(self, tmp_path):
        """Create sample reports directory with test files."""
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        
        # Create sample report files
        (reports_dir / "analysis_20240101.json").write_text('{"test": "json"}')
        (reports_dir / "summary_20240102.csv").write_text('header1,header2\nvalue1,value2')
        (reports_dir / "detailed_20240103.html").write_text('<html><body>Test</body></html>')
        
        return reports_dir
    
    def test_list_reports_basic(self, runner, mock_cli_context, sample_reports_dir):
        """Test basic report list command."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(list_reports, ['--directory', str(sample_reports_dir)])
            
            assert result.exit_code == 0
            assert "analysis_20240101.json" in result.output
            assert "summary_20240102.csv" in result.output
            assert "detailed_20240103.html" in result.output
    
    def test_list_reports_default_directory(self, runner, mock_cli_context, tmp_path):
        """Test report list with default directory."""
        # Create default reports directory
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        (reports_dir / "test.json").write_text('{}')
        
        mock_cli_context.output_dir = str(reports_dir)
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(list_reports, [])
            
            assert result.exit_code == 0
            assert "test.json" in result.output
    
    def test_list_reports_format_filter(self, runner, mock_cli_context, sample_reports_dir):
        """Test report list with format filter."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            # Filter for JSON files only
            result = runner.invoke(list_reports, [
                '--directory', str(sample_reports_dir),
                '--format-filter', 'json'
            ])
            
            assert result.exit_code == 0
            assert "analysis_20240101.json" in result.output
            assert "summary_20240102.csv" not in result.output
            assert "detailed_20240103.html" not in result.output
    
    def test_list_reports_sort_by_name(self, runner, mock_cli_context, sample_reports_dir):
        """Test report list sorted by name."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(list_reports, [
                '--directory', str(sample_reports_dir),
                '--sort-by', 'name'
            ])
            
            assert result.exit_code == 0
            # Files should be listed in alphabetical order
    
    def test_list_reports_sort_by_size(self, runner, mock_cli_context, sample_reports_dir):
        """Test report list sorted by size."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(list_reports, [
                '--directory', str(sample_reports_dir),
                '--sort-by', 'size'
            ])
            
            assert result.exit_code == 0
            # Files should be listed by size
    
    def test_list_reports_limit(self, runner, mock_cli_context, sample_reports_dir):
        """Test report list with limit."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(list_reports, [
                '--directory', str(sample_reports_dir),
                '--limit', '2'
            ])
            
            assert result.exit_code == 0
            # Should show only 2 files
    
    def test_list_reports_directory_not_exists(self, runner, mock_cli_context):
        """Test report list with non-existent directory."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(list_reports, ['--directory', '/nonexistent'])
            
            assert result.exit_code == 0
            assert "Report directory does not exist" in result.output
    
    def test_list_reports_no_files(self, runner, mock_cli_context, tmp_path):
        """Test report list with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(list_reports, ['--directory', str(empty_dir)])
            
            assert result.exit_code == 0
            assert "No reports found" in result.output


class TestConvertReportCommand:
    """Test cases for report convert command."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_container(self):
        """Mock dependency container."""
        with patch('ticket_analyzer.cli.commands.report.DependencyContainer') as mock:
            container = Mock()
            conversion_service = Mock()
            container.conversion_service = conversion_service
            mock.return_value = container
            yield container
    
    @pytest.fixture
    def mock_cli_context(self):
        """Mock CLI context."""
        context = Mock()
        context.verbose = False
        return context
    
    @pytest.fixture
    def sample_input_file(self, tmp_path):
        """Create sample input file for conversion."""
        input_file = tmp_path / "input.json"
        input_file.write_text('{"test": "data", "tickets": 100}')
        return input_file
    
    def test_convert_report_basic(self, runner, mock_container, mock_cli_context, sample_input_file):
        """Test basic report conversion."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(convert_report, [
                str(sample_input_file),
                '--format', 'html'
            ])
            
            assert result.exit_code == 0
            assert "Report converted successfully" in result.output
            mock_container.conversion_service.convert_report.assert_called_once()
    
    def test_convert_report_with_output(self, runner, mock_container, mock_cli_context, sample_input_file, tmp_path):
        """Test report conversion with specific output file."""
        output_file = tmp_path / "output.html"
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(convert_report, [
                str(sample_input_file),
                '--output', str(output_file),
                '--format', 'html'
            ])
            
            assert result.exit_code == 0
            
            # Verify correct output path
            call_args = mock_container.conversion_service.convert_report.call_args
            assert call_args[1]['output_path'] == output_file
    
    def test_convert_report_with_charts(self, runner, mock_container, mock_cli_context, sample_input_file):
        """Test report conversion with charts."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(convert_report, [
                str(sample_input_file),
                '--format', 'html',
                '--include-charts'
            ])
            
            assert result.exit_code == 0
            
            # Verify charts are included
            call_args = mock_container.conversion_service.convert_report.call_args
            assert call_args[1]['include_charts'] is True
    
    def test_convert_report_with_template(self, runner, mock_container, mock_cli_context, sample_input_file):
        """Test report conversion with custom template."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(convert_report, [
                str(sample_input_file),
                '--format', 'html',
                '--template', 'custom_template.html'
            ])
            
            assert result.exit_code == 0
            
            # Verify template is used
            call_args = mock_container.conversion_service.convert_report.call_args
            assert call_args[1]['template'] == 'custom_template.html'
    
    def test_convert_report_verbose(self, runner, mock_container, mock_cli_context, sample_input_file, tmp_path):
        """Test report conversion with verbose output."""
        mock_cli_context.verbose = True
        output_file = tmp_path / "output.html"
        output_file.write_text('<html></html>')  # Create output file for size check
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            # Mock the conversion to create output file
            def mock_convert(*args, **kwargs):
                output_file.write_text('<html><body>Converted</body></html>')
            
            mock_container.conversion_service.convert_report.side_effect = mock_convert
            
            result = runner.invoke(convert_report, [
                str(sample_input_file),
                '--output', str(output_file),
                '--format', 'html'
            ])
            
            assert result.exit_code == 0
            assert "Converting" in result.output
            assert "Input size:" in result.output
            assert "Output size:" in result.output
    
    def test_convert_report_error_handling(self, runner, mock_container, mock_cli_context, sample_input_file):
        """Test report conversion error handling."""
        mock_container.conversion_service.convert_report.side_effect = Exception("Conversion failed")
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(convert_report, [
                str(sample_input_file),
                '--format', 'html'
            ])
            
            assert result.exit_code == 1
            assert "Conversion failed" in result.output


class TestMergeReportsCommand:
    """Test cases for report merge command."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_container(self):
        """Mock dependency container."""
        with patch('ticket_analyzer.cli.commands.report.DependencyContainer') as mock:
            container = Mock()
            merge_service = Mock()
            container.merge_service = merge_service
            mock.return_value = container
            yield container
    
    @pytest.fixture
    def mock_cli_context(self):
        """Mock CLI context."""
        context = Mock()
        context.verbose = False
        return context
    
    @pytest.fixture
    def sample_input_files(self, tmp_path):
        """Create sample input files for merging."""
        file1 = tmp_path / "report1.json"
        file2 = tmp_path / "report2.json"
        file3 = tmp_path / "report3.json"
        
        file1.write_text('{"tickets": 50, "date": "2024-01-01"}')
        file2.write_text('{"tickets": 75, "date": "2024-01-02"}')
        file3.write_text('{"tickets": 100, "date": "2024-01-03"}')
        
        return [file1, file2, file3]
    
    def test_merge_reports_basic(self, runner, mock_container, mock_cli_context, sample_input_files, tmp_path):
        """Test basic report merging."""
        output_file = tmp_path / "merged.json"
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(merge_reports, [
                str(sample_input_files[0]),
                str(sample_input_files[1]),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "Reports merged successfully" in result.output
            mock_container.merge_service.merge_reports.assert_called_once()
    
    def test_merge_reports_multiple_files(self, runner, mock_container, mock_cli_context, sample_input_files, tmp_path):
        """Test merging multiple report files."""
        output_file = tmp_path / "merged.json"
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(merge_reports, [
                str(sample_input_files[0]),
                str(sample_input_files[1]),
                str(sample_input_files[2]),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            
            # Verify all files are included
            call_args = mock_container.merge_service.merge_reports.call_args
            assert len(call_args[1]['input_paths']) == 3
    
    def test_merge_reports_different_format(self, runner, mock_container, mock_cli_context, sample_input_files, tmp_path):
        """Test merging reports with different output format."""
        output_file = tmp_path / "merged.html"
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(merge_reports, [
                str(sample_input_files[0]),
                str(sample_input_files[1]),
                '--output', str(output_file),
                '--format', 'html'
            ])
            
            assert result.exit_code == 0
            
            # Verify format parameter
            call_args = mock_container.merge_service.merge_reports.call_args
            assert call_args[1]['output_format'] == 'html'
    
    def test_merge_reports_different_strategies(self, runner, mock_container, mock_cli_context, sample_input_files, tmp_path):
        """Test merging reports with different strategies."""
        output_file = tmp_path / "merged.json"
        strategies = ['combine', 'compare', 'aggregate']
        
        for strategy in strategies:
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj = mock_cli_context
                
                result = runner.invoke(merge_reports, [
                    str(sample_input_files[0]),
                    str(sample_input_files[1]),
                    '--output', str(output_file),
                    '--merge-strategy', strategy
                ])
                
                assert result.exit_code == 0
                
                # Verify strategy parameter
                call_args = mock_container.merge_service.merge_reports.call_args
                assert call_args[1]['strategy'] == strategy
    
    def test_merge_reports_insufficient_files(self, runner, mock_container, mock_cli_context, sample_input_files):
        """Test merge reports with insufficient input files."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(merge_reports, [
                str(sample_input_files[0]),
                '--output', 'merged.json'
            ])
            
            assert result.exit_code == 1
            assert "At least 2 input files are required" in result.output
    
    def test_merge_reports_verbose(self, runner, mock_container, mock_cli_context, sample_input_files, tmp_path):
        """Test merge reports with verbose output."""
        mock_cli_context.verbose = True
        output_file = tmp_path / "merged.json"
        output_file.write_text('{}')  # Create output file for size check
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            # Mock the merge to create output file
            def mock_merge(*args, **kwargs):
                output_file.write_text('{"merged": true}')
            
            mock_container.merge_service.merge_reports.side_effect = mock_merge
            
            result = runner.invoke(merge_reports, [
                str(sample_input_files[0]),
                str(sample_input_files[1]),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 0
            assert "Merging" in result.output
            assert "Input:" in result.output
            assert "Merged report size:" in result.output
    
    def test_merge_reports_error_handling(self, runner, mock_container, mock_cli_context, sample_input_files, tmp_path):
        """Test merge reports error handling."""
        mock_container.merge_service.merge_reports.side_effect = Exception("Merge failed")
        output_file = tmp_path / "merged.json"
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(merge_reports, [
                str(sample_input_files[0]),
                str(sample_input_files[1]),
                '--output', str(output_file)
            ])
            
            assert result.exit_code == 1
            assert "Merge failed" in result.output


class TestCleanReportsCommand:
    """Test cases for report clean command."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_cli_context(self):
        """Mock CLI context."""
        context = Mock()
        context.output_dir = "./reports"
        context.verbose = False
        return context
    
    @pytest.fixture
    def sample_reports_with_dates(self, tmp_path):
        """Create sample reports with different modification dates."""
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        
        # Create files with different ages
        now = datetime.now()
        
        # Recent file (1 day old)
        recent_file = reports_dir / "recent.json"
        recent_file.write_text('{}')
        recent_time = (now - timedelta(days=1)).timestamp()
        recent_file.touch(times=(recent_time, recent_time))
        
        # Old file (35 days old)
        old_file = reports_dir / "old.json"
        old_file.write_text('{}')
        old_time = (now - timedelta(days=35)).timestamp()
        old_file.touch(times=(old_time, old_time))
        
        # Very old file (60 days old)
        very_old_file = reports_dir / "very_old.csv"
        very_old_file.write_text('header\nvalue')
        very_old_time = (now - timedelta(days=60)).timestamp()
        very_old_file.touch(times=(very_old_time, very_old_time))
        
        return reports_dir
    
    def test_clean_reports_basic(self, runner, mock_cli_context, sample_reports_with_dates):
        """Test basic report cleaning."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(clean_reports, [
                '--directory', str(sample_reports_with_dates),
                '--older-than', '30',
                '--force'
            ])
            
            assert result.exit_code == 0
            assert "Cleanup completed" in result.output
            
            # Check that old files are deleted
            assert not (sample_reports_with_dates / "old.json").exists()
            assert not (sample_reports_with_dates / "very_old.csv").exists()
            # Recent file should still exist
            assert (sample_reports_with_dates / "recent.json").exists()
    
    def test_clean_reports_default_directory(self, runner, mock_cli_context, sample_reports_with_dates):
        """Test clean reports with default directory."""
        mock_cli_context.output_dir = str(sample_reports_with_dates)
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(clean_reports, [
                '--older-than', '30',
                '--force'
            ])
            
            assert result.exit_code == 0
            assert "Cleanup completed" in result.output
    
    def test_clean_reports_format_filter(self, runner, mock_cli_context, sample_reports_with_dates):
        """Test clean reports with format filter."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(clean_reports, [
                '--directory', str(sample_reports_with_dates),
                '--older-than', '30',
                '--format-filter', 'json',
                '--force'
            ])
            
            assert result.exit_code == 0
            
            # Only JSON files should be deleted
            assert not (sample_reports_with_dates / "old.json").exists()
            # CSV file should still exist (not matching filter)
            assert (sample_reports_with_dates / "very_old.csv").exists()
    
    def test_clean_reports_dry_run(self, runner, mock_cli_context, sample_reports_with_dates):
        """Test clean reports dry run mode."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(clean_reports, [
                '--directory', str(sample_reports_with_dates),
                '--older-than', '30',
                '--dry-run'
            ])
            
            assert result.exit_code == 0
            assert "Dry run - no files were deleted" in result.output
            
            # All files should still exist
            assert (sample_reports_with_dates / "old.json").exists()
            assert (sample_reports_with_dates / "very_old.csv").exists()
    
    def test_clean_reports_confirmation_prompt(self, runner, mock_cli_context, sample_reports_with_dates):
        """Test clean reports confirmation prompt."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            # Test declining confirmation
            result = runner.invoke(clean_reports, [
                '--directory', str(sample_reports_with_dates),
                '--older-than', '30'
            ], input='n\n')
            
            assert result.exit_code == 0
            assert "Cleanup cancelled" in result.output
            
            # Files should still exist
            assert (sample_reports_with_dates / "old.json").exists()
    
    def test_clean_reports_no_old_files(self, runner, mock_cli_context, tmp_path):
        """Test clean reports with no old files."""
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        
        # Create only recent files
        recent_file = reports_dir / "recent.json"
        recent_file.write_text('{}')
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(clean_reports, [
                '--directory', str(reports_dir),
                '--older-than', '30'
            ])
            
            assert result.exit_code == 0
            assert "No files older than 30 days found" in result.output
    
    def test_clean_reports_directory_not_exists(self, runner, mock_cli_context):
        """Test clean reports with non-existent directory."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(clean_reports, ['--directory', '/nonexistent'])
            
            assert result.exit_code == 0
            assert "Report directory does not exist" in result.output
    
    def test_clean_reports_verbose(self, runner, mock_cli_context, sample_reports_with_dates):
        """Test clean reports with verbose output."""
        mock_cli_context.verbose = True
        
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            result = runner.invoke(clean_reports, [
                '--directory', str(sample_reports_with_dates),
                '--older-than', '30',
                '--force'
            ])
            
            assert result.exit_code == 0
            assert "Deleted:" in result.output
    
    def test_clean_reports_partial_failure(self, runner, mock_cli_context, sample_reports_with_dates):
        """Test clean reports with partial deletion failure."""
        with patch('click.get_current_context') as mock_ctx:
            mock_ctx.return_value.obj = mock_cli_context
            
            # Mock file deletion to fail for one file
            original_unlink = Path.unlink
            
            def mock_unlink(self):
                if "old.json" in str(self):
                    raise PermissionError("Permission denied")
                return original_unlink(self)
            
            with patch.object(Path, 'unlink', mock_unlink):
                result = runner.invoke(clean_reports, [
                    '--directory', str(sample_reports_with_dates),
                    '--older-than', '30',
                    '--force'
                ])
                
                assert result.exit_code == 0
                assert "Failed to delete" in result.output
                assert "Cleanup completed" in result.output


class TestReportCommandIntegration:
    """Integration tests for report commands."""
    
    @pytest.fixture
    def runner(self):
        """Click test runner."""
        return CliRunner()
    
    def test_report_workflow_integration(self, runner, tmp_path):
        """Test complete report workflow: list -> convert -> merge -> clean."""
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        
        # Create initial reports
        report1 = reports_dir / "report1.json"
        report2 = reports_dir / "report2.json"
        report1.write_text('{"tickets": 50}')
        report2.write_text('{"tickets": 75}')
        
        with patch('ticket_analyzer.cli.commands.report.DependencyContainer') as mock_container:
            container = Mock()
            
            # Mock services
            conversion_service = Mock()
            merge_service = Mock()
            container.conversion_service = conversion_service
            container.merge_service = merge_service
            
            mock_container.return_value = container
            
            # 1. List reports
            result = runner.invoke(list_reports, ['--directory', str(reports_dir)])
            assert result.exit_code == 0
            assert "report1.json" in result.output
            assert "report2.json" in result.output
            
            # 2. Convert a report
            result = runner.invoke(convert_report, [
                str(report1),
                '--format', 'html'
            ])
            assert result.exit_code == 0
            conversion_service.convert_report.assert_called_once()
            
            # 3. Merge reports
            merged_file = tmp_path / "merged.json"
            result = runner.invoke(merge_reports, [
                str(report1),
                str(report2),
                '--output', str(merged_file)
            ])
            assert result.exit_code == 0
            merge_service.merge_reports.assert_called_once()
            
            # 4. Clean old reports (dry run)
            result = runner.invoke(clean_reports, [
                '--directory', str(reports_dir),
                '--older-than', '1',
                '--dry-run'
            ])
            assert result.exit_code == 0
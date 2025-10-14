"""Tests for CLI signal handling and graceful shutdown.

This module tests the signal handling capabilities including graceful shutdown,
progress interruption, and proper resource cleanup during CLI operations.
"""

import pytest
import signal
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from ticket_analyzer.cli.signals import (
    GracefulShutdown, InterruptibleOperation, ProgressTracker,
    with_graceful_shutdown, create_temp_file_manager, TempFileManager,
    ExitCodes, handle_exit_code
)
from ticket_analyzer.models.exceptions import (
    AuthenticationError, ConfigurationError, DataRetrievalError, AnalysisError
)


class TestGracefulShutdown:
    """Test cases for graceful shutdown handler."""
    
    @pytest.fixture
    def shutdown_handler(self):
        """Create a graceful shutdown handler for testing."""
        with patch('signal.signal'):
            return GracefulShutdown()
    
    def test_graceful_shutdown_initialization(self, shutdown_handler):
        """Test graceful shutdown handler initialization."""
        assert shutdown_handler.shutdown_requested is False
        assert shutdown_handler.cleanup_functions == []
        assert shutdown_handler.temp_files == []
        assert shutdown_handler.active_processes == []
        assert shutdown_handler.progress_bars == []
    
    def test_signal_handler_registration(self):
        """Test signal handlers are registered during initialization."""
        with patch('signal.signal') as mock_signal:
            GracefulShutdown()
            
            # Should register SIGINT handler
            mock_signal.assert_called()
            call_args = [call[0][0] for call in mock_signal.call_args_list]
            assert signal.SIGINT in call_args
    
    def test_register_cleanup_function(self, shutdown_handler):
        """Test registering cleanup functions."""
        cleanup_func = Mock()
        
        shutdown_handler.register_cleanup_function(cleanup_func)
        
        assert cleanup_func in shutdown_handler.cleanup_functions
    
    def test_register_temp_file(self, shutdown_handler, tmp_path):
        """Test registering temporary files."""
        temp_file = tmp_path / "temp.txt"
        temp_file.write_text("test")
        
        shutdown_handler.register_temp_file(temp_file)
        
        assert temp_file in shutdown_handler.temp_files
    
    def test_register_process(self, shutdown_handler):
        """Test registering processes."""
        mock_process = Mock()
        
        shutdown_handler.register_process(mock_process)
        
        assert mock_process in shutdown_handler.active_processes
    
    def test_register_progress_bar(self, shutdown_handler):
        """Test registering progress bars."""
        mock_pbar = Mock()
        
        shutdown_handler.register_progress_bar(mock_pbar)
        
        assert mock_pbar in shutdown_handler.progress_bars
    
    def test_unregister_process(self, shutdown_handler):
        """Test unregistering processes."""
        mock_process = Mock()
        shutdown_handler.register_process(mock_process)
        
        shutdown_handler.unregister_process(mock_process)
        
        assert mock_process not in shutdown_handler.active_processes
    
    def test_unregister_progress_bar(self, shutdown_handler):
        """Test unregistering progress bars."""
        mock_pbar = Mock()
        shutdown_handler.register_progress_bar(mock_pbar)
        
        shutdown_handler.unregister_progress_bar(mock_pbar)
        
        assert mock_pbar not in shutdown_handler.progress_bars
    
    def test_is_shutdown_requested(self, shutdown_handler):
        """Test checking shutdown request status."""
        assert shutdown_handler.is_shutdown_requested() is False
        
        shutdown_handler.shutdown_requested = True
        assert shutdown_handler.is_shutdown_requested() is True
    
    def test_handle_interrupt_first_time(self, shutdown_handler):
        """Test handling first interrupt signal."""
        with patch.object(shutdown_handler, '_initiate_graceful_shutdown') as mock_shutdown:
            with patch('ticket_analyzer.cli.signals.click.echo'):
                shutdown_handler._handle_interrupt(signal.SIGINT, None)
                
                assert shutdown_handler.shutdown_requested is True
                mock_shutdown.assert_called_once()
    
    def test_handle_interrupt_second_time(self, shutdown_handler):
        """Test handling second interrupt signal (force exit)."""
        shutdown_handler.shutdown_requested = True
        
        with patch.object(shutdown_handler, '_force_exit') as mock_force_exit:
            with patch('ticket_analyzer.cli.signals.click.echo'):
                shutdown_handler._handle_interrupt(signal.SIGINT, None)
                
                mock_force_exit.assert_called_once()
    
    def test_handle_termination(self, shutdown_handler):
        """Test handling termination signal."""
        with patch.object(shutdown_handler, '_initiate_graceful_shutdown') as mock_shutdown:
            with patch('ticket_analyzer.cli.signals.click.echo'):
                shutdown_handler._handle_termination(signal.SIGTERM, None)
                
                assert shutdown_handler.shutdown_requested is True
                mock_shutdown.assert_called_once()
    
    def test_stop_progress_bars(self, shutdown_handler):
        """Test stopping progress bars during shutdown."""
        mock_pbar1 = Mock()
        mock_pbar2 = Mock()
        mock_pbar3 = Mock()
        
        # Different types of progress bars
        mock_pbar1.close = Mock()
        mock_pbar2.finish = Mock()
        del mock_pbar3.close  # No close method
        del mock_pbar3.finish  # No finish method
        
        shutdown_handler.progress_bars = [mock_pbar1, mock_pbar2, mock_pbar3]
        
        shutdown_handler._stop_progress_bars()
        
        mock_pbar1.close.assert_called_once()
        mock_pbar2.finish.assert_called_once()
    
    def test_terminate_processes(self, shutdown_handler):
        """Test terminating processes during shutdown."""
        mock_process1 = Mock()
        mock_process2 = Mock()
        
        # Configure process 1 to terminate gracefully
        mock_process1.terminate = Mock()
        mock_process1.wait = Mock()
        
        # Configure process 2 to require force kill
        mock_process2.terminate = Mock()
        mock_process2.wait = Mock(side_effect=Exception("Timeout"))
        mock_process2.kill = Mock()
        
        shutdown_handler.active_processes = [mock_process1, mock_process2]
        
        shutdown_handler._terminate_processes()
        
        mock_process1.terminate.assert_called_once()
        mock_process1.wait.assert_called_once()
        mock_process2.terminate.assert_called_once()
        mock_process2.kill.assert_called_once()
    
    def test_run_cleanup_functions(self, shutdown_handler):
        """Test running cleanup functions during shutdown."""
        cleanup_func1 = Mock()
        cleanup_func2 = Mock()
        cleanup_func3 = Mock(side_effect=Exception("Cleanup error"))
        
        shutdown_handler.cleanup_functions = [cleanup_func1, cleanup_func2, cleanup_func3]
        
        with patch('ticket_analyzer.cli.signals.logger'):
            shutdown_handler._run_cleanup_functions()
            
            cleanup_func1.assert_called_once()
            cleanup_func2.assert_called_once()
            cleanup_func3.assert_called_once()
    
    def test_cleanup_temp_files(self, shutdown_handler, tmp_path):
        """Test cleaning up temporary files during shutdown."""
        temp_file1 = tmp_path / "temp1.txt"
        temp_file2 = tmp_path / "temp2.txt"
        temp_file3 = tmp_path / "nonexistent.txt"
        
        temp_file1.write_text("test1")
        temp_file2.write_text("test2")
        
        shutdown_handler.temp_files = [temp_file1, temp_file2, temp_file3]
        
        with patch('ticket_analyzer.cli.signals.logger'):
            shutdown_handler._cleanup_temp_files()
            
            assert not temp_file1.exists()
            assert not temp_file2.exists()
    
    def test_initiate_graceful_shutdown(self, shutdown_handler):
        """Test initiating graceful shutdown process."""
        with patch.object(shutdown_handler, '_stop_progress_bars') as mock_stop_bars:
            with patch.object(shutdown_handler, '_terminate_processes') as mock_terminate:
                with patch.object(shutdown_handler, '_run_cleanup_functions') as mock_cleanup:
                    with patch.object(shutdown_handler, '_cleanup_temp_files') as mock_temp_cleanup:
                        with patch('ticket_analyzer.cli.signals.click.echo'):
                            with patch('sys.exit') as mock_exit:
                                shutdown_handler._initiate_graceful_shutdown()
                                
                                mock_stop_bars.assert_called_once()
                                mock_terminate.assert_called_once()
                                mock_cleanup.assert_called_once()
                                mock_temp_cleanup.assert_called_once()
                                mock_exit.assert_called_once_with(130)
    
    def test_force_exit(self, shutdown_handler):
        """Test force exit process."""
        with patch('signal.signal') as mock_signal:
            with patch('sys.exit') as mock_exit:
                shutdown_handler._original_handlers = {signal.SIGINT: Mock()}
                
                shutdown_handler._force_exit()
                
                mock_signal.assert_called()
                mock_exit.assert_called_once_with(1)
    
    def test_restore_signal_handlers(self, shutdown_handler):
        """Test restoring original signal handlers."""
        original_handler = Mock()
        shutdown_handler._original_handlers = {signal.SIGINT: original_handler}
        
        with patch('signal.signal') as mock_signal:
            shutdown_handler.restore_signal_handlers()
            
            mock_signal.assert_called_once_with(signal.SIGINT, original_handler)


class TestInterruptibleOperation:
    """Test cases for interruptible operation context manager."""
    
    @pytest.fixture
    def shutdown_handler(self):
        """Create a mock shutdown handler."""
        return Mock()
    
    def test_interruptible_operation_context(self, shutdown_handler):
        """Test interruptible operation context manager."""
        operation = InterruptibleOperation(shutdown_handler, "test_operation")
        
        cleanup_func = Mock()
        
        with operation:
            operation.add_cleanup(cleanup_func)
        
        cleanup_func.assert_called_once()
    
    def test_interruptible_operation_cleanup_error(self, shutdown_handler):
        """Test interruptible operation with cleanup error."""
        operation = InterruptibleOperation(shutdown_handler, "test_operation")
        
        cleanup_func = Mock(side_effect=Exception("Cleanup error"))
        
        with patch('ticket_analyzer.cli.signals.logger'):
            with operation:
                operation.add_cleanup(cleanup_func)
            
            cleanup_func.assert_called_once()
    
    def test_check_interruption_not_requested(self, shutdown_handler):
        """Test checking interruption when not requested."""
        shutdown_handler.is_shutdown_requested.return_value = False
        
        operation = InterruptibleOperation(shutdown_handler, "test_operation")
        
        # Should not raise exception
        operation.check_interruption()
    
    def test_check_interruption_requested(self, shutdown_handler):
        """Test checking interruption when requested."""
        shutdown_handler.is_shutdown_requested.return_value = True
        
        operation = InterruptibleOperation(shutdown_handler, "test_operation")
        
        with pytest.raises(KeyboardInterrupt):
            operation.check_interruption()


class TestProgressTracker:
    """Test cases for progress tracker with interruption support."""
    
    @pytest.fixture
    def shutdown_handler(self):
        """Create a mock shutdown handler."""
        return Mock()
    
    def test_progress_tracker_with_tqdm(self, shutdown_handler):
        """Test progress tracker with tqdm available."""
        with patch('ticket_analyzer.cli.signals.tqdm') as mock_tqdm:
            mock_pbar = Mock()
            mock_tqdm.return_value = mock_pbar
            shutdown_handler.is_shutdown_requested.return_value = False
            
            with ProgressTracker(shutdown_handler, total=10, desc="Testing") as tracker:
                tracker.update(1)
                
                mock_tqdm.assert_called_once_with(total=10, desc="Testing", unit="item")
                mock_pbar.update.assert_called_once_with(1)
                shutdown_handler.register_progress_bar.assert_called_once_with(mock_pbar)
                shutdown_handler.unregister_progress_bar.assert_called_once_with(mock_pbar)
    
    def test_progress_tracker_without_tqdm(self, shutdown_handler):
        """Test progress tracker without tqdm."""
        with patch('ticket_analyzer.cli.signals.tqdm', side_effect=ImportError):
            with patch('ticket_analyzer.cli.signals.click.echo') as mock_echo:
                shutdown_handler.is_shutdown_requested.return_value = False
                
                with ProgressTracker(shutdown_handler, total=10, desc="Testing") as tracker:
                    tracker.update(1)
                    
                    mock_echo.assert_called()
    
    def test_progress_tracker_interruption(self, shutdown_handler):
        """Test progress tracker with interruption."""
        with patch('ticket_analyzer.cli.signals.tqdm', side_effect=ImportError):
            shutdown_handler.is_shutdown_requested.return_value = True
            
            with ProgressTracker(shutdown_handler, desc="Testing") as tracker:
                with pytest.raises(KeyboardInterrupt):
                    tracker.update(1)
    
    def test_progress_tracker_set_description(self, shutdown_handler):
        """Test setting progress tracker description."""
        with patch('ticket_analyzer.cli.signals.tqdm') as mock_tqdm:
            mock_pbar = Mock()
            mock_tqdm.return_value = mock_pbar
            shutdown_handler.is_shutdown_requested.return_value = False
            
            with ProgressTracker(shutdown_handler, desc="Testing") as tracker:
                tracker.set_description("New description")
                
                mock_pbar.set_description.assert_called_once_with("New description")
    
    def test_progress_tracker_without_total(self, shutdown_handler):
        """Test progress tracker without total count."""
        with patch('ticket_analyzer.cli.signals.tqdm', side_effect=ImportError):
            with patch('ticket_analyzer.cli.signals.click.echo') as mock_echo:
                shutdown_handler.is_shutdown_requested.return_value = False
                
                with ProgressTracker(shutdown_handler, desc="Testing") as tracker:
                    tracker.update(1)
                    
                    # Should show current count without percentage
                    call_args = mock_echo.call_args[0][0]
                    assert "Testing: 1" in call_args


class TestGracefulShutdownDecorator:
    """Test cases for graceful shutdown decorator."""
    
    def test_with_graceful_shutdown_success(self):
        """Test graceful shutdown decorator with successful function."""
        @with_graceful_shutdown
        def test_function():
            return "success"
        
        with patch('ticket_analyzer.cli.signals.GracefulShutdown') as mock_shutdown:
            mock_instance = Mock()
            mock_shutdown.return_value = mock_instance
            
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj = Mock()
                
                result = test_function()
                
                assert result == "success"
                mock_instance.restore_signal_handlers.assert_called_once()
    
    def test_with_graceful_shutdown_keyboard_interrupt(self):
        """Test graceful shutdown decorator with keyboard interrupt."""
        @with_graceful_shutdown
        def test_function():
            raise KeyboardInterrupt()
        
        with patch('ticket_analyzer.cli.signals.GracefulShutdown') as mock_shutdown:
            mock_instance = Mock()
            mock_shutdown.return_value = mock_instance
            
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj = Mock()
                
                with patch('ticket_analyzer.cli.signals.click.echo'):
                    with patch('sys.exit') as mock_exit:
                        test_function()
                        
                        mock_exit.assert_called_once_with(130)
                        mock_instance.restore_signal_handlers.assert_called_once()
    
    def test_with_graceful_shutdown_no_context(self):
        """Test graceful shutdown decorator without click context."""
        @with_graceful_shutdown
        def test_function():
            return "success"
        
        with patch('ticket_analyzer.cli.signals.GracefulShutdown') as mock_shutdown:
            mock_instance = Mock()
            mock_shutdown.return_value = mock_instance
            
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value = None
                
                result = test_function()
                
                assert result == "success"
                mock_instance.restore_signal_handlers.assert_called_once()


class TestTempFileManager:
    """Test cases for temporary file manager."""
    
    @pytest.fixture
    def shutdown_handler(self):
        """Create a mock shutdown handler."""
        return Mock()
    
    def test_create_temp_file_manager(self, shutdown_handler):
        """Test creating temporary file manager."""
        manager = create_temp_file_manager(shutdown_handler)
        
        assert isinstance(manager, TempFileManager)
        assert manager.shutdown_handler == shutdown_handler
    
    def test_temp_file_manager_create_file(self, shutdown_handler):
        """Test creating temporary file."""
        manager = TempFileManager(shutdown_handler)
        
        with patch('tempfile.mkstemp') as mock_mkstemp:
            with patch('os.close') as mock_close:
                mock_mkstemp.return_value = (123, '/tmp/test_file.tmp')
                
                temp_file = manager.create_temp_file(suffix='.test', prefix='test_')
                
                assert temp_file == Path('/tmp/test_file.tmp')
                assert temp_file in manager.temp_files
                shutdown_handler.register_temp_file.assert_called_once_with(temp_file)
                mock_close.assert_called_once_with(123)
    
    def test_temp_file_manager_cleanup_file(self, shutdown_handler, tmp_path):
        """Test cleaning up specific temporary file."""
        manager = TempFileManager(shutdown_handler)
        
        temp_file = tmp_path / "temp.txt"
        temp_file.write_text("test")
        manager.temp_files.append(temp_file)
        
        manager.cleanup_file(temp_file)
        
        assert not temp_file.exists()
        assert temp_file not in manager.temp_files
    
    def test_temp_file_manager_cleanup_nonexistent_file(self, shutdown_handler, tmp_path):
        """Test cleaning up non-existent file."""
        manager = TempFileManager(shutdown_handler)
        
        temp_file = tmp_path / "nonexistent.txt"
        manager.temp_files.append(temp_file)
        
        with patch('ticket_analyzer.cli.signals.logger'):
            manager.cleanup_file(temp_file)
            
            assert temp_file not in manager.temp_files
    
    def test_temp_file_manager_cleanup_all(self, shutdown_handler, tmp_path):
        """Test cleaning up all temporary files."""
        manager = TempFileManager(shutdown_handler)
        
        temp_file1 = tmp_path / "temp1.txt"
        temp_file2 = tmp_path / "temp2.txt"
        temp_file1.write_text("test1")
        temp_file2.write_text("test2")
        
        manager.temp_files = [temp_file1, temp_file2]
        
        manager.cleanup_all()
        
        assert not temp_file1.exists()
        assert not temp_file2.exists()
        assert len(manager.temp_files) == 0


class TestExitCodes:
    """Test cases for exit code handling."""
    
    def test_exit_codes_constants(self):
        """Test exit code constants."""
        assert ExitCodes.SUCCESS == 0
        assert ExitCodes.GENERAL_ERROR == 1
        assert ExitCodes.CONFIGURATION_ERROR == 2
        assert ExitCodes.DATA_ERROR == 3
        assert ExitCodes.ANALYSIS_ERROR == 4
        assert ExitCodes.AUTHENTICATION_ERROR == 5
        assert ExitCodes.INTERRUPTED == 130
        assert ExitCodes.TERMINATED == 143
    
    def test_handle_exit_code_keyboard_interrupt(self):
        """Test handling keyboard interrupt exit code."""
        exception = KeyboardInterrupt()
        
        result = handle_exit_code(exception)
        
        assert result == ExitCodes.INTERRUPTED
    
    def test_handle_exit_code_authentication_error(self):
        """Test handling authentication error exit code."""
        exception = AuthenticationError("Auth failed")
        
        result = handle_exit_code(exception)
        
        assert result == ExitCodes.AUTHENTICATION_ERROR
    
    def test_handle_exit_code_configuration_error(self):
        """Test handling configuration error exit code."""
        exception = ConfigurationError("Config error")
        
        result = handle_exit_code(exception)
        
        assert result == ExitCodes.CONFIGURATION_ERROR
    
    def test_handle_exit_code_data_retrieval_error(self):
        """Test handling data retrieval error exit code."""
        exception = DataRetrievalError("Data error")
        
        result = handle_exit_code(exception)
        
        assert result == ExitCodes.DATA_ERROR
    
    def test_handle_exit_code_analysis_error(self):
        """Test handling analysis error exit code."""
        exception = AnalysisError("Analysis error")
        
        result = handle_exit_code(exception)
        
        assert result == ExitCodes.ANALYSIS_ERROR
    
    def test_handle_exit_code_general_error(self):
        """Test handling general error exit code."""
        exception = ValueError("General error")
        
        result = handle_exit_code(exception)
        
        assert result == ExitCodes.GENERAL_ERROR


class TestSignalHandlingIntegration:
    """Integration tests for signal handling."""
    
    def test_signal_handling_workflow(self):
        """Test complete signal handling workflow."""
        with patch('signal.signal') as mock_signal:
            # Create shutdown handler
            shutdown_handler = GracefulShutdown()
            
            # Register resources
            cleanup_func = Mock()
            mock_process = Mock()
            mock_pbar = Mock()
            
            shutdown_handler.register_cleanup_function(cleanup_func)
            shutdown_handler.register_process(mock_process)
            shutdown_handler.register_progress_bar(mock_pbar)
            
            # Simulate interrupt
            with patch.object(shutdown_handler, '_stop_progress_bars') as mock_stop:
                with patch.object(shutdown_handler, '_terminate_processes') as mock_terminate:
                    with patch.object(shutdown_handler, '_run_cleanup_functions') as mock_cleanup:
                        with patch.object(shutdown_handler, '_cleanup_temp_files') as mock_temp:
                            with patch('ticket_analyzer.cli.signals.click.echo'):
                                with patch('sys.exit'):
                                    shutdown_handler._handle_interrupt(signal.SIGINT, None)
                                    
                                    # Should initiate graceful shutdown
                                    assert shutdown_handler.shutdown_requested is True
                                    mock_stop.assert_called_once()
                                    mock_terminate.assert_called_once()
                                    mock_cleanup.assert_called_once()
                                    mock_temp.assert_called_once()
    
    def test_interruptible_operation_with_progress(self):
        """Test interruptible operation with progress tracking."""
        shutdown_handler = Mock()
        shutdown_handler.is_shutdown_requested.return_value = False
        
        with InterruptibleOperation(shutdown_handler, "test") as operation:
            with patch('ticket_analyzer.cli.signals.tqdm', side_effect=ImportError):
                with patch('ticket_analyzer.cli.signals.click.echo'):
                    with ProgressTracker(shutdown_handler, desc="Testing") as tracker:
                        tracker.update(1)
                        operation.check_interruption()
        
        # Should complete without errors
    
    def test_temp_file_cleanup_on_shutdown(self, tmp_path):
        """Test temporary file cleanup during shutdown."""
        with patch('signal.signal'):
            shutdown_handler = GracefulShutdown()
            temp_manager = TempFileManager(shutdown_handler)
            
            # Create temporary files
            temp_file = tmp_path / "temp.txt"
            temp_file.write_text("test")
            temp_manager.temp_files.append(temp_file)
            
            # Simulate shutdown
            with patch('ticket_analyzer.cli.signals.logger'):
                shutdown_handler._cleanup_temp_files()
                
                assert not temp_file.exists()
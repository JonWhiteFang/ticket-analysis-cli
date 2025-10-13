"""Secure file operations for ticket analyzer.

This module provides secure file handling capabilities including:
- Secure temporary file management with proper permissions
- Secure file deletion with data overwriting
- Secure configuration file management
- Path validation and sanitization
"""

from __future__ import annotations
import os
import stat
import tempfile
import shutil
import secrets
import re
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Generator
from contextlib import contextmanager
import logging
import json
import configparser
from dataclasses import dataclass

from .sanitizer import TicketDataSanitizer
from .logging import SecureLogger

logger = SecureLogger(__name__)


@dataclass
class FileSecurityConfig:
    """Configuration for file security settings."""
    temp_dir_permissions: int = 0o700
    temp_file_permissions: int = 0o600
    config_dir_permissions: int = 0o700
    config_file_permissions: int = 0o600
    secure_delete_passes: int = 3
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: List[str] = None
    
    def __post_init__(self) -> None:
        if self.allowed_extensions is None:
            self.allowed_extensions = ['.json', '.ini', '.txt', '.log', '.csv']


class SecureFileManager:
    """Secure file operations manager with comprehensive security measures."""
    
    def __init__(self, 
                 config: Optional[FileSecurityConfig] = None,
                 sanitizer: Optional[TicketDataSanitizer] = None) -> None:
        """Initialize secure file manager."""
        self._config = config or FileSecurityConfig()
        self._sanitizer = sanitizer or TicketDataSanitizer()
        self._temp_files: List[Path] = []
        self._temp_dirs: List[Path] = []
    
    @contextmanager
    def create_secure_temp_file(self, 
                               suffix: str = '.tmp', 
                               prefix: str = 'ticket_data_',
                               text_mode: bool = True) -> Generator[Path, None, None]:
        """Create secure temporary file with restricted permissions."""
        temp_file_path = None
        try:
            # Create temporary file with secure permissions
            fd, temp_path = tempfile.mkstemp(
                suffix=suffix,
                prefix=prefix,
                dir=self._get_secure_temp_dir()
            )
            
            # Set restrictive permissions (owner read/write only)
            os.chmod(temp_path, self._config.temp_file_permissions)
            os.close(fd)  # Close file descriptor, keep path
            
            temp_file_path = Path(temp_path)
            self._temp_files.append(temp_file_path)
            
            logger.debug(f"Created secure temporary file: {temp_file_path}")
            yield temp_file_path
            
        except Exception as e:
            logger.error(f"Failed to create secure temporary file: {e}")
            raise
        finally:
            # Secure cleanup
            if temp_file_path:
                self._secure_delete_file(temp_file_path)
                if temp_file_path in self._temp_files:
                    self._temp_files.remove(temp_file_path)
    
    @contextmanager
    def create_secure_temp_dir(self, 
                              prefix: str = 'ticket_analyzer_') -> Generator[Path, None, None]:
        """Create secure temporary directory with restricted permissions."""
        temp_dir_path = None
        try:
            # Create temporary directory with secure permissions
            temp_dir = tempfile.mkdtemp(
                prefix=prefix,
                dir=self._get_secure_temp_dir()
            )
            
            temp_dir_path = Path(temp_dir)
            os.chmod(temp_dir_path, self._config.temp_dir_permissions)
            self._temp_dirs.append(temp_dir_path)
            
            logger.debug(f"Created secure temporary directory: {temp_dir_path}")
            yield temp_dir_path
            
        except Exception as e:
            logger.error(f"Failed to create secure temporary directory: {e}")
            raise
        finally:
            # Secure cleanup
            if temp_dir_path:
                self._secure_delete_directory(temp_dir_path)
                if temp_dir_path in self._temp_dirs:
                    self._temp_dirs.remove(temp_dir_path)
    
    def write_secure_file(self, 
                         file_path: Union[str, Path], 
                         content: Union[str, bytes],
                         permissions: Optional[int] = None) -> None:
        """Write file with secure permissions and validation."""
        path = Path(file_path)
        
        # Validate file path
        self._validate_file_path(path)
        
        # Validate file size
        if isinstance(content, str):
            content_size = len(content.encode('utf-8'))
        else:
            content_size = len(content)
        
        if content_size > self._config.max_file_size:
            raise ValueError(f"File size {content_size} exceeds maximum {self._config.max_file_size}")
        
        # Ensure parent directory exists with secure permissions
        self._create_secure_directory(path.parent)
        
        # Sanitize content if it's text
        if isinstance(content, str):
            sanitized_content = self._sanitizer.sanitize_log_message(content)
        else:
            sanitized_content = content
        
        try:
            # Write file atomically
            temp_path = path.with_suffix(path.suffix + '.tmp')
            
            mode = 'w' if isinstance(sanitized_content, str) else 'wb'
            with open(temp_path, mode, encoding='utf-8' if isinstance(sanitized_content, str) else None) as f:
                f.write(sanitized_content)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # Set secure permissions
            file_permissions = permissions or self._config.config_file_permissions
            os.chmod(temp_path, file_permissions)
            
            # Atomic move to final location
            temp_path.replace(path)
            
            logger.debug(f"Securely wrote file: {path}")
            
        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                self._secure_delete_file(temp_path)
            logger.error(f"Failed to write secure file {path}: {e}")
            raise
    
    def read_secure_file(self, 
                        file_path: Union[str, Path],
                        validate_permissions: bool = True) -> str:
        """Read file with security checks."""
        path = Path(file_path)
        
        # Validate file path
        self._validate_file_path(path)
        
        # Check if file exists
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        # Check file permissions if requested
        if validate_permissions:
            self._validate_file_permissions(path)
        
        # Check file size
        file_size = path.stat().st_size
        if file_size > self._config.max_file_size:
            raise ValueError(f"File size {file_size} exceeds maximum {self._config.max_file_size}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.debug(f"Securely read file: {path}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to read secure file {path}: {e}")
            raise
    
    def _get_secure_temp_dir(self) -> Optional[str]:
        """Get secure temporary directory."""
        # Try to use user-specific temp directory
        user_temp = Path.home() / ".ticket-analyzer" / "temp"
        try:
            user_temp.mkdir(mode=self._config.temp_dir_permissions, parents=True, exist_ok=True)
            return str(user_temp)
        except Exception:
            # Fall back to system temp
            return None
    
    def _create_secure_directory(self, path: Path) -> None:
        """Create directory with secure permissions."""
        try:
            path.mkdir(mode=self._config.config_dir_permissions, parents=True, exist_ok=True)
            # Ensure permissions are set correctly
            os.chmod(path, self._config.config_dir_permissions)
        except Exception as e:
            logger.error(f"Failed to create secure directory {path}: {e}")
            raise
    
    def _validate_file_path(self, path: Path) -> None:
        """Validate file path for security."""
        # Check for path traversal attempts
        try:
            resolved_path = path.resolve()
        except Exception:
            raise ValueError(f"Invalid file path: {path}")
        
        # Check for dangerous path components
        path_str = str(resolved_path)
        if '..' in path_str or path_str.startswith('/etc') or path_str.startswith('/proc'):
            raise ValueError(f"Potentially dangerous file path: {path}")
        
        # Check file extension if configured
        if self._config.allowed_extensions and path.suffix not in self._config.allowed_extensions:
            raise ValueError(f"File extension {path.suffix} not allowed")
    
    def _validate_file_permissions(self, path: Path) -> None:
        """Validate file permissions for security."""
        try:
            file_stat = path.stat()
            
            # Check if file is world-readable or world-writable
            if file_stat.st_mode & (stat.S_IROTH | stat.S_IWOTH):
                logger.warning(f"File {path} has world permissions")
            
            # Check if file is group-writable (might be acceptable in some cases)
            if file_stat.st_mode & stat.S_IWGRP:
                logger.debug(f"File {path} is group-writable")
                
        except Exception as e:
            logger.warning(f"Could not validate permissions for {path}: {e}")
    
    def _secure_delete_file(self, file_path: Path) -> None:
        """Securely delete file by overwriting before removal."""
        if not file_path.exists():
            return
        
        try:
            # Get file size
            file_size = file_path.stat().st_size
            
            # Overwrite with random data multiple times
            with open(file_path, 'r+b') as f:
                for _ in range(self._config.secure_delete_passes):
                    f.seek(0)
                    f.write(secrets.token_bytes(file_size))
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
            
            # Remove file
            file_path.unlink()
            logger.debug(f"Securely deleted file: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to securely delete {file_path}: {e}")
            # Try regular deletion as fallback
            try:
                file_path.unlink()
            except Exception:
                pass
    
    def _secure_delete_directory(self, dir_path: Path) -> None:
        """Securely delete directory and all contents."""
        if not dir_path.exists():
            return
        
        try:
            # Recursively secure delete all files
            for item in dir_path.rglob('*'):
                if item.is_file():
                    self._secure_delete_file(item)
            
            # Remove directory structure
            shutil.rmtree(dir_path, ignore_errors=True)
            logger.debug(f"Securely deleted directory: {dir_path}")
            
        except Exception as e:
            logger.error(f"Failed to securely delete directory {dir_path}: {e}")
    
    def cleanup_all(self) -> None:
        """Clean up all managed temporary files and directories."""
        for temp_file in self._temp_files.copy():
            self._secure_delete_file(temp_file)
        self._temp_files.clear()
        
        for temp_dir in self._temp_dirs.copy():
            self._secure_delete_directory(temp_dir)
        self._temp_dirs.clear()
        
        logger.debug("Cleaned up all temporary files and directories")


class SecureConfigManager:
    """Secure configuration file management."""
    
    def __init__(self, 
                 config_dir: Optional[Path] = None,
                 file_manager: Optional[SecureFileManager] = None) -> None:
        """Initialize secure configuration manager."""
        self._config_dir = config_dir or Path.home() / ".ticket-analyzer"
        self._file_manager = file_manager or SecureFileManager()
        self._sanitizer = TicketDataSanitizer()
        
        # Ensure config directory exists with secure permissions
        self._file_manager._create_secure_directory(self._config_dir)
    
    def save_json_config(self, 
                        config_name: str, 
                        config_data: Dict[str, Any]) -> None:
        """Save JSON configuration securely."""
        config_file = self._config_dir / f"{config_name}.json"
        
        # Validate config name
        if not re.match(r'^[a-zA-Z0-9_-]+$', config_name):
            raise ValueError("Invalid configuration name")
        
        # Sanitize config data
        sanitized_data = self._sanitize_config_data(config_data)
        
        # Write securely
        content = json.dumps(sanitized_data, indent=2, sort_keys=True)
        self._file_manager.write_secure_file(config_file, content)
        
        logger.info(f"Saved JSON configuration: {config_name}")
    
    def load_json_config(self, config_name: str) -> Dict[str, Any]:
        """Load JSON configuration securely."""
        config_file = self._config_dir / f"{config_name}.json"
        
        if not config_file.exists():
            logger.warning(f"Configuration file not found: {config_name}")
            return {}
        
        try:
            content = self._file_manager.read_secure_file(config_file)
            config_data = json.loads(content)
            
            logger.debug(f"Loaded JSON configuration: {config_name}")
            return config_data
            
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to load JSON configuration {config_name}: {e}")
            return {}
    
    def save_ini_config(self, 
                       config_name: str, 
                       config_data: Dict[str, Dict[str, Any]]) -> None:
        """Save INI configuration securely."""
        config_file = self._config_dir / f"{config_name}.ini"
        
        # Validate config name
        if not re.match(r'^[a-zA-Z0-9_-]+$', config_name):
            raise ValueError("Invalid configuration name")
        
        # Create ConfigParser and populate
        config_parser = configparser.ConfigParser()
        
        for section_name, section_data in config_data.items():
            config_parser.add_section(section_name)
            sanitized_section = self._sanitize_config_data(section_data)
            
            for key, value in sanitized_section.items():
                config_parser.set(section_name, key, str(value))
        
        # Write to string then to file
        import io
        config_string = io.StringIO()
        config_parser.write(config_string)
        content = config_string.getvalue()
        
        self._file_manager.write_secure_file(config_file, content)
        
        logger.info(f"Saved INI configuration: {config_name}")
    
    def load_ini_config(self, config_name: str) -> Dict[str, Dict[str, str]]:
        """Load INI configuration securely."""
        config_file = self._config_dir / f"{config_name}.ini"
        
        if not config_file.exists():
            logger.warning(f"Configuration file not found: {config_name}")
            return {}
        
        try:
            content = self._file_manager.read_secure_file(config_file)
            
            config_parser = configparser.ConfigParser()
            config_parser.read_string(content)
            
            # Convert to dictionary
            config_dict = {}
            for section_name in config_parser.sections():
                config_dict[section_name] = dict(config_parser.items(section_name))
            
            logger.debug(f"Loaded INI configuration: {config_name}")
            return config_dict
            
        except Exception as e:
            logger.error(f"Failed to load INI configuration {config_name}: {e}")
            return {}
    
    def delete_config(self, config_name: str, config_type: str = 'json') -> None:
        """Securely delete configuration file."""
        config_file = self._config_dir / f"{config_name}.{config_type}"
        
        if config_file.exists():
            self._file_manager._secure_delete_file(config_file)
            logger.info(f"Deleted configuration: {config_name}.{config_type}")
        else:
            logger.warning(f"Configuration file not found: {config_name}.{config_type}")
    
    def list_configs(self) -> List[str]:
        """List available configuration files."""
        configs = []
        
        try:
            for config_file in self._config_dir.glob('*.json'):
                configs.append(config_file.stem)
            for config_file in self._config_dir.glob('*.ini'):
                configs.append(config_file.stem)
        except Exception as e:
            logger.error(f"Failed to list configurations: {e}")
        
        return sorted(configs)
    
    def _sanitize_config_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize configuration data."""
        return self._sanitizer.sanitize_ticket_data(data)


class SecureTempFileProcessor:
    """Process sensitive data using secure temporary files."""
    
    def __init__(self, file_manager: Optional[SecureFileManager] = None) -> None:
        """Initialize secure temp file processor."""
        self._file_manager = file_manager or SecureFileManager()
        self._sanitizer = TicketDataSanitizer()
    
    def process_sensitive_data(self, 
                              data: Union[Dict[str, Any], List[Dict[str, Any]]],
                              processor_func: callable) -> Any:
        """Process sensitive data using secure temporary storage."""
        with self._file_manager.create_secure_temp_file(suffix='.json') as temp_file:
            # Sanitize data before writing to temp file
            if isinstance(data, list):
                sanitized_data = [
                    self._sanitizer.sanitize_ticket_data(item) 
                    for item in data
                ]
            else:
                sanitized_data = self._sanitizer.sanitize_ticket_data(data)
            
            # Write sanitized data to secure temp file
            content = json.dumps(sanitized_data, indent=2)
            self._file_manager.write_secure_file(temp_file, content)
            
            # Process data from temp file
            return processor_func(temp_file)
    
    def batch_process_files(self, 
                           file_paths: List[Path],
                           processor_func: callable) -> List[Any]:
        """Batch process multiple files securely."""
        results = []
        
        with self._file_manager.create_secure_temp_dir() as temp_dir:
            for i, file_path in enumerate(file_paths):
                try:
                    # Read and sanitize file content
                    content = self._file_manager.read_secure_file(file_path)
                    sanitized_content = self._sanitizer.sanitize_log_message(content)
                    
                    # Write to secure temp file
                    temp_file = temp_dir / f"processed_{i}.tmp"
                    self._file_manager.write_secure_file(temp_file, sanitized_content)
                    
                    # Process file
                    result = processor_func(temp_file)
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Failed to process file {file_path}: {e}")
                    results.append(None)
        
        return results
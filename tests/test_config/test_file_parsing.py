"""Comprehensive tests for configuration file parsing.

This module contains unit tests for configuration file parsing including
JSON and INI formats, error handling, file precedence, and edge cases
for the FileConfigHandler class.
"""

from __future__ import annotations
import pytest
import json
import configparser
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, mock_open

from ticket_analyzer.config.handlers import FileConfigHandler
from ticket_analyzer.models.exceptions import ConfigurationError


class TestJSONConfigFileParsing:
    """Test cases for JSON configuration file parsing."""
    
    def test_parse_valid_json_config(self, tmp_path: Path) -> None:
        """Test parsing valid JSON configuration file."""
        config_data = {
            "auth": {
                "timeout_seconds": 120,
                "auth_method": "kerberos",
                "max_retry_attempts": 4,
                "auto_refresh": True
            },
            "report": {
                "format": "html",
                "include_charts": False,
                "max_results_display": 250,
                "color_output": True
            },
            "mcp": {
                "server_command": ["python", "mcp_server.py"],
                "connection_timeout": 45,
                "retry_delay": 1.5
            },
            "logging": {
                "level": "DEBUG",
                "sanitize_logs": False
            },
            "debug_mode": True,
            "max_concurrent_requests": 20
        }
        
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data, indent=2))
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        assert result == config_data
    
    def test_parse_json_config_with_comments(self, tmp_path: Path) -> None:
        """Test parsing JSON config (comments not supported in standard JSON)."""
        # Standard JSON doesn't support comments, so this should fail gracefully
        json_with_comments = '''
        {
            // This is a comment - not valid JSON
            "auth": {
                "timeout_seconds": 60 // Another comment
            }
        }
        '''
        
        config_file = tmp_path / "config.json"
        config_file.write_text(json_with_comments)
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        # Should return empty config due to invalid JSON
        assert result == {}
    
    def test_parse_json_config_malformed(self, tmp_path: Path) -> None:
        """Test parsing malformed JSON configuration file."""
        malformed_json_cases = [
            '{ "key": "value" missing_comma "key2": "value2" }',
            '{ "key": "value", }',  # Trailing comma
            '{ "key": value }',  # Unquoted value
            '{ key: "value" }',  # Unquoted key
            '{ "key": "value" "key2": "value2" }',  # Missing comma
            '{ "key": "unclosed string }',
            '{ "key": "value", "nested": { "incomplete": }',
            '[ "array", "instead", "of", "object" ]'  # Array instead of object
        ]
        
        for i, malformed_json in enumerate(malformed_json_cases):
            config_file = tmp_path / f"config_{i}.json"
            config_file.write_text(malformed_json)
            
            handler = FileConfigHandler(tmp_path)
            # Should handle error gracefully and return empty config
            result = handler.load_all()
            assert result == {}
    
    def test_parse_json_config_empty_file(self, tmp_path: Path) -> None:
        """Test parsing empty JSON configuration file."""
        config_file = tmp_path / "config.json"
        config_file.write_text("")
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        # Empty file should result in empty config
        assert result == {}
    
    def test_parse_json_config_null_values(self, tmp_path: Path) -> None:
        """Test parsing JSON config with null values."""
        config_data = {
            "auth": {
                "timeout_seconds": 60,
                "auth_method": None
            },
            "report": {
                "format": "json",
                "output_path": None,
                "template_name": None
            },
            "debug_mode": None
        }
        
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        assert result == config_data
        assert result["auth"]["auth_method"] is None
        assert result["report"]["output_path"] is None
        assert result["debug_mode"] is None
    
    def test_parse_json_config_nested_structures(self, tmp_path: Path) -> None:
        """Test parsing JSON config with deeply nested structures."""
        config_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "deep_value": "found_it",
                            "deep_number": 42,
                            "deep_array": [1, 2, 3],
                            "deep_object": {
                                "nested_key": "nested_value"
                            }
                        }
                    }
                }
            },
            "arrays": {
                "simple_array": ["a", "b", "c"],
                "mixed_array": [1, "two", true, null],
                "nested_arrays": [[1, 2], [3, 4], [5, 6]]
            }
        }
        
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        assert result == config_data
        assert result["level1"]["level2"]["level3"]["level4"]["deep_value"] == "found_it"
        assert result["arrays"]["mixed_array"] == [1, "two", True, None]
    
    def test_parse_json_config_unicode_content(self, tmp_path: Path) -> None:
        """Test parsing JSON config with unicode content."""
        config_data = {
            "unicode_strings": {
                "chinese": "测试配置",
                "emoji": "🎫📊💻",
                "accents": "café résumé naïve",
                "cyrillic": "Конфигурация",
                "arabic": "التكوين"
            },
            "unicode_keys": {
                "测试": "test_value",
                "🔧": "tool_value"
            }
        }
        
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data, ensure_ascii=False, indent=2))
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        assert result == config_data
        assert result["unicode_strings"]["chinese"] == "测试配置"
        assert result["unicode_strings"]["emoji"] == "🎫📊💻"
        assert result["unicode_keys"]["测试"] == "test_value"


class TestINIConfigFileParsing:
    """Test cases for INI configuration file parsing."""
    
    def test_parse_valid_ini_config(self, tmp_path: Path) -> None:
        """Test parsing valid INI configuration file."""
        ini_content = """
[auth]
timeout_seconds = 90
auth_method = midway
max_retry_attempts = 4
auto_refresh = true
require_auth = yes
cache_credentials = false

[report]
format = csv
include_charts = no
max_results_display = 300
color_output = 1
show_progress = 0
verbose = off

[mcp]
connection_timeout = 45
request_timeout = 120
max_retries = 5
retry_delay = 2.5
enable_logging = on

[logging]
level = WARNING
sanitize_logs = true
include_timestamps = yes
backup_count = 3
"""
        
        config_file = tmp_path / "config.ini"
        config_file.write_text(ini_content)
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        # Check converted values
        assert result["auth"]["timeout_seconds"] == 90
        assert result["auth"]["auth_method"] == "midway"
        assert result["auth"]["max_retry_attempts"] == 4
        assert result["auth"]["auto_refresh"] is True
        assert result["auth"]["require_auth"] is True
        assert result["auth"]["cache_credentials"] is False
        
        assert result["report"]["format"] == "csv"
        assert result["report"]["include_charts"] is False
        assert result["report"]["max_results_display"] == 300
        assert result["report"]["color_output"] is True
        assert result["report"]["show_progress"] is False
        assert result["report"]["verbose"] is False
        
        assert result["mcp"]["connection_timeout"] == 45
        assert result["mcp"]["request_timeout"] == 120
        assert result["mcp"]["max_retries"] == 5
        assert result["mcp"]["retry_delay"] == 2.5
        assert result["mcp"]["enable_logging"] is True
        
        assert result["logging"]["level"] == "WARNING"
        assert result["logging"]["sanitize_logs"] is True
        assert result["logging"]["include_timestamps"] is True
        assert result["logging"]["backup_count"] == 3
    
    def test_parse_ini_config_type_conversions(self, tmp_path: Path) -> None:
        """Test INI type conversions for various value types."""
        ini_content = """
[types]
# Boolean values - true variants
bool_true1 = true
bool_true2 = yes
bool_true3 = 1
bool_true4 = on
bool_true5 = TRUE
bool_true6 = YES

# Boolean values - false variants
bool_false1 = false
bool_false2 = no
bool_false3 = 0
bool_false4 = off
bool_false5 = FALSE
bool_false6 = NO

# Integer values
int_positive = 42
int_negative = -10
int_zero = 0
int_large = 999999

# Float values
float_positive = 3.14
float_negative = -2.5
float_zero = 0.0
float_scientific = 1.23e-4

# String values
string_simple = hello_world
string_with_spaces = hello world
string_with_numbers = abc123
string_path = /path/to/file

# List values (comma-separated)
list_simple = item1,item2,item3
list_with_spaces = item1, item2 , item3
list_mixed = text,123,true,false
"""
        
        config_file = tmp_path / "config.ini"
        config_file.write_text(ini_content)
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        types_section = result["types"]
        
        # Test boolean conversions
        assert types_section["bool_true1"] is True
        assert types_section["bool_true2"] is True
        assert types_section["bool_true3"] is True
        assert types_section["bool_true4"] is True
        assert types_section["bool_true5"] is True
        assert types_section["bool_true6"] is True
        
        assert types_section["bool_false1"] is False
        assert types_section["bool_false2"] is False
        assert types_section["bool_false3"] is False
        assert types_section["bool_false4"] is False
        assert types_section["bool_false5"] is False
        assert types_section["bool_false6"] is False
        
        # Test numeric conversions
        assert types_section["int_positive"] == 42
        assert types_section["int_negative"] == -10
        assert types_section["int_zero"] == 0
        assert types_section["int_large"] == 999999
        
        assert types_section["float_positive"] == 3.14
        assert types_section["float_negative"] == -2.5
        assert types_section["float_zero"] == 0.0
        assert types_section["float_scientific"] == 1.23e-4
        
        # Test string values
        assert types_section["string_simple"] == "hello_world"
        assert types_section["string_with_spaces"] == "hello world"
        assert types_section["string_with_numbers"] == "abc123"
        assert types_section["string_path"] == "/path/to/file"
        
        # Test list values
        assert types_section["list_simple"] == ["item1", "item2", "item3"]
        assert types_section["list_with_spaces"] == ["item1", "item2", "item3"]
        assert types_section["list_mixed"] == ["text", "123", "true", "false"]
    
    def test_parse_ini_config_malformed(self, tmp_path: Path) -> None:
        """Test parsing malformed INI configuration file."""
        malformed_ini_cases = [
            # Missing section header
            "key = value\nother_key = other_value",
            
            # Invalid section syntax
            "[section\nkey = value",
            
            # Invalid key-value syntax
            "[section]\nkey value\nother_key = value",
            
            # Duplicate sections (should merge)
            "[section]\nkey1 = value1\n[section]\nkey2 = value2"
        ]
        
        for i, malformed_ini in enumerate(malformed_ini_cases):
            config_file = tmp_path / f"config_{i}.ini"
            config_file.write_text(malformed_ini)
            
            handler = FileConfigHandler(tmp_path)
            
            if i == 3:  # Duplicate sections case - should work (merge)
                result = handler.load_all()
                assert "section" in result
                assert result["section"]["key1"] == "value1"
                assert result["section"]["key2"] == "value2"
            else:
                # Other malformed cases should result in empty config
                result = handler.load_all()
                assert result == {}
    
    def test_parse_ini_config_empty_sections(self, tmp_path: Path) -> None:
        """Test parsing INI config with empty sections."""
        ini_content = """
[empty_section]

[section_with_values]
key1 = value1
key2 = value2

[another_empty_section]

[final_section]
final_key = final_value
"""
        
        config_file = tmp_path / "config.ini"
        config_file.write_text(ini_content)
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        assert "empty_section" in result
        assert result["empty_section"] == {}
        
        assert "section_with_values" in result
        assert result["section_with_values"]["key1"] == "value1"
        assert result["section_with_values"]["key2"] == "value2"
        
        assert "another_empty_section" in result
        assert result["another_empty_section"] == {}
        
        assert "final_section" in result
        assert result["final_section"]["final_key"] == "final_value"
    
    def test_parse_ini_config_special_characters(self, tmp_path: Path) -> None:
        """Test parsing INI config with special characters."""
        ini_content = """
[special_chars]
spaces_in_value = value with spaces
quotes_in_value = value with "quotes" and 'apostrophes'
symbols = !@#$%^&*()_+-=[]{}|;:,.<>?
unicode = café 测试 🎫
path_windows = C:\\Users\\Name\\Documents
path_unix = /home/user/documents
url = https://example.com/path?param=value&other=123
multiline_value = line1
    line2
    line3
"""
        
        config_file = tmp_path / "config.ini"
        config_file.write_text(ini_content)
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        special_section = result["special_chars"]
        
        assert special_section["spaces_in_value"] == "value with spaces"
        assert special_section["quotes_in_value"] == 'value with "quotes" and \'apostrophes\''
        assert special_section["symbols"] == "!@#$%^&*()_+-=[]{}|;:,.<>?"
        assert special_section["unicode"] == "café 测试 🎫"
        assert special_section["path_windows"] == "C:\\Users\\Name\\Documents"
        assert special_section["path_unix"] == "/home/user/documents"
        assert special_section["url"] == "https://example.com/path?param=value&other=123"
    
    def test_parse_ini_config_case_sensitivity(self, tmp_path: Path) -> None:
        """Test INI config case sensitivity handling."""
        ini_content = """
[Section1]
Key1 = Value1
key2 = value2
KEY3 = VALUE3

[section2]
MixedCase = MixedValue
lowercase = lowervalue
UPPERCASE = UPPERVALUE
"""
        
        config_file = tmp_path / "config.ini"
        config_file.write_text(ini_content)
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        # Section names should be preserved as-is
        assert "Section1" in result
        assert "section2" in result
        
        # Key names are typically converted to lowercase by configparser
        section1 = result["Section1"]
        assert "key1" in section1  # Converted to lowercase
        assert "key2" in section1
        assert "key3" in section1  # Converted to lowercase
        
        # Values should be preserved as-is
        assert section1["key1"] == "Value1"
        assert section1["key2"] == "value2"
        assert section1["key3"] == "VALUE3"


class TestConfigFileHandlerIntegration:
    """Integration tests for FileConfigHandler with multiple file types."""
    
    def test_multiple_config_files_precedence(self, tmp_path: Path) -> None:
        """Test precedence when multiple config files exist."""
        # Create config.json (first in precedence)
        json_config = {
            "auth": {"timeout_seconds": 60},
            "report": {"format": "json"},
            "from_json": True
        }
        json_file = tmp_path / "config.json"
        json_file.write_text(json.dumps(json_config))
        
        # Create config.ini (second in precedence)
        ini_content = """
[auth]
timeout_seconds = 120
max_retry_attempts = 5

[report]
format = csv
verbose = true

[from_ini]
value = ini_value
"""
        ini_file = tmp_path / "config.ini"
        ini_file.write_text(ini_content)
        
        # Create .ticket-analyzer.json (third in precedence)
        hidden_json_config = {
            "auth": {"timeout_seconds": 180},
            "report": {"format": "html", "color_output": False},
            "from_hidden_json": True
        }
        hidden_json_file = tmp_path / ".ticket-analyzer.json"
        hidden_json_file.write_text(json.dumps(hidden_json_config))
        
        # Create .ticket-analyzer.ini (fourth in precedence)
        hidden_ini_content = """
[auth]
timeout_seconds = 240

[report]
format = yaml
theme = dark

[from_hidden_ini]
value = hidden_ini_value
"""
        hidden_ini_file = tmp_path / ".ticket-analyzer.ini"
        hidden_ini_file.write_text(hidden_ini_content)
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        # Later files should override earlier ones
        # Final precedence: .ticket-analyzer.ini (last) wins
        assert result["auth"]["timeout_seconds"] == 240  # From hidden INI
        assert result["report"]["format"] == "yaml"  # From hidden INI
        assert result["report"]["theme"] == "dark"  # From hidden INI
        
        # Values from earlier files should be preserved if not overridden
        assert result["auth"]["max_retry_attempts"] == 5  # From INI
        assert result["report"]["verbose"] is True  # From INI
        assert result["report"]["color_output"] is False  # From hidden JSON
        
        # Unique values from each file should be preserved
        assert result["from_json"] is True
        assert result["from_ini"]["value"] == "ini_value"
        assert result["from_hidden_json"] is True
        assert result["from_hidden_ini"]["value"] == "hidden_ini_value"
    
    def test_config_file_not_found_handling(self, tmp_path: Path) -> None:
        """Test handling when config files don't exist."""
        # Empty directory - no config files
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        assert result == {}
    
    def test_config_file_permission_errors(self, tmp_path: Path) -> None:
        """Test handling of file permission errors."""
        # Create a config file
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "value"}')
        
        # Make file unreadable (skip on Windows or if running as root)
        import platform
        import os
        if platform.system() != "Windows" and os.getuid() != 0:
            config_file.chmod(0o000)  # No permissions
            
            handler = FileConfigHandler(tmp_path)
            result = handler.load_all()
            
            # Should handle permission error gracefully
            assert result == {}
            
            # Restore permissions for cleanup
            config_file.chmod(0o644)
        else:
            pytest.skip("Permission test not applicable on Windows or as root")
    
    def test_config_file_encoding_handling(self, tmp_path: Path) -> None:
        """Test handling of different file encodings."""
        # Test UTF-8 encoding (default)
        utf8_config = {"unicode": "测试 🎫 café"}
        utf8_file = tmp_path / "utf8_config.json"
        utf8_file.write_text(json.dumps(utf8_config, ensure_ascii=False), encoding='utf-8')
        
        # Test with different file name to avoid conflicts
        handler = FileConfigHandler(tmp_path)
        handler._config_files = ["utf8_config.json"]
        result = handler.load_all()
        
        assert result["unicode"] == "测试 🎫 café"
    
    def test_config_file_size_limits(self, tmp_path: Path) -> None:
        """Test handling of very large config files."""
        # Create a large config file
        large_config = {
            "large_section": {
                f"key_{i}": f"value_{i}" * 100  # Long values
                for i in range(1000)  # Many keys
            }
        }
        
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(large_config))
        
        handler = FileConfigHandler(tmp_path)
        result = handler.load_all()
        
        # Should handle large files successfully
        assert "large_section" in result
        assert len(result["large_section"]) == 1000
        assert result["large_section"]["key_0"].startswith("value_0")
    
    def test_config_file_concurrent_access(self, tmp_path: Path) -> None:
        """Test handling of concurrent file access."""
        import threading
        import time
        
        config_file = tmp_path / "config.json"
        config_file.write_text('{"test": "value"}')
        
        results = []
        errors = []
        
        def load_config():
            try:
                handler = FileConfigHandler(tmp_path)
                result = handler.load_all()
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads to access the file concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=load_config)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All threads should succeed
        assert len(errors) == 0
        assert len(results) == 10
        assert all(result == {"test": "value"} for result in results)
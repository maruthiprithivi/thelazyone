"""
Security utilities for Claude Code MCP Server.

Provides input validation, rate limiting, and security measures.
"""

import re
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import hashlib
import secrets


class SecurityError(Exception):
    """Security-related exceptions."""
    pass


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10
    window_size: int = 60  # seconds


class RateLimiter:
    """Rate limiting with sliding window."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests: Dict[str, List[float]] = {}
    
    def check_rate_limit(self, identifier: str) -> bool:
        """Check if request is within rate limits."""
        now = time.time()
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Clean old requests
        cutoff = now - self.config.window_size
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > cutoff
        ]
        
        # Check limits
        if len(self.requests[identifier]) >= self.config.requests_per_minute:
            return False
        
        self.requests[identifier].append(now)
        return True
    
    def get_remaining_requests(self, identifier: str) -> int:
        """Get remaining requests for identifier."""
        now = time.time()
        cutoff = now - self.config.window_size
        
        if identifier not in self.requests:
            return self.config.requests_per_minute
        
        recent_requests = [
            req_time for req_time in self.requests[identifier]
            if req_time > cutoff
        ]
        
        return max(0, self.config.requests_per_minute - len(recent_requests))


class InputValidator:
    """Input validation and sanitization."""
    
    # Common patterns
    PATTERNS = {
        'alphanumeric': re.compile(r'^[a-zA-Z0-9_-]+$'),
        'email': re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$'),
        'path': re.compile(r'^[a-zA-Z0-9_\-\./]+$'),
        'command': re.compile(r'^[a-zA-Z0-9\s\-_./]+$'),
        'code_block': re.compile(r'```[a-zA-Z]*\n[\s\S]*?\n```'),
    }
    
    # Blacklisted terms
    BLACKLISTED_COMMANDS = {
        'rm -rf /', 'sudo', 'chmod 777', 'wget', 'curl', 'nc', 'netcat',
        'python -c', 'exec(', 'eval(', 'import os', 'import subprocess'
    }
    
    @classmethod
    def validate_string(cls, value: str, pattern: str, max_length: int = 1000) -> str:
        """Validate string against pattern."""
        if not isinstance(value, str):
            raise SecurityError("Value must be a string")
        
        if len(value) > max_length:
            raise SecurityError(f"String too long (max {max_length} chars)")
        
        if not cls.PATTERNS[pattern].match(value):
            raise SecurityError(f"Invalid string format: {pattern}")
        
        return value
    
    @classmethod
    def sanitize_command(cls, command: str) -> str:
        """Sanitize command input."""
        if not isinstance(command, str):
            raise SecurityError("Command must be a string")
        
        command = command.strip()
        
        # Check for blacklisted commands
        for blacklisted in cls.BLACKLISTED_COMMANDS:
            if blacklisted.lower() in command.lower():
                raise SecurityError(f"Command contains blacklisted term: {blacklisted}")
        
        # Remove potentially dangerous characters
        dangerous_chars = ['&', '|', ';', '$', '`', '>', '<']
        for char in dangerous_chars:
            command = command.replace(char, '')
        
        return command
    
    @classmethod
    def validate_path(cls, path: str, base_path: Optional[str] = None) -> str:
        """Validate file path."""
        if not isinstance(path, str):
            raise SecurityError("Path must be a string")
        
        # Resolve path
        path_obj = Path(path).resolve()
        
        # Check for path traversal
        if '..' in str(path_obj) or path_obj.is_absolute():
            raise SecurityError("Path traversal detected")
        
        # Check against base path if provided
        if base_path:
            base_obj = Path(base_path).resolve()
            try:
                path_obj.relative_to(base_obj)
            except ValueError:
                raise SecurityError("Path outside allowed directory")
        
        return str(path_obj)
    
    @classmethod
    def validate_code_block(cls, code: str) -> str:
        """Validate code block content."""
        if not isinstance(code, str):
            raise SecurityError("Code must be a string")
        
        # Check for dangerous imports
        dangerous_imports = [
            'os', 'subprocess', 'sys', 'socket', 'requests', 'urllib',
            'ftplib', 'smtplib', 'telnetlib', 'pickle', 'marshal'
        ]
        
        for imp in dangerous_imports:
            if f"import {imp}" in code or f"from {imp}" in code:
                # Allow safe usage patterns
                if imp in ['os'] and 'os.path' in code:
                    continue
                if imp in ['sys'] and 'sys.argv' in code:
                    continue
                raise SecurityError(f"Potentially dangerous import: {imp}")
        
        return code.strip()


class SecurityManager:
    """Central security management."""
    
    def __init__(self, rate_limit_config: Optional[RateLimitConfig] = None):
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())
        self.validator = InputValidator()
        self.session_tokens: Dict[str, str] = {}
    
    def generate_session_token(self, session_id: str) -> str:
        """Generate secure session token."""
        token = secrets.token_urlsafe(32)
        self.session_tokens[session_id] = token
        return token
    
    def validate_session_token(self, session_id: str, token: str) -> bool:
        """Validate session token."""
        return self.session_tokens.get(session_id) == token
    
    def validate_mcp_request(self, request: Dict[str, Any], client_id: str) -> bool:
        """Validate MCP request."""
        # Rate limiting
        if not self.rate_limiter.check_rate_limit(client_id):
            raise SecurityError("Rate limit exceeded")
        
        # Validate method
        method = request.get("method")
        if not isinstance(method, str):
            raise SecurityError("Invalid method")
        
        # Validate params
        params = request.get("params", {})
        if not isinstance(params, dict):
            raise SecurityError("Invalid params")
        
        return True
    
    def validate_tool_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool arguments based on tool type."""
        validated = {}
        
        for key, value in arguments.items():
            if key == "path" or key.endswith("_path"):
                validated[key] = self.validator.validate_path(str(value))
            elif key == "command" or key.endswith("_command"):
                validated[key] = self.validator.sanitize_command(str(value))
            elif key == "code" or key.endswith("_code"):
                validated[key] = self.validator.validate_code_block(str(value))
            elif key == "prompt" or key.endswith("_prompt"):
                validated[key] = str(value)[:5000]  # Limit prompt length
            else:
                validated[key] = str(value)[:1000]  # General string limit
        
        return validated
    
    def cleanup_session(self, session_id: str):
        """Clean up session security data."""
        self.session_tokens.pop(session_id, None)
        self.rate_limiter.requests.pop(session_id, None)


# Global security manager instance
security_manager = SecurityManager()
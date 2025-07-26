"""
Configuration Management

Handles server configuration with support for YAML/JSON files and environment variable overrides.
Provides validation and runtime configuration management.
"""

import os
import json
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    MOONSHOT = "moonshot"


@dataclass
class ModelConfig:
    """Configuration for an LLM model"""
    provider: LLMProvider
    api_key: str
    model_name: str
    base_url: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


@dataclass
class DockerConfig:
    """Docker-related configuration"""
    base_image: str = "python:3.11-slim"
    memory_limit: str = "512m"
    cpu_limit: str = "1.0"
    timeout: int = 300
    network_mode: str = "bridge"
    security_opts: List[str] = field(default_factory=lambda: ["no-new-privileges:true"])


@dataclass
class ResearchConfig:
    """Research engine configuration"""
    context7_enabled: bool = True
    web_search_enabled: bool = True
    cache_ttl: int = 3600
    cache_ttl_minutes: int = 60  # Derived from cache_ttl in minutes
    max_results: int = 10
    rate_limit_max_calls: int = 100
    rate_limit_window_seconds: int = 60


@dataclass
class JournalConfig:
    """Journal and logging configuration"""
    journal_path: str = "docs/agentJournal.md"
    master_guide_path: str = "docs/masterGuide.md"
    state_recovery_path: str = "docs/stateRecovery.md"
    log_level: str = "INFO"
    max_entries: int = 10000


@dataclass
class StateConfig:
    """State management configuration"""
    state_directory: str = "state"
    checkpoint_interval: int = 300  # seconds
    auto_checkpoint_interval: int = 300  # seconds
    max_checkpoints: int = 50
    max_checkpoints_per_session: int = 10
    session_timeout: int = 3600  # seconds
    auto_recovery: bool = True
    cleanup_interval: int = 3600  # seconds


@dataclass
class ServerConfig:
    """Main server configuration"""
    llm_providers: List[ModelConfig] = field(default_factory=list)
    docker_settings: DockerConfig = field(default_factory=DockerConfig)
    research_settings: ResearchConfig = field(default_factory=ResearchConfig)
    journal_settings: JournalConfig = field(default_factory=JournalConfig)
    state_settings: StateConfig = field(default_factory=StateConfig)
    spec_directory: str = ".kiro/specs"
    default_model: str = "openai"
    default_llm_provider: str = "openai"
    server_port: int = 8000
    debug: bool = False

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "ServerConfig":
        """Load configuration from YAML or JSON file"""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif config_path.suffix.lower() == '.json':
                data = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")
        
        return cls._from_dict(data)
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load configuration from environment variables"""
        config = cls()
        
        # Override with environment variables
        config._apply_env_overrides()
        
        return config
    
    @classmethod
    def load(cls, config_path: Optional[Union[str, Path]] = None) -> "ServerConfig":
        """
        Load configuration with the following precedence:
        1. Configuration file (if provided)
        2. Environment variables
        3. Default values
        """
        if config_path:
            config = cls.from_file(config_path)
        else:
            config = cls()
        
        # Apply environment variable overrides
        config._apply_env_overrides()
        
        # Validate configuration
        config.validate()
        
        return config
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        # Server settings
        if os.getenv("MCP_SERVER_PORT"):
            self.server_port = int(os.getenv("MCP_SERVER_PORT"))
        
        if os.getenv("MCP_DEBUG"):
            self.debug = os.getenv("MCP_DEBUG").lower() == "true"
        
        if os.getenv("MCP_DEFAULT_MODEL"):
            self.default_model = os.getenv("MCP_DEFAULT_MODEL")
        
        if os.getenv("MCP_DEFAULT_LLM_PROVIDER"):
            self.default_llm_provider = os.getenv("MCP_DEFAULT_LLM_PROVIDER")
        
        if os.getenv("MCP_SPEC_DIRECTORY"):
            self.spec_directory = os.getenv("MCP_SPEC_DIRECTORY")
        
        # LLM provider settings
        self._load_llm_providers_from_env()
        
        # Docker settings
        if os.getenv("MCP_DOCKER_MEMORY_LIMIT"):
            self.docker_settings.memory_limit = os.getenv("MCP_DOCKER_MEMORY_LIMIT")
        
        if os.getenv("MCP_DOCKER_CPU_LIMIT"):
            self.docker_settings.cpu_limit = os.getenv("MCP_DOCKER_CPU_LIMIT")
        
        if os.getenv("MCP_DOCKER_TIMEOUT"):
            self.docker_settings.timeout = int(os.getenv("MCP_DOCKER_TIMEOUT"))
        
        # Journal settings
        if os.getenv("MCP_JOURNAL_PATH"):
            self.journal_settings.journal_path = os.getenv("MCP_JOURNAL_PATH")
        
        if os.getenv("MCP_LOG_LEVEL"):
            self.journal_settings.log_level = os.getenv("MCP_LOG_LEVEL")
        
        # State settings
        if os.getenv("MCP_STATE_DIRECTORY"):
            self.state_settings.state_directory = os.getenv("MCP_STATE_DIRECTORY")
        
        if os.getenv("MCP_AUTO_RECOVERY"):
            self.state_settings.auto_recovery = os.getenv("MCP_AUTO_RECOVERY").lower() == "true"
    
    def _load_llm_providers_from_env(self):
        """Load LLM provider configurations from environment variables"""
        # OpenAI configuration
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            openai_config = ModelConfig(
                provider=LLMProvider.OPENAI,
                api_key=openai_key,
                model_name=os.getenv("OPENAI_MODEL", "gpt-4"),
                base_url=os.getenv("OPENAI_BASE_URL"),
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
                temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
            )
            self.llm_providers.append(openai_config)
        
        # MoonShot configuration
        moonshot_key = os.getenv("MOONSHOT_API_KEY")
        if moonshot_key:
            moonshot_config = ModelConfig(
                provider=LLMProvider.MOONSHOT,
                api_key=moonshot_key,
                model_name=os.getenv("MOONSHOT_MODEL", "moonshot-v1-8k"),
                base_url=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1"),
                max_tokens=int(os.getenv("MOONSHOT_MAX_TOKENS", "8000")),
                temperature=float(os.getenv("MOONSHOT_TEMPERATURE", "0.1"))
            )
            self.llm_providers.append(moonshot_config)
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "ServerConfig":
        """Create configuration from dictionary"""
        config = cls()
        
        # Parse LLM providers
        if "llm_providers" in data:
            config.llm_providers = []
            for provider_data in data["llm_providers"]:
                provider_config = ModelConfig(
                    provider=LLMProvider(provider_data["provider"]),
                    api_key=provider_data["api_key"],
                    model_name=provider_data["model_name"],
                    base_url=provider_data.get("base_url"),
                    max_tokens=provider_data.get("max_tokens"),
                    temperature=provider_data.get("temperature")
                )
                config.llm_providers.append(provider_config)
        
        # Parse Docker settings
        if "docker_settings" in data:
            docker_data = data["docker_settings"]
            config.docker_settings = DockerConfig(
                base_image=docker_data.get("base_image", "python:3.11-slim"),
                memory_limit=docker_data.get("memory_limit", "512m"),
                cpu_limit=docker_data.get("cpu_limit", "1.0"),
                timeout=docker_data.get("timeout", 300),
                network_mode=docker_data.get("network_mode", "bridge"),
                security_opts=docker_data.get("security_opts", ["no-new-privileges:true"])
            )
        
        # Parse other settings
        for key, value in data.items():
            if hasattr(config, key) and key not in ["llm_providers", "docker_settings", "research_settings", "journal_settings", "state_settings"]:
                setattr(config, key, value)
        
        return config
    
    def validate(self):
        """Validate configuration"""
        if not self.llm_providers:
            raise ValueError("At least one LLM provider must be configured")
        
        # Validate default model exists
        provider_names = [p.provider.value for p in self.llm_providers]
        if self.default_model not in provider_names:
            raise ValueError(f"Default model '{self.default_model}' not found in configured providers")
        
        # Validate default LLM provider exists
        if self.default_llm_provider not in provider_names:
            raise ValueError(f"Default LLM provider '{self.default_llm_provider}' not found in configured providers")
        
        # Validate paths
        spec_path = Path(self.spec_directory)
        if not spec_path.exists():
            spec_path.mkdir(parents=True, exist_ok=True)
        
        state_path = Path(self.state_settings.state_directory)
        if not state_path.exists():
            state_path.mkdir(parents=True, exist_ok=True)
        
        # Validate journal paths
        journal_path = Path(self.journal_settings.journal_path).parent
        if not journal_path.exists():
            journal_path.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "llm_providers": [
                {
                    "provider": p.provider.value,
                    "api_key": p.api_key,
                    "model_name": p.model_name,
                    "base_url": p.base_url,
                    "max_tokens": p.max_tokens,
                    "temperature": p.temperature
                }
                for p in self.llm_providers
            ],
            "docker_settings": {
                "base_image": self.docker_settings.base_image,
                "memory_limit": self.docker_settings.memory_limit,
                "cpu_limit": self.docker_settings.cpu_limit,
                "timeout": self.docker_settings.timeout,
                "network_mode": self.docker_settings.network_mode,
                "security_opts": self.docker_settings.security_opts
            },
            "research_settings": {
                "context7_enabled": self.research_settings.context7_enabled,
                "web_search_enabled": self.research_settings.web_search_enabled,
                "cache_ttl": self.research_settings.cache_ttl,
                "max_results": self.research_settings.max_results
            },
            "journal_settings": {
                "journal_path": self.journal_settings.journal_path,
                "master_guide_path": self.journal_settings.master_guide_path,
                "state_recovery_path": self.journal_settings.state_recovery_path,
                "log_level": self.journal_settings.log_level,
                "max_entries": self.journal_settings.max_entries
            },
            "state_settings": {
                "state_directory": self.state_settings.state_directory,
                "checkpoint_interval": self.state_settings.checkpoint_interval,
                "max_checkpoints": self.state_settings.max_checkpoints,
                "session_timeout": self.state_settings.session_timeout,
                "auto_recovery": self.state_settings.auto_recovery
            },
            "spec_directory": self.spec_directory,
            "default_model": self.default_model,
            "default_llm_provider": self.default_llm_provider,
            "server_port": self.server_port,
            "debug": self.debug
        }
    
    def save(self, config_path: Union[str, Path], format: str = "yaml"):
        """Save configuration to file"""
        config_path = Path(config_path)
        data = self.to_dict()
        
        with open(config_path, 'w') as f:
            if format.lower() in ['yaml', 'yml']:
                yaml.dump(data, f, default_flow_style=False, indent=2)
            elif format.lower() == 'json':
                json.dump(data, f, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format}")


def load_config(config_path: Optional[Union[str, Path]] = None) -> ServerConfig:
    """Convenience function to load configuration"""
    return ServerConfig.load(config_path)
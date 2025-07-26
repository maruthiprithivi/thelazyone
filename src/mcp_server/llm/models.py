"""
Additional LLM Model Classes

Provides extended model definitions and data structures for LLM interactions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import datetime


class MessageRole(Enum):
    """Message roles in conversation"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ResponseType(Enum):
    """Types of LLM responses"""
    TEXT = "text"
    STREAM = "stream"
    TOOL_CALL = "tool_call"
    ERROR = "error"


@dataclass
class Message:
    """Represents a message in conversation history"""
    role: MessageRole
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format"""
        return {
            "role": self.role.value,
            "content": self.content,
            "metadata": self.metadata or {},
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class LLMRequest:
    """Request structure for LLM interactions"""
    messages: List[Message]
    model: str
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def add_message(self, role: MessageRole, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to the conversation"""
        self.messages.append(Message(role=role, content=content, metadata=metadata))


@dataclass
class LLMResponse:
    """Response structure from LLM providers"""
    content: str
    model: str
    usage: Dict[str, int]
    response_type: ResponseType = ResponseType.TEXT
    metadata: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    
    @property
    def prompt_tokens(self) -> int:
        """Get prompt tokens from usage"""
        return self.usage.get("prompt_tokens", 0)
    
    @property
    def completion_tokens(self) -> int:
        """Get completion tokens from usage"""
        return self.usage.get("completion_tokens", 0)
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens from usage"""
        return self.usage.get("total_tokens", 0)


@dataclass
class StreamChunk:
    """Represents a chunk in streaming response"""
    content: str
    is_final: bool = False
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProviderConfig:
    """Extended provider configuration with additional settings"""
    name: str
    api_key: str
    base_url: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit: Optional[int] = None
    rate_limit_period: int = 60  # seconds
    default_model: str = ""
    supported_models: List[str] = field(default_factory=list)
    additional_headers: Dict[str, str] = field(default_factory=dict)
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        headers.update(self.additional_headers)
        return headers


@dataclass
class RoutingRule:
    """Rule for routing requests between providers"""
    provider: str
    priority: int
    condition: Optional[str] = None  # Optional condition expression
    fallback_providers: List[str] = field(default_factory=list)
    weight: float = 1.0  # For load balancing


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    retry_on: List[str] = field(default_factory=lambda: ["rate_limit", "server_error", "timeout"])
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        delay = min(
            self.base_delay * (self.backoff_factor ** attempt),
            self.max_delay
        )
        return delay


@dataclass
class RateLimitInfo:
    """Rate limit information"""
    requests_remaining: int
    requests_limit: int
    reset_time: datetime.datetime
    retry_after: Optional[float] = None
    
    @property
    def is_rate_limited(self) -> bool:
        """Check if rate limit has been reached"""
        return self.requests_remaining <= 0
    
    @property
    def reset_seconds(self) -> float:
        """Get seconds until rate limit resets"""
        now = datetime.datetime.now()
        if self.reset_time > now:
            return (self.reset_time - now).total_seconds()
        return 0.0


@dataclass
class LLMError:
    """Error information for LLM operations"""
    error_type: str
    message: str
    provider: str
    model: str
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    details: Optional[Dict[str, Any]] = None
    retryable: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "provider": self.provider,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details or {},
            "retryable": self.retryable
        }


@dataclass
class ConversationContext:
    """Context for maintaining conversation state"""
    session_id: str
    provider: str
    model: str
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    last_activity: datetime.datetime = field(default_factory=datetime.datetime.now)
    
    def add_message(self, message: Message):
        """Add message and update last activity"""
        self.messages.append(message)
        self.last_activity = datetime.datetime.now()
    
    def get_recent_messages(self, count: int = 10) -> List[Message]:
        """Get recent messages from conversation"""
        return self.messages[-count:] if len(self.messages) > count else self.messages
    
    def clear_messages(self):
        """Clear all messages"""
        self.messages.clear()


@dataclass
class CodeGenerationRequest:
    """Request structure for code generation tasks"""
    prompt: str
    language: str = "python"
    context: Optional[str] = None
    requirements: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    style_guide: Optional[str] = None
    
    def to_llm_request(self, model: str) -> LLMRequest:
        """Convert to generic LLM request"""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt()
        
        return LLMRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content=system_prompt),
                Message(role=MessageRole.USER, content=user_prompt)
            ],
            model=model
        )
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for code generation"""
        prompt_parts = [
            "You are an expert code generator. Generate high-quality, production-ready code.",
            f"Language: {self.language}",
            "Follow best practices and write clean, maintainable code.",
            "Include appropriate comments and documentation."
        ]
        
        if self.style_guide:
            prompt_parts.append(f"Follow this style guide: {self.style_guide}")
        
        return "\n".join(prompt_parts)
    
    def _build_user_prompt(self) -> str:
        """Build user prompt for code generation"""
        prompt_parts = [f"Generate code for: {self.prompt}"]
        
        if self.context:
            prompt_parts.append(f"Context: {self.context}")
        
        if self.requirements:
            prompt_parts.append(f"Requirements: {', '.join(self.requirements)}")
        
        if self.constraints:
            prompt_parts.append(f"Constraints: {', '.join(self.constraints)}")
        
        if self.examples:
            prompt_parts.append(f"Examples: {'; '.join(self.examples)}")
        
        return "\n".join(prompt_parts)


@dataclass
class CodeAnalysisRequest:
    """Request structure for code analysis tasks"""
    code: str
    language: str = "python"
    analysis_type: str = "general"  # general, security, performance, style, bugs
    context: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    
    def to_llm_request(self, model: str) -> LLMRequest:
        """Convert to generic LLM request"""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt()
        
        return LLMRequest(
            messages=[
                Message(role=MessageRole.SYSTEM, content=system_prompt),
                Message(role=MessageRole.USER, content=user_prompt)
            ],
            model=model
        )
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for code analysis"""
        return f"""You are an expert code analyst. Perform a thorough {self.analysis_type} analysis of the provided code.
Focus on identifying issues, suggesting improvements, and providing actionable recommendations.
Be specific and provide concrete examples where possible."""
    
    def _build_user_prompt(self) -> str:
        """Build user prompt for code analysis"""
        prompt_parts = [
            f"Analyze the following {self.language} code for {self.analysis_type}:",
            f"```\n{self.code}\n```"
        ]
        
        if self.context:
            prompt_parts.append(f"Context: {self.context}")
        
        if self.focus_areas:
            prompt_parts.append(f"Focus areas: {', '.join(self.focus_areas)}")
        
        return "\n".join(prompt_parts)
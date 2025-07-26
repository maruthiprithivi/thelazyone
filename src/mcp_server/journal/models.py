"""
Journal Models

Data models for structured journaling and logging in the MCP server.
Provides comprehensive data structures for tracking all server activities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import uuid
import hashlib
import json


class LogLevel(Enum):
    """Standard log levels for journal entries"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EntryType(Enum):
    """Types of journal entries"""
    SYSTEM = "system"
    LLM = "llm"
    DOCKER = "docker"
    RESEARCH = "research"
    STATE = "state"
    CONVERSATION = "conversation"
    ERROR = "error"
    METRIC = "metric"
    USER_ACTION = "user_action"
    API_CALL = "api_call"
    OPERATION = "operation"


class EntryStatus(Enum):
    """Status of journal entries"""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JournalMetadata:
    """Metadata for journal entries"""
    session_id: str
    component: str
    operation: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMInteraction:
    """Details about LLM interactions"""
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    response: Optional[str] = None
    error: Optional[str] = None


@dataclass
class DockerOperation:
    """Details about Docker operations"""
    container_id: Optional[str] = None
    image: Optional[str] = None
    command: Optional[str] = None
    working_dir: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    volumes: List[str] = field(default_factory=list)
    ports: Dict[str, str] = field(default_factory=dict)
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class ResearchContext:
    """Details about research operations"""
    query: Optional[str] = None
    search_engine: Optional[str] = None
    context7_queries: List[str] = field(default_factory=list)
    web_queries: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    results_count: int = 0
    processing_time_ms: Optional[int] = None
    cache_hit: bool = False


@dataclass
class StateTransition:
    """Details about state changes"""
    from_state: Optional[str] = None
    to_state: str = ""
    checkpoint_id: Optional[str] = None
    recovery_point: Optional[str] = None
    session_data: Dict[str, Any] = field(default_factory=dict)
    changed_keys: List[str] = field(default_factory=list)


@dataclass
class ConversationMessage:
    """Details about conversation messages"""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    message_id: str = ""
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JournalEntry:
    """Main journal entry class"""
    id: str
    timestamp: datetime
    level: LogLevel
    entry_type: EntryType
    status: EntryStatus
    title: str
    message: str
    metadata: JournalMetadata
    
    # Specific data based on entry type
    llm_interaction: Optional[LLMInteraction] = None
    docker_operation: Optional[DockerOperation] = None
    research_context: Optional[ResearchContext] = None
    state_transition: Optional[StateTransition] = None
    conversation_message: Optional[ConversationMessage] = None
    
    # Generic data storage
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Cross-referencing
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)
    related_ids: List[str] = field(default_factory=list)
    
    # Error handling
    error_details: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # File attachments
    attachments: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize computed fields"""
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
    
    @property
    def hash(self) -> str:
        """Generate a unique hash for this entry"""
        content = f"{self.id}{self.timestamp.isoformat()}{self.title}{self.message}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds"""
        return (datetime.now() - self.timestamp).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "entry_type": self.entry_type.value,
            "status": self.status.value,
            "title": self.title,
            "message": self.message,
            "metadata": {
                "session_id": self.metadata.session_id,
                "component": self.metadata.component,
                "operation": self.metadata.operation,
                "user_id": self.metadata.user_id,
                "request_id": self.metadata.request_id,
                "tags": self.metadata.tags,
                "references": self.metadata.references,
                "custom_fields": self.metadata.custom_fields
            },
            "llm_interaction": self._llm_to_dict() if self.llm_interaction else None,
            "docker_operation": self._docker_to_dict() if self.docker_operation else None,
            "research_context": self._research_to_dict() if self.research_context else None,
            "state_transition": self._state_to_dict() if self.state_transition else None,
            "conversation_message": self._conversation_to_dict() if self.conversation_message else None,
            "data": self.data,
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
            "related_ids": self.related_ids,
            "error_details": self.error_details,
            "stack_trace": self.stack_trace,
            "attachments": self.attachments,
            "hash": self.hash
        }
    
    def _llm_to_dict(self) -> Dict[str, Any]:
        """Convert LLM interaction to dictionary"""
        if not self.llm_interaction:
            return None
        return {
            "provider": self.llm_interaction.provider,
            "model": self.llm_interaction.model,
            "prompt_tokens": self.llm_interaction.prompt_tokens,
            "completion_tokens": self.llm_interaction.completion_tokens,
            "total_tokens": self.llm_interaction.total_tokens,
            "cost": self.llm_interaction.cost,
            "temperature": self.llm_interaction.temperature,
            "max_tokens": self.llm_interaction.max_tokens,
            "system_prompt": self.llm_interaction.system_prompt,
            "user_prompt": self.llm_interaction.user_prompt,
            "response": self.llm_interaction.response,
            "error": self.llm_interaction.error
        }
    
    def _docker_to_dict(self) -> Dict[str, Any]:
        """Convert Docker operation to dictionary"""
        if not self.docker_operation:
            return None
        return {
            "container_id": self.docker_operation.container_id,
            "image": self.docker_operation.image,
            "command": self.docker_operation.command,
            "working_dir": self.docker_operation.working_dir,
            "environment": self.docker_operation.environment,
            "volumes": self.docker_operation.volumes,
            "ports": self.docker_operation.ports,
            "exit_code": self.docker_operation.exit_code,
            "stdout": self.docker_operation.stdout,
            "stderr": self.docker_operation.stderr,
            "duration_ms": self.docker_operation.duration_ms
        }
    
    def _research_to_dict(self) -> Dict[str, Any]:
        """Convert research context to dictionary"""
        if not self.research_context:
            return None
        return {
            "query": self.research_context.query,
            "search_engine": self.research_context.search_engine,
            "context7_queries": self.research_context.context7_queries,
            "web_queries": self.research_context.web_queries,
            "sources": self.research_context.sources,
            "results_count": self.research_context.results_count,
            "processing_time_ms": self.research_context.processing_time_ms,
            "cache_hit": self.research_context.cache_hit
        }
    
    def _state_to_dict(self) -> Dict[str, Any]:
        """Convert state transition to dictionary"""
        if not self.state_transition:
            return None
        return {
            "from_state": self.state_transition.from_state,
            "to_state": self.state_transition.to_state,
            "checkpoint_id": self.state_transition.checkpoint_id,
            "recovery_point": self.state_transition.recovery_point,
            "session_data": self.state_transition.session_data,
            "changed_keys": self.state_transition.changed_keys
        }
    
    def _conversation_to_dict(self) -> Dict[str, Any]:
        """Convert conversation message to dictionary"""
        if not self.conversation_message:
            return None
        return {
            "role": self.conversation_message.role,
            "content": self.conversation_message.content,
            "timestamp": self.conversation_message.timestamp.isoformat(),
            "message_id": self.conversation_message.message_id,
            "parent_id": self.conversation_message.parent_id,
            "metadata": self.conversation_message.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JournalEntry":
        """Create entry from dictionary"""
        # Parse metadata
        metadata_data = data.get("metadata", {})
        metadata = JournalMetadata(
            session_id=metadata_data.get("session_id", ""),
            component=metadata_data.get("component", ""),
            operation=metadata_data.get("operation", ""),
            user_id=metadata_data.get("user_id"),
            request_id=metadata_data.get("request_id"),
            tags=metadata_data.get("tags", []),
            references=metadata_data.get("references", []),
            custom_fields=metadata_data.get("custom_fields", {})
        )
        
        # Parse specific data types
        llm_interaction = None
        if data.get("llm_interaction"):
            llm_data = data["llm_interaction"]
            llm_interaction = LLMInteraction(
                provider=llm_data.get("provider", ""),
                model=llm_data.get("model", ""),
                prompt_tokens=llm_data.get("prompt_tokens", 0),
                completion_tokens=llm_data.get("completion_tokens", 0),
                total_tokens=llm_data.get("total_tokens", 0),
                cost=llm_data.get("cost", 0.0),
                temperature=llm_data.get("temperature"),
                max_tokens=llm_data.get("max_tokens"),
                system_prompt=llm_data.get("system_prompt"),
                user_prompt=llm_data.get("user_prompt"),
                response=llm_data.get("response"),
                error=llm_data.get("error")
            )
        
        docker_operation = None
        if data.get("docker_operation"):
            docker_data = data["docker_operation"]
            docker_operation = DockerOperation(
                container_id=docker_data.get("container_id"),
                image=docker_data.get("image"),
                command=docker_data.get("command"),
                working_dir=docker_data.get("working_dir"),
                environment=docker_data.get("environment", {}),
                volumes=docker_data.get("volumes", []),
                ports=docker_data.get("ports", {}),
                exit_code=docker_data.get("exit_code"),
                stdout=docker_data.get("stdout"),
                stderr=docker_data.get("stderr"),
                duration_ms=docker_data.get("duration_ms")
            )
        
        research_context = None
        if data.get("research_context"):
            research_data = data["research_context"]
            research_context = ResearchContext(
                query=research_data.get("query"),
                search_engine=research_data.get("search_engine"),
                context7_queries=research_data.get("context7_queries", []),
                web_queries=research_data.get("web_queries", []),
                sources=research_data.get("sources", []),
                results_count=research_data.get("results_count", 0),
                processing_time_ms=research_data.get("processing_time_ms"),
                cache_hit=research_data.get("cache_hit", False)
            )
        
        state_transition = None
        if data.get("state_transition"):
            state_data = data["state_transition"]
            state_transition = StateTransition(
                from_state=state_data.get("from_state"),
                to_state=state_data.get("to_state", ""),
                checkpoint_id=state_data.get("checkpoint_id"),
                recovery_point=state_data.get("recovery_point"),
                session_data=state_data.get("session_data", {}),
                changed_keys=state_data.get("changed_keys", [])
            )
        
        conversation_message = None
        if data.get("conversation_message"):
            conv_data = data["conversation_message"]
            conversation_message = ConversationMessage(
                role=conv_data.get("role", "user"),
                content=conv_data.get("content", ""),
                timestamp=datetime.fromisoformat(conv_data.get("timestamp", datetime.now().isoformat())),
                message_id=conv_data.get("message_id", ""),
                parent_id=conv_data.get("parent_id"),
                metadata=conv_data.get("metadata", {})
            )
        
        return cls(
            id=data.get("id", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            level=LogLevel(data.get("level", "INFO")),
            entry_type=EntryType(data.get("entry_type", "system")),
            status=EntryStatus(data.get("status", "completed")),
            title=data.get("title", ""),
            message=data.get("message", ""),
            metadata=metadata,
            llm_interaction=llm_interaction,
            docker_operation=docker_operation,
            research_context=research_context,
            state_transition=state_transition,
            conversation_message=conversation_message,
            data=data.get("data", {}),
            parent_id=data.get("parent_id"),
            child_ids=data.get("child_ids", []),
            related_ids=data.get("related_ids", []),
            error_details=data.get("error_details"),
            stack_trace=data.get("stack_trace"),
            attachments=data.get("attachments", [])
        )
    
    def to_json(self) -> str:
        """Convert entry to JSON string"""
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> "JournalEntry":
        """Create entry from JSON string"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class JournalSummary:
    """Summary statistics for journal entries"""
    total_entries: int
    entries_by_type: Dict[str, int]
    entries_by_level: Dict[str, int]
    entries_by_status: Dict[str, int]
    date_range: tuple
    components: List[str]
    tags: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary"""
        return {
            "total_entries": self.total_entries,
            "entries_by_type": self.entries_by_type,
            "entries_by_level": self.entries_by_level,
            "entries_by_status": self.entries_by_status,
            "date_range": [d.isoformat() if isinstance(d, datetime) else str(d) for d in self.date_range],
            "components": self.components,
            "tags": self.tags
        }
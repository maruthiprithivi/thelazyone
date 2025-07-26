"""
Journal Manager

Comprehensive logging system for MCP server operations.
Provides structured logging, cross-referencing, search capabilities, and log rotation.
"""

import os
import json
import logging
import threading
import queue
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
import re
import markdown
from concurrent.futures import ThreadPoolExecutor
import shutil

from .models import (
    JournalEntry, LogLevel, EntryType, EntryStatus, JournalMetadata,
    LLMInteraction, DockerOperation, ResearchContext, StateTransition,
    ConversationMessage, JournalSummary
)
from ..config import ServerConfig


class JournalRotationHandler:
    """Handles log rotation and file management"""
    
    def __init__(self, base_path: Path, max_size_mb: int = 50, max_files: int = 10):
        self.base_path = Path(base_path)
        self.max_size_mb = max_size_mb
        self.max_files = max_files
        self.current_file = None
        self.lock = threading.RLock()
    
    def get_current_file(self) -> Path:
        """Get the current journal file"""
        with self.lock:
            if not self.current_file or self._should_rotate():
                self.current_file = self._create_new_file()
            return self.current_file
    
    def _should_rotate(self) -> bool:
        """Check if file rotation is needed"""
        if not self.current_file or not self.current_file.exists():
            return True
        
        try:
            size_mb = self.current_file.stat().st_size / (1024 * 1024)
            return size_mb >= self.max_size_mb
        except OSError:
            return True
    
    def _create_new_file(self) -> Path:
        """Create a new journal file with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"journal_{timestamp}.md"
        new_file = self.base_path / filename
        
        # Ensure directory exists
        new_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file with header
        with open(new_file, 'w', encoding='utf-8') as f:
            f.write(self._create_header())
        
        # Clean up old files
        self._cleanup_old_files()
        
        return new_file
    
    def _create_header(self) -> str:
        """Create markdown header for new journal file"""
        return f"""# MCP Server Journal

**File Created:** {datetime.now().isoformat()}

---

"""
    
    def _cleanup_old_files(self):
        """Remove old journal files if over max_files limit"""
        try:
            files = sorted(self.base_path.glob("journal_*.md"),
                         key=lambda f: f.stat().st_mtime,
                         reverse=True)
            
            for old_file in files[self.max_files:]:
                try:
                    old_file.unlink()
                except OSError:
                    pass  # Ignore errors when cleaning up
        except OSError:
            pass
    
    def get_all_files(self) -> List[Path]:
        """Get all journal files sorted by modification time"""
        try:
            files = list(self.base_path.glob("journal_*.md"))
            return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
        except OSError:
            return []


class JournalSearchEngine:
    """Advanced search capabilities for journal entries"""
    
    def __init__(self):
        self._compiled_patterns = {}
    
    def search_entries(self, entries: List[JournalEntry], 
                      query: str = None,
                      entry_type: EntryType = None,
                      level: LogLevel = None,
                      status: EntryStatus = None,
                      component: str = None,
                      tags: List[str] = None,
                      date_from: datetime = None,
                      date_to: datetime = None,
                      session_id: str = None,
                      full_text: bool = True) -> List[JournalEntry]:
        """Search journal entries with multiple criteria"""
        
        results = entries
        
        if query:
            results = self._filter_by_query(results, query, full_text)
        
        if entry_type:
            results = [e for e in results if e.entry_type == entry_type]
        
        if level:
            results = [e for e in results if e.level == level]
        
        if status:
            results = [e for e in results if e.status == status]
        
        if component:
            results = [e for e in results if e.metadata.component == component]
        
        if tags:
            results = [e for e in results if any(tag in e.metadata.tags for tag in tags)]
        
        if date_from:
            results = [e for e in results if e.timestamp >= date_from]
        
        if date_to:
            results = [e for e in results if e.timestamp <= date_to]
        
        if session_id:
            results = [e for e in results if e.metadata.session_id == session_id]
        
        return results
    
    def _filter_by_query(self, entries: List[JournalEntry], 
                        query: str, full_text: bool) -> List[JournalEntry]:
        """Filter entries by text query"""
        query_lower = query.lower()
        pattern = self._get_pattern(query)
        
        filtered = []
        for entry in entries:
            # Search in title and message
            if query_lower in entry.title.lower() or query_lower in entry.message.lower():
                filtered.append(entry)
                continue
            
            # Full text search
            if full_text:
                entry_text = self._get_entry_text(entry)
                if pattern.search(entry_text):
                    filtered.append(entry)
        
        return filtered
    
    def _get_pattern(self, query: str):
        """Get compiled regex pattern for query"""
        if query not in self._compiled_patterns:
            try:
                pattern = re.compile(re.escape(query.lower()), re.IGNORECASE)
                self._compiled_patterns[query] = pattern
            except re.error:
                # Fallback to simple string matching
                pattern = None
                self._compiled_patterns[query] = pattern
        
        return self._compiled_patterns[query]
    
    def _get_entry_text(self, entry: JournalEntry) -> str:
        """Get searchable text from entry"""
        text_parts = [
            entry.title,
            entry.message,
            str(entry.data),
            entry.metadata.component,
            entry.metadata.operation,
            " ".join(entry.metadata.tags),
            str(entry.error_details or "")
        ]
        
        # Add specific data based on entry type
        if entry.llm_interaction:
            text_parts.extend([
                entry.llm_interaction.provider,
                entry.llm_interaction.model,
                entry.llm_interaction.response or "",
                entry.llm_interaction.error or ""
            ])
        
        if entry.docker_operation:
            text_parts.extend([
                entry.docker_operation.image or "",
                entry.docker_operation.command or "",
                entry.docker_operation.stdout or "",
                entry.docker_operation.stderr or ""
            ])
        
        return " ".join(str(part) for part in text_parts)


class JournalManager:
    """Main journal manager for comprehensive logging"""
    
    def __init__(self, journal_config):
        self.journal_config = journal_config
        
        # Setup paths
        self.journal_dir = Path(self.journal_config.journal_path).parent
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        
        # File management
        self.rotation_handler = JournalRotationHandler(
            self.journal_dir,
            max_size_mb=50,
            max_files=10
        )
        
        # Search engine
        self.search_engine = JournalSearchEngine()
        
        # In-memory cache
        self._entries_cache = []
        self._cache_lock = threading.RLock()
        self._cache_dirty = False
        
        # Async processing
        self._queue = queue.Queue()
        self._worker_thread = None
        self._stop_event = threading.Event()
        
        # Logging
        self._setup_logging()
        
        # Start background worker
        self._start_worker()
    
    def _setup_logging(self):
        """Setup Python logging integration"""
        self.logger = logging.getLogger("mcp.journal")
        self.logger.setLevel(getattr(logging, self.journal_config.log_level.upper()))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.journal_config.log_level.upper()))
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(console_handler)
    
    def _start_worker(self):
        """Start background worker thread"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
    
    def _worker_loop(self):
        """Background worker loop for async processing"""
        while not self._stop_event.is_set():
            try:
                task = self._queue.get(timeout=1)
                if task is None:  # Shutdown signal
                    break
                
                task_type, data = task
                if task_type == "write":
                    self._write_entry_sync(data)
                elif task_type == "rotate":
                    self._rotate_files()
                elif task_type == "cleanup":
                    self._cleanup_cache()
                
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
    
    def log_entry(self, entry: JournalEntry, async_write: bool = True):
        """Log a journal entry"""
        with self._cache_lock:
            self._entries_cache.append(entry)
            self._cache_dirty = True
        
        if async_write:
            self._queue.put(("write", entry))
        else:
            self._write_entry_sync(entry)
    
    def log_system(self, title: str, message: str, 
                   level: LogLevel = LogLevel.INFO,
                   status: EntryStatus = EntryStatus.COMPLETED,
                   metadata: Optional[JournalMetadata] = None,
                   **kwargs) -> JournalEntry:
        """Log a system entry"""
        entry = JournalEntry(
            id="",
            timestamp=datetime.now(),
            level=level,
            entry_type=EntryType.SYSTEM,
            status=status,
            title=title,
            message=message,
            metadata=metadata or JournalMetadata(
                session_id="system",
                component="journal",
                operation="system_log"
            ),
            data=kwargs
        )
        self.log_entry(entry)
        return entry
    
    def log_llm_interaction(self, 
                           provider: str,
                           model: str,
                           prompt_tokens: int,
                           completion_tokens: int,
                           cost: float,
                           system_prompt: Optional[str] = None,
                           user_prompt: Optional[str] = None,
                           response: Optional[str] = None,
                           error: Optional[str] = None,
                           metadata: Optional[JournalMetadata] = None,
                           **kwargs) -> JournalEntry:
        """Log an LLM interaction"""
        llm_data = LLMInteraction(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
            error=error
        )
        
        title = f"LLM: {provider}/{model}"
        if error:
            title += " - ERROR"
        elif response:
            title += f" - {len(response)} chars"
        
        entry = JournalEntry(
            id="",
            timestamp=datetime.now(),
            level=LogLevel.ERROR if error else LogLevel.INFO,
            entry_type=EntryType.LLM,
            status=EntryStatus.FAILED if error else EntryStatus.COMPLETED,
            title=title,
            message=f"LLM interaction with {provider}/{model}",
            metadata=metadata or JournalMetadata(
                session_id="system",
                component="llm",
                operation="interaction"
            ),
            llm_interaction=llm_data,
            data=kwargs
        )
        
        self.log_entry(entry)
        return entry
    
    def log_docker_operation(self,
                            image: str,
                            command: str,
                            container_id: Optional[str] = None,
                            exit_code: Optional[int] = None,
                            stdout: Optional[str] = None,
                            stderr: Optional[str] = None,
                            duration_ms: Optional[int] = None,
                            metadata: Optional[JournalMetadata] = None,
                            **kwargs) -> JournalEntry:
        """Log a Docker operation"""
        docker_data = DockerOperation(
            container_id=container_id,
            image=image,
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms
        )
        
        title = f"Docker: {image}"
        if container_id:
            title += f" ({container_id[:12]})"
        
        status = EntryStatus.COMPLETED
        if exit_code is not None and exit_code != 0:
            status = EntryStatus.FAILED
        
        entry = JournalEntry(
            id="",
            timestamp=datetime.now(),
            level=LogLevel.ERROR if exit_code and exit_code != 0 else LogLevel.INFO,
            entry_type=EntryType.DOCKER,
            status=status,
            title=title,
            message=f"Docker operation: {command}",
            metadata=metadata or JournalMetadata(
                session_id="system",
                component="docker",
                operation="container_operation"
            ),
            docker_operation=docker_data,
            data=kwargs
        )
        
        self.log_entry(entry)
        return entry
    
    def log_research(self,
                    query: str,
                    sources: List[str],
                    results_count: int = 0,
                    processing_time_ms: Optional[int] = None,
                    cache_hit: bool = False,
                    metadata: Optional[JournalMetadata] = None,
                    **kwargs) -> JournalEntry:
        """Log a research operation"""
        research_data = ResearchContext(
            query=query,
            sources=sources,
            results_count=results_count,
            processing_time_ms=processing_time_ms,
            cache_hit=cache_hit
        )
        
        entry = JournalEntry(
            id="",
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            entry_type=EntryType.RESEARCH,
            status=EntryStatus.COMPLETED,
            title=f"Research: {query[:50]}{'...' if len(query) > 50 else ''}",
            message=f"Research completed with {results_count} results",
            metadata=metadata or JournalMetadata(
                session_id="system",
                component="research",
                operation="search"
            ),
            research_context=research_data,
            data=kwargs
        )
        
        self.log_entry(entry)
        return entry
    
    def log_state_change(self,
                        from_state: Optional[str],
                        to_state: str,
                        checkpoint_id: Optional[str] = None,
                        session_data: Optional[Dict[str, Any]] = None,
                        metadata: Optional[JournalMetadata] = None,
                        **kwargs) -> JournalEntry:
        """Log a state change"""
        state_data = StateTransition(
            from_state=from_state,
            to_state=to_state,
            checkpoint_id=checkpoint_id,
            session_data=session_data or {}
        )
        
        entry = JournalEntry(
            id="",
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            entry_type=EntryType.STATE,
            status=EntryStatus.COMPLETED,
            title=f"State: {from_state} -> {to_state}",
            message=f"State transition from {from_state} to {to_state}",
            metadata=metadata or JournalMetadata(
                session_id="system",
                component="state",
                operation="transition"
            ),
            state_transition=state_data,
            data=kwargs
        )
        
        self.log_entry(entry)
        return entry
    
    def log_conversation(self,
                        role: str,
                        content: str,
                        message_id: Optional[str] = None,
                        parent_id: Optional[str] = None,
                        metadata: Optional[JournalMetadata] = None,
                        **kwargs) -> JournalEntry:
        """Log a conversation message"""
        if not message_id:
            message_id = f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        conversation_data = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            message_id=message_id,
            parent_id=parent_id,
            metadata=kwargs.get("message_metadata", {})
        )
        
        entry = JournalEntry(
            id="",
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            entry_type=EntryType.CONVERSATION,
            status=EntryStatus.COMPLETED,
            title=f"Conversation: {role}",
            message=content[:100] + ("..." if len(content) > 100 else ""),
            metadata=metadata or JournalMetadata(
                session_id="system",
                component="conversation",
                operation="message"
            ),
            conversation_message=conversation_data,
            data=kwargs
        )
        
        self.log_entry(entry)
        return entry
    
    def log_operation(self,
                     operation: str,
                     session_id: str = None,
                     parameters: Dict[str, Any] = None,
                     metadata: Optional[Union[JournalMetadata, Dict[str, Any]]] = None,
                     **kwargs) -> JournalEntry:
        """Log a general operation"""
        # Handle dict metadata by converting to JournalMetadata
        if isinstance(metadata, dict):
            journal_metadata = JournalMetadata(
                session_id=session_id or metadata.get("session_id", "system"),
                component="server",
                operation=operation,
                request_id=metadata.get("request_id", ""),
                tags=[],
                custom_fields={}
            )
        else:
            journal_metadata = metadata or JournalMetadata(
                session_id=session_id or "system",
                component="server",
                operation=operation,
                tags=[],
                request_id="",
                custom_fields={}
            )
        
        entry = JournalEntry(
            id="",
            timestamp=datetime.now(),
            level=LogLevel.INFO,
            entry_type=EntryType.OPERATION,
            status=EntryStatus.COMPLETED,
            title=f"Operation: {operation}",
            message=f"Executing operation: {operation}",
            metadata=journal_metadata,
            data={"parameters": parameters or {}, **kwargs}
        )
        
        self.log_entry(entry)
        return entry
    
    def log_tool_call(self,
                     tool_name: str,
                     arguments: Dict[str, Any],
                     result: Any = None,
                     session_id: str = None,
                     duration_ms: float = None,
                     success: bool = True,
                     **kwargs) -> JournalEntry:
        """Log a tool call"""
        entry = JournalEntry(
            id="",
            timestamp=datetime.now(),
            level=LogLevel.ERROR if not success else LogLevel.INFO,
            entry_type=EntryType.API_CALL,
            status=EntryStatus.FAILED if not success else EntryStatus.COMPLETED,
            title=f"Tool: {tool_name} {'- SUCCESS' if success else '- FAILED'}",
            message=f"Tool {tool_name} {'executed successfully' if success else 'failed'}",
            metadata=JournalMetadata(
                session_id=session_id or "system",
                component="tools",
                operation=tool_name,
                tags=[],
                request_id=""
            ),
            data={
                "tool_name": tool_name,
                "arguments": arguments,
                "result": str(result)[:500] if result else None,
                "duration_ms": duration_ms,
                "success": success,
                **kwargs
            }
        )
        
        self.log_entry(entry)
        return entry
    
    def log_error(self,
                 error: Exception,
                 title: str = None,
                 operation: str = None,
                 session_id: str = None,
                 metadata: Optional[JournalMetadata] = None,
                 **kwargs) -> JournalEntry:
        """Log an error"""
        import traceback
        
        entry = JournalEntry(
            id="",
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            entry_type=EntryType.ERROR,
            status=EntryStatus.FAILED,
            title=title or f"Error: {type(error).__name__}",
            message=str(error),
            metadata=metadata or JournalMetadata(
                session_id=session_id or "system",
                component=operation or "error",
                operation=operation or "log_error",
                tags=[],
                request_id="",
                custom_fields={}
            ),
            error_details=str(error),
            stack_trace=traceback.format_exc(),
            data=kwargs
        )
        
        self.log_entry(entry)
        return entry
    
    def _write_entry_sync(self, entry: JournalEntry):
        """Write entry to file synchronously"""
        try:
            journal_file = self.rotation_handler.get_current_file()
            
            with open(journal_file, 'a', encoding='utf-8') as f:
                f.write(self._format_entry_markdown(entry))
                f.write("\n\n---\n\n")
            
            self.logger.log(
                getattr(logging, entry.level.value),
                f"{entry.entry_type.value.upper()}: {entry.title}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to write journal entry: {e}")
    
    def _format_entry_markdown(self, entry: JournalEntry) -> str:
        """Format entry as markdown"""
        lines = []
        
        # Header
        lines.append(f"## {entry.title}")
        lines.append("")
        lines.append(f"**Time:** {entry.timestamp.isoformat()}")
        lines.append(f"**Level:** {entry.level.value}")
        lines.append(f"**Type:** {entry.entry_type.value}")
        lines.append(f"**Status:** {entry.status.value}")
        lines.append(f"**ID:** {entry.id}")
        lines.append("")
        
        # Metadata
        lines.append("### Metadata")
        lines.append(f"- **Session:** {entry.metadata.session_id}")
        lines.append(f"- **Component:** {entry.metadata.component}")
        lines.append(f"- **Operation:** {entry.metadata.operation}")
        
        if entry.metadata.user_id:
            lines.append(f"- **User:** {entry.metadata.user_id}")
        
        if entry.metadata.request_id:
            lines.append(f"- **Request:** {entry.metadata.request_id}")
        
        if entry.metadata.tags:
            lines.append(f"- **Tags:** {', '.join(entry.metadata.tags)}")
        
        if entry.metadata.references:
            lines.append(f"- **References:** {', '.join(entry.metadata.references)}")
        
        lines.append("")
        
        # Message
        lines.append("### Message")
        lines.append(entry.message)
        lines.append("")
        
        # Type-specific data
        if entry.llm_interaction:
            lines.append("### LLM Interaction")
            lines.append(f"- **Provider:** {entry.llm_interaction.provider}")
            lines.append(f"- **Model:** {entry.llm_interaction.model}")
            lines.append(f"- **Tokens:** {entry.llm_interaction.total_tokens} "
                        f"({entry.llm_interaction.prompt_tokens} + {entry.llm_interaction.completion_tokens})")
            lines.append(f"- **Cost:** ${entry.llm_interaction.cost:.4f}")
            
            if entry.llm_interaction.error:
                lines.append(f"- **Error:** {entry.llm_interaction.error}")
            
            lines.append("")
        
        if entry.docker_operation:
            lines.append("### Docker Operation")
            lines.append(f"- **Image:** {entry.docker_operation.image}")
            lines.append(f"- **Command:** {entry.docker_operation.command}")
            
            if entry.docker_operation.container_id:
                lines.append(f"- **Container:** {entry.docker_operation.container_id[:12]}")
            
            if entry.docker_operation.exit_code is not None:
                lines.append(f"- **Exit Code:** {entry.docker_operation.exit_code}")
            
            if entry.docker_operation.duration_ms:
                lines.append(f"- **Duration:** {entry.docker_operation.duration_ms}ms")
            
            lines.append("")
        
        if entry.research_context:
            lines.append("### Research Context")
            lines.append(f"- **Query:** {entry.research_context.query}")
            lines.append(f"- **Results:** {entry.research_context.results_count}")
            lines.append(f"- **Sources:** {len(entry.research_context.sources)}")
            lines.append(f"- **Time:** {entry.research_context.processing_time_ms}ms")
            lines.append("")
        
        if entry.state_transition:
            lines.append("### State Transition")
            lines.append(f"- **From:** {entry.state_transition.from_state}")
            lines.append(f"- **To:** {entry.state_transition.to_state}")
            
            if entry.state_transition.checkpoint_id:
                lines.append(f"- **Checkpoint:** {entry.state_transition.checkpoint_id}")
            
            lines.append("")
        
        if entry.conversation_message:
            lines.append("### Conversation")
            lines.append(f"- **Role:** {entry.conversation_message.role}")
            lines.append(f"- **Content:** {entry.conversation_message.content}")
            lines.append("")
        
        # Error details
        if entry.error_details:
            lines.append("### Error Details")
            lines.append(f"```\n{entry.error_details}\n```")
            lines.append("")
        
        if entry.stack_trace:
            lines.append("### Stack Trace")
            lines.append(f"```\n{entry.stack_trace}\n```")
            lines.append("")
        
        # Additional data
        if entry.data:
            lines.append("### Additional Data")
            lines.append(f"```json\n{json.dumps(entry.data, indent=2)}\n```")
            lines.append("")
        
        # Cross-references
        if entry.parent_id or entry.child_ids or entry.related_ids:
            lines.append("### Cross-references")
            if entry.parent_id:
                lines.append(f"- **Parent:** {entry.parent_id}")
            if entry.child_ids:
                lines.append(f"- **Children:** {', '.join(entry.child_ids)}")
            if entry.related_ids:
                lines.append(f"- **Related:** {', '.join(entry.related_ids)}")
            lines.append("")
        
        return "\n".join(lines)
    
    def search(self, **kwargs) -> List[JournalEntry]:
        """Search journal entries"""
        # Load all entries if cache is dirty
        if self._cache_dirty:
            self._load_all_entries()
        
        with self._cache_lock:
            return self.search_engine.search_entries(self._entries_cache, **kwargs)
    
    def get_summary(self) -> JournalSummary:
        """Get summary statistics"""
        entries = self.search()
        
        if not entries:
            return JournalSummary(
                total_entries=0,
                entries_by_type={},
                entries_by_level={},
                entries_by_status={},
                date_range=(datetime.now(), datetime.now()),
                components=[],
                tags=[]
            )
        
        entries_by_type = {}
        entries_by_level = {}
        entries_by_status = {}
        components = set()
        tags = set()
        
        for entry in entries:
            entries_by_type[entry.entry_type.value] = entries_by_type.get(entry.entry_type.value, 0) + 1
            entries_by_level[entry.level.value] = entries_by_level.get(entry.level.value, 0) + 1
            entries_by_status[entry.status.value] = entries_by_status.get(entry.status.value, 0) + 1
            
            components.add(entry.metadata.component)
            tags.update(entry.metadata.tags)
        
        timestamps = [e.timestamp for e in entries]
        date_range = (min(timestamps), max(timestamps))
        
        return JournalSummary(
            total_entries=len(entries),
            entries_by_type=entries_by_type,
            entries_by_level=entries_by_level,
            entries_by_status=entries_by_status,
            date_range=date_range,
            components=sorted(list(components)),
            tags=sorted(list(tags))
        )
    
    def _load_all_entries(self):
        """Load all entries from files"""
        # This is a simplified version - in practice, you'd need to parse markdown
        # For now, we'll just mark cache as clean
        with self._cache_lock:
            self._cache_dirty = False
    
    def export_json(self, output_path: str, **search_kwargs) -> str:
        """Export entries to JSON"""
        entries = self.search(**search_kwargs)
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_entries": len(entries),
            "search_criteria": search_kwargs,
            "entries": [entry.to_dict() for entry in entries]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return output_path
    
    def cleanup(self):
        """Cleanup resources"""
        self._stop_event.set()
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._queue.put(None)  # Shutdown signal
            self._worker_thread.join(timeout=5)
        
        # Write any remaining entries
        while not self._queue.empty():
            try:
                task = self._queue.get_nowait()
                if task and task[0] == "write":
                    self._write_entry_sync(task[1])
            except queue.Empty:
                break
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
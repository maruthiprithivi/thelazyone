"""
Specification data models for spec-driven development workflows.

This module defines the core data structures for managing requirements,
design specifications, and task specifications in a structured format.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import uuid


class SpecType(Enum):
    """Types of specifications supported by the system."""
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    TASK = "task"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    TEST = "test"
    DOCUMENTATION = "documentation"


class SpecStatus(Enum):
    """Status of a specification document."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ChangeType(Enum):
    """Types of changes tracked in specification history."""
    CREATED = "created"
    MODIFIED = "modified"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    ROLLED_BACK = "rolled_back"
    DEPRECATED = "deprecated"


@dataclass
class ChangeRecord:
    """Represents a change entry in the specification's history."""
    change_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    change_type: ChangeType = ChangeType.MODIFIED
    description: str = ""
    author: str = ""
    previous_version: Optional[str] = None
    new_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Results of specification validation."""
    is_valid: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Requirement:
    """Individual requirement specification."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    priority: str = "medium"  # low, medium, high, critical
    category: str = "functional"
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_effort: Optional[str] = None
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class DesignComponent:
    """Design specification component."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    type: str = ""  # module, service, class, interface, etc.
    description: str = ""
    responsibilities: List[str] = field(default_factory=list)
    interfaces: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    technology: str = ""
    diagram_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskSpecification:
    """Task specification for implementation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    task_type: str = ""  # feature, bugfix, refactoring, research
    priority: str = "medium"
    estimated_hours: float = 0.0
    requirements: List[str] = field(default_factory=list)
    design_references: List[str] = field(default_factory=list)
    implementation_notes: str = ""
    test_cases: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class SpecDocument:
    """Main specification document container."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: str = "1.0.0"
    spec_type: SpecType = SpecType.REQUIREMENTS
    status: SpecStatus = SpecStatus.DRAFT
    
    # Core content
    requirements: List[Requirement] = field(default_factory=list)
    design_components: List[DesignComponent] = field(default_factory=list)
    tasks: List[TaskSpecification] = field(default_factory=list)
    
    # Metadata
    description: str = ""
    author: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    # Version control
    history: List[ChangeRecord] = field(default_factory=list)
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    
    # Integration
    source_code_references: List[str] = field(default_factory=list)
    research_references: List[str] = field(default_factory=list)
    llm_references: List[str] = field(default_factory=list)
    
    # Configuration
    configuration: Dict[str, Any] = field(default_factory=dict)
    
    # Validation results
    validation_results: List[ValidationResult] = field(default_factory=list)
    
    def add_requirement(self, requirement: Requirement) -> None:
        """Add a requirement to the specification."""
        self.requirements.append(requirement)
        self.updated_at = datetime.now()
        
    def add_design_component(self, component: DesignComponent) -> None:
        """Add a design component to the specification."""
        self.design_components.append(component)
        self.updated_at = datetime.now()
        
    def add_task(self, task: TaskSpecification) -> None:
        """Add a task specification to the document."""
        self.tasks.append(task)
        self.updated_at = datetime.now()
        
    def add_change_record(self, change: ChangeRecord) -> None:
        """Add a change record to the history."""
        self.history.append(change)
        self.updated_at = datetime.now()
        
    def get_requirements_by_priority(self, priority: str) -> List[Requirement]:
        """Get requirements filtered by priority."""
        return [req for req in self.requirements if req.priority == priority]
        
    def get_tasks_by_status(self, status: str) -> List[TaskSpecification]:
        """Get tasks filtered by status."""
        return [task for task in self.tasks if task.status == status]
        
    def get_design_components_by_type(self, component_type: str) -> List[DesignComponent]:
        """Get design components filtered by type."""
        return [comp for comp in self.design_components if comp.type == component_type]
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the specification to a dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'spec_type': self.spec_type.value,
            'status': self.status.value,
            'description': self.description,
            'author': self.author,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'tags': self.tags,
            'requirements': [
                {
                    'id': req.id,
                    'title': req.title,
                    'description': req.description,
                    'priority': req.priority,
                    'category': req.category,
                    'acceptance_criteria': req.acceptance_criteria,
                    'dependencies': req.dependencies,
                    'estimated_effort': req.estimated_effort,
                    'status': req.status,
                    'metadata': req.metadata,
                    'created_at': req.created_at.isoformat(),
                    'updated_at': req.updated_at.isoformat()
                }
                for req in self.requirements
            ],
            'design_components': [
                {
                    'id': comp.id,
                    'name': comp.name,
                    'type': comp.type,
                    'description': comp.description,
                    'responsibilities': comp.responsibilities,
                    'interfaces': comp.interfaces,
                    'dependencies': comp.dependencies,
                    'constraints': comp.constraints,
                    'technology': comp.technology,
                    'diagram_url': comp.diagram_url,
                    'metadata': comp.metadata
                }
                for comp in self.design_components
            ],
            'tasks': [
                {
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'task_type': task.task_type,
                    'priority': task.priority,
                    'estimated_hours': task.estimated_hours,
                    'requirements': task.requirements,
                    'design_references': task.design_references,
                    'implementation_notes': task.implementation_notes,
                    'test_cases': task.test_cases,
                    'acceptance_criteria': task.acceptance_criteria,
                    'assigned_to': task.assigned_to,
                    'status': task.status,
                    'metadata': task.metadata,
                    'created_at': task.created_at.isoformat(),
                    'updated_at': task.updated_at.isoformat()
                }
                for task in self.tasks
            ],
            'history': [
                {
                    'change_id': change.change_id,
                    'timestamp': change.timestamp.isoformat(),
                    'change_type': change.change_type.value,
                    'description': change.description,
                    'author': change.author,
                    'previous_version': change.previous_version,
                    'new_version': change.new_version,
                    'metadata': change.metadata
                }
                for change in self.history
            ],
            'source_code_references': self.source_code_references,
            'research_references': self.research_references,
            'llm_references': self.llm_references,
            'configuration': self.configuration
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpecDocument':
        """Create a specification document from a dictionary."""
        spec = cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            version=data.get('version', '1.0.0'),
            spec_type=SpecType(data.get('spec_type', 'requirements')),
            status=SpecStatus(data.get('status', 'draft')),
            description=data.get('description', ''),
            author=data.get('author', ''),
            tags=data.get('tags', []),
            source_code_references=data.get('source_code_references', []),
            research_references=data.get('research_references', []),
            llm_references=data.get('llm_references', []),
            configuration=data.get('configuration', {})
        )
        
        # Parse requirements
        for req_data in data.get('requirements', []):
            spec.add_requirement(Requirement(
                id=req_data.get('id', str(uuid.uuid4())),
                title=req_data.get('title', ''),
                description=req_data.get('description', ''),
                priority=req_data.get('priority', 'medium'),
                category=req_data.get('category', 'functional'),
                acceptance_criteria=req_data.get('acceptance_criteria', []),
                dependencies=req_data.get('dependencies', []),
                estimated_effort=req_data.get('estimated_effort'),
                status=req_data.get('status', 'pending'),
                metadata=req_data.get('metadata', {}),
                created_at=datetime.fromisoformat(req_data.get('created_at', datetime.now().isoformat())),
                updated_at=datetime.fromisoformat(req_data.get('updated_at', datetime.now().isoformat()))
            ))
            
        # Parse design components
        for comp_data in data.get('design_components', []):
            spec.add_design_component(DesignComponent(
                id=comp_data.get('id', str(uuid.uuid4())),
                name=comp_data.get('name', ''),
                type=comp_data.get('type', ''),
                description=comp_data.get('description', ''),
                responsibilities=comp_data.get('responsibilities', []),
                interfaces=comp_data.get('interfaces', []),
                dependencies=comp_data.get('dependencies', []),
                constraints=comp_data.get('constraints', []),
                technology=comp_data.get('technology', ''),
                diagram_url=comp_data.get('diagram_url'),
                metadata=comp_data.get('metadata', {})
            ))
            
        # Parse tasks
        for task_data in data.get('tasks', []):
            spec.add_task(TaskSpecification(
                id=task_data.get('id', str(uuid.uuid4())),
                title=task_data.get('title', ''),
                description=task_data.get('description', ''),
                task_type=task_data.get('task_type', ''),
                priority=task_data.get('priority', 'medium'),
                estimated_hours=task_data.get('estimated_hours', 0.0),
                requirements=task_data.get('requirements', []),
                design_references=task_data.get('design_references', []),
                implementation_notes=task_data.get('implementation_notes', ''),
                test_cases=task_data.get('test_cases', []),
                acceptance_criteria=task_data.get('acceptance_criteria', []),
                assigned_to=task_data.get('assigned_to'),
                status=task_data.get('status', 'pending'),
                metadata=task_data.get('metadata', {}),
                created_at=datetime.fromisoformat(task_data.get('created_at', datetime.now().isoformat())),
                updated_at=datetime.fromisoformat(task_data.get('updated_at', datetime.now().isoformat()))
            ))
            
        # Parse history
        for change_data in data.get('history', []):
            spec.add_change_record(ChangeRecord(
                change_id=change_data.get('change_id', str(uuid.uuid4())),
                timestamp=datetime.fromisoformat(change_data.get('timestamp', datetime.now().isoformat())),
                change_type=ChangeType(change_data.get('change_type', 'modified')),
                description=change_data.get('description', ''),
                author=change_data.get('author', ''),
                previous_version=change_data.get('previous_version'),
                new_version=change_data.get('new_version'),
                metadata=change_data.get('metadata', {})
            ))
            
        return spec
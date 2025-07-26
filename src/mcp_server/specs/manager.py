"""
Specification Manager - Core orchestrator for spec-driven development workflows.

Provides comprehensive management of requirements, design, and task specifications
with version control, validation, feedback integration, and export capabilities.
"""

import os
import json
import yaml
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path
import uuid

from .models import (
    SpecDocument, SpecType, SpecStatus, ChangeRecord, ChangeType, ValidationResult
)
from .generators import RequirementsGenerator, DesignGenerator, TaskGenerator


class SpecManager:
    """Central manager for all specification-related operations."""
    
    def __init__(self, 
                 storage_path: str = "./specs",
                 llm_client=None, 
                 research_engine=None,
                 validation_engine=None):
        """
        Initialize the SpecManager.
        
        Args:
            storage_path: Directory to store specifications
            llm_client: LLM client for generation and analysis
            research_engine: Research engine for context gathering
            validation_engine: Validation engine for spec verification
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.llm_client = llm_client
        self.research_engine = research_engine
        self.validation_engine = validation_engine
        
        # Initialize generators
        self.requirements_generator = RequirementsGenerator(llm_client, research_engine)
        self.design_generator = DesignGenerator(llm_client)
        self.task_generator = TaskGenerator(llm_client)
        
        # Cache for loaded specifications
        self._spec_cache: Dict[str, SpecDocument] = {}
        
        # Configuration
        self.config = {
            'auto_validate': True,
            'auto_backup': True,
            'max_versions': 10,
            'export_formats': ['json', 'yaml', 'markdown'],
            'validation_rules': {
                'min_requirements': 1,
                'min_description_length': 10,
                'require_acceptance_criteria': True
            }
        }
    
    def create_spec(self, 
                   spec_type: SpecType, 
                   name: str, 
                   description: str = "",
                   author: str = "System",
                   tags: List[str] = None) -> SpecDocument:
        """Create a new specification document."""
        spec = SpecDocument(
            name=name,
            spec_type=spec_type,
            description=description,
            author=author,
            tags=tags or []
        )
        
        spec.add_change_record(ChangeRecord(
            change_type=ChangeType.CREATED,
            description=f"Created new {spec_type.value} specification: {name}",
            author=author
        ))
        
        if self.config['auto_validate']:
            validation_result = self.validate_spec(spec)
            spec.validation_results.append(validation_result)
        
        self.save_spec(spec)
        return spec
    
    def generate_requirements(self, 
                            source: str,
                            source_type: str = "prompt",
                            context: Dict[str, Any] = None) -> SpecDocument:
        """Generate requirements specification from various sources."""
        context = context or {}
        
        if source_type == "prompt":
            spec = self.requirements_generator.from_prompt(source, context)
        elif source_type == "code_analysis":
            spec = self.requirements_generator.from_code_analysis(source, context)
        elif source_type == "research":
            spec = self.requirements_generator.from_research(source, context)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        self.save_spec(spec)
        return spec
    
    def generate_design(self, 
                       source_spec: SpecDocument,
                       context: Dict[str, Any] = None) -> SpecDocument:
        """Generate design specification from requirements."""
        context = context or {}
        design_spec = self.design_generator.from_requirements(source_spec, context)
        
        self.save_spec(design_spec)
        return design_spec
    
    def generate_tasks(self, 
                      source_spec: SpecDocument,
                      context: Dict[str, Any] = None) -> SpecDocument:
        """Generate task specifications from requirements or design."""
        context = context or {}
        task_spec = self.task_generator.from_requirements(source_spec, context)
        
        self.save_spec(task_spec)
        return task_spec
    
    def load_spec(self, spec_id: str) -> Optional[SpecDocument]:
        """Load a specification from storage."""
        if spec_id in self._spec_cache:
            return self._spec_cache[spec_id]
        
        spec_file = self.storage_path / f"{spec_id}.json"
        if not spec_file.exists():
            return None
        
        try:
            with open(spec_file, 'r') as f:
                data = json.load(f)
            
            spec = SpecDocument.from_dict(data)
            self._spec_cache[spec_id] = spec
            return spec
        except Exception as e:
            print(f"Error loading spec {spec_id}: {e}")
            return None
    
    def save_spec(self, spec: SpecDocument) -> None:
        """Save specification to storage."""
        # Save current version
        spec_file = self.storage_path / f"{spec.id}.json"
        with open(spec_file, 'w') as f:
            json.dump(spec.to_dict(), f, indent=2)
        
        # Save version backup
        if self.config['auto_backup']:
            self._create_version_backup(spec)
        
        self._spec_cache[spec.id] = spec
    
    def _create_version_backup(self, spec: SpecDocument) -> None:
        """Create a backup of the specification version."""
        backup_dir = self.storage_path / "backups" / spec.id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{spec.version}_{timestamp}.json"
        
        with open(backup_file, 'w') as f:
            json.dump(spec.to_dict(), f, indent=2)
        
        # Clean old backups
        self._cleanup_old_backups(backup_dir)
    
    def _cleanup_old_backups(self, backup_dir: Path) -> None:
        """Remove old backup files when exceeding max_versions."""
        backups = sorted(backup_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        
        if len(backups) > self.config['max_versions']:
            for backup in backups[:-self.config['max_versions']]:
                backup.unlink()
    
    def update_spec(self, 
                   spec_id: str, 
                   updates: Dict[str, Any],
                   author: str = "System") -> Optional[SpecDocument]:
        """Update specification with new data."""
        spec = self.load_spec(spec_id)
        if not spec:
            return None
        
        # Create change record
        change_description = f"Updated: {', '.join(updates.keys())}"
        spec.add_change_record(ChangeRecord(
            change_type=ChangeType.MODIFIED,
            description=change_description,
            author=author
        ))
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(spec, key):
                setattr(spec, key, value)
        
        spec.updated_at = datetime.now()
        
        # Re-validate if enabled
        if self.config['auto_validate']:
            validation_result = self.validate_spec(spec)
            spec.validation_results.append(validation_result)
        
        self.save_spec(spec)
        return spec
    
    def validate_spec(self, spec: SpecDocument) -> ValidationResult:
        """Validate specification against configured rules."""
        errors = []
        warnings = []
        suggestions = []
        score = 100.0
        
        rules = self.config['validation_rules']
        
        # Check minimum requirements
        if spec.spec_type == SpecType.REQUIREMENTS:
            if len(spec.requirements) < rules['min_requirements']:
                errors.append(f"Minimum {rules['min_requirements']} requirements required")
                score -= 20
        
        # Check description length
        if len(spec.description) < rules['min_description_length']:
            warnings.append(f"Description should be at least {rules['min_description_length']} characters")
            score -= 5
        
        # Check acceptance criteria for requirements
        if rules.get('require_acceptance_criteria', False):
            for req in spec.requirements:
                if not req.acceptance_criteria:
                    errors.append(f"Requirement '{req.title}' missing acceptance criteria")
                    score -= 10
        
        # Check task specifications
        for task in spec.tasks:
            if not task.acceptance_criteria:
                warnings.append(f"Task '{task.title}' missing acceptance criteria")
                score -= 3
        
        # Generate suggestions
        if len(spec.tags) == 0:
            suggestions.append("Consider adding tags for better organization")
        
        if len(spec.history) == 1:
            suggestions.append("Consider adding more detailed change history")
        
        # Use custom validation engine if available
        if self.validation_engine:
            custom_result = self.validation_engine.validate(spec)
            errors.extend(custom_result.get('errors', []))
            warnings.extend(custom_result.get('warnings', []))
            suggestions.extend(custom_result.get('suggestions', []))
            score = min(score, custom_result.get('score', score))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            score=max(0, score)
        )
    
    def get_specs_by_type(self, spec_type: SpecType) -> List[SpecDocument]:
        """Get all specifications of a specific type."""
        specs = []
        
        for spec_file in self.storage_path.glob("*.json"):
            try:
                spec = self.load_spec(spec_file.stem)
                if spec and spec.spec_type == spec_type:
                    specs.append(spec)
            except Exception as e:
                print(f"Error loading spec {spec_file}: {e}")
        
        return specs
    
    def get_specs_by_status(self, status: SpecStatus) -> List[SpecDocument]:
        """Get all specifications with a specific status."""
        specs = []
        
        for spec_file in self.storage_path.glob("*.json"):
            try:
                spec = self.load_spec(spec_file.stem)
                if spec and spec.status == status:
                    specs.append(spec)
            except Exception as e:
                print(f"Error loading spec {spec_file}: {e}")
        
        return specs
    
    def get_related_specs(self, spec_id: str) -> List[SpecDocument]:
        """Get specifications related to the given spec."""
        base_spec = self.load_spec(spec_id)
        if not base_spec:
            return []
        
        related = []
        
        # Get parent
        if base_spec.parent_id:
            parent = self.load_spec(base_spec.parent_id)
            if parent:
                related.append(parent)
        
        # Get children
        for child_id in base_spec.children_ids:
            child = self.load_spec(child_id)
            if child:
                related.append(child)
        
        # Get by tags
        all_specs = self.get_all_specs()
        for spec in all_specs:
            if spec.id != spec_id and set(spec.tags) & set(base_spec.tags):
                related.append(spec)
        
        return related
    
    def get_all_specs(self) -> List[SpecDocument]:
        """Get all specifications."""
        specs = []
        
        for spec_file in self.storage_path.glob("*.json"):
            try:
                spec = self.load_spec(spec_file.stem)
                if spec:
                    specs.append(spec)
            except Exception as e:
                print(f"Error loading spec {spec_file}: {e}")
        
        return specs
    
    def export_spec(self, 
                   spec_id: str, 
                   format: str = "json", 
                   output_path: Optional[str] = None) -> Optional[str]:
        """Export specification to different formats."""
        spec = self.load_spec(spec_id)
        if not spec:
            return None
        
        if format not in self.config['export_formats']:
            raise ValueError(f"Unsupported format: {format}")
        
        if not output_path:
            output_path = str(self.storage_path / f"{spec.name}.{format}")
        
        if format == "json":
            with open(output_path, 'w') as f:
                json.dump(spec.to_dict(), f, indent=2)
        
        elif format == "yaml":
            with open(output_path, 'w') as f:
                yaml.dump(spec.to_dict(), f, default_flow_style=False)
        
        elif format == "markdown":
            with open(output_path, 'w') as f:
                f.write(self._generate_markdown(spec))
        
        return output_path
    
    def _generate_markdown(self, spec: SpecDocument) -> str:
        """Generate markdown documentation for specification."""
        md = [f"# {spec.name}\n"]
        md.append(f"**Type:** {spec.spec_type.value}")
        md.append(f"**Status:** {spec.status.value}")
        md.append(f"**Version:** {spec.version}")
        md.append(f"**Author:** {spec.author}")
        md.append(f"**Updated:** {spec.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if spec.description:
            md.append(f"## Description\n{spec.description}\n")
        
        if spec.tags:
            md.append("## Tags\n" + ", ".join(f"`{tag}`" for tag in spec.tags) + "\n")
        
        if spec.requirements:
            md.append("## Requirements\n")
            for req in spec.requirements:
                md.append(f"### {req.title}")
                md.append(f"- **Priority:** {req.priority}")
                md.append(f"- **Category:** {req.category}")
                md.append(f"- **Description:** {req.description}")
                if req.acceptance_criteria:
                    md.append("- **Acceptance Criteria:**")
                    for criterion in req.acceptance_criteria:
                        md.append(f"  - {criterion}")
                md.append("")
        
        if spec.design_components:
            md.append("## Design Components\n")
            for comp in spec.design_components:
                md.append(f"### {comp.name}")
                md.append(f"- **Type:** {comp.type}")
                md.append(f"- **Technology:** {comp.technology}")
                md.append(f"- **Description:** {comp.description}")
                if comp.responsibilities:
                    md.append("- **Responsibilities:**")
                    for resp in comp.responsibilities:
                        md.append(f"  - {resp}")
                md.append("")
        
        if spec.tasks:
            md.append("## Tasks\n")
            for task in spec.tasks:
                md.append(f"### {task.title}")
                md.append(f"- **Type:** {task.task_type}")
                md.append(f"- **Priority:** {task.priority}")
                md.append(f"- **Estimated Hours:** {task.estimated_hours}")
                md.append(f"- **Description:** {task.description}")
                if task.assigned_to:
                    md.append(f"- **Assigned to:** {task.assigned_to}")
                md.append("")
        
        return "\n".join(md)
    
    def import_spec(self, file_path: str) -> Optional[SpecDocument]:
        """Import specification from file."""
        path = Path(file_path)
        if not path.exists():
            return None
        
        try:
            if path.suffix == '.json':
                with open(path, 'r') as f:
                    data = json.load(f)
            elif path.suffix in ['.yml', '.yaml']:
                with open(path, 'r') as f:
                    data = yaml.safe_load(f)
            else:
                return None
            
            spec = SpecDocument.from_dict(data)
            self.save_spec(spec)
            return spec
        except Exception as e:
            print(f"Error importing spec from {file_path}: {e}")
            return None
    
    def search_specs(self, 
                    query: str, 
                    spec_type: Optional[SpecType] = None,
                    tags: Optional[List[str]] = None) -> List[SpecDocument]:
        """Search specifications by content."""
        results = []
        
        for spec in self.get_all_specs():
            # Filter by type
            if spec_type and spec.spec_type != spec_type:
                continue
            
            # Filter by tags
            if tags and not set(tags).issubset(set(spec.tags)):
                continue
            
            # Search in content
            search_text = " ".join([
                spec.name,
                spec.description,
                *[req.title + " " + req.description for req in spec.requirements],
                *[comp.name + " " + comp.description for comp in spec.design_components],
                *[task.title + " " + task.description for task in spec.tasks]
            ]).lower()
            
            if query.lower() in search_text:
                results.append(spec)
        
        return results
    
    def get_spec_statistics(self) -> Dict[str, Any]:
        """Get statistics about all specifications."""
        specs = self.get_all_specs()
        
        stats = {
            'total_specs': len(specs),
            'by_type': {},
            'by_status': {},
            'total_requirements': 0,
            'total_design_components': 0,
            'total_tasks': 0
        }
        
        for spec_type in SpecType:
            specs_by_type = [s for s in specs if s.spec_type == spec_type]
            stats['by_type'][spec_type.value] = len(specs_by_type)
        
        for status in SpecStatus:
            specs_by_status = [s for s in specs if s.status == status]
            stats['by_status'][status.value] = len(specs_by_status)
        
        for spec in specs:
            stats['total_requirements'] += len(spec.requirements)
            stats['total_design_components'] += len(spec.design_components)
            stats['total_tasks'] += len(spec.tasks)
        
        return stats
    
    def create_workflow_chain(self, 
                            name: str, 
                            source: str,
                            source_type: str = "prompt",
                            context: Dict[str, Any] = None) -> Dict[str, SpecDocument]:
        """
        Create a complete workflow chain: Requirements → Design → Tasks.
        
        Returns:
            Dictionary with 'requirements', 'design', and 'tasks' specifications
        """
        context = context or {}
        
        # Generate requirements
        requirements_spec = self.generate_requirements(source, source_type, context)
        
        # Generate design from requirements
        design_context = {**context, 'parent_id': requirements_spec.id}
        design_spec = self.generate_design(requirements_spec, design_context)
        
        # Generate tasks from requirements
        tasks_context = {**context, 'parent_id': requirements_spec.id}
        tasks_spec = self.generate_tasks(requirements_spec, tasks_context)
        
        # Link specifications
        requirements_spec.children_ids.extend([design_spec.id, tasks_spec.id])
        self.save_spec(requirements_spec)
        
        return {
            'requirements': requirements_spec,
            'design': design_spec,
            'tasks': tasks_spec
        }
    
    def cleanup_cache(self) -> None:
        """Clear the specification cache."""
        self._spec_cache.clear()
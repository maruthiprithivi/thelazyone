"""
Specification Generators

Provides intelligent generation of requirements, design, and task specifications.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class RequirementsGenerator:
    """Generates structured requirements from high-level descriptions."""
    
    def __init__(self, llm_client=None, research_engine=None):
        """Initialize the requirements generator."""
        self.llm_client = llm_client
        self.research_engine = research_engine
    
    def generate_requirements(
        self,
        title: str,
        description: str,
        project_context: Optional[Dict[str, Any]] = None,
        constraints: Optional[List[str]] = None,
        acceptance_criteria: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate structured requirements from description.
        
        Args:
            title: Title of the requirements
            description: Detailed description
            project_context: Additional context
            constraints: Technical/business constraints
            acceptance_criteria: Acceptance criteria
            
        Returns:
            Dict containing structured requirements
        """
        
        # Parse description to identify requirement types
        requirements = {
            "functional_requirements": [],
            "non_functional_requirements": [],
            "business_requirements": [],
            "technical_constraints": constraints or [],
            "acceptance_criteria": acceptance_criteria or []
        }
        
        # Simple parsing for functional requirements
        functional_keywords = ["must", "should", "will", "need to", "required to"]
        description_lower = description.lower()
        
        for keyword in functional_keywords:
            if keyword in description_lower:
                # Extract sentences containing functional keywords
                sentences = [s.strip() for s in description.split('.') if keyword in s.lower()]
                for sentence in sentences:
                    requirements["functional_requirements"].append({
                        "id": f"FR-{len(requirements['functional_requirements']) + 1}",
                        "description": sentence,
                        "priority": "high" if "must" in sentence.lower() else "medium"
                    })
        
        # Add performance requirements
        if "performance" in description_lower or "fast" in description_lower:
            requirements["non_functional_requirements"].append({
                "id": "NFR-1",
                "description": "System must meet performance benchmarks",
                "priority": "high",
                "metrics": ["response_time", "throughput"]
            })
        
        # Add security requirements based on context
        if project_context and "security" in str(project_context).lower():
            requirements["non_functional_requirements"].append({
                "id": "NFR-2",
                "description": "System must implement security best practices",
                "priority": "high",
                "areas": ["authentication", "authorization", "data_encryption"]
            })
        
        return requirements


class DesignGenerator:
    """Generates technical design specifications."""
    
    def __init__(self, llm_client=None):
        """Initialize the design generator."""
        self.llm_client = llm_client
    
    def generate_design(
        self,
        title: str,
        requirements: Optional[Dict[str, Any]] = None,
        design_type: str = "technical",
        components: Optional[List[str]] = None,
        architecture_style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate technical design from requirements.
        
        Args:
            title: Design title
            requirements: Requirements to design for
            design_type: Type of design
            components: Specific components to design
            architecture_style: Architecture style
            
        Returns:
            Dict containing design specification
        """
        
        design = {
            "overview": f"Technical design for {title}",
            "architecture_style": architecture_style or "layered",
            "components": [],
            "data_flow": [],
            "interfaces": [],
            "security_considerations": []
        }
        
        # Generate components based on requirements
        if requirements:
            functional_reqs = requirements.get("functional_requirements", [])
            for i, req in enumerate(functional_reqs[:5]):  # Limit to first 5
                component = {
                    "name": f"{req['description'][:20].replace(' ', '_')}_component",
                    "type": "service",
                    "description": f"Implements requirement {req['id']}",
                    "responsibilities": [req["description"]],
                    "dependencies": [],
                    "interfaces": ["REST API"]
                }
                design["components"].append(component)
        
        # Add common components
        common_components = [
            {
                "name": "api_gateway",
                "type": "service",
                "description": "Entry point for all API requests",
                "responsibilities": ["routing", "authentication", "rate_limiting"],
                "dependencies": ["auth_service"],
                "interfaces": ["HTTP/REST"]
            },
            {
                "name": "data_layer",
                "type": "module",
                "description": "Data access and storage layer",
                "responsibilities": ["data_persistence", "query_optimization"],
                "dependencies": ["database"],
                "interfaces": ["internal"]
            }
        ]
        
        design["components"].extend(common_components)
        
        # Add data flow
        design["data_flow"] = [
            {
                "from": "api_gateway",
                "to": "business_logic",
                "data": "user_requests",
                "format": "JSON"
            },
            {
                "from": "business_logic",
                "to": "data_layer",
                "data": "persistence_operations",
                "format": "ORM_objects"
            }
        ]
        
        # Add security considerations
        design["security_considerations"] = [
            "Input validation on all API endpoints",
            "Authentication and authorization checks",
            "Data encryption in transit and at rest",
            "Rate limiting to prevent abuse"
        ]
        
        return design


class TaskGenerator:
    """Generates development tasks from requirements and design."""
    
    def __init__(self, llm_client=None):
        """Initialize the task generator."""
        self.llm_client = llm_client
    
    def generate_tasks(
        self,
        title: str,
        requirements: Optional[Dict[str, Any]] = None,
        design: Optional[Dict[str, Any]] = None,
        priority: str = "medium",
        estimated_hours: Optional[float] = None,
        dependencies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate development tasks.
        
        Args:
            title: Task title
            requirements: Requirements to implement
            design: Design to implement
            priority: Priority level
            estimated_hours: Estimated effort
            dependencies: Task dependencies
            
        Returns:
            Dict containing task breakdown
        """
        
        tasks = {
            "project_title": title,
            "priority": priority,
            "estimated_total_hours": estimated_hours or 8.0,
            "tasks": [],
            "milestones": []
        }
        
        # Generate tasks based on components
        if design and "components" in design:
            for component in design["components"]:
                task = {
                    "id": f"TASK-{len(tasks['tasks']) + 1:03d}",
                    "title": f"Implement {component['name']}",
                    "description": f"Implement {component['type']} component: {component['description']}",
                    "priority": priority,
                    "estimated_hours": 2.0,  # Default estimate
                    "status": "pending",
                    "dependencies": dependencies or [],
                    "acceptance_criteria": [
                        f"Component {component['name']} is implemented",
                        f"Component passes unit tests",
                        f"Component integrates with existing system"
                    ]
                }
                tasks["tasks"].append(task)
        
        # Add setup tasks
        setup_tasks = [
            {
                "id": "TASK-SETUP-001",
                "title": "Project setup",
                "description": "Set up development environment and project structure",
                "priority": "high",
                "estimated_hours": 1.0,
                "status": "pending",
                "dependencies": [],
                "acceptance_criteria": [
                    "Development environment is ready",
                    "Project structure is established",
                    "Dependencies are installed"
                ]
            },
            {
                "id": "TASK-SETUP-002",
                "title": "Testing setup",
                "description": "Set up testing framework and initial tests",
                "priority": "high",
                "estimated_hours": 1.0,
                "status": "pending",
                "dependencies": ["TASK-SETUP-001"],
                "acceptance_criteria": [
                    "Testing framework is configured",
                    "Basic test suite is running",
                    "CI/CD pipeline is set up"
                ]
            }
        ]
        
        tasks["tasks"] = setup_tasks + tasks["tasks"]
        
        # Add integration tasks
        integration_task = {
            "id": f"TASK-INTEGRATION-{len(tasks['tasks']) + 1:03d}",
            "title": "Integration testing",
            "description": "Test integration between all components",
            "priority": "medium",
            "estimated_hours": 2.0,
            "status": "pending",
            "dependencies": [t["id"] for t in tasks["tasks"][2:]],  # Depends on all implementation tasks
            "acceptance_criteria": [
                "All components work together correctly",
                "Integration tests pass",
                "System meets requirements"
            ]
        }
        
        tasks["tasks"].append(integration_task)
        
        # Calculate total estimated hours
        total_hours = sum(task["estimated_hours"] for task in tasks["tasks"])
        tasks["estimated_total_hours"] = total_hours
        
        # Add milestones
        tasks["milestones"] = [
            {
                "name": "Setup Complete",
                "description": "Development environment and structure ready",
                "tasks": ["TASK-SETUP-001", "TASK-SETUP-002"]
            },
            {
                "name": "Core Implementation",
                "description": "All core components implemented",
                "tasks": [t["id"] for t in tasks["tasks"][2:-1]]  # All except setup and integration
            },
            {
                "name": "Project Complete",
                "description": "All tasks completed and tested",
                "tasks": [t["id"] for t in tasks["tasks"]]
            }
        ]
        
        return tasks
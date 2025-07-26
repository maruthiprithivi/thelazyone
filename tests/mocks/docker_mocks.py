"""
Mock implementations for Docker-related dependencies.
"""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock


class MockDockerContainer:
    """Mock Docker container."""
    
    def __init__(self, container_id: str = "mock-container-123", name: str = "test-container"):
        self.id = container_id
        self.name = name
        self.status = "created"
        self.image = "python:3.11-slim"
        self.attrs = {
            "Id": container_id,
            "Names": [f"/test-{name}"],
            "State": {"Status": "running", "Running": True},
            "NetworkSettings": {
                "IPAddress": "172.17.0.2",
                "Ports": {"8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8080"}]}
            },
            "Mounts": [
                {
                    "Type": "bind",
                    "Source": "/host/path",
                    "Destination": "/container/path",
                    "Mode": "rw"
                }
            ]
        }
        self.logs_data = []
        self.exec_results = []
    
    def logs(self, **kwargs) -> bytes:
        """Mock logs method."""
        return b"Mock container logs\n"
    
    def start(self, **kwargs) -> None:
        """Mock start method."""
        self.status = "running"
        self.attrs["State"]["Status"] = "running"
        self.attrs["State"]["Running"] = True
    
    def stop(self, **kwargs) -> None:
        """Mock stop method."""
        self.status = "exited"
        self.attrs["State"]["Status"] = "exited"
        self.attrs["State"]["Running"] = False
    
    def remove(self, **kwargs) -> None:
        """Mock remove method."""
        self.status = "removed"
    
    def reload(self) -> None:
        """Mock reload method."""
        pass
    
    def exec_run(self, cmd: str, **kwargs) -> tuple:
        """Mock exec_run method."""
        result = {
            "exit_code": 0,
            "output": f"Executed: {cmd}\n".encode(),
            "stderr": b""
        }
        
        # Simulate different command results
        if "pytest" in cmd:
            result["output"] = b"============================= test session starts ==============================\nplatform linux -- Python 3.11.0\ncollected 3 items\n\ntest_sample.py ..F\n\n============================== 3 passed, 1 failed ==============================\n"
            result["exit_code"] = 1
        elif "python" in cmd and "-m" not in cmd:
            result["output"] = b"Hello from Python!\n"
        elif "pip" in cmd:
            result["output"] = b"Successfully installed packages\n"
        
        return (result["exit_code"], result["output"])


class MockDockerImage:
    """Mock Docker image."""
    
    def __init__(self, image_id: str = "mock-image-456", tags: List[str] = None):
        self.id = image_id
        self.tags = tags or ["python:3.11-slim"]
        self.attrs = {
            "Id": image_id,
            "RepoTags": self.tags,
            "Size": 123456789,
            "Created": "2024-01-01T00:00:00Z"
        }


class MockDockerClient:
    """Mock Docker client."""
    
    def __init__(self, base_url: str = "unix:///var/run/docker.sock"):
        self.base_url = base_url
        self.containers = MockContainerCollection()
        self.images = MockImageCollection()
        self.networks = MockNetworkCollection()
        self.volumes = MockVolumeCollection()
        self.api = MockDockerAPI()
    
    def close(self) -> None:
        """Mock close method."""
        pass


class MockContainerCollection:
    """Mock container collection."""
    
    def __init__(self):
        self.containers = {}
        self.next_id = 1
    
    def list(self, **kwargs) -> List[MockDockerContainer]:
        """Mock list method."""
        return list(self.containers.values())
    
    def get(self, container_id: str) -> MockDockerContainer:
        """Mock get method."""
        if container_id in self.containers:
            return self.containers[container_id]
        raise Exception(f"Container {container_id} not found")
    
    def run(self, image: str, **kwargs) -> MockDockerContainer:
        """Mock run method."""
        container_id = f"mock-container-{self.next_id}"
        self.next_id += 1
        
        name = kwargs.get("name", f"test-{self.next_id}")
        container = MockDockerContainer(container_id, name)
        
        # Apply kwargs
        if "environment" in kwargs:
            container.attrs["Config"] = {"Env": kwargs["environment"]}
        if "ports" in kwargs:
            container.attrs["HostConfig"] = {"PortBindings": kwargs["ports"]}
        if "volumes" in kwargs:
            container.attrs["Mounts"].extend(kwargs["volumes"])
        
        # Start container
        container.start()
        self.containers[container_id] = container
        return container
    
    def create(self, **kwargs) -> MockDockerContainer:
        """Mock create method."""
        return self.run("python:3.11-slim", **kwargs)


class MockImageCollection:
    """Mock image collection."""
    
    def __init__(self):
        self.images = {}
    
    def list(self, **kwargs) -> List[MockDockerImage]:
        """Mock list method."""
        return [
            MockDockerImage("python:3.11-slim"),
            MockDockerImage("python:3.10-slim"),
            MockDockerImage("alpine:latest")
        ]
    
    def pull(self, repository: str, tag: str = None, **kwargs) -> MockDockerImage:
        """Mock pull method."""
        full_tag = f"{repository}:{tag}" if tag else repository
        return MockDockerImage(tags=[full_tag])
    
    def get(self, image_id: str) -> MockDockerImage:
        """Mock get method."""
        return MockDockerImage(image_id)


class MockNetworkCollection:
    """Mock network collection."""
    
    def __init__(self):
        self.networks = {}
    
    def list(self, **kwargs) -> List[Dict[str, Any]]:
        """Mock list method."""
        return [
            {"Id": "bridge", "Name": "bridge", "Driver": "bridge"},
            {"Id": "host", "Name": "host", "Driver": "host"}
        ]
    
    def create(self, name: str, **kwargs) -> Dict[str, Any]:
        """Mock create method."""
        return {"Id": f"network-{name}", "Name": name, "Driver": "bridge"}


class MockVolumeCollection:
    """Mock volume collection."""
    
    def __init__(self):
        self.volumes = {}
    
    def list(self, **kwargs) -> List[Dict[str, Any]]:
        """Mock list method."""
        return [
            {"Name": "test-volume", "Driver": "local", "Mountpoint": "/var/lib/docker/volumes/test-volume"}
        ]
    
    def create(self, name: str, **kwargs) -> Dict[str, Any]:
        """Mock create method."""
        return {"Name": name, "Driver": "local", "Mountpoint": f"/var/lib/docker/volumes/{name}"}


class MockDockerAPI:
    """Mock Docker API for low-level operations."""
    
    def __init__(self):
        self.build_results = []
    
    def build(self, path: str, **kwargs) -> tuple:
        """Mock build method."""
        return (
            [{"stream": f"Building from {path}\n"}],
            [{"stream": "Successfully built image\n"}]
        )
    
    def create_container(self, **kwargs) -> Dict[str, Any]:
        """Mock create_container method."""
        return {"Id": "mock-container-123", "Warnings": []}
    
    def start_container(self, container_id: str) -> None:
        """Mock start_container method."""
        pass
    
    def stop_container(self, container_id: str, **kwargs) -> None:
        """Mock stop_container method."""
        pass
    
    def remove_container(self, container_id: str, **kwargs) -> None:
        """Mock remove_container method."""
        pass
    
    def logs(self, container_id: str, **kwargs) -> bytes:
        """Mock logs method."""
        return b"Mock logs\n"
    
    def exec_create(self, container_id: str, cmd: str, **kwargs) -> Dict[str, str]:
        """Mock exec_create method."""
        return {"Id": "mock-exec-123"}
    
    def exec_start(self, exec_id: str, **kwargs) -> bytes:
        """Mock exec_start method."""
        return b"Mock exec output\n"
    
    def exec_inspect(self, exec_id: str) -> Dict[str, Any]:
        """Mock exec_inspect method."""
        return {"ExitCode": 0, "Running": False}


class MockAioDockerContainer:
    """Mock aiohttp-based Docker container."""
    
    def __init__(self, container_id: str, **kwargs):
        self.id = container_id
        self.name = kwargs.get("name", f"test-{container_id}")
        self.config = kwargs
        self._status = "created"
    
    async def show(self) -> Dict[str, Any]:
        """Mock show method."""
        return {
            "Id": self.id,
            "Names": [f"/{self.name}"],
            "State": {"Status": self._status, "Running": self._status == "running"},
            "NetworkSettings": {"IPAddress": "172.17.0.2"}
        }
    
    async def start(self) -> None:
        """Mock start method."""
        self._status = "running"
    
    async def stop(self) -> None:
        """Mock stop method."""
        self._status = "exited"
    
    async def delete(self, **kwargs) -> None:
        """Mock delete method."""
        self._status = "removed"
    
    async def logs(self, **kwargs) -> str:
        """Mock logs method."""
        return "Mock container logs\n"
    
    async def execute(self, cmd: str, **kwargs) -> Dict[str, Any]:
        """Mock execute method."""
        return {
            "exit_code": 0,
            "output": f"Executed: {cmd}\n",
            "stderr": ""
        }


class MockAioDocker:
    """Mock aiohttp-based Docker client."""
    
    def __init__(self):
        self.containers = MockAioDockerContainers()
        self.images = MockAioDockerImages()
        self.close = AsyncMock()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class MockAioDockerContainers:
    """Mock aiohttp-based containers collection."""
    
    def __init__(self):
        self.containers = {}
    
    async def list(self, **kwargs) -> List[MockAioDockerContainer]:
        """Mock list method."""
        return list(self.containers.values())
    
    async def create(self, **kwargs) -> MockAioDockerContainer:
        """Mock create method."""
        container_id = f"mock-{len(self.containers) + 1}"
        container = MockAioDockerContainer(container_id, **kwargs)
        self.containers[container_id] = container
        return container
    
    async def get(self, container_id: str) -> MockAioDockerContainer:
        """Mock get method."""
        return self.containers[container_id]


class MockAioDockerImages:
    """Mock aiohttp-based images collection."""
    
    async def list(self, **kwargs) -> List[Dict[str, Any]]:
        """Mock list method."""
        return [
            {"Id": "python:3.11-slim", "RepoTags": ["python:3.11-slim"]},
            {"Id": "alpine:latest", "RepoTags": ["alpine:latest"]}
        ]
    
    async def pull(self, name: str, **kwargs) -> Dict[str, Any]:
        """Mock pull method."""
        return {"Id": name, "RepoTags": [name]}


def create_mock_container_info(**kwargs) -> Dict[str, Any]:
    """Create mock container information."""
    return {
        "id": kwargs.get("id", "mock-container-123"),
        "name": kwargs.get("name", "test-container"),
        "status": kwargs.get("status", "running"),
        "image": kwargs.get("image", "python:3.11-slim"),
        "ports": kwargs.get("ports", {"8000/tcp": [{"HostPort": "8080"}]}),
        "mounts": kwargs.get("mounts", [{"Source": "/host/path", "Destination": "/container/path"}]),
        "environment": kwargs.get("environment", {}),
        "labels": kwargs.get("labels", {}),
        "access_info": kwargs.get("access_info", {"url": "http://localhost:8080"})
    }
"""
Mock implementations for LLM-related dependencies.
"""

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from mcp_server.llm.models import LLMRequest, LLMResponse, Message, MessageRole


class MockLLMProvider:
    """Mock LLM provider for testing."""
    
    def __init__(self, name: str = "mock-provider", model: str = "mock-model"):
        self.name = name
        self.model = model
        self.generate_call_count = 0
        self.last_request = None
        self.should_fail = False
        self.delay = 0.1  # Small delay to simulate network
    
    async def generate(self, request: LLMRequest, conversation_id: Optional[str] = None) -> LLMResponse:
        """Mock generate method."""
        self.generate_call_count += 1
        self.last_request = request
        
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        
        if self.should_fail:
            raise Exception("Mock LLM generation failed")
        
        # Generate mock response based on request
        content = self._generate_mock_content(request)
        
        return LLMResponse(
            content=content,
            model=self.model,
            usage={
                "prompt_tokens": len(str(request)),
                "completion_tokens": len(content),
                "total_tokens": len(str(request)) + len(content)
            },
            finish_reason="stop"
        )
    
    def _generate_mock_content(self, request: LLMRequest) -> str:
        """Generate mock content based on request."""
        messages = request.messages
        if not messages:
            return "Mock response"
        
        last_message = messages[-1]
        content = last_message.content.lower()
        
        # Simple content generation based on keywords
        if "code" in content or "python" in content:
            return '''def hello_world():
    """A simple hello world function."""
    return "Hello, World!"

if __name__ == "__main__":
    print(hello_world())'''
        elif "debug" in content or "fix" in content:
            return '''# Fixed code
import logging

def safe_divide(a, b):
    """Safely divide two numbers."""
    if b == 0:
        logging.error("Division by zero attempted")
        return None
    return a / b'''
        elif "test" in content:
            return '''import pytest

def test_example():
    assert True
    
@pytest.mark.parametrize("x", [1, 2, 3])
def test_parametrized(x):
    assert x > 0'''
        else:
            return f"Mock response to: {content[:50]}..."


class MockLLMRouter:
    """Mock LLM router for testing."""
    
    def __init__(self, providers: Dict[str, Any], default_provider: str = "mock"):
        self.providers = providers
        self.default_provider = default_provider
        self.call_count = 0
        self.provider_usage = {}
        self.should_fail = False
    
    async def initialize(self) -> None:
        """Mock initialization."""
        pass
    
    async def cleanup(self) -> None:
        """Mock cleanup."""
        pass
    
    async def generate(self, request: LLMRequest, provider: Optional[str] = None, conversation_id: Optional[str] = None) -> LLMResponse:
        """Mock generate method."""
        self.call_count += 1
        provider_name = provider or self.default_provider
        
        if provider_name not in self.provider_usage:
            self.provider_usage[provider_name] = 0
        self.provider_usage[provider_name] += 1
        
        if self.should_fail:
            raise Exception("Mock LLM router failed")
        
        # Use mock provider
        mock_provider = MockLLMProvider(provider_name)
        return await mock_provider.generate(request, conversation_id)
    
    def get_provider_stats(self) -> Dict[str, int]:
        """Get usage statistics."""
        return self.provider_usage.copy()


class MockMessage(Message):
    """Mock message for testing."""
    
    @classmethod
    def create_user_message(cls, content: str) -> "MockMessage":
        """Create a user message."""
        return cls(role=MessageRole.USER, content=content)
    
    @classmethod
    def create_assistant_message(cls, content: str) -> "MockMessage":
        """Create an assistant message."""
        return cls(role=MessageRole.ASSISTANT, content=content)
    
    @classmethod
    def create_system_message(cls, content: str) -> "MockMessage":
        """Create a system message."""
        return cls(role=MessageRole.SYSTEM, content=content)


def create_mock_llm_response(request: LLMRequest, model: str = "mock-model") -> LLMResponse:
    """Create a mock LLM response."""
    content = f"Mock response to: {request.messages[-1].content}"
    return LLMResponse(
        content=content,
        model=model,
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        finish_reason="stop"
    )


def create_mock_llm_error_response(error_message: str) -> Dict[str, Any]:
    """Create a mock LLM error response."""
    return {
        "error": {
            "message": error_message,
            "type": "invalid_request_error",
            "param": None,
            "code": None
        }
    }
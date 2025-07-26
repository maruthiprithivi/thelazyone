"""
LLM Provider Implementations

Provides concrete implementations for different LLM providers including OpenAI and MoonShot AI.
Handles API communication, authentication, and response processing.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncIterator, Union
import aiohttp
import logging
from .models import (
    LLMRequest, LLMResponse, StreamChunk, ProviderConfig, 
    RateLimitInfo, LLMError, ResponseType
)
from ..config import ModelConfig, LLMProvider as ConfigLLMProvider


logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.provider_config = self._create_provider_config(config)
        self.session: Optional[aiohttp.ClientSession] = None
        
    def _create_provider_config(self, config: ModelConfig) -> ProviderConfig:
        """Create provider-specific configuration"""
        return ProviderConfig(
            name=config.provider.value,
            api_key=config.api_key,
            base_url=config.base_url,
            default_model=config.model_name,
            max_retries=3,
            timeout=30
        )
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize the provider (create HTTP session)"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.provider_config.timeout)
            headers = self.provider_config.get_headers()
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
    
    async def cleanup(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            self.session = None
    
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from the LLM"""
        pass
    
    @abstractmethod
    def _get_api_url(self) -> str:
        """Get the API endpoint URL"""
        pass
    
    @abstractmethod
    def _prepare_request_body(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare the request body for the API"""
        pass
    
    @abstractmethod
    def _parse_response(self, response_data: Dict[str, Any]) -> LLMResponse:
        """Parse the API response into LLMResponse"""
        pass
    
    def _prepare_messages(self, messages: List[Any]) -> List[Dict[str, str]]:
        """Convert messages to provider format"""
        return [
            {
                "role": msg.role.value,
                "content": msg.content
            }
            for msg in messages
        ]
    
    def _extract_rate_limit_info(self, headers: Dict[str, str]) -> Optional[RateLimitInfo]:
        """Extract rate limit information from response headers"""
        try:
            remaining = int(headers.get('x-ratelimit-remaining', headers.get('X-RateLimit-Remaining', 0)))
            limit = int(headers.get('x-ratelimit-limit', headers.get('X-RateLimit-Limit', 0)))
            reset = int(headers.get('x-ratelimit-reset', headers.get('X-RateLimit-Reset', 0)))
            
            if reset > 0:
                import datetime
                reset_time = datetime.datetime.fromtimestamp(reset)
            else:
                reset_time = datetime.datetime.now() + datetime.timedelta(minutes=1)
            
            return RateLimitInfo(
                requests_remaining=remaining,
                requests_limit=limit,
                reset_time=reset_time
            )
        except (ValueError, KeyError):
            return None


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider implementation"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.provider_config.supported_models = [
            "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
        ]
        
        if not self.provider_config.base_url:
            self.provider_config.base_url = "https://api.openai.com/v1"
    
    def _get_api_url(self) -> str:
        """Get OpenAI API URL"""
        return f"{self.provider_config.base_url}/chat/completions"
    
    def _prepare_request_body(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare request body for OpenAI API"""
        body = {
            "model": request.model,
            "messages": self._prepare_messages(request.messages),
            "temperature": request.temperature,
            "stream": request.stream
        }
        
        if request.max_tokens:
            body["max_tokens"] = request.max_tokens
        
        if request.tools:
            body["tools"] = request.tools
        
        if request.response_format:
            body["response_format"] = request.response_format
            
        return body
    
    def _parse_response(self, response_data: Dict[str, Any]) -> LLMResponse:
        """Parse OpenAI API response"""
        choice = response_data["choices"][0]
        message = choice["message"]
        
        usage = response_data.get("usage", {})
        
        return LLMResponse(
            content=message.get("content", ""),
            model=response_data.get("model", request.model if 'request' in locals() else ""),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            },
            finish_reason=choice.get("finish_reason"),
            tool_calls=message.get("tool_calls")
        )
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using OpenAI API"""
        if not self.session:
            await self.initialize()
        
        url = self._get_api_url()
        body = self._prepare_request_body(request)
        
        try:
            async with self.session.post(url, json=body) as response:
                if response.status == 429:
                    rate_limit_info = self._extract_rate_limit_info(response.headers)
                    raise LLMError(
                        error_type="rate_limit",
                        message="Rate limit exceeded",
                        provider="openai",
                        model=request.model,
                        details={"rate_limit_info": rate_limit_info.to_dict() if rate_limit_info else None}
                    )
                elif response.status >= 400:
                    error_data = await response.json()
                    raise LLMError(
                        error_type="api_error",
                        message=error_data.get("error", {}).get("message", "Unknown API error"),
                        provider="openai",
                        model=request.model,
                        details=error_data
                    )
                
                response_data = await response.json()
                return self._parse_response(response_data)
                
        except aiohttp.ClientError as e:
            raise LLMError(
                error_type="network_error",
                message=str(e),
                provider="openai",
                model=request.model
            )
    
    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        """Generate streaming response using OpenAI API"""
        if not self.session:
            await self.initialize()
        
        url = self._get_api_url()
        body = self._prepare_request_body(request)
        
        try:
            async with self.session.post(url, json=body) as response:
                if response.status == 429:
                    rate_limit_info = self._extract_rate_limit_info(response.headers)
                    raise LLMError(
                        error_type="rate_limit",
                        message="Rate limit exceeded",
                        provider="openai",
                        model=request.model,
                        details={"rate_limit_info": rate_limit_info.to_dict() if rate_limit_info else None}
                    )
                elif response.status >= 400:
                    error_data = await response.json()
                    raise LLMError(
                        error_type="api_error",
                        message=error_data.get("error", {}).get("message", "Unknown API error"),
                        provider="openai",
                        model=request.model,
                        details=error_data
                    )
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            yield StreamChunk(content="", is_final=True)
                            break
                        
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            if delta.get("content"):
                                yield StreamChunk(content=delta["content"])
                        except json.JSONDecodeError:
                            continue
                            
        except aiohttp.ClientError as e:
            raise LLMError(
                error_type="network_error",
                message=str(e),
                provider="openai",
                model=request.model
            )


class MoonShotProvider(BaseLLMProvider):
    """MoonShot AI provider implementation"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.provider_config.supported_models = [
            "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"
        ]
        
        if not self.provider_config.base_url:
            self.provider_config.base_url = "https://api.moonshot.cn/v1"
    
    def _get_api_url(self) -> str:
        """Get MoonShot API URL"""
        return f"{self.provider_config.base_url}/chat/completions"
    
    def _prepare_request_body(self, request: LLMRequest) -> Dict[str, Any]:
        """Prepare request body for MoonShot API"""
        body = {
            "model": request.model,
            "messages": self._prepare_messages(request.messages),
            "temperature": request.temperature,
            "stream": request.stream
        }
        
        if request.max_tokens:
            body["max_tokens"] = request.max_tokens
        
        if request.tools:
            body["tools"] = request.tools
            
        return body
    
    def _parse_response(self, response_data: Dict[str, Any]) -> LLMResponse:
        """Parse MoonShot API response"""
        choice = response_data["choices"][0]
        message = choice["message"]
        
        usage = response_data.get("usage", {})
        
        return LLMResponse(
            content=message.get("content", ""),
            model=response_data.get("model", request.model if 'request' in locals() else ""),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            },
            finish_reason=choice.get("finish_reason"),
            tool_calls=message.get("tool_calls")
        )
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using MoonShot API"""
        if not self.session:
            await self.initialize()
        
        url = self._get_api_url()
        body = self._prepare_request_body(request)
        
        try:
            async with self.session.post(url, json=body) as response:
                if response.status == 429:
                    rate_limit_info = self._extract_rate_limit_info(response.headers)
                    raise LLMError(
                        error_type="rate_limit",
                        message="Rate limit exceeded",
                        provider="moonshot",
                        model=request.model,
                        details={"rate_limit_info": rate_limit_info.to_dict() if rate_limit_info else None}
                    )
                elif response.status >= 400:
                    try:
                        error_data = await response.json()
                        message = error_data.get("error", {}).get("message", "Unknown API error")
                    except:
                        message = await response.text()
                    
                    raise LLMError(
                        error_type="api_error",
                        message=message,
                        provider="moonshot",
                        model=request.model,
                        details=error_data if 'error_data' in locals() else {}
                    )
                
                response_data = await response.json()
                return self._parse_response(response_data)
                
        except aiohttp.ClientError as e:
            raise LLMError(
                error_type="network_error",
                message=str(e),
                provider="moonshot",
                model=request.model
            )
    
    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[StreamChunk]:
        """Generate streaming response using MoonShot API"""
        if not self.session:
            await self.initialize()
        
        url = self._get_api_url()
        body = self._prepare_request_body(request)
        
        try:
            async with self.session.post(url, json=body) as response:
                if response.status == 429:
                    rate_limit_info = self._extract_rate_limit_info(response.headers)
                    raise LLMError(
                        error_type="rate_limit",
                        message="Rate limit exceeded",
                        provider="moonshot",
                        model=request.model,
                        details={"rate_limit_info": rate_limit_info.to_dict() if rate_limit_info else None}
                    )
                elif response.status >= 400:
                    try:
                        error_data = await response.json()
                        message = error_data.get("error", {}).get("message", "Unknown API error")
                    except:
                        message = await response.text()
                    
                    raise LLMError(
                        error_type="api_error",
                        message=message,
                        provider="moonshot",
                        model=request.model,
                        details=error_data if 'error_data' in locals() else {}
                    )
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            yield StreamChunk(content="", is_final=True)
                            break
                        
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            if delta.get("content"):
                                yield StreamChunk(content=delta["content"])
                        except json.JSONDecodeError:
                            continue
                            
        except aiohttp.ClientError as e:
            raise LLMError(
                error_type="network_error",
                message=str(e),
                provider="moonshot",
                model=request.model
            )


def create_provider(config: ModelConfig) -> BaseLLMProvider:
    """Factory function to create provider instances"""
    if config.provider == ConfigLLMProvider.OPENAI:
        return OpenAIProvider(config)
    elif config.provider == ConfigLLMProvider.MOONSHOT:
        return MoonShotProvider(config)
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")
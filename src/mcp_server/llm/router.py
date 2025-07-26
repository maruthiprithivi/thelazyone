"""
LLM Router Implementation

Provides intelligent routing between different LLM providers with load balancing,
failover, retry logic, and rate limiting support.
"""

import asyncio
import logging
import random
from typing import Dict, List, Optional, Any, AsyncIterator, Tuple
from datetime import datetime, timedelta
import time

from .models import (
    LLMRequest, LLMResponse, StreamChunk, LLMError, 
    RoutingRule, RetryConfig, RateLimitInfo, ConversationContext
)
from .providers import BaseLLMProvider, create_provider
from ..config import ModelConfig, LLMProvider as ConfigLLMProvider


logger = logging.getLogger(__name__)


class ProviderHealth:
    """Tracks health status of a provider"""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.is_healthy = True
        self.last_failure = None
        self.failure_count = 0
        self.success_count = 0
        self.last_success = None
        self.rate_limit_info = None
    
    def record_success(self):
        """Record a successful request"""
        self.success_count += 1
        self.last_success = datetime.now()
        self.is_healthy = True
        self.failure_count = 0  # Reset failure count on success
    
    def record_failure(self, error: LLMError):
        """Record a failed request"""
        self.failure_count += 1
        self.last_failure = datetime.now()
        
        # Mark as unhealthy if too many failures
        if self.failure_count >= 3:
            self.is_healthy = False
    
    def record_rate_limit(self, rate_limit_info: RateLimitInfo):
        """Record rate limit information"""
        self.rate_limit_info = rate_limit_info
        if rate_limit_info.is_rate_limited:
            self.is_healthy = False
    
    def should_retry(self) -> bool:
        """Check if provider should be retried"""
        if not self.is_healthy:
            # Allow retry after 60 seconds of last failure
            if self.last_failure and datetime.now() - self.last_failure > timedelta(seconds=60):
                return True
        return self.is_healthy


class RateLimiter:
    """Simple rate limiter using sliding window"""
    
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
    
    def is_allowed(self) -> bool:
        """Check if request is allowed under rate limit"""
        now = datetime.now()
        # Remove old requests outside the window
        self.requests = [
            req_time for req_time in self.requests 
            if now - req_time < timedelta(seconds=self.window_seconds)
        ]
        
        return len(self.requests) < self.max_requests
    
    def record_request(self):
        """Record a request"""
        self.requests.append(datetime.now())


class LLMRouter:
    """Intelligent router for LLM providers"""
    
    def __init__(self, providers: List[ModelConfig], default_provider: str = None):
        self.providers = {config.provider.value: config for config in providers}
        self.default_provider = default_provider or ConfigLLMProvider.OPENAI.value
        self.provider_instances: Dict[str, BaseLLMProvider] = {}
        self.health_status: Dict[str, ProviderHealth] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.retry_config = RetryConfig()
        self.routing_rules: List[RoutingRule] = []
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        
        # Initialize health tracking for each provider
        for provider_name in self.providers:
            self.health_status[provider_name] = ProviderHealth(provider_name)
            self.rate_limiters[provider_name] = RateLimiter(
                max_requests=60,  # Default 60 requests per minute
                window_seconds=60
            )
        
        # Set up default routing rules
        self._setup_default_routing_rules()
    
    def _setup_default_routing_rules(self):
        """Set up default routing rules"""
        self.routing_rules = [
            RoutingRule(
                provider=ConfigLLMProvider.OPENAI.value,
                priority=1,
                weight=1.0
            ),
            RoutingRule(
                provider=ConfigLLMProvider.MOONSHOT.value,
                priority=2,
                weight=1.0,
                fallback_providers=[ConfigLLMProvider.OPENAI.value]
            )
        ]
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize all providers"""
        for provider_name, config in self.providers.items():
            try:
                provider = create_provider(config)
                await provider.initialize()
                self.provider_instances[provider_name] = provider
                logger.info(f"Initialized provider: {provider_name}")
            except Exception as e:
                logger.error(f"Failed to initialize provider {provider_name}: {e}")
                self.health_status[provider_name].record_failure(
                    LLMError(
                        error_type="initialization_error",
                        message=str(e),
                        provider=provider_name,
                        model=config.model_name
                    )
                )
    
    async def cleanup(self):
        """Clean up all providers"""
        for provider in self.provider_instances.values():
            await provider.cleanup()
        self.provider_instances.clear()
    
    def get_available_providers(self) -> List[str]:
        """Get list of available and healthy providers"""
        available = []
        for provider_name, health in self.health_status.items():
            if provider_name in self.provider_instances and health.should_retry():
                available.append(provider_name)
        return available
    
    def select_provider(self, preferred_provider: Optional[str] = None) -> Optional[str]:
        """Select the best provider for a request"""
        available = self.get_available_providers()
        
        if not available:
            return None
        
        # If preferred provider is specified and available, use it
        if preferred_provider and preferred_provider in available:
            return preferred_provider
        
        # Use routing rules to select provider
        for rule in sorted(self.routing_rules, key=lambda r: r.priority):
            if rule.provider in available:
                # Check rate limiter
                if self.rate_limiters[rule.provider].is_allowed():
                    return rule.provider
        
        # Fallback to random selection from available providers
        return random.choice(available) if available else None
    
    async def generate(
        self, 
        request: LLMRequest, 
        provider: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> LLMResponse:
        """Generate response with retry logic and provider selection"""
        
        # Add conversation context if provided
        if conversation_id:
            context = self._get_or_create_context(conversation_id, provider)
            request.messages = context.messages + request.messages
        
        selected_provider = self.select_provider(provider) or self.default_provider
        
        last_error = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                provider_instance = self.provider_instances[selected_provider]
                
                # Record rate limit check
                if not self.rate_limiters[selected_provider].is_allowed():
                    raise LLMError(
                        error_type="rate_limit",
                        message=f"Rate limit exceeded for {selected_provider}",
                        provider=selected_provider,
                        model=request.model
                    )
                
                self.rate_limiters[selected_provider].record_request()
                
                # Generate response
                response = await provider_instance.generate(request)
                
                # Update health status
                self.health_status[selected_provider].record_success()
                
                # Update conversation context
                if conversation_id:
                    self._update_context(conversation_id, selected_provider, request, response)
                
                return response
                
            except LLMError as e:
                last_error = e
                self.health_status[selected_provider].record_failure(e)
                
                # Check if error is retryable
                if not e.retryable or attempt >= self.retry_config.max_retries:
                    break
                
                # Try fallback providers
                fallback_providers = self._get_fallback_providers(selected_provider)
                if fallback_providers:
                    for fallback_provider in fallback_providers:
                        if fallback_provider in self.provider_instances:
                            selected_provider = fallback_provider
                            break
                
                # Calculate delay
                delay = self.retry_config.get_delay(attempt)
                await asyncio.sleep(delay)
                
            except Exception as e:
                # Wrap unexpected errors
                last_error = LLMError(
                    error_type="unexpected_error",
                    message=str(e),
                    provider=selected_provider,
                    model=request.model,
                    retryable=False
                )
                break
        
        # If all retries failed, raise the last error
        if last_error:
            raise last_error
        
        raise LLMError(
            error_type="no_providers_available",
            message="No providers available after retries",
            provider="router",
            model=request.model
        )
    
    async def generate_stream(
        self, 
        request: LLMRequest, 
        provider: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> AsyncIterator[StreamChunk]:
        """Generate streaming response with retry logic"""
        
        # Add conversation context if provided
        if conversation_id:
            context = self._get_or_create_context(conversation_id, provider)
            request.messages = context.messages + request.messages
        
        selected_provider = self.select_provider(provider) or self.default_provider
        
        last_error = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                provider_instance = self.provider_instances[selected_provider]
                
                # Check rate limit
                if not self.rate_limiters[selected_provider].is_allowed():
                    raise LLMError(
                        error_type="rate_limit",
                        message=f"Rate limit exceeded for {selected_provider}",
                        provider=selected_provider,
                        model=request.model
                    )
                
                self.rate_limiters[selected_provider].record_request()
                
                # Generate streaming response
                full_content = ""
                async for chunk in provider_instance.generate_stream(request):
                    if chunk.is_final:
                        # Update health status and context
                        self.health_status[selected_provider].record_success()
                        if conversation_id:
                            response = LLMResponse(
                                content=full_content,
                                model=request.model,
                                usage=chunk.usage or {}
                            )
                            self._update_context(conversation_id, selected_provider, request, response)
                    else:
                        full_content += chunk.content
                    
                    yield chunk
                
                return
                
            except LLMError as e:
                last_error = e
                self.health_status[selected_provider].record_failure(e)
                
                if not e.retryable or attempt >= self.retry_config.max_retries:
                    break
                
                # Try fallback providers
                fallback_providers = self._get_fallback_providers(selected_provider)
                if fallback_providers:
                    for fallback_provider in fallback_providers:
                        if fallback_provider in self.provider_instances:
                            selected_provider = fallback_provider
                            break
                
                delay = self.retry_config.get_delay(attempt)
                await asyncio.sleep(delay)
        
        # Yield error as final chunk
        if last_error:
            yield StreamChunk(
                content=f"",
                is_final=True,
                metadata={"error": last_error.to_dict()}
            )
    
    def _get_fallback_providers(self, current_provider: str) -> List[str]:
        """Get fallback providers for a given provider"""
        for rule in self.routing_rules:
            if rule.provider == current_provider:
                return rule.fallback_providers
        return []
    
    def _get_or_create_context(
        self, 
        conversation_id: str, 
        provider: Optional[str] = None
    ) -> ConversationContext:
        """Get or create conversation context"""
        if conversation_id not in self.conversation_contexts:
            self.conversation_contexts[conversation_id] = ConversationContext(
                session_id=conversation_id,
                provider=provider or self.default_provider,
                model=self.providers[provider or self.default_provider].model_name
            )
        return self.conversation_contexts[conversation_id]
    
    def _update_context(
        self, 
        conversation_id: str, 
        provider: str, 
        request: LLMRequest, 
        response: LLMResponse
    ):
        """Update conversation context with new messages"""
        context = self.conversation_contexts[conversation_id]
        
        # Add user messages
        for msg in request.messages:
            if msg.role.value == "user":
                context.add_message(msg)
        
        # Add assistant response
        from .models import Message, MessageRole
        context.add_message(Message(
            role=MessageRole.ASSISTANT,
            content=response.content
        ))
    
    def get_provider_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all providers"""
        health = {}
        for provider_name, health_status in self.health_status.items():
            health[provider_name] = {
                "is_healthy": health_status.is_healthy,
                "success_count": health_status.success_count,
                "failure_count": health_status.failure_count,
                "last_success": health_status.last_success.isoformat() if health_status.last_success else None,
                "last_failure": health_status.last_failure.isoformat() if health_status.last_failure else None
            }
        return health
    
    def reset_provider_health(self, provider_name: str):
        """Reset health status for a provider"""
        if provider_name in self.health_status:
            self.health_status[provider_name] = ProviderHealth(provider_name)
    
    def add_routing_rule(self, rule: RoutingRule):
        """Add a custom routing rule"""
        self.routing_rules.append(rule)
        # Sort by priority
        self.routing_rules.sort(key=lambda r: r.priority)
    
    def clear_routing_rules(self):
        """Clear all routing rules and reset to defaults"""
        self._setup_default_routing_rules()
    
    def update_retry_config(self, retry_config: RetryConfig):
        """Update retry configuration"""
        self.retry_config = retry_config
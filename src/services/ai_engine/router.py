"""AI Model Router - Routes requests to appropriate AI provider.

This module provides intelligent model selection and routing based on:
- Task type and requirements
- Provider availability
- Cost and performance considerations
"""

from typing import Dict, Optional, Type

import structlog

from src.config.ai_settings import (
    AIModelProvider,
    ai_engine_settings,
    anthropic_settings,
    dashscope_settings,
    deepseek_settings,
    openai_settings,
)
from src.services.ai_engine.base import AIModelClient
from src.services.ai_engine.providers.dashscope import DashScopeClient

logger = structlog.get_logger()

# Registry of available clients
CLIENT_REGISTRY: Dict[AIModelProvider, Type[AIModelClient]] = {
    AIModelProvider.DASHSCOPE: DashScopeClient,
    # Future providers:
    # AIModelProvider.OPENAI: OpenAIClient,
    # AIModelProvider.ANTHROPIC: AnthropicClient,
    # AIModelProvider.DEEPSEEK: DeepSeekClient,
}


class ModelRouter:
    """Router for AI model requests.

    Provides:
    - Model selection based on task type
    - Provider fallback mechanism
    - Load balancing across providers
    """

    # Task type to model mapping
    TASK_MODELS = {
        # General chat and reasoning
        "chat": "qwen-max",
        "reasoning": "qwen-max",
        "analysis": "qwen-max",

        # Code-related tasks
        "code": "qwen-coder-plus",
        "code_review": "qwen-coder-plus",
        "code_generation": "qwen-coder-plus",

        # Long text processing
        "summarization": "qwen-max-longcontext",
        "document_analysis": "qwen-max-longcontext",
        "long_context": "qwen-max-longcontext",

        # Creative tasks
        "creative": "qwen-max",
        "writing": "qwen-max",

        # Quick/simple tasks
        "quick": "qwen-turbo",
        "simple": "qwen-turbo",
    }

    def __init__(self):
        """Initialize the model router."""
        self._logger = logger.bind(component="ModelRouter")
        self._clients: Dict[AIModelProvider, AIModelClient] = {}

    def _get_client(self, provider: AIModelProvider) -> Optional[AIModelClient]:
        """Get or create client for a provider.

        Args:
            provider: AI model provider

        Returns:
            Client instance or None if not configured
        """
        if provider in self._clients:
            return self._clients[provider]

        client_class = CLIENT_REGISTRY.get(provider)
        if not client_class:
            self._logger.warning("provider_not_registered", provider=provider)
            return None

        # Get settings based on provider
        settings_map = {
            AIModelProvider.DASHSCOPE: dashscope_settings,
            AIModelProvider.OPENAI: openai_settings,
            AIModelProvider.ANTHROPIC: anthropic_settings,
            AIModelProvider.DEEPSEEK: deepseek_settings,
        }

        settings = settings_map.get(provider)
        if not settings or not settings.api_key:
            self._logger.warning("provider_not_configured", provider=provider)
            return None

        # Create client
        try:
            client = client_class(
                api_key=settings.api_key,
                base_url=settings.base_url,
            )
            self._clients[provider] = client
            self._logger.info("client_initialized", provider=provider)
            return client

        except Exception as e:
            self._logger.error("client_init_failed", provider=provider, error=str(e))
            return None

    def select_model(self, task_type: str = "chat", preferred_model: Optional[str] = None) -> tuple:
        """Select appropriate model for a task.

        Args:
            task_type: Type of task (chat, code, summarization, etc.)
            preferred_model: User-preferred model (optional)

        Returns:
            Tuple of (provider, model_name)
        """
        # Use preferred model if specified
        if preferred_model:
            return self._resolve_model(preferred_model)

        # Auto-select based on task type
        if ai_engine_settings.selection_strategy == "auto":
            model = self.TASK_MODELS.get(task_type, ai_engine_settings.default_model)
            return self._resolve_model(model)

        # Use default
        return (
            ai_engine_settings.default_provider,
            ai_engine_settings.default_model,
        )

    def _resolve_model(self, model_name: str) -> tuple:
        """Resolve model name to provider and model.

        Args:
            model_name: Model name or identifier

        Returns:
            Tuple of (provider, model_name)
        """
        # DashScope models
        dashscope_models = [
            "qwen-max", "qwen-max-longcontext",
            "qwen-plus", "qwen-turbo",
            "qwen-coder-plus", "qwen-coder-turbo",
        ]

        if model_name in dashscope_models:
            return (AIModelProvider.DASHSCOPE, model_name)

        # Default to configured default
        return (
            ai_engine_settings.default_provider,
            ai_engine_settings.default_model,
        )

    async def get_client_for_task(
        self,
        task_type: str = "chat",
        preferred_model: Optional[str] = None,
    ) -> tuple:
        """Get appropriate client for a task.

        Args:
            task_type: Type of task
            preferred_model: Preferred model name

        Returns:
            Tuple of (client, model_name)
        """
        provider, model = self.select_model(task_type, preferred_model)

        client = self._get_client(provider)
        if not client:
            # Try fallback providers
            for fallback in [AIModelProvider.DASHSCOPE]:  # Add more fallbacks
                if fallback != provider:
                    client = self._get_client(fallback)
                    if client:
                        model = client.get_default_model(task_type)
                        self._logger.info(
                            "using_fallback_provider",
                            original=provider,
                            fallback=fallback,
                        )
                        break

        if not client:
            raise RuntimeError("No AI provider available")

        return (client, model)

    async def close_all(self) -> None:
        """Close all client connections."""
        for provider, client in self._clients.items():
            try:
                await client.close()
                self._logger.info("client_closed", provider=provider)
            except Exception as e:
                self._logger.error("client_close_failed", provider=provider, error=str(e))
        self._clients.clear()


# Global router instance
model_router = ModelRouter()

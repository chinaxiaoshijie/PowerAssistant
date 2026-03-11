"""AI Model abstraction layer.

This module provides a unified interface for different AI model providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import structlog

logger = structlog.get_logger()


@dataclass
class Message:
    """Chat message structure."""

    role: str  # "system", "user", "assistant"
    content: str
    name: Optional[str] = None


@dataclass
class ChatCompletionRequest:
    """Chat completion request parameters."""

    messages: List[Message]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatCompletionResponse:
    """Chat completion response."""

    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingRequest:
    """Embedding request parameters."""

    input: Union[str, List[str]]
    model: Optional[str] = None


@dataclass
class EmbeddingResponse:
    """Embedding response."""

    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int] = field(default_factory=dict)


class AIModelClient(ABC):
    """Abstract base class for AI model clients.

    All AI provider implementations should inherit from this class
    and implement the abstract methods.
    """

    def __init__(self, api_key: str, base_url: str, **kwargs):
        """Initialize the AI model client.

        Args:
            api_key: API key for authentication
            base_url: Base URL for the API
            **kwargs: Additional provider-specific parameters
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.extra_params = kwargs
        self._logger = logger.bind(client=self.__class__.__name__)

    @abstractmethod
    async def chat_complete(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        """Generate chat completion.

        Args:
            request: Chat completion request parameters

        Returns:
            Chat completion response
        """
        pass

    @abstractmethod
    async def chat_complete_stream(
        self,
        request: ChatCompletionRequest,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming chat completion.

        Args:
            request: Chat completion request parameters

        Yields:
            Text chunks as they are generated
        """
        pass

    @abstractmethod
    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResponse:
        """Generate embeddings for text.

        Args:
            request: Embedding request parameters

        Returns:
            Embedding response
        """
        pass

    @abstractmethod
    def get_default_model(self, task_type: str = "chat") -> str:
        """Get default model for a task type.

        Args:
            task_type: Type of task (chat, completion, embedding, etc.)

        Returns:
            Default model name
        """
        pass

    async def close(self) -> None:
        """Close client resources."""
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

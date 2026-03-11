"""AI Engine module for management assistant.

This module provides a unified interface for multiple AI providers.

Example usage:
    >>> from src.services.ai_engine import ai_engine
    >>>
    >>> # Simple text generation
    >>> response = await ai_engine.generate_text("Hello, how are you?")
    >>>
    >>> # Document summarization
    >>> summary = await ai_engine.summarize_document(document_text)
    >>>
    >>> # Data analysis
    >>> insights = await ai_engine.analyze_data(metrics_data)
    >>>
    >>> # Report generation
    >>> section = await ai_engine.generate_report_section("summary", data)

Available providers:
    - DashScope (Alibaba Cloud): qwen-max, qwen-plus, qwen-coder-plus
    - (Future) OpenAI: gpt-4, gpt-3.5-turbo
    - (Future) Anthropic: claude-3
    - (Future) DeepSeek: deepseek-chat
"""

from src.services.ai_engine.base import (
    AIModelClient,
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    Message,
)
from src.services.ai_engine.router import model_router
from src.services.ai_engine.service import AIEngineService, ai_engine

__all__ = [
    # Base classes
    "AIModelClient",
    "Message",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "EmbeddingRequest",
    "EmbeddingResponse",
    # Router
    "model_router",
    # Service
    "AIEngineService",
    "ai_engine",
]

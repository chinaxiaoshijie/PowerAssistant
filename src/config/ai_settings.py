"""AI Engine configuration settings.

This module provides configuration for multiple AI providers including:
- Alibaba Cloud DashScope (Tongyi Qianwen)
- OpenAI (GPT)
- Anthropic (Claude)
- DeepSeek
"""

from enum import Enum
from typing import Optional

from pydantic_settings import BaseSettings


class AIModelProvider(str, Enum):
    """Supported AI model providers."""

    DASHSCOPE = "dashscope"  # Alibaba Cloud
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


class DashScopeSettings(BaseSettings):
    """Alibaba Cloud DashScope (Tongyi Qianwen) settings."""

    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/api/v1"

    # Available models
    model_chat: str = "qwen-max"  # 通义千问 Max
    model_long: str = "qwen-max-longcontext"  # 长文本模型
    model_coder: str = "qwen-coder-plus"  # 代码模型

    class Config:
        env_prefix = "DASHSCOPE_"
        env_file = ".env"
        extra = "ignore"


class OpenAISettings(BaseSettings):
    """OpenAI API settings."""

    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4"

    class Config:
        env_prefix = "OPENAI_"
        env_file = ".env"
        extra = "ignore"


class AnthropicSettings(BaseSettings):
    """Anthropic (Claude) API settings."""

    api_key: Optional[str] = None
    base_url: str = "https://api.anthropic.com"
    model: str = "claude-3-sonnet-20240229"

    class Config:
        env_prefix = "ANTHROPIC_"
        env_file = ".env"
        extra = "ignore"


class DeepSeekSettings(BaseSettings):
    """DeepSeek API settings."""

    api_key: Optional[str] = None
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"

    class Config:
        env_prefix = "DEEPSEEK_"
        env_file = ".env"
        extra = "ignore"


class AIEngineSettings(BaseSettings):
    """AI Engine global settings."""

    # Default model provider
    default_provider: AIModelProvider = AIModelProvider.DASHSCOPE

    # Default model for general tasks
    default_model: str = "qwen-max"

    # Model selection strategy
    # - "default": Always use default model
    # - "auto": Auto-select based on task type
    selection_strategy: str = "auto"

    # Request timeout (seconds)
    request_timeout: int = 120

    # Max retries
    max_retries: int = 3

    # Temperature for generation (0-2)
    default_temperature: float = 0.7

    # Max tokens per request
    max_tokens: int = 4096

    class Config:
        env_prefix = "AI_"
        env_file = ".env"
        extra = "ignore"


# Global instances
dashscope_settings = DashScopeSettings()
openai_settings = OpenAISettings()
anthropic_settings = AnthropicSettings()
deepseek_settings = DeepSeekSettings()
ai_engine_settings = AIEngineSettings()

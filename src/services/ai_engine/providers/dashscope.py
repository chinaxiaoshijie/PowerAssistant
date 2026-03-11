"""Alibaba Cloud DashScope (Tongyi Qianwen) client implementation.

This module provides integration with Alibaba Cloud's DashScope platform,
which hosts the Tongyi Qianwen (Qwen) series of models.

Documentation: https://help.aliyun.com/document_detail/2587494.html
"""

import json
from typing import AsyncGenerator, Dict, List, Optional, Any

import aiohttp
import structlog

from src.config.ai_settings import dashscope_settings
from src.services.ai_engine.base import (
    AIModelClient,
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    Message,
)

logger = structlog.get_logger()


class DashScopeClient(AIModelClient):
    """Alibaba Cloud DashScope API client.

    Supports models:
    - qwen-max: High-performance general model (recommended)
    - qwen-max-longcontext: Long context model (30k tokens)
    - qwen-plus: Balanced performance and cost
    - qwen-turbo: Fast and cost-effective
    - qwen-coder-plus: Code generation optimized
    - text-embedding-v2: Text embeddings
    """

    # Model mapping
    CHAT_MODELS = {
        "qwen-max": "qwen-max",
        "qwen-max-longcontext": "qwen-max-longcontext",
        "qwen-plus": "qwen-plus",
        "qwen-turbo": "qwen-turbo",
        "qwen-coder": "qwen-coder-plus",
    }

    EMBEDDING_MODELS = {
        "text-embedding-v2": "text-embedding-v2",
        "text-embedding-v1": "text-embedding-v1",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs,
    ):
        """Initialize DashScope client.

        Args:
            api_key: DashScope API key (defaults to settings)
            base_url: API base URL (defaults to settings)
            **kwargs: Additional parameters
        """
        self._api_key = api_key or dashscope_settings.api_key
        self._base_url = (base_url or dashscope_settings.base_url).rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None
        self._logger = logger.bind(client="DashScopeClient")

        super().__init__(self._api_key, self._base_url, **kwargs)

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=120),
            )
        return self._session

    def _convert_messages(
        self,
        messages: List[Message],
    ) -> List[Dict[str, str]]:
        """Convert internal messages to DashScope format.

        Args:
            messages: List of Message objects

        Returns:
            List of message dicts in DashScope format
        """
        result = []
        for msg in messages:
            message_dict = {"role": msg.role, "content": msg.content}
            if msg.name:
                message_dict["name"] = msg.name
            result.append(message_dict)
        return result

    async def chat_complete(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        """Generate chat completion using DashScope.

        Args:
            request: Chat completion request

        Returns:
            Chat completion response

        Raises:
            Exception: If API call fails
        """
        model = request.model or self.get_default_model("chat")

        self._logger.info(
            "chat_completion_request",
            model=model,
            message_count=len(request.messages),
        )

        url = f"{self._base_url}/services/aigc/text-generation/generation"

        payload = {
            "model": model,
            "input": {
                "messages": self._convert_messages(request.messages),
            },
            "parameters": {
                "temperature": request.temperature,
                "max_tokens": request.max_tokens or 2048,
                "top_p": request.top_p or 0.8,
                "result_format": "message",
            },
        }

        # Add any extra parameters
        payload["parameters"].update(request.extra_params)

        session = self._get_session()

        try:
            async with session.post(url, json=payload) as response:
                response_text = await response.text()

                if response.status != 200:
                    self._logger.error(
                        "dashscope_api_error",
                        status=response.status,
                        response=response_text,
                    )
                    raise Exception(
                        f"DashScope API error: {response.status} - {response_text}"
                    )

                data = json.loads(response_text)

                if "error_code" in data:
                    self._logger.error(
                        "dashscope_error",
                        error_code=data.get("error_code"),
                        error_message=data.get("error_message"),
                    )
                    raise Exception(
                        f"DashScope error: {data.get('error_code')} - {data.get('error_message')}"
                    )

                # Extract response content
                output = data.get("output", {})
                choices = output.get("choices", [])

                if not choices:
                    raise Exception("No response generated")

                message = choices[0].get("message", {})
                content = message.get("content", "")
                finish_reason = choices[0].get("finish_reason")

                # Get usage info
                usage = data.get("usage", {})
                usage_dict = {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }

                self._logger.info(
                    "chat_completion_success",
                    model=model,
                    usage=usage_dict,
                    finish_reason=finish_reason,
                )

                return ChatCompletionResponse(
                    content=content,
                    model=model,
                    usage=usage_dict,
                    finish_reason=finish_reason,
                    raw_response=data,
                )

        except aiohttp.ClientError as e:
            self._logger.error("dashscope_request_error", error=str(e))
            raise Exception(f"DashScope request failed: {e}")

    async def chat_complete_stream(
        self,
        request: ChatCompletionRequest,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming chat completion.

        Args:
            request: Chat completion request

        Yields:
            Text chunks as they are generated
        """
        model = request.model or self.get_default_model("chat")

        url = f"{self._base_url}/services/aigc/text-generation/generation"

        payload = {
            "model": model,
            "input": {
                "messages": self._convert_messages(request.messages),
            },
            "parameters": {
                "temperature": request.temperature,
                "max_tokens": request.max_tokens or 2048,
                "result_format": "message",
            },
        }

        session = self._get_session()

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"DashScope error: {response.status} - {error_text}")

                # For now, return the full response
                # DashScope streaming requires SSE handling
                data = await response.json()
                output = data.get("output", {})
                choices = output.get("choices", [])

                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    yield content

        except Exception as e:
            self._logger.error("stream_error", error=str(e))
            raise

    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResponse:
        """Generate text embeddings.

        Args:
            request: Embedding request

        Returns:
            Embedding response
        """
        model = request.model or self.get_default_model("embedding")

        url = f"{self._base_url}/api/v1/services/embeddings/text-embedding/text-embedding"

        # Handle single string or list of strings
        texts = request.input if isinstance(request.input, list) else [request.input]

        payload = {
            "model": model,
            "input": {
                "texts": texts,
            },
        }

        session = self._get_session()

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"DashScope error: {response.status} - {error_text}")

                data = await response.json()

                if "error_code" in data:
                    raise Exception(
                        f"DashScope error: {data.get('error_code')} - {data.get('error_message')}"
                    )

                embeddings = data.get("output", {}).get("embeddings", [])
                usage = data.get("usage", {})

                return EmbeddingResponse(
                    embeddings=[e["embedding"] for e in embeddings],
                    model=model,
                    usage={
                        "prompt_tokens": usage.get("total_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    },
                )

        except Exception as e:
            self._logger.error("embedding_error", error=str(e))
            raise

    def get_default_model(self, task_type: str = "chat") -> str:
        """Get default model for a task type.

        Args:
            task_type: Type of task (chat, completion, embedding, code)

        Returns:
            Default model name
        """
        defaults = {
            "chat": dashscope_settings.model_chat,
            "long": dashscope_settings.model_long,
            "code": dashscope_settings.model_coder,
            "embedding": "text-embedding-v2",
        }
        return defaults.get(task_type, dashscope_settings.model_chat)

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

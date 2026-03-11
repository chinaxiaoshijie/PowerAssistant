"""Tests for AI Engine service."""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.ai_engine.base import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
)
from src.services.ai_engine.router import ModelRouter
from src.services.ai_engine.service import AIEngineService


class TestAIEngineService:
    """Test AI Engine Service."""

    @pytest.fixture
    def ai_service(self):
        """Create AI engine service."""
        return AIEngineService()

    @pytest.mark.asyncio
    async def test_chat(self, ai_service):
        """Test chat method."""
        messages = [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="Hello!"),
        ]

        mock_response = ChatCompletionResponse(
            content="Hello! How can I help?",
            model="qwen-max",
            usage={"total_tokens": 25},
        )

        with patch.object(ai_service._router, 'get_client_for_task') as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat_complete = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = (mock_client, "qwen-max")

            response = await ai_service.chat(messages)

            assert response.content == "Hello! How can I help?"
            assert response.model == "qwen-max"

    @pytest.mark.asyncio
    async def test_generate_text(self, ai_service):
        """Test text generation."""
        mock_response = ChatCompletionResponse(
            content="Generated response",
            model="qwen-max",
            usage={"total_tokens": 30},
        )

        with patch.object(ai_service, 'chat') as mock_chat:
            mock_chat.return_value = mock_response

            result = await ai_service.generate_text("Test prompt")

            assert result == "Generated response"
            mock_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_document(self, ai_service):
        """Test document summarization."""
        doc_text = "This is a long document about AI in education." * 10

        with patch.object(ai_service, 'generate_text') as mock_generate:
            mock_generate.return_value = "Document summary: AI in education is important."

            summary = await ai_service.summarize_document(doc_text, max_length=100)

            assert "summary" in summary.lower()
            mock_generate.assert_called_once()

            # Check system prompt contains summarization instructions
            call_args = mock_generate.call_args
            assert "summarization" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_analyze_data(self, ai_service):
        """Test data analysis."""
        data = {
            "metric1": 100,
            "metric2": 200,
        }

        analysis_json = json.dumps({
            "summary": "Test summary",
            "key_insights": ["insight1"],
            "recommendations": ["rec1"],
        })

        with patch.object(ai_service, 'generate_text') as mock_generate:
            mock_generate.return_value = analysis_json

            result = await ai_service.analyze_data(data)

            assert "summary" in result
            assert result["summary"] == "Test summary"

    @pytest.mark.asyncio
    async def test_analyze_data_invalid_json(self, ai_service):
        """Test data analysis with invalid JSON response."""
        data = {"metric": 100}

        with patch.object(ai_service, 'generate_text') as mock_generate:
            mock_generate.return_value = "Plain text response"

            result = await ai_service.analyze_data(data)

            assert "summary" in result
            assert result["summary"] == "Plain text response"


class TestModelRouter:
    """Test Model Router."""

    def test_select_model_for_task(self):
        """Test model selection for different tasks."""
        router = ModelRouter()

        # Test chat task
        provider, model = router.select_model("chat")
        assert model == "qwen-max"

        # Test code task
        provider, model = router.select_model("code")
        assert model == "qwen-coder-plus"

        # Test summarization task
        provider, model = router.select_model("summarization")
        assert model == "qwen-max-longcontext"

    def test_select_model_with_preference(self):
        """Test model selection with user preference."""
        router = ModelRouter()

        provider, model = router.select_model("chat", preferred_model="qwen-plus")
        assert model == "qwen-plus"

    def test_resolve_model_dashscope(self):
        """Test model resolution for DashScope."""
        router = ModelRouter()

        provider, model = router._resolve_model("qwen-max")
        assert provider.value == "dashscope"
        assert model == "qwen-max"

        provider, model = router._resolve_model("qwen-coder-plus")
        assert model == "qwen-coder-plus"


class TestChatCompletionRequest:
    """Test Chat Completion Request dataclass."""

    def test_request_creation(self):
        """Test request creation."""
        messages = [
            Message(role="user", content="Hello"),
        ]

        request = ChatCompletionRequest(
            messages=messages,
            model="qwen-max",
            temperature=0.7,
            max_tokens=1000,
            stream=False,
        )

        assert request.messages == messages
        assert request.model == "qwen-max"
        assert request.temperature == 0.7

    def test_request_defaults(self):
        """Test request default values."""
        messages = [Message(role="user", content="Hi")]

        request = ChatCompletionRequest(messages=messages)

        assert request.temperature == 0.7
        assert request.stream is False
        assert request.max_tokens is None


class TestChatCompletionResponse:
    """Test Chat Completion Response dataclass."""

    def test_response_creation(self):
        """Test response creation."""
        response = ChatCompletionResponse(
            content="Test response",
            model="qwen-max",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            finish_reason="stop",
        )

        assert response.content == "Test response"
        assert response.model == "qwen-max"
        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 20
        assert response.finish_reason == "stop"

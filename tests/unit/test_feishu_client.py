"""Tests for Feishu client."""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
from pydantic import ValidationError

from src.schemas.feishu import (
    FeishuDepartmentRaw,
    FeishuDepartmentListResponse,
    FeishuUserRaw,
    FeishuUserListResponse,
    FeishuTokenResponse,
)
from src.services.feishu.client import FeishuClient, FeishuAPIError, TokenInfo


class TestTokenInfo:
    """Test TokenInfo dataclass."""

    def test_token_not_expired(self):
        """Test token not expired check."""
        future = datetime.utcnow() + timedelta(hours=1)
        token = TokenInfo(token="test_token", expires_at=future)
        assert not token.is_expired

    def test_token_expired(self):
        """Test token expired check."""
        past = datetime.utcnow() - timedelta(hours=1)
        token = TokenInfo(token="test_token", expires_at=past)
        assert token.is_expired

    def test_token_expires_soon(self):
        """Test token expiring within buffer time."""
        soon = datetime.utcnow() + timedelta(minutes=5)
        token = TokenInfo(token="test_token", expires_at=soon)
        assert token.is_expired  # 10 minute buffer


class TestFeishuClientInitialization:
    """Test Feishu client initialization."""

    def test_client_init_with_settings(self, mock_feishu_settings):
        """Test client initialization with settings."""
        client = FeishuClient(settings=mock_feishu_settings)
        assert client._settings == mock_feishu_settings
        assert client._token_info is None
        assert client._session is None

    def test_client_init_without_settings(self):
        """Test client initialization without settings raises error."""
        # Patch the settings module that the client imports from
        with patch('src.config.settings.settings') as mock_global_settings:
            mock_global_settings.feishu = None
            with pytest.raises(ValueError, match="Feishu settings not configured"):
                FeishuClient()


class TestFeishuClientToken:
    """Test Feishu client token management."""

    @pytest.mark.asyncio
    async def test_get_access_token_success(self, mock_feishu_settings, mock_session, mock_response):
        """Test successful token acquisition."""
        mock_resp = mock_response(
            status=200,
            json_data={
                "code": 0,
                "msg": "ok",
                "tenant_access_token": "test_token_123",
                "expire": 7200,
            }
        )

        # Set up mock response
        mock_session._mock_response = mock_resp

        client = FeishuClient(settings=mock_feishu_settings, session=mock_session)
        token = await client._get_access_token()

        assert token == "test_token_123"
        assert client._token_info is not None
        assert client._token_info.token == "test_token_123"

    @pytest.mark.asyncio
    async def test_get_access_token_api_error(self, mock_feishu_settings, mock_session, mock_response):
        """Test token acquisition with API error."""
        mock_resp = mock_response(
            status=200,
            json_data={
                "code": 99991663,
                "msg": "Invalid app_id or app_secret",
            }
        )

        mock_session._mock_response = mock_resp

        client = FeishuClient(settings=mock_feishu_settings, session=mock_session)
        with pytest.raises(FeishuAPIError) as exc_info:
            await client._get_access_token()

        assert "Invalid app_id or app_secret" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_access_token_cached(self, mock_feishu_settings):
        """Test token caching behavior."""
        future = datetime.utcnow() + timedelta(hours=1)
        client = FeishuClient(settings=mock_feishu_settings)
        client._token_info = TokenInfo(token="cached_token", expires_at=future)

        token = await client._get_access_token()
        assert token == "cached_token"


class TestFeishuClientDepartments:
    """Test Feishu client department operations."""

    @pytest.mark.asyncio
    async def test_list_departments(self, mock_feishu_settings, mock_session, mock_response, sample_feishu_departments):
        """Test listing departments."""
        mock_resp = mock_response(
            status=200,
            json_data={
                "code": 0,
                "data": {
                    "items": [
                        {
                            "department_id": dept.department_id,
                            "name": dept.name,
                            "parent_department_id": dept.parent_department_id,
                            "order": dept.order,
                            "member_count": dept.member_count,
                        }
                        for dept in sample_feishu_departments
                    ],
                    "has_more": False,
                }
            }
        )

        mock_session._mock_response = mock_resp

        client = FeishuClient(settings=mock_feishu_settings, session=mock_session)
        # Pre-set token to avoid token fetch
        future = datetime.utcnow() + timedelta(hours=1)
        client._token_info = TokenInfo(token="test_token", expires_at=future)

        departments = await client.list_departments()

        assert len(departments) == 3
        assert departments[0].name == "研发中心"
        assert departments[1].parent_department_id == "dept_001"


class TestFeishuClientUsers:
    """Test Feishu client user operations."""

    @pytest.mark.asyncio
    async def test_list_users(self, mock_feishu_settings, mock_session, mock_response, sample_feishu_users):
        """Test listing users."""
        mock_resp = mock_response(
            status=200,
            json_data={
                "code": 0,
                "data": {
                    "items": [
                        {
                            "user_id": user.user_id,
                            "name": user.name,
                            "email": user.email,
                            "department_ids": user.department_ids,
                        }
                        for user in sample_feishu_users
                    ],
                    "has_more": False,
                }
            }
        )

        mock_session._mock_response = mock_resp

        client = FeishuClient(settings=mock_feishu_settings, session=mock_session)
        future = datetime.utcnow() + timedelta(hours=1)
        client._token_info = TokenInfo(token="test_token", expires_at=future)

        users = await client.list_users()

        assert len(users) == 2
        assert users[0].name == "张三"
        assert users[1].department_ids == ["dept_003"]


class TestFeishuClientDocuments:
    """Test Feishu client document operations."""

    @pytest.mark.asyncio
    async def test_get_document(self, mock_feishu_settings, mock_session, mock_response):
        """Test getting document metadata."""
        mock_resp = mock_response(
            status=200,
            json_data={
                "code": 0,
                "data": {
                    "document": {
                        "document_id": "doc_123",
                        "title": "Test Document",
                        "url": "https://example.com/doc",
                        "owner_id": "user_001",
                        "create_time": int(datetime.utcnow().timestamp()),
                    }
                }
            }
        )

        mock_session._mock_response = mock_resp

        client = FeishuClient(settings=mock_feishu_settings, session=mock_session)
        future = datetime.utcnow() + timedelta(hours=1)
        client._token_info = TokenInfo(token="test_token", expires_at=future)

        doc = await client.get_document("doc_123")

        assert doc.document_id == "doc_123"
        assert doc.title == "Test Document"

    @pytest.mark.asyncio
    async def test_get_document_content(self, mock_feishu_settings, mock_session, mock_response):
        """Test getting document content."""
        mock_resp = mock_response(
            status=200,
            json_data={
                "code": 0,
                "data": {
                    "document_id": "doc_123",
                    "revision": 5,
                    "items": [
                        {"block_id": "b1", "block_type": 1},
                        {"block_id": "b2", "block_type": 2},
                    ],
                    "has_more": False,
                }
            }
        )

        mock_session._mock_response = mock_resp

        client = FeishuClient(settings=mock_feishu_settings, session=mock_session)
        future = datetime.utcnow() + timedelta(hours=1)
        client._token_info = TokenInfo(token="test_token", expires_at=future)

        content = await client.get_document_content("doc_123")

        # The method returns a dict, not a FeishuDocContentRaw object
        assert content["document_id"] == "doc_123"
        assert content["revision"] == 5
        assert len(content["blocks"]) == 2


class TestFeishuAPIError:
    """Test Feishu API error handling."""

    def test_error_message(self):
        """Test error message formatting."""
        error = FeishuAPIError(
            message="Test error",
            status_code=400,
            code=99991663,
        )
        assert "Test error" in str(error)
        assert "400" in str(error)

    def test_error_with_request_id(self):
        """Test error with request ID."""
        error = FeishuAPIError(
            message="Rate limit exceeded",
            status_code=429,
            code=99991400,
            request_id="req_123",
        )
        assert "req_123" in str(error)

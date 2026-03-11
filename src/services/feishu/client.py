"""Feishu (Lark) API client with authentication and rate limiting.

This module provides an async HTTP client for Feishu OpenAPI with:
- Automatic token management and refresh
- Rate limiting with exponential backoff
- Retry logic for transient failures
- Structured logging
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
import structlog

from src.config.settings import FeishuSettings, settings
from src.schemas.feishu import (
    FeishuDepartmentListResponse,
    FeishuDepartmentRaw,
    FeishuTokenResponse,
    FeishuUserListResponse,
    FeishuUserRaw,
)
from src.schemas.feishu_docs import (
    FeishuDocContentRaw,
    FeishuDocRaw,
    FeishuDocSearchItem,
)

logger = structlog.get_logger()


@dataclass
class TokenInfo:
    """Token information with expiry tracking."""

    token: str
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if token is expired or about to expire."""
        # Consider token expired 10 minutes before actual expiry
        buffer = timedelta(minutes=10)
        return datetime.utcnow() >= (self.expires_at - buffer)


class FeishuAPIError(Exception):
    """Base exception for Feishu API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict] = None,
        code: Optional[int] = None,
        request_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}
        self.code = code
        self.request_id = request_id

    def __str__(self) -> str:
        """Format error message with all available details."""
        parts = [self.args[0]]
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        if self.code:
            parts.append(f"(code: {self.code})")
        if self.request_id:
            parts.append(f"[Request ID: {self.request_id}]")
        return " ".join(parts)


class FeishuAuthError(FeishuAPIError):
    """Authentication/authorization error."""

    pass


class FeishuRateLimitError(FeishuAPIError):
    """Rate limit exceeded error."""

    pass


class FeishuClient:
    """Async HTTP client for Feishu OpenAPI.

    Features:
    - Automatic token acquisition and refresh
    - Rate limiting with configurable delay
    - Exponential backoff retry logic
    - Comprehensive logging

    Example:
        >>> async with FeishuClient() as client:
        ...     departments = await client.list_departments()
        ...     users = await client.list_users(dept_id="0")
    """

    def __init__(
        self,
        settings: Optional[FeishuSettings] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        """Initialize Feishu client.

        Args:
            settings: Feishu settings (uses global settings if not provided)
            session: Optional aiohttp session for dependency injection
        """
        self._settings = settings
        if self._settings is None:
            # Import here to avoid circular import issues
            from src.config.settings import settings as global_settings
            self._settings = global_settings.feishu

        if self._settings is None:
            raise ValueError("Feishu settings not configured")

        self._session = session
        self._token_info: Optional[TokenInfo] = None
        self._semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        self._logger = logger.bind(component="FeishuClient")

    async def __aenter__(self) -> "FeishuClient":
        """Async context manager entry."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _get_access_token(self) -> str:
        """Get valid access token, fetching new one if needed.

        Returns:
            Valid tenant access token

        Raises:
            FeishuAuthError: If authentication fails
        """
        if self._token_info is not None and not self._token_info.is_expired:
            return self._token_info.token

        self._logger.info("fetching_new_token")

        url = f"{self._settings.base_url}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self._settings.app_id,
            "app_secret": self._settings.app_secret,
        }

        try:
            async with self._semaphore:
                async with self._session.post(url, json=payload) as response:
                    data = await response.json()
                    token_response = FeishuTokenResponse(**data)

                    if not token_response.is_success:
                        error_msg = (
                            f"Token acquisition failed: {token_response.msg} "
                            f"(code: {token_response.code})"
                        )
                        self._logger.error(
                            "token_acquisition_failed",
                            code=token_response.code,
                            msg=token_response.msg,
                        )
                        raise FeishuAuthError(error_msg)

                    if not token_response.tenant_access_token:
                        raise FeishuAuthError("No token in response")

                    # Calculate expiry time
                    expires_in = token_response.expire or 7200  # Default 2 hours
                    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                    self._token_info = TokenInfo(
                        token=token_response.tenant_access_token,
                        expires_at=expires_at,
                    )

                    self._logger.info(
                        "token_acquired",
                        expires_in_seconds=expires_in,
                        expires_at=expires_at.isoformat(),
                    )

                    return self._token_info.token

        except aiohttp.ClientError as e:
            self._logger.exception("token_request_failed")
            raise FeishuAuthError(f"Token request failed: {e}") from e

    async def _make_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Make authenticated request to Feishu API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (without base URL)
            params: Query parameters
            json_data: JSON request body
            max_retries: Maximum number of retries

        Returns:
            JSON response data

        Raises:
            FeishuAPIError: If request fails after retries
        """
        token = await self._get_access_token()
        url = f"{self._settings.base_url}{path}"
        headers = {"Authorization": f"Bearer {token}"}

        last_exception: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                # Rate limiting delay
                if attempt > 0:
                    delay = (self._settings.rate_limit_delay_ms / 1000.0) * (2 ** attempt)
                    self._logger.debug(
                        "retry_delay",
                        attempt=attempt + 1,
                        delay_seconds=delay,
                    )
                    await asyncio.sleep(delay)

                async with self._semaphore:
                    self._logger.debug(
                        "making_request",
                        method=method,
                        url=url,
                        attempt=attempt + 1,
                    )

                    async with self._session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=json_data,
                    ) as response:
                        # Handle rate limiting
                        if response.status == 429:
                            retry_after = int(response.headers.get("Retry-After", 60))
                            self._logger.warning(
                                "rate_limited",
                                retry_after=retry_after,
                                attempt=attempt + 1,
                            )
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_after)
                                continue
                            raise FeishuRateLimitError(
                                "Rate limit exceeded",
                                status_code=429,
                            )

                        # Handle authentication errors
                        if response.status == 401:
                            self._logger.warning("token_expired_during_request")
                            self._token_info = None  # Force token refresh
                            token = await self._get_access_token()
                            headers["Authorization"] = f"Bearer {token}"
                            if attempt < max_retries - 1:
                                continue
                            raise FeishuAuthError(
                                "Authentication failed after token refresh",
                                status_code=401,
                            )

                        # Read response body
                        try:
                            data = await response.json()
                        except aiohttp.ContentTypeError:
                            text = await response.text()
                            data = {"code": response.status, "msg": text}

                        # Check for API-level errors
                        if response.status >= 400:
                            error_msg = data.get("msg", f"HTTP {response.status}")
                            self._logger.error(
                                "api_error",
                                status_code=response.status,
                                code=data.get("code"),
                                msg=error_msg,
                            )

                            if response.status >= 500 and attempt < max_retries - 1:
                                # Server error, retry
                                continue

                            raise FeishuAPIError(
                                error_msg,
                                status_code=response.status,
                                response_data=data,
                            )

                        # Check Feishu business logic errors
                        if data.get("code", 0) != 0:
                            error_msg = f"Feishu error: {data.get('msg')} (code: {data.get('code')})"
                            self._logger.error(
                                "feishu_business_error",
                                code=data.get("code"),
                                msg=data.get("msg"),
                            )
                            raise FeishuAPIError(
                                error_msg,
                                response_data=data,
                            )

                        return data.get("data", data)

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                self._logger.warning(
                    "request_failed",
                    error=str(e),
                    attempt=attempt + 1,
                )
                if attempt < max_retries - 1:
                    continue

        # All retries exhausted
        raise FeishuAPIError(
            f"Request failed after {max_retries} attempts: {last_exception}"
        ) from last_exception

    async def list_departments(
        self,
        parent_department_id: Optional[str] = None,
        page_size: int = 50,
    ) -> List[FeishuDepartmentRaw]:
        """List departments from Feishu.

        Args:
            parent_department_id: Filter by parent department (None for root)
            page_size: Number of results per page (max 50)

        Returns:
            List of department objects
        """
        self._logger.info(
            "listing_departments",
            parent_id=parent_department_id,
            page_size=page_size,
        )

        departments: List[FeishuDepartmentRaw] = []
        page_token: Optional[str] = None

        while True:
            params: Dict[str, Any] = {"page_size": min(page_size, 50)}
            if parent_department_id:
                params["parent_department_id"] = parent_department_id
            if page_token:
                params["page_token"] = page_token

            data = await self._make_request(
                "GET",
                "/contact/v3/departments",
                params=params,
            )

            response = FeishuDepartmentListResponse(**data)
            departments.extend(response.items)

            self._logger.debug(
                "departments_page_fetched",
                count=len(response.items),
                has_more=response.has_more,
            )

            if not response.has_more:
                break

            page_token = response.page_token

        self._logger.info(
            "departments_listed",
            total_count=len(departments),
        )

        return departments

    async def list_users(
        self,
        department_id: Optional[str] = None,
        page_size: int = 50,
    ) -> List[FeishuUserRaw]:
        """List users from Feishu.

        Args:
            department_id: Filter by department (None for all users)
            page_size: Number of results per page (max 50)

        Returns:
            List of user objects
        """
        self._logger.info(
            "listing_users",
            department_id=department_id,
            page_size=page_size,
        )

        users: List[FeishuUserRaw] = []
        page_token: Optional[str] = None

        while True:
            params: Dict[str, Any] = {"page_size": min(page_size, 50)}
            if department_id:
                params["department_id"] = department_id
            if page_token:
                params["page_token"] = page_token

            data = await self._make_request(
                "GET",
                "/contact/v3/users",
                params=params,
            )

            response = FeishuUserListResponse(**data)
            users.extend(response.items)

            self._logger.debug(
                "users_page_fetched",
                count=len(response.items),
                has_more=response.has_more,
            )

            if not response.has_more:
                break

            page_token = response.page_token

        self._logger.info(
            "users_listed",
            total_count=len(users),
        )

        return users

    async def get_user_info(self, user_id: str) -> FeishuUserRaw:
        """Get detailed user information.

        Args:
            user_id: Feishu user ID

        Returns:
            User details
        """
        self._logger.info("getting_user_info", user_id=user_id)

        data = await self._make_request(
            "GET",
            f"/contact/v3/users/{user_id}",
        )

        user = FeishuUserRaw(**data)

        self._logger.debug("user_info_retrieved", user_id=user_id)

        return user

    async def get_department_info(self, department_id: str) -> FeishuDepartmentRaw:
        """Get detailed department information.

        Args:
            department_id: Feishu department ID

        Returns:
            Department details
        """
        self._logger.info("getting_department_info", department_id=department_id)

        data = await self._make_request(
            "GET",
            f"/contact/v3/departments/{department_id}",
        )

        dept = FeishuDepartmentRaw(**data)

        self._logger.debug("department_info_retrieved", department_id=department_id)

        return dept

    # ==================== Document API Methods ====================

    async def get_document(self, document_id: str) -> FeishuDocRaw:
        """Get document metadata from Feishu.

        Args:
            document_id: Feishu document ID (doc_xxx or doxcnxxx)

        Returns:
            Document metadata
        """
        self._logger.info("getting_document", document_id=document_id)

        data = await self._make_request(
            "GET",
            f"/docx/v1/documents/{document_id}",
        )

        # The API returns document data in 'document' field
        doc_data = data.get("document", data)
        doc = FeishuDocRaw(**doc_data)

        self._logger.debug("document_retrieved", document_id=document_id, title=doc.title)

        return doc

    async def get_document_content(
        self,
        document_id: str,
        page_size: int = 500,
    ) -> FeishuDocContentRaw:
        """Get document content from Feishu.

        Args:
            document_id: Feishu document ID
            page_size: Number of blocks per page (max 500)

        Returns:
            Document content with blocks
        """
        self._logger.info(
            "getting_document_content",
            document_id=document_id,
            page_size=page_size,
        )

        all_blocks: List[Dict[str, Any]] = []
        page_token: Optional[str] = None
        revision: Optional[int] = None
        title: Optional[str] = None

        while True:
            params: Dict[str, Any] = {"page_size": min(page_size, 500)}
            if page_token:
                params["page_token"] = page_token

            data = await self._make_request(
                "GET",
                f"/docx/v1/documents/{document_id}/content",
                params=params,
            )

            # Extract blocks from response
            content_data = data.get("content", data)
            blocks = content_data.get("blocks", [])
            all_blocks.extend(blocks)

            # Get metadata from first response
            if revision is None:
                revision = content_data.get("revision")
            if title is None:
                title = content_data.get("title")

            # Check for more pages
            has_more = content_data.get("has_more", False)
            page_token = content_data.get("page_token")

            self._logger.debug(
                "document_content_page_fetched",
                document_id=document_id,
                blocks_count=len(blocks),
                has_more=has_more,
            )

            if not has_more:
                break

        self._logger.info(
            "document_content_retrieved",
            document_id=document_id,
            total_blocks=len(all_blocks),
            revision=revision,
        )

        return FeishuDocContentRaw(
            document_id=document_id,
            revision=revision,
            title=title,
            blocks=all_blocks,
        )

    async def get_my_documents(
        self,
        page_size: int = 50,
    ) -> List[FeishuDocSearchItem]:
        """Get current user's documents from Feishu.

        Note: This uses a workaround via the search API as there's no
        direct "list my documents" endpoint.

        Args:
            page_size: Number of documents per page

        Returns:
            List of document metadata
        """
        self._logger.info("getting_my_documents", page_size=page_size)

        # Use search API to get documents
        # This is a simplified approach - in production, you might need
        # to use a different API or maintain a document index
        documents: List[FeishuDocSearchItem] = []

        # Note: The actual implementation depends on available APIs
        # For now, this is a placeholder that would need to be
        # implemented based on specific Feishu API capabilities

        self._logger.warning(
            "get_my_documents_not_fully_implemented",
            message="This method requires additional Feishu permissions or a different approach",
        )

        return documents

    async def get_document_raw_content(self, document_id: str) -> str:
        """Get raw text content from a document.

        This is a convenience method that extracts plain text
        from the document content.

        Args:
            document_id: Feishu document ID

        Returns:
            Plain text content of the document
        """
        content = await self.get_document_content(document_id)
        return content.get_all_text()

    # ==================== Document API Methods ====================

    async def get_document_meta(self, document_id: str) -> Dict[str, Any]:
        """Get document metadata from Feishu.

        Args:
            document_id: Feishu document ID (e.g., "doxcnxxxxxxxx")

        Returns:
            Document metadata including title, owner, timestamps
        """
        self._logger.info("getting_document_meta", document_id=document_id)

        data = await self._make_request(
            "GET",
            f"/docx/v1/documents/{document_id}",
        )

        self._logger.debug("document_meta_retrieved", document_id=document_id)

        return data

    async def get_document_content(
        self,
        document_id: str,
        page_size: int = 500,
    ) -> Dict[str, Any]:
        """Get document content from Feishu.

        Args:
            document_id: Feishu document ID
            page_size: Number of content blocks per page (max 500)

        Returns:
            Document content including blocks and text
        """
        self._logger.info(
            "getting_document_content",
            document_id=document_id,
            page_size=page_size,
        )

        all_blocks: List[Dict[str, Any]] = []
        page_token: Optional[str] = None
        document_info: Optional[Dict[str, Any]] = None

        while True:
            params: Dict[str, Any] = {"page_size": min(page_size, 500)}
            if page_token:
                params["page_token"] = page_token

            data = await self._make_request(
                "GET",
                f"/docx/v1/documents/{document_id}/blocks",
                params=params,
            )

            # Store document info from first response
            if document_info is None:
                document_info = {
                    "document_id": data.get("document_id"),
                    "revision": data.get("revision"),
                    "title": data.get("title"),
                }

            blocks = data.get("items", [])
            all_blocks.extend(blocks)

            has_more = data.get("has_more", False)
            self._logger.debug(
                "document_content_page_fetched",
                document_id=document_id,
                blocks_count=len(blocks),
                has_more=has_more,
            )

            if not has_more:
                break

            page_token = data.get("page_token")

        self._logger.info(
            "document_content_retrieved",
            document_id=document_id,
            total_blocks=len(all_blocks),
        )

        return {
            **document_info,
            "blocks": all_blocks,
        }

    async def get_my_documents(
        self,
        page_size: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get documents accessible by the app.

        Note: This uses the search API to get recent documents.
        Requires docs:document:readonly permission.

        Args:
            page_size: Number of documents per page

        Returns:
            List of document metadata
        """
        self._logger.info("getting_my_documents", page_size=page_size)

        documents: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        while True:
            params: Dict[str, Any] = {
                "page_size": min(page_size, 50),
                "search_key": "",  # Empty search to get all accessible docs
            }
            if page_token:
                params["page_token"] = page_token

            try:
                data = await self._make_request(
                    "POST",
                    "/drive/v1/files/search",
                    json_data=params,
                )

                items = data.get("items", [])
                # Filter for documents only
                for item in items:
                    if item.get("type") in ["doc", "docx", "document"]:
                        documents.append(item)

                has_more = data.get("has_more", False)
                self._logger.debug(
                    "documents_search_page_fetched",
                    count=len(items),
                    has_more=has_more,
                )

                if not has_more:
                    break

                page_token = data.get("page_token")

            except FeishuAPIError as e:
                # Search API might not be available
                self._logger.warning(
                    "document_search_not_available",
                    error=str(e),
                )
                break

        self._logger.info(
            "my_documents_retrieved",
            total_count=len(documents),
        )

        return documents

    async def get_document_permissions(
        self,
        document_id: str,
    ) -> Dict[str, Any]:
        """Get document permissions and collaborators.

        Args:
            document_id: Feishu document ID

        Returns:
            Permission information including collaborators
        """
        self._logger.info("getting_document_permissions", document_id=document_id)

        data = await self._make_request(
            "GET",
            f"/drive/v1/permissions/{document_id}/public",
        )

        self._logger.debug("document_permissions_retrieved", document_id=document_id)

        return data

    # ==================== Task API Methods ====================

    async def list_tasks(
        self,
        user_id: Optional[str] = None,
        page_size: int = 50,
        completed: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """List tasks from Feishu Task (TaskBit).

        Args:
            user_id: Filter by assignee user ID (None for all tasks)
            page_size: Number of results per page (max 50)
            completed: Filter by completion status (None for all)

        Returns:
            List of task objects
        """
        self._logger.info(
            "listing_tasks",
            user_id=user_id,
            page_size=page_size,
            completed=completed,
        )

        tasks: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        while True:
            params: Dict[str, Any] = {"page_size": min(page_size, 50)}
            if user_id:
                params["user_id"] = user_id
            if completed is not None:
                params["completed"] = str(completed).lower()
            if page_token:
                params["page_token"] = page_token

            try:
                data = await self._make_request(
                    "GET",
                    "/task/v1/tasks",
                    params=params,
                )

                items = data.get("items", [])
                tasks.extend(items)

                self._logger.debug(
                    "tasks_page_fetched",
                    count=len(items),
                    has_more=data.get("has_more", False),
                )

                if not data.get("has_more", False):
                    break

                page_token = data.get("page_token")

            except FeishuAPIError as e:
                # Task API might not be available or insufficient permissions
                self._logger.warning(
                    "task_api_not_available",
                    error=str(e),
                )
                break

        self._logger.info(
            "tasks_listed",
            total_count=len(tasks),
        )

        return tasks

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get detailed task information.

        Args:
            task_id: Feishu task ID

        Returns:
            Task details
        """
        self._logger.info("getting_task", task_id=task_id)

        data = await self._make_request(
            "GET",
            f"/task/v1/tasks/{task_id}",
        )

        self._logger.debug("task_retrieved", task_id=task_id)

        return data.get("task", data)

    # ==================== Project API Methods ====================

    async def list_projects(
        self,
        user_id: Optional[str] = None,
        page_size: int = 50,
    ) -> List[Dict[str, Any]]:
        """List projects from Feishu Project (ProjectBit).

        Args:
            user_id: Filter by member user ID (None for all projects)
            page_size: Number of results per page (max 50)

        Returns:
            List of project objects
        """
        self._logger.info(
            "listing_projects",
            user_id=user_id,
            page_size=page_size,
        )

        projects: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        while True:
            params: Dict[str, Any] = {"page_size": min(page_size, 50)}
            if user_id:
                params["user_id"] = user_id
            if page_token:
                params["page_token"] = page_token

            try:
                data = await self._make_request(
                    "GET",
                    "/project/v1/projects",
                    params=params,
                )

                items = data.get("items", [])
                projects.extend(items)

                self._logger.debug(
                    "projects_page_fetched",
                    count=len(items),
                    has_more=data.get("has_more", False),
                )

                if not data.get("has_more", False):
                    break

                page_token = data.get("page_token")

            except FeishuAPIError as e:
                # Project API might not be available
                self._logger.warning(
                    "project_api_not_available",
                    error=str(e),
                )
                break

        self._logger.info(
            "projects_listed",
            total_count=len(projects),
        )

        return projects

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get detailed project information.

        Args:
            project_id: Feishu project ID

        Returns:
            Project details
        """
        self._logger.info("getting_project", project_id=project_id)

        data = await self._make_request(
            "GET",
            f"/project/v1/projects/{project_id}",
        )

        self._logger.debug("project_retrieved", project_id=project_id)

        return data.get("project", data)

    # ==================== OKR API Methods ====================

    async def list_okrs(
        self,
        user_id: Optional[str] = None,
        cycle: Optional[str] = None,
        page_size: int = 50,
    ) -> List[Dict[str, Any]]:
        """List OKRs from Feishu OKR.

        Args:
            user_id: Filter by owner user ID (None for all OKRs)
            cycle: Filter by OKR cycle (e.g., "2026-Q1")
            page_size: Number of results per page (max 50)

        Returns:
            List of OKR objects
        """
        self._logger.info(
            "listing_okrs",
            user_id=user_id,
            cycle=cycle,
            page_size=page_size,
        )

        okrs: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        while True:
            params: Dict[str, Any] = {"page_size": min(page_size, 50)}
            if user_id:
                params["user_id"] = user_id
            if cycle:
                params["cycle"] = cycle
            if page_token:
                params["page_token"] = page_token

            try:
                data = await self._make_request(
                    "GET",
                    "/okr/v1/okrs",
                    params=params,
                )

                items = data.get("items", [])
                okrs.extend(items)

                self._logger.debug(
                    "okrs_page_fetched",
                    count=len(items),
                    has_more=data.get("has_more", False),
                )

                if not data.get("has_more", False):
                    break

                page_token = data.get("page_token")

            except FeishuAPIError as e:
                # OKR API might not be available
                self._logger.warning(
                    "okr_api_not_available",
                    error=str(e),
                )
                break

        self._logger.info(
            "okrs_listed",
            total_count=len(okrs),
        )

        return okrs

    async def get_okr(self, okr_id: str) -> Dict[str, Any]:
        """Get detailed OKR information.

        Args:
            okr_id: Feishu OKR ID

        Returns:
            OKR details
        """
        self._logger.info("getting_okr", okr_id=okr_id)

        data = await self._make_request(
            "GET",
            f"/okr/v1/okrs/{okr_id}",
        )

        self._logger.debug("okr_retrieved", okr_id=okr_id)

        return data.get("okr", data)

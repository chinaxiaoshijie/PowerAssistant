"""Pytest configuration and shared fixtures."""

import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config.ai_settings import (
    AIModelProvider,
    AIEngineSettings,
    DashScopeSettings,
)
from src.config.settings import AppSettings, DatabaseSettings, FeishuSettings
from src.database import Base
from src.models.ai_intelligence import (
    CrawlerSource,
    IntelligenceAnalysis,
    IntelligenceItem,
    IntelligenceReport,
)
from src.models.document import FeishuDocument, FeishuDocumentContent, DocumentSyncLog
from src.models.organization import Department, Employee
from src.models.sync_log import SyncLog
from src.schemas.feishu import FeishuDepartmentRaw, FeishuUserRaw, FeishuAvatar
from src.services.ai_engine.base import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
)
from src.services.ai_intelligence.base import CrawlResult
from src.services.feishu.client import FeishuClient


# ============================================================================
# Event Loop Fixture
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Settings Fixtures
# ============================================================================

@pytest.fixture
def mock_feishu_settings() -> FeishuSettings:
    """Create mock Feishu settings."""
    return FeishuSettings(
        app_id="cli_test_app_id",
        app_secret="test_secret_key",
        base_url="https://open.feishu.cn/open-apis",
        token_refresh_buffer_minutes=10,
        rate_limit_delay_ms=100,
    )


@pytest.fixture
def mock_dashscope_settings() -> DashScopeSettings:
    """Create mock DashScope settings."""
    return DashScopeSettings(
        api_key="test-api-key",
        base_url="https://dashscope.aliyuncs.com/api/v1",
        model_chat="qwen-max",
        model_long="qwen-max-longcontext",
        model_coder="qwen-coder-plus",
    )


@pytest.fixture
def mock_ai_engine_settings() -> AIEngineSettings:
    """Create mock AI engine settings."""
    return AIEngineSettings(
        default_provider=AIModelProvider.DASHSCOPE,
        default_model="qwen-max",
        selection_strategy="auto",
        request_timeout=120,
        max_retries=3,
        default_temperature=0.7,
        max_tokens=4096,
    )


# ============================================================================
# HTTP Session Fixtures
# ============================================================================

@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock aiohttp ClientSession."""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.closed = False
    session.close = AsyncMock()

    # Will be set by tests via mock_session._mock_response
    session._mock_response = None

    def _create_async_context_manager(response):
        """Create an async context manager class for the response."""
        class AsyncContextManager:
            def __init__(self, resp):
                self.response = resp
            async def __aenter__(self):
                return self.response
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False
        return AsyncContextManager(response)

    def _make_post(*args, **kwargs):
        """Mock POST method."""
        response = session._mock_response
        if response is None:
            response = MagicMock(spec=aiohttp.ClientResponse)
            response.status = 200
            response.headers = {}
            response.json = AsyncMock(return_value={"code": 0, "data": {}})
            response.text = AsyncMock(return_value="")
        return _create_async_context_manager(response)

    def _make_get(*args, **kwargs):
        """Mock GET method."""
        return _make_post(*args, **kwargs)

    def _make_request(*args, **kwargs):
        """Mock generic request method."""
        return _make_post(*args, **kwargs)

    # Set up the mock methods to return coroutines
    session.post = MagicMock(side_effect=_make_post)
    session.get = MagicMock(side_effect=_make_get)
    session.request = MagicMock(side_effect=_make_request)

    return session


@pytest.fixture
def mock_response():
    """Create a mock aiohttp response factory."""
    def _create_mock_response(
        status: int = 200,
        json_data: Optional[dict] = None,
        text: str = "",
        headers: Optional[dict] = None,
    ) -> MagicMock:
        response = MagicMock(spec=aiohttp.ClientResponse)
        response.status = status
        response.headers = headers or {}
        response.json = AsyncMock(return_value=json_data or {})
        response.text = AsyncMock(return_value=text)
        return response

    return _create_mock_response


@pytest_asyncio.fixture
async def feishu_client(mock_feishu_settings: FeishuSettings, mock_session: MagicMock) -> FeishuClient:
    """Create Feishu client with mocked session."""
    client = FeishuClient(
        settings=mock_feishu_settings,
        session=mock_session,
    )
    return client


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def async_engine():
    """Create async engine for testing (using SQLite in-memory)."""
    # Use aiosqlite for async SQLite testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    yield engine
    asyncio.run(engine.dispose())


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing."""
    async_session_factory = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        yield session
        await session.rollback()

    # Drop tables after test
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ============================================================================
# Model Fixtures - Organization
# ============================================================================

@pytest.fixture
def sample_department() -> Department:
    """Create a sample department."""
    return Department(
        id=1,
        feishu_dept_id="dept_001",
        name="研发中心",
        parent_id=None,
        order=0,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        sync_updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_child_department() -> Department:
    """Create a sample child department."""
    return Department(
        id=2,
        feishu_dept_id="dept_002",
        name="AI算法组",
        parent_id="dept_001",
        order=1,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        sync_updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_employee() -> Employee:
    """Create a sample employee."""
    return Employee(
        id=1,
        feishu_user_id="user_001",
        name="张三",
        email="zhangsan@example.com",
        mobile="13800138000",
        job_title="高级工程师",
        employee_no="E001",
        avatar_url="https://example.com/avatar.jpg",
        department_ids=["dept_001", "dept_002"],
        role_type="研发",
        join_date=datetime.utcnow().date(),
        is_active=True,
        is_admin=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        sync_updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_sync_log() -> SyncLog:
    """Create a sample sync log."""
    return SyncLog(
        id=1,
        sync_type="full",
        entity_type="all",
        records_fetched=100,
        records_created=50,
        records_updated=30,
        records_deactivated=5,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        status="success",
        error_message=None,
        duration_seconds=60,
    )


# ============================================================================
# Schema Fixtures - Feishu
# ============================================================================

@pytest.fixture
def sample_feishu_departments() -> list[FeishuDepartmentRaw]:
    """Create sample Feishu department data."""
    return [
        FeishuDepartmentRaw(
            department_id="dept_001",
            name="研发中心",
            parent_department_id=None,
            order=0,
            member_count=50,
            status=0,
        ),
        FeishuDepartmentRaw(
            department_id="dept_002",
            name="AI算法组",
            parent_department_id="dept_001",
            order=1,
            member_count=20,
            status=0,
        ),
        FeishuDepartmentRaw(
            department_id="dept_003",
            name="交付团队",
            parent_department_id=None,
            order=2,
            member_count=30,
            status=0,
        ),
    ]


@pytest.fixture
def sample_feishu_users() -> list[FeishuUserRaw]:
    """Create sample Feishu user data."""
    return [
        FeishuUserRaw(
            user_id="user_001",
            name="张三",
            email="zhangsan@example.com",
            mobile="13800138000",
            job_title="高级工程师",
            employee_no="E001",
            avatar=FeishuAvatar(
                avatar_72="https://example.com/avatar72.jpg",
                avatar_240="https://example.com/avatar240.jpg",
            ),
            department_ids=["dept_001", "dept_002"],
            status=None,
            is_tenant_manager=False,
        ),
        FeishuUserRaw(
            user_id="user_002",
            name="李四",
            email="lisi@example.com",
            mobile="13900139000",
            job_title="产品经理",
            employee_no="E002",
            avatar=None,
            department_ids=["dept_003"],
            status=None,
            is_tenant_manager=True,
        ),
    ]


# ============================================================================
# Model Fixtures - Documents
# ============================================================================

@pytest.fixture
def sample_document() -> FeishuDocument:
    """Create a sample document."""
    return FeishuDocument(
        id=1,
        document_id="doc_001",
        title="测试文档",
        url="https://feishu.example.com/doc/doc_001",
        owner_id="user_001",
        owner_name="张三",
        create_time=datetime.utcnow(),
        update_time=datetime.utcnow(),
        last_sync_time=datetime.utcnow(),
        content_summary="这是一个测试文档的摘要",
        headings=[{"level": 1, "text": "标题一"}, {"level": 2, "text": "子标题"}],
        word_count=500,
        is_deleted=False,
        sync_status="success",
        sync_error=None,
    )


@pytest.fixture
def sample_document_content() -> FeishuDocumentContent:
    """Create a sample document content."""
    return FeishuDocumentContent(
        id=1,
        document_id="doc_001",
        revision=1,
        content_text="这是文档的完整内容...",
        content_blocks=[
            {"block_id": "block_1", "type": "paragraph", "text": "第一段"},
            {"block_id": "block_2", "type": "heading", "text": "标题"},
        ],
        captured_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_doc_sync_log() -> DocumentSyncLog:
    """Create a sample document sync log."""
    return DocumentSyncLog(
        id=1,
        sync_type="batch",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        status="success",
        documents_processed=10,
        documents_created=5,
        documents_updated=3,
        documents_failed=0,
        error_message=None,
    )


# ============================================================================
# Model Fixtures - AI Intelligence
# ============================================================================

@pytest.fixture
def sample_intelligence_item() -> IntelligenceItem:
    """Create a sample intelligence item."""
    return IntelligenceItem(
        id=1,
        source_type="arxiv",
        source_name="arXiv",
        external_id="arxiv_1234.5678",
        title="Transformer架构的新进展",
        url="https://arxiv.org/abs/1234.5678",
        content="这是一篇关于Transformer新架构的论文摘要...",
        content_hash="abc123def456",
        author="John Doe et al.",
        published_at=datetime.utcnow(),
        language="en",
        category="research_paper",
        summary="论文提出了一种新的注意力机制改进",
        key_points=["新注意力机制", "计算效率提升", "实验验证"],
        relevance_score=0.85,
        relevance_reasoning="该研究对我们的AI教育产品有直接参考价值",
        tags=["transformer", "attention", "deep-learning"],
        technologies=["PyTorch", "CUDA"],
        is_processed=True,
        is_notified=False,
        is_read=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_intelligence_analysis() -> IntelligenceAnalysis:
    """Create a sample intelligence analysis."""
    return IntelligenceAnalysis(
        id=1,
        intelligence_item_id=1,
        analysis_type="general",
        model_used="qwen-max",
        analysis_content="这是一个详细的分析结果...",
        action_items=[["调研实现方案"], ["评估集成成本"]],
        applicability_score=0.8,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_intelligence_report() -> IntelligenceReport:
    """Create a sample intelligence report."""
    return IntelligenceReport(
        id=1,
        report_type="daily",
        title="AI情报日报 - 2024-01-15",
        period_start=datetime.utcnow() - timedelta(days=1),
        period_end=datetime.utcnow(),
        summary="今日共收集25条AI相关情报，其中高相关度5条。",
        highlights=[
            {
                "id": 1,
                "title": "Transformer架构的新进展",
                "url": "https://arxiv.org/abs/1234.5678",
                "category": "research_paper",
                "relevance_score": 0.85,
                "summary": "论文提出了一种新的注意力机制改进",
            }
        ],
        category_breakdown={"research_paper": 10, "product": 5, "tutorial": 10},
        trends_analysis="本周AI研究领域关注点集中在高效Transformer变体...",
        status="generated",
        sent_at=None,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_crawler_source() -> CrawlerSource:
    """Create a sample crawler source."""
    return CrawlerSource(
        id=1,
        name="arXiv AI Papers",
        source_type="arxiv",
        url="http://export.arxiv.org/api/query",
        config={"categories": ["cs.AI", "cs.CL", "cs.LG"]},
        fetch_interval_hours=6,
        last_fetched_at=datetime.utcnow(),
        next_fetch_at=datetime.utcnow() + timedelta(hours=6),
        is_active=True,
        last_error=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


# ============================================================================
# Crawler Fixtures
# ============================================================================

@pytest.fixture
def sample_crawl_results() -> list[CrawlResult]:
    """Create sample crawl results."""
    return [
        CrawlResult(
            title="Test Paper 1",
            url="https://example.com/paper1",
            content="This is the abstract of paper 1",
            author="Author One",
            published_at=datetime.utcnow(),
            external_id="paper_001",
            metadata={"category": "cs.AI"},
        ),
        CrawlResult(
            title="Test Paper 2",
            url="https://example.com/paper2",
            content="This is the abstract of paper 2",
            author="Author Two",
            published_at=datetime.utcnow(),
            external_id="paper_002",
            metadata={"category": "cs.CL"},
        ),
    ]


# ============================================================================
# AI Engine Fixtures
# ============================================================================

@pytest.fixture
def sample_chat_messages() -> list[Message]:
    """Create sample chat messages."""
    return [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello, how are you?"),
    ]


@pytest.fixture
def sample_chat_request(sample_chat_messages: list[Message]) -> ChatCompletionRequest:
    """Create a sample chat completion request."""
    return ChatCompletionRequest(
        messages=sample_chat_messages,
        model="qwen-max",
        temperature=0.7,
        max_tokens=2048,
    )


@pytest.fixture
def sample_chat_response() -> ChatCompletionResponse:
    """Create a sample chat completion response."""
    return ChatCompletionResponse(
        content="I'm doing well, thank you! How can I help you today?",
        model="qwen-max",
        usage={"prompt_tokens": 20, "completion_tokens": 15, "total_tokens": 35},
        finish_reason="stop",
        raw_response={"choices": [{"message": {"content": "I'm doing well..."}}]},
    )


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_ai_engine_service():
    """Create a mock AI engine service."""
    service = MagicMock()
    service.chat = AsyncMock()
    service.generate_text = AsyncMock(return_value="Generated text response")
    service.summarize_document = AsyncMock(return_value="Document summary")
    service.analyze_data = AsyncMock(return_value={
        "summary": "Analysis summary",
        "key_insights": ["insight 1", "insight 2"],
        "recommendations": ["rec 1"],
    })
    service.code_review = AsyncMock(return_value={
        "overall_assessment": "Good code",
        "issues": [],
        "strengths": ["Clean structure"],
    })
    service.close = AsyncMock()
    return service


@pytest.fixture
def mock_model_router():
    """Create a mock model router."""
    router = MagicMock()
    router.select_model = Mock(return_value=(AIModelProvider.DASHSCOPE, "qwen-max"))
    router.get_client_for_task = AsyncMock()
    router.close_all = AsyncMock()
    return router


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test."""
    # Reset any global caches or singletons here
    yield
    # Cleanup after test if needed


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================

@pytest.fixture
def app():
    """Create FastAPI application for testing."""
    from src.main import app
    return app


@pytest_asyncio.fixture
async def async_client(app):
    """Create async test client."""
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

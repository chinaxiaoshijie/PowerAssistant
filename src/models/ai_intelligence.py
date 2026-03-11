"""Database models for AI intelligence gathering system.

This module stores AI news, papers, tools, and their analysis results.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class IntelligenceCategory(str, Enum):
    """Categories of AI intelligence."""

    ALGORITHM = "algorithm"  # 新算法、模型架构
    PRODUCT = "product"  # AI产品发布
    DEVELOPMENT_TOOL = "development_tool"  # 开发工具、框架
    RESEARCH_PAPER = "research_paper"  # 研究论文
    INDUSTRY_NEWS = "industry_news"  # 行业动态
    TUTORIAL = "tutorial"  # 教程、最佳实践
    OPINION = "opinion"  # 观点、分析文章


class IntelligenceSource(str, Enum):
    """Sources of AI intelligence."""

    ARXIV = "arxiv"
    GITHUB = "github"
    TWITTER = "twitter"
    HACKER_NEWS = "hacker_news"
    REDDIT = "reddit"
    COMPANY_BLOG = "company_blog"
    TECH_BLOG = "tech_blog"
    RSS = "rss"
    API = "api"


class IntelligenceItem(Base):
    """Model for storing AI intelligence items.

    Represents a single piece of AI-related content
    (paper, news article, tool, etc.)
    """

    __tablename__ = "intelligence_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Source information
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Source type (arxiv/github/twitter/etc)",
    )
    source_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable source name",
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        index=True,
        comment="External ID (e.g., arxiv_id, github_repo)",
    )

    # Content
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Title of the item",
    )
    url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Original URL",
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full content or abstract",
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="MD5 hash for deduplication",
    )

    # Metadata
    author: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Author or creator",
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Original publication time",
    )
    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        comment="Content language (en/zh/etc)",
    )

    # AI Analysis results
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="uncategorized",
        index=True,
        comment="AI-determined category",
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI-generated summary",
    )
    key_points: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        comment="Key points extracted by AI",
    )
    relevance_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        index=True,
        comment="Relevance score 0-1",
    )
    relevance_reasoning: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Why this is relevant to our work",
    )

    # Tags and classification
    tags: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        comment="AI-generated tags",
    )
    technologies: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        comment="Technologies mentioned",
    )

    # Status
    is_processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        comment="Whether AI analysis is complete",
    )
    is_notified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether notification was sent",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether user has read this",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    analysis_results: Mapped[List["IntelligenceAnalysis"]] = relationship(
        "IntelligenceAnalysis",
        back_populates="intelligence_item",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<IntelligenceItem(id={self.id}, title={self.title[:50]}...)>"


class IntelligenceAnalysis(Base):
    """Model for storing AI analysis results.

    Stores multiple analysis versions or perspectives.
    """

    __tablename__ = "intelligence_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    intelligence_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("intelligence_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Analysis configuration
    analysis_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
        comment="Type of analysis (general/technical/business)",
    )
    model_used: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="AI model used for analysis",
    )

    # Analysis results
    analysis_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full analysis content",
    )
    action_items: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        comment="Suggested action items",
    )
    applicability_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="How applicable to our work (0-1)",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    intelligence_item: Mapped["IntelligenceItem"] = relationship(
        "IntelligenceItem",
        back_populates="analysis_results",
    )

    def __repr__(self) -> str:
        return f"<IntelligenceAnalysis(id={self.id}, type={self.analysis_type})>"


class IntelligenceReport(Base):
    """Model for storing generated intelligence reports.

    Periodic reports summarizing AI intelligence.
    """

    __tablename__ = "intelligence_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Report metadata
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="daily/weekly/monthly",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Report title",
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Report period start",
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Report period end",
    )

    # Content
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Executive summary",
    )
    highlights: Mapped[List[dict]] = mapped_column(
        JSON,
        default=list,
        comment="Key highlights with item references",
    )
    category_breakdown: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="Items by category",
    )
    trends_analysis: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Trends and patterns analysis",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="generated",
        comment="generated/reviewed/sent",
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<IntelligenceReport(id={self.id}, type={self.report_type})>"


class CrawlerSource(Base):
    """Model for configuring crawler sources.

    Allows dynamic configuration of information sources.
    """

    __tablename__ = "crawler_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Source configuration
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
        comment="Source name",
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="arxiv/github/rss/api/etc",
    )
    url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Source URL or endpoint",
    )
    config: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="Source-specific configuration",
    )

    # Scheduling
    fetch_interval_hours: Mapped[int] = mapped_column(
        Integer,
        default=6,
        comment="How often to fetch (hours)",
    )
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_fetch_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<CrawlerSource(id={self.id}, name={self.name})>"

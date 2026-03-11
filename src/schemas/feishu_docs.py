"""Pydantic schemas for Feishu Document API data validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FeishuDocOwner(BaseModel):
    """Document owner information."""

    model_config = ConfigDict(populate_by_name=True)

    user_id: Optional[str] = Field(None, alias="user_id")
    open_id: Optional[str] = Field(None, alias="open_id")
    union_id: Optional[str] = Field(None, alias="union_id")


class FeishuDocRaw(BaseModel):
    """Raw document data from Feishu Docx API.

    Schema for /docx/v1/documents/:document_id response.
    """

    model_config = ConfigDict(populate_by_name=True)

    document_id: str = Field(..., alias="document_id")
    title: Optional[str] = Field(None, description="Document title")
    url: Optional[str] = Field(None, description="Document URL")
    owner_id: Optional[str] = Field(None, alias="owner_id")
    owner: Optional[FeishuDocOwner] = Field(None, description="Document owner")
    create_time: Optional[int] = Field(
        None,
        alias="create_time",
        description="Creation timestamp in seconds",
    )
    update_time: Optional[int] = Field(
        None,
        alias="update_time",
        description="Last update timestamp in seconds",
    )
    delete_time: Optional[int] = Field(
        None,
        alias="delete_time",
        description="Deletion timestamp in seconds",
    )
    version: Optional[int] = Field(None, description="Document version")
    status: Optional[int] = Field(None, description="Document status")

    @property
    def is_deleted(self) -> bool:
        """Check if document is deleted."""
        return self.delete_time is not None or self.status == 0

    @property
    def create_datetime(self) -> Optional[datetime]:
        """Convert create_time to datetime."""
        if self.create_time:
            return datetime.fromtimestamp(self.create_time)
        return None

    @property
    def update_datetime(self) -> Optional[datetime]:
        """Convert update_time to datetime."""
        if self.update_time:
            return datetime.fromtimestamp(self.update_time)
        return None


class FeishuDocBlockTextStyle(BaseModel):
    """Text style in a document block."""

    model_config = ConfigDict(populate_by_name=True)

    bold: Optional[bool] = Field(None)
    italic: Optional[bool] = Field(None)
    underline: Optional[bool] = Field(None)
    strikethrough: Optional[bool] = Field(None)
    text_color: Optional[int] = Field(None, alias="text_color")
    background_color: Optional[int] = Field(None, alias="background_color")
    font_size: Optional[int] = Field(None, alias="font_size")


class FeishuDocBlockTextRun(BaseModel):
    """Text run in a document block."""

    model_config = ConfigDict(populate_by_name=True)

    content: str = Field(..., description="Text content")
    text_style: Optional[FeishuDocBlockTextStyle] = Field(
        None,
        alias="text_style",
        description="Text style",
    )


class FeishuDocBlockText(BaseModel):
    """Text block content."""

    model_config = ConfigDict(populate_by_name=True)

    elements: List[FeishuDocBlockTextRun] = Field(default_factory=list)
    style: Optional[Dict[str, Any]] = Field(None)


class FeishuDocBlockHeading(BaseModel):
    """Heading block content."""

    model_config = ConfigDict(populate_by_name=True)

    level: int = Field(..., description="Heading level 1-9")
    elements: List[FeishuDocBlockTextRun] = Field(default_factory=list)


class FeishuDocBlockParagraph(BaseModel):
    """Paragraph block content."""

    model_config = ConfigDict(populate_by_name=True)

    elements: List[FeishuDocBlockTextRun] = Field(default_factory=list)
    style: Optional[Dict[str, Any]] = Field(None)


class FeishuDocBlock(BaseModel):
    """Document block (element) in Feishu document.

    Documents are composed of blocks like paragraphs, headings, tables, etc.
    """

    model_config = ConfigDict(populate_by_name=True)

    block_id: str = Field(..., alias="block_id")
    block_type: int = Field(..., alias="block_type")
    parent_id: Optional[str] = Field(None, alias="parent_id")
    children: Optional[List[str]] = Field(default_factory=list)

    # Content based on block type
    text: Optional[FeishuDocBlockText] = Field(None)
    heading1: Optional[FeishuDocBlockHeading] = Field(None, alias="heading1")
    heading2: Optional[FeishuDocBlockHeading] = Field(None, alias="heading2")
    heading3: Optional[FeishuDocBlockHeading] = Field(None, alias="heading3")
    heading4: Optional[FeishuDocBlockHeading] = Field(None, alias="heading4")
    heading5: Optional[FeishuDocBlockHeading] = Field(None, alias="heading5")
    heading6: Optional[FeishuDocBlockHeading] = Field(None, alias="heading6")
    heading7: Optional[FeishuDocBlockHeading] = Field(None, alias="heading7")
    heading8: Optional[FeishuDocBlockHeading] = Field(None, alias="heading8")
    heading9: Optional[FeishuDocBlockHeading] = Field(None, alias="heading9")
    paragraph: Optional[FeishuDocBlockParagraph] = Field(None)

    @property
    def content_text(self) -> str:
        """Extract plain text content from this block."""
        texts = []

        # Check various block types
        for field_name in [
            "text", "paragraph", "heading1", "heading2", "heading3",
            "heading4", "heading5", "heading6", "heading7", "heading8", "heading9",
        ]:
            block_content = getattr(self, field_name, None)
            if block_content and hasattr(block_content, "elements"):
                for element in block_content.elements:
                    if element.content:
                        texts.append(element.content)

        return "".join(texts)


class FeishuDocContentRaw(BaseModel):
    """Raw document content from Feishu Docx API.

    Schema for /docx/v1/documents/:document_id/content response.
    """

    model_config = ConfigDict(populate_by_name=True)

    document_id: str = Field(..., alias="document_id")
    revision: Optional[int] = Field(None, description="Document revision")
    title: Optional[str] = Field(None, description="Document title")
    blocks: List[FeishuDocBlock] = Field(default_factory=list)

    def get_all_text(self) -> str:
        """Get all text content from the document."""
        texts = []
        for block in self.blocks:
            text = block.content_text
            if text:
                texts.append(text)
        return "\n".join(texts)

    def get_headings(self) -> List[Dict[str, Any]]:
        """Extract all headings from the document."""
        headings = []
        for block in self.blocks:
            for level in range(1, 10):
                heading = getattr(block, f"heading{level}", None)
                if heading:
                    text = heading.elements[0].content if heading.elements else ""
                    headings.append({
                        "level": level,
                        "text": text,
                        "block_id": block.block_id,
                    })
        return headings


class FeishuDocSearchItem(BaseModel):
    """Document search result item."""

    model_config = ConfigDict(populate_by_name=True)

    document_id: str = Field(..., alias="document_id")
    title: str = Field(..., description="Document title")
    url: Optional[str] = Field(None, description="Document URL")
    owner_id: Optional[str] = Field(None, alias="owner_id")
    owner_name: Optional[str] = Field(None, alias="owner_name")
    create_time: Optional[int] = Field(None, alias="create_time")
    update_time: Optional[int] = Field(None, alias="update_time")


class FeishuDocSearchResponse(BaseModel):
    """Response for document search API."""

    has_more: bool = Field(default=False)
    items: List[FeishuDocSearchItem] = Field(default_factory=list)
    page_token: Optional[str] = Field(None, alias="page_token")
    total: Optional[int] = Field(None)


class FeishuDocMeta(BaseModel):
    """Document metadata for database storage."""

    model_config = ConfigDict(populate_by_name=True)

    document_id: str = Field(..., alias="document_id")
    title: Optional[str] = None
    url: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    last_sync_time: datetime = Field(default_factory=datetime.utcnow)
    content_summary: Optional[str] = Field(None, max_length=2000)
    headings: List[str] = Field(default_factory=list)
    word_count: Optional[int] = None
    is_deleted: bool = False

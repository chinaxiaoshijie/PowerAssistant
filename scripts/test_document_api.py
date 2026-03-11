"""Test script for Feishu document API.

This script tests the Feishu document API functionality without requiring
database connectivity.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

from config.settings import settings
from services.feishu.client import FeishuClient


async def test_document_api():
    """Test Feishu document API."""
    print("=" * 70)
    print("  Feishu Document API Test")
    print("=" * 70)
    print()

    async with FeishuClient(settings=settings.feishu) as client:
        # Test 1: Get a document (you need to provide a document ID)
        print("NOTE: To test document API, you need a Feishu document ID.")
        print("Document ID format: doc_xxx or doxcnxxx")
        print()
        print("You can get a document ID from:")
        print("  1. Open a Feishu document")
        print("  2. Look at the URL: https://xxx.feishu.cn/docx/xxxxx")
        print("  3. The document ID is the part after /docx/")
        print()

        # Try to get a test document
        # Replace with an actual document ID for testing
        test_doc_id = input("Enter a Feishu document ID to test (or press Enter to skip): ").strip()

        if not test_doc_id:
            print("\nSkipping document API test.")
            print("Please provide a document ID to test the API.")
            return

        try:
            print(f"\nTesting get_document() with ID: {test_doc_id}")
            print("-" * 70)

            doc = await client.get_document(test_doc_id)

            print(f"SUCCESS!")
            print(f"  Document ID: {doc.document_id}")
            print(f"  Title: {doc.title}")
            print(f"  URL: {doc.url}")
            print(f"  Owner ID: {doc.owner_id}")
            print(f"  Create Time: {doc.create_datetime}")
            print(f"  Update Time: {doc.update_datetime}")
            print()

            # Test 2: Get document content
            print(f"Testing get_document_content()...")
            print("-" * 70)

            content = await client.get_document_content(test_doc_id)

            print(f"SUCCESS!")
            print(f"  Document ID: {content.document_id}")
            print(f"  Title: {content.title}")
            print(f"  Revision: {content.revision}")
            print(f"  Total Blocks: {len(content.blocks)}")
            print()

            # Extract headings
            headings = content.get_headings()
            if headings:
                print(f"  Headings ({len(headings)}):")
                for h in headings[:10]:  # Show first 10 headings
                    indent = "  " * (h["level"] - 1)
                    print(f"    {indent}{h['level']}. {h['text'][:50]}")
                if len(headings) > 10:
                    print(f"    ... and {len(headings) - 10} more")
                print()

            # Show content preview
            full_text = content.get_all_text()
            if full_text:
                preview = full_text[:500].replace("\n", " ")
                print(f"  Content Preview (first 500 chars):")
                print(f"    {preview}...")
                print()

            print("=" * 70)
            print("All tests passed!")
            print("=" * 70)

        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
            return False

    return True


if __name__ == "__main__":
    result = asyncio.run(test_document_api())
    sys.exit(0 if result else 1)

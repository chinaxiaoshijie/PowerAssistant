"""Test script for AI Intelligence Gathering system.

Tests crawling and analysis without database.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
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

from src.services.ai_intelligence.analyzer import ContentAnalyzer
from src.services.ai_intelligence.crawlers.arxiv import ArxivCrawler
from src.services.ai_intelligence.crawlers.github import GitHubTrendingCrawler


async def test_arxiv_crawler():
    """Test arXiv crawler."""
    print("\n" + "=" * 70)
    print("Test 1: arXiv Crawler")
    print("=" * 70)

    crawler = ArxivCrawler()

    try:
        count = 0
        async for result in crawler.crawl(limit=3):
            count += 1
            print(f"\nItem {count}:")
            print(f"  Title: {result.title[:80]}...")
            print(f"  URL: {result.url}")
            print(f"  Author: {result.author}")
            print(f"  Published: {result.published_at}")
            print(f"  External ID: {result.external_id}")
            if result.content:
                print(f"  Content Preview: {result.content[:200]}...")

        print(f"\nTotal items fetched: {count}")
        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await crawler.close()


async def test_github_crawler():
    """Test GitHub crawler."""
    print("\n" + "=" * 70)
    print("Test 2: GitHub Trending Crawler")
    print("=" * 70)

    crawler = GitHubTrendingCrawler()

    try:
        count = 0
        async for result in crawler.crawl(limit=3):
            count += 1
            print(f"\nItem {count}:")
            print(f"  Name: {result.title}")
            print(f"  URL: {result.url}")
            print(f"  Author: {result.author}")
            print(f"  Stars: {result.metadata.get('stars', 'N/A')}")
            print(f"  Language: {result.metadata.get('language', 'N/A')}")
            if result.content:
                print(f"  Description: {result.content[:100]}...")

        print(f"\nTotal items fetched: {count}")
        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await crawler.close()


async def test_content_analyzer():
    """Test content analyzer."""
    print("\n" + "=" * 70)
    print("Test 3: Content Analyzer")
    print("=" * 70)

    from src.services.ai_intelligence.base import CrawlResult

    analyzer = ContentAnalyzer()

    # Sample arXiv result
    sample_result = CrawlResult(
        title="Large Language Models for Educational Assessment",
        url="https://arxiv.org/abs/2403.12345",
        content="""
We present a novel approach to using Large Language Models for automated educational assessment.
Our method improves upon existing techniques by incorporating domain-specific knowledge and
adapting to individual student learning patterns. Experiments show 15% improvement in grading accuracy.
        """.strip(),
        author="John Doe et al.",
        external_id="2403.12345",
        metadata={"categories": "cs.CL cs.AI", "primary_category": "cs.CL"},
    )

    try:
        print("Analyzing sample content...")
        analysis = await analyzer.analyze(sample_result)

        print(f"\nAnalysis Results:")
        print(f"  Category: {analysis.get('category')}")
        print(f"  Relevance Score: {analysis.get('relevance_score')}")
        print(f"\n  Summary:")
        print(f"    {analysis.get('summary')}")
        print(f"\n  Key Points:")
        for point in analysis.get('key_points', []):
            print(f"    - {point}")
        print(f"\n  Tags: {', '.join(analysis.get('tags', []))}")
        print(f"\n  Relevance Reasoning:")
        print(f"    {analysis.get('relevance_reasoning')}")

        return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 70)
    print("  AI Intelligence Gathering System Test")
    print("=" * 70)

    results = []

    # Note: These tests make real API calls
    # Uncomment the tests you want to run

    print("\nNOTE: These tests make real API calls.")
    print("Select tests to run:")
    print("  1. arXiv Crawler")
    print("  2. GitHub Crawler (requires GitHub token for best results)")
    print("  3. Content Analyzer (requires AI API key)")
    print("  4. All tests")
    print("  0. Exit")

    choice = input("\nEnter choice (0-4): ").strip()

    if choice == "1" or choice == "4":
        results.append(("arXiv Crawler", await test_arxiv_crawler()))

    if choice == "2" or choice == "4":
        results.append(("GitHub Crawler", await test_github_crawler()))

    if choice == "3" or choice == "4":
        results.append(("Content Analyzer", await test_content_analyzer()))

    if choice == "0":
        print("Exiting...")
        return

    # Summary
    if results:
        print("\n" + "=" * 70)
        print("  Test Summary")
        print("=" * 70)

        for name, passed in results:
            status = "PASSED" if passed else "FAILED"
            print(f"  {name}: {status}")

        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

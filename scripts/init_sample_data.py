"""Initialize database with sample data for testing."""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

from src.database import database
from src.models.ai_intelligence import (
    CrawlerSource,
    IntelligenceAnalysis,
    IntelligenceItem,
    IntelligenceReport,
)


async def init_sample_data():
    """Initialize database with sample intelligence data."""
    print("Initializing database with sample data...")

    # Initialize database connection
    database.initialize()

    async with database.session_factory() as db:
        # Check if data already exists
        result = await db.execute(select(IntelligenceItem).limit(1))
        if result.scalar_one_or_none():
            print("Database already has data, skipping initialization.")
            return

        # Create crawler sources
        sources = [
            CrawlerSource(
                name="arXiv AI Papers",
                source_type="arxiv",
                url="http://export.arxiv.org/api/query",
                config={"categories": ["cs.AI", "cs.CL", "cs.LG"]},
                fetch_interval_hours=6,
                is_active=True,
            ),
            CrawlerSource(
                name="GitHub Trending",
                source_type="github",
                url="https://api.github.com/search/repositories",
                config={"query": "AI education language:python stars:>100"},
                fetch_interval_hours=12,
                is_active=True,
            ),
            CrawlerSource(
                name="Hacker News",
                source_type="hackernews",
                url="https://hacker-news.firebaseio.com/v0",
                config={"keywords": ["AI", "education", "machine learning"]},
                fetch_interval_hours=2,
                is_active=True,
            ),
        ]

        for source in sources:
            db.add(source)

        await db.commit()
        print(f"Created {len(sources)} crawler sources")

        # Create sample intelligence items
        items = [
            IntelligenceItem(
                source_type="arxiv",
                source_name="arXiv",
                external_id="arxiv_2403.12345",
                title="Large Language Models for Educational Assessment: A Comprehensive Survey",
                url="https://arxiv.org/abs/2403.12345",
                content="This paper surveys the application of large language models in educational assessment, proposing a new evaluation framework that can significantly improve scoring accuracy and efficiency.",
                content_hash="abc123def456",
                author="John Doe et al.",
                published_at=datetime.utcnow() - timedelta(days=1),
                language="en",
                category="research_paper",
                summary="本文全面综述了大语言模型在教育评估领域的应用，提出了一种新的评估框架，能够显著提高评分准确性和效率。",
                key_points=["提出新的LLM评估框架", "在5个教育场景验证", "准确率提升15%", "支持多语言评估"],
                relevance_score=0.92,
                relevance_reasoning="该研究对我们的AI教育产品有直接参考价值，特别是实验评估模块。",
                tags=["LLM", "Education", "Assessment", "AI"],
                technologies=["PyTorch", "Transformers"],
                is_processed=True,
                is_notified=False,
                is_read=False,
            ),
            IntelligenceItem(
                source_type="github",
                source_name="GitHub",
                external_id="github_teachers_ai",
                title="TeachersAI: Open Source AI Teaching Assistant Framework",
                url="https://github.com/example/teachers-ai",
                content="An open-source AI teaching assistant framework supporting personalized learning path planning and real-time feedback.",
                content_hash="def789ghi012",
                author="OpenEdu Team",
                published_at=datetime.utcnow() - timedelta(hours=5),
                language="en",
                category="development_tool",
                summary="一个开源的AI教学助手框架，支持个性化学习路径规划和实时反馈。",
                key_points=["支持多种教学场景", "模块化设计易于扩展", "已有1000+ Stars", "活跃的社区支持"],
                relevance_score=0.85,
                relevance_reasoning="开源框架可以借鉴其架构设计，对我们的慧瞳产品有启发。",
                tags=["Open Source", "Teaching", "Framework", "GitHub"],
                technologies=["Python", "FastAPI", "Vue.js"],
                is_processed=True,
                is_notified=False,
                is_read=True,
            ),
            IntelligenceItem(
                source_type="arxiv",
                source_name="arXiv",
                external_id="arxiv_2403.67890",
                title="Computer Vision Applications in Smart Classrooms: Latest Research Progress",
                url="https://arxiv.org/abs/2403.67890",
                content="This paper explores the latest applications of CV technology in classroom behavior analysis, attention detection, etc.",
                content_hash="ghi345jkl678",
                author="Research Team",
                published_at=datetime.utcnow() - timedelta(hours=3),
                language="en",
                category="algorithm",
                summary="探讨了CV技术在课堂行为分析、注意力检测等方面的最新应用。",
                key_points=["实时行为分析准确率95%+", "边缘设备部署优化", "隐私保护机制", "与慧瞳产品高度相关"],
                relevance_score=0.88,
                relevance_reasoning="计算机视觉技术直接相关，可用于优化我们的实验AI视觉模块。",
                tags=["Computer Vision", "Smart Classroom", "Edge AI"],
                technologies=["OpenCV", "TensorFlow", "Edge TPU"],
                is_processed=True,
                is_notified=False,
                is_read=False,
            ),
            IntelligenceItem(
                source_type="hackernews",
                source_name="Hacker News",
                external_id="hn_39501234",
                title="OpenAI releases GPT-4 Turbo with improved educational capabilities",
                url="https://openai.com/blog",
                content="New version shows significant improvements in mathematical reasoning and code generation, ideal for educational tutoring scenarios.",
                content_hash="jkl901mno234",
                author="OpenAI",
                published_at=datetime.utcnow() - timedelta(hours=2),
                language="en",
                category="product",
                summary="新版本在数学推理和代码生成方面有显著改进，特别适合教育场景中的解题辅导。",
                key_points=["数学推理能力提升40%", "代码解释更清晰", "支持更长上下文", "API成本降低"],
                relevance_score=0.78,
                relevance_reasoning="GPT-4更新对我们的AI助教系统有直接影响，建议评估升级。",
                tags=["GPT-4", "OpenAI", "Education", "API"],
                technologies=["OpenAI API"],
                is_processed=True,
                is_notified=True,
                is_read=False,
            ),
            IntelligenceItem(
                source_type="hackernews",
                source_name="Hacker News",
                external_id="hn_39505678",
                title="Best Practices for UX Design in AI Education Products",
                url="https://example.com/blog",
                content="Summary of UX design patterns from 10 successful AI education products.",
                content_hash="mno567pqr890",
                author="UX Collective",
                published_at=datetime.utcnow() - timedelta(hours=8),
                language="en",
                category="tutorial",
                summary="总结了10个成功的AI教育产品的UX设计模式。",
                key_points=["简洁的交互设计", "实时反馈机制", "个性化学习路径展示"],
                relevance_score=0.65,
                relevance_reasoning="产品设计参考，可用于改进我们的用户界面。",
                tags=["UX Design", "Product", "Education"],
                technologies=["Design Systems"],
                is_processed=True,
                is_notified=False,
                is_read=True,
            ),
        ]

        for item in items:
            db.add(item)

        await db.commit()
        print(f"Created {len(items)} intelligence items")

        # Create sample report
        report = IntelligenceReport(
            report_type="daily",
            title="AI情报日报 - 2026年3月4日",
            period_start=datetime.utcnow() - timedelta(days=1),
            period_end=datetime.utcnow(),
            summary="今日共收集5条AI相关情报，其中高相关度3条。重点关注：教育评估LLM框架、开源教学助手、CV课堂应用。",
            highlights=[
                {
                    "id": 1,
                    "title": "Large Language Models for Educational Assessment",
                    "url": "https://arxiv.org/abs/2403.12345",
                    "category": "research_paper",
                    "relevance_score": 0.92,
                    "summary": "新的LLM教育评估框架",
                },
                {
                    "id": 2,
                    "title": "TeachersAI: Open Source Framework",
                    "url": "https://github.com/example/teachers-ai",
                    "category": "development_tool",
                    "relevance_score": 0.85,
                    "summary": "开源AI教学助手框架",
                },
            ],
            category_breakdown={"research_paper": 2, "product": 1, "development_tool": 1, "tutorial": 1},
            trends_analysis="本周AI教育领域关注点：1) LLM在评估场景的应用深化 2) 开源教育工具兴起 3) CV技术在课堂场景的落地",
            status="generated",
        )

        db.add(report)
        await db.commit()
        print("Created sample report")

        print("Database initialization complete!")


if __name__ == "__main__":
    asyncio.run(init_sample_data())

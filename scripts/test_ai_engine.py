"""Test script for Alibaba Cloud DashScope AI.

This script tests the AI engine service with the configured DashScope API key.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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

# Import directly from modules (bypass services/__init__.py)
import importlib.util

def load_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load required modules
base_module = load_module_from_path("base", "src/services/ai_engine/base.py")
router_module = load_module_from_path("router", "src/services/ai_engine/router.py")
service_module = load_module_from_path("service", "src/services/ai_engine/service.py")

# Get classes
Message = base_module.Message
AIEngineService = service_module.AIEngineService


async def test_ai_engine():
    """Test AI engine with various tasks."""
    print("=" * 70)
    print("  Alibaba Cloud DashScope AI Engine Test")
    print("=" * 70)
    print()

    # Create service instance
    ai_engine = AIEngineService()

    try:
        # Test 1: Simple chat
        print("Test 1: Simple Chat")
        print("-" * 70)

        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="Hello! What is your name and capabilities? Please respond in Chinese."),
        ]

        response = await ai_engine.chat(messages)
        print(f"Model: {response.model}")
        print(f"Response: {response.content[:300]}...")
        print(f"Usage: {response.usage}")
        print()

        # Test 2: Text generation
        print("Test 2: Text Generation")
        print("-" * 70)

        text = await ai_engine.generate_text(
            prompt="What are 3 key benefits of AI in management? Respond in Chinese.",
            system_prompt="You are a management consultant. Be concise.",
        )
        print(f"Generated text: {text[:400]}...")
        print()

        # Test 3: Document summarization
        print("Test 3: Document Summarization")
        print("-" * 70)

        sample_doc = """
        团队绩效报告 - 2026年2月第4周

        研发团队本周取得了显著进展。
        用户认证模块提前完成开发。
        但是支付集成由于API变更面临延迟。
        团队加班解决了移动应用的关键bug。
        代码审查覆盖率提升到85%。
        三个新功能部署到测试环境。
        客户满意度分数提高了12%。
        下周我们计划专注于性能优化。
        """

        summary = await ai_engine.summarize_document(
            text=sample_doc,
            style="executive",
            max_length=200,
        )
        print(f"Summary: {summary}")
        print()

        # Test 4: Data analysis
        print("Test 4: Data Analysis")
        print("-" * 70)

        sample_data = {
            "week": "2026-W09",
            "tasks_completed": 45,
            "tasks_delayed": 8,
            "bugs_fixed": 23,
            "bugs_reported": 18,
            "code_reviews": 67,
            "deployments": 5,
            "team_members": 12,
            "avg_task_duration_hours": 16.5,
        }

        analysis = await ai_engine.analyze_data(
            data=sample_data,
            analysis_type="trends",
            context="这是研发团队的周度指标数据",
        )
        print(f"Analysis Summary: {analysis.get('summary', 'N/A')}")
        print(f"Key Insights: {analysis.get('key_insights', [])}")
        print()

        # Test 5: Report section generation
        print("Test 5: Report Section Generation")
        print("-" * 70)

        report_section = await ai_engine.generate_report_section(
            section_type="summary",
            data=sample_data,
            tone="professional",
        )
        print(f"Report Section:\n{report_section}")
        print()

        print("=" * 70)
        print("All tests completed successfully!")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await ai_engine.close()


if __name__ == "__main__":
    result = asyncio.run(test_ai_engine())
    sys.exit(0 if result else 1)

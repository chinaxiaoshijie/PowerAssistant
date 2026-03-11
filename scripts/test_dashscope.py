"""Test script for Alibaba Cloud DashScope AI.

Tests the DashScope API directly using the configured API key.
"""

import asyncio
import json
import sys

import aiohttp

# DashScope API Key
DASHSCOPE_API_KEY = "sk-4ac26721ba2e4c54ba6e8a777e42e257"
BASE_URL = "https://dashscope.aliyuncs.com/api/v1"


class DashScopeTester:
    """Simple DashScope API tester."""

    def __init__(self):
        self.api_key = DASHSCOPE_API_KEY
        self.base_url = BASE_URL

    async def test_chat_completion(self):
        """Test basic chat completion."""
        print("=" * 70)
        print("Test 1: Chat Completion")
        print("=" * 70)

        url = f"{self.base_url}/services/aigc/text-generation/generation"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "qwen-max",
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant."
                    },
                    {
                        "role": "user",
                        "content": "你好！请简单介绍一下你自己，以及你能帮我做什么？请用中文回答。"
                    }
                ]
            },
            "parameters": {
                "temperature": 0.7,
                "max_tokens": 500,
                "result_format": "message"
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"Response Status: {response.status}")
                    print(f"Request ID: {data.get('request_id', 'N/A')}")

                    output = data.get("output", {})
                    choices = output.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        content = message.get("content", "")
                        print(f"\nAI Response:\n{content}")

                    usage = data.get("usage", {})
                    print(f"\nUsage: {usage}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"Error: HTTP {response.status}")
                    print(f"Response: {error_text}")
                    return False

    async def test_document_summarization(self):
        """Test document summarization."""
        print("\n" + "=" * 70)
        print("Test 2: Document Summarization")
        print("=" * 70)

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

        url = f"{self.base_url}/services/aigc/text-generation/generation"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        prompt = f"""请对以下团队周报进行 executive summary 风格的总结，控制在100字以内：

{sample_doc}
"""

        payload = {
            "model": "qwen-max",
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个管理报告撰写助手。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "temperature": 0.3,
                "max_tokens": 300,
                "result_format": "message"
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    output = data.get("output", {})
                    choices = output.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        content = message.get("content", "")
                        print(f"Summary:\n{content}")
                        return True
                else:
                    error_text = await response.text()
                    print(f"Error: HTTP {response.status}")
                    print(f"Response: {error_text}")
                    return False

    async def test_data_analysis(self):
        """Test data analysis."""
        print("\n" + "=" * 70)
        print("Test 3: Data Analysis")
        print("=" * 70)

        sample_data = {
            "week": "2026-W09",
            "tasks_completed": 45,
            "tasks_delayed": 8,
            "bugs_fixed": 23,
            "bugs_reported": 18,
            "code_reviews": 67,
            "deployments": 5,
            "team_members": 12,
        }

        url = f"{self.base_url}/services/aigc/text-generation/generation"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        prompt = f"""请分析以下研发团队周度数据，提供关键洞察和建议，用JSON格式返回：

数据：{json.dumps(sample_data, ensure_ascii=False, indent=2)}

请以JSON格式返回，包含以下字段：
- summary: 简要总结
- key_insights: 关键洞察（数组）
- recommendations: 建议（数组）
- risk_factors: 风险因素（数组）
"""

        payload = {
            "model": "qwen-max",
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个数据分析专家，擅长从研发数据中提取洞察。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "temperature": 0.2,
                "max_tokens": 800,
                "result_format": "message"
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    output = data.get("output", {})
                    choices = output.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        content = message.get("content", "")
                        print(f"Analysis Result:\n{content}")
                        return True
                else:
                    error_text = await response.text()
                    print(f"Error: HTTP {response.status}")
                    print(f"Response: {error_text}")
                    return False

    async def run_all_tests(self):
        """Run all tests."""
        print("\n" + "=" * 70)
        print("  Alibaba Cloud DashScope AI Engine Test")
        print("=" * 70)
        print(f"API Key: {self.api_key[:10]}...{self.api_key[-4:]}")
        print()

        results = []

        try:
            results.append(("Chat Completion", await self.test_chat_completion()))
        except Exception as e:
            print(f"Chat Completion Test Failed: {e}")
            results.append(("Chat Completion", False))

        try:
            results.append(("Document Summarization", await self.test_document_summarization()))
        except Exception as e:
            print(f"Document Summarization Test Failed: {e}")
            results.append(("Document Summarization", False))

        try:
            results.append(("Data Analysis", await self.test_data_analysis()))
        except Exception as e:
            print(f"Data Analysis Test Failed: {e}")
            results.append(("Data Analysis", False))

        # Summary
        print("\n" + "=" * 70)
        print("  Test Summary")
        print("=" * 70)

        for name, passed in results:
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"  {name}: {status}")

        all_passed = all(passed for _, passed in results)

        print("=" * 70)
        if all_passed:
            print("  All tests passed!")
        else:
            print("  Some tests failed.")
        print("=" * 70)

        return all_passed


if __name__ == "__main__":
    tester = DashScopeTester()
    result = asyncio.run(tester.run_all_tests())
    sys.exit(0 if result else 1)

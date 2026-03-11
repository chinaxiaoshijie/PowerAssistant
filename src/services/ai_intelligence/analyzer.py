"""AI Content Analyzer for intelligence items.

Uses AI models to analyze and categorize intelligence content.
"""

import json
from typing import Dict, List, Optional

import structlog

from src.services.ai_intelligence.base import CrawlResult
from src.services.ai_engine import ai_engine

logger = structlog.get_logger()


class ContentAnalyzer:
    """Analyzes intelligence content using AI models.

    Provides:
    - Category classification
    - Summary generation
    - Relevance scoring
    - Key point extraction
    - Action item suggestions
    """

    # Relevance context for our organization
    RELEVANCE_CONTEXT = """
You are analyzing content for a management assistant at Malong Technologies (码隆科技),
a company focused on AI + Education solutions.

The company works on:
- Educational AI products (慧瞳 I3, teaching AI systems)
- Computer Vision and Deep Learning
- Educational Large Language Models
- AI-powered learning spaces for schools

The target audience includes:
- R&D department managers
- Delivery department managers
- Technical leads and architects
- Product managers

Score relevance based on:
- Can this improve our AI education products?
- Can this optimize our development process?
- Can this enhance our algorithms or models?
- Is this relevant to education technology?
"""

    def __init__(self):
        """Initialize content analyzer."""
        self._logger = logger.bind(component="ContentAnalyzer")

    async def analyze(
        self,
        result: CrawlResult,
        analysis_type: str = "general",
    ) -> Dict:
        """Analyze a crawled item.

        Args:
            result: Crawl result to analyze
            analysis_type: Type of analysis (general/technical/business)

        Returns:
            Analysis results dictionary
        """
        self._logger.debug(
            "analyzing_content",
            title=result.title[:50],
            source=result.external_id,
        )

        # Build analysis prompt
        content = f"""
Title: {result.title}
Author: {result.author or 'Unknown'}
Content: {result.content or 'N/A'}
URL: {result.url}
"""

        if result.metadata:
            content += f"\nMetadata: {json.dumps(result.metadata, ensure_ascii=False, indent=2)}"

        # Run analysis
        analysis = await self._run_ai_analysis(content, analysis_type)

        self._logger.debug(
            "content_analyzed",
            title=result.title[:50],
            category=analysis.get("category"),
            relevance=analysis.get("relevance_score"),
        )

        return analysis

    async def _run_ai_analysis(
        self,
        content: str,
        analysis_type: str,
    ) -> Dict:
        """Run AI analysis on content.

        Args:
            content: Content to analyze
            analysis_type: Analysis type

        Returns:
            Structured analysis results
        """
        system_prompt = f"""{self.RELEVANCE_CONTEXT}

You are an AI intelligence analyst. Analyze the provided content and respond in JSON format with:
{{
    "category": "algorithm|product|development_tool|research_paper|industry_news|tutorial|opinion",
    "summary": "2-3 sentence summary in Chinese",
    "key_points": ["point 1", "point 2", "point 3"],
    "tags": ["tag1", "tag2"],
    "technologies": ["technology1", "technology2"],
    "relevance_score": 0.0-1.0,
    "relevance_reasoning": "Why this is relevant to our AI education work",
    "action_items": ["suggested action 1", "suggested action 2"]
}}

Be concise but informative."""

        try:
            response = await ai_engine.generate_text(
                prompt=f"Analyze this AI-related content:\n\n{content[:4000]}",
                system_prompt=system_prompt,
                temperature=0.3,
            )

            # Parse JSON response
            # Extract JSON from response (handle markdown code blocks)
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            result = json.loads(json_str.strip())

            # Ensure all required fields
            return {
                "category": result.get("category", "uncategorized"),
                "summary": result.get("summary", ""),
                "key_points": result.get("key_points", []),
                "tags": result.get("tags", []),
                "technologies": result.get("technologies", []),
                "relevance_score": float(result.get("relevance_score", 0)),
                "relevance_reasoning": result.get("relevance_reasoning", ""),
                "action_items": result.get("action_items", []),
            }

        except json.JSONDecodeError as e:
            self._logger.error("json_parse_failed", error=str(e), response=response[:200])
            # Return basic analysis on parse failure
            return {
                "category": "uncategorized",
                "summary": response[:500] if response else "",
                "key_points": [],
                "tags": [],
                "technologies": [],
                "relevance_score": 0.0,
                "relevance_reasoning": "Failed to parse analysis",
                "action_items": [],
            }

        except Exception as e:
            self._logger.error("analysis_failed", error=str(e))
            return {
                "category": "uncategorized",
                "summary": "",
                "key_points": [],
                "tags": [],
                "technologies": [],
                "relevance_score": 0.0,
                "relevance_reasoning": f"Analysis error: {str(e)}",
                "action_items": [],
            }

    async def batch_analyze(
        self,
        results: List[CrawlResult],
        analysis_type: str = "general",
    ) -> List[Dict]:
        """Analyze multiple items.

        Args:
            results: List of crawl results
            analysis_type: Analysis type

        Returns:
            List of analysis results
        """
        analyses = []

        for result in results:
            try:
                analysis = await self.analyze(result, analysis_type)
                analyses.append(analysis)
            except Exception as e:
                self._logger.error(
                    "batch_analysis_item_failed",
                    title=result.title[:50],
                    error=str(e),
                )
                analyses.append({
                    "category": "uncategorized",
                    "summary": "",
                    "key_points": [],
                    "tags": [],
                    "technologies": [],
                    "relevance_score": 0.0,
                    "relevance_reasoning": f"Error: {str(e)}",
                    "action_items": [],
                })

        return analyses

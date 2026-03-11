"""Specialized AI agents for different domains.

This module implements four specialized AI agents that analyze AI intelligence
and provide domain-specific recommendations for Malong Technologies.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ai_intelligence import IntelligenceItem, IntelligenceAnalysis
from src.models.feishu_tasks import FeishuTask, FeishuProject
from src.services.ai_engine import ai_engine

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Abstract base class for specialized AI agents."""

    def __init__(self, db_session: AsyncSession):
        """Initialize base agent.

        Args:
            db_session: Database session
        """
        self._db = db_session
        self._logger = logger.bind(agent=self.__class__.__name__)

    @abstractmethod
    async def analyze(self) -> Dict[str, Any]:
        """Perform domain-specific analysis.

        Returns:
            Analysis results and recommendations
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get agent name."""
        pass


class DevelopmentPracticeAgent(BaseAgent):
    """仕杰 - AI原生开发新实践智能体.

    Analyzes AI development trends and recommends improvements to development workflow.
    """

    def get_name(self) -> str:
        return "仕杰 (AI原生开发实践)"

    async def analyze(self) -> Dict[str, Any]:
        """Analyze AI development trends and suggest workflow improvements."""
        self._logger.info("starting_analysis")

        try:
            # Fetch recent intelligence related to development
            from sqlalchemy import select, desc

            query = (
                select(IntelligenceItem)
                .where(IntelligenceItem.category.in_([
                    "development_tool",
                    "tutorial",
                    "research_paper",
                ]))
                .where(IntelligenceItem.relevance_score >= 0.6)
                .order_by(desc(IntelligenceItem.created_at))
                .limit(20)
            )

            result = await self._db.execute(query)
            items = result.scalars().all()

            if not items:
                return self._build_response(
                    status="no_data",
                    recommendations=["暂无相关开发实践数据"],
                )

            # Extract insights
            insights = []
            recommendations = []

            for item in items:
                insights.append({
                    "title": item.title,
                    "summary": item.summary,
                    "source": item.source_name,
                    "relevance": item.relevance_score,
                })

                # Generate recommendations based on content
                if item.content:
                    if "workflow" in item.content.lower() or "CI/CD" in item.content:
                        recommendations.append(
                            f"考虑引入 {item.title} 中的实践来优化我们的开发流程"
                        )
                    elif "testing" in item.content.lower() or "质量" in item.content:
                        recommendations.append(
                            f"参考 {item.title} 改进我们的测试策略"
                        )
                    elif "git" in item.content.lower() or "版本控制" in item.content:
                        recommendations.append(
                            f"评估 {item.title} 对我们版本控制流程的改进价值"
                        )

            # Use AI to synthesize insights
            ai_summary = await self._generate_ai_summary(insights)

            return self._build_response(
                status="success",
                insights=insights[:10],  # Limit to top 10
                recommendations=recommendations[:5] or [
                    "暂无具体的开发流程改进建议",
                    "建议关注更多AI原生开发实践相关的技术文章",
                ],
                ai_summary=ai_summary,
            )

        except Exception as e:
            self._logger.error("analysis_failed", error=str(e))
            return self._build_response(
                status="error",
                error=str(e),
            )

    async def _generate_ai_summary(self, insights: List[Dict]) -> str:
        """Generate AI-powered summary of insights."""
        try:
            content = "\n".join([
                f"【{i['title']}】\n{i['summary']}\n"
                for i in insights[:5]
            ])

            prompt = f"""你是一位资深的软件开发专家，正在为码隆科技的研发团队分析最新的AI原生开发实践趋势。

请基于以下信息，给出3-5条具体的开发流程改进建议：

{content}

要求：
1. 建议要具体、可操作
2. 考虑我们公司的实际情况（50人规模，AI教育领域）
3. 优先考虑能提高开发效率和代码质量的改进
4. 每条建议用"-"开头

请用简洁的中文回答："""

            response = await ai_engine.generate_text(
                prompt=prompt,
                max_tokens=300,
            )
            return response

        except Exception as e:
            self._logger.warning("ai_summary_failed", error=str(e))
            return "AI生成摘要失败，使用基础分析结果"

    def _build_response(self, **kwargs) -> Dict[str, Any]:
        """Build standardized response."""
        return {
            "agent": self.get_name(),
            "timestamp": datetime.utcnow().isoformat(),
            "data": kwargs,
        }


class AlgorithmResearchAgent(BaseAgent):
    """运明 - AI算法进展智能体.

    Analyzes latest AI algorithm research and recommends improvements to our algorithms.
    """

    def get_name(self) -> str:
        return "运明 (AI算法研究)"

    async def analyze(self) -> Dict[str, Any]:
        """Analyze AI algorithm research and suggest algorithm improvements."""
        self._logger.info("starting_analysis")

        try:
            # Fetch recent algorithm research
            from sqlalchemy import select, desc

            query = (
                select(IntelligenceItem)
                .where(IntelligenceItem.category == "algorithm")
                .where(IntelligenceItem.relevance_score >= 0.7)
                .order_by(desc(IntelligenceItem.created_at))
                .limit(15)
            )

            result = await self._db.execute(query)
            items = result.scalars().all()

            if not items:
                return self._build_response(
                    status="no_data",
                    recommendations=["暂无相关算法研究数据"],
                )

            insights = []
            recommendations = []

            for item in items:
                insights.append({
                    "title": item.title,
                    "summary": item.summary,
                    "key_points": item.key_points,
                    "technologies": item.technologies,
                    "source": item.source_name,
                })

                # Generate recommendations
                if item.key_points:
                    for point in item.key_points:
                        if any(kw in point.lower() for kw in ["accuracy", "precision", "performance", "效率"]):
                            recommendations.append(
                                f"研究 {item.title} 中的算法优化方法，可能提升我们产品的性能"
                            )
                        elif "computer vision" in point.lower() or "视觉" in point:
                            recommendations.append(
                                f"评估 {item.title} 中的CV技术对慧瞳产品的应用价值"
                            )

            ai_summary = await self._generate_ai_summary(insights)

            return self._build_response(
                status="success",
                insights=insights[:8],
                recommendations=recommendations[:5] or [
                    "建议关注更多计算机视觉和深度学习领域的最新研究成果",
                    "定期评估新技术对我们现有算法的改进潜力",
                ],
                ai_summary=ai_summary,
            )

        except Exception as e:
            self._logger.error("analysis_failed", error=str(e))
            return self._build_response(
                status="error",
                error=str(e),
            )

    async def _generate_ai_summary(self, insights: List[Dict]) -> str:
        """Generate AI-powered summary."""
        try:
            content = "\n".join([
                f"【{i['title']}】\n" + "\n".join(i.get('key_points', []))
                for i in insights[:5]
            ])

            prompt = f"""你是一位AI算法专家，正在为码隆科技（专注于AI+教育）分析最新的算法研究进展。

请基于以下研究信息，给出3-5条具体的算法改进建议：

{content}

重点关注：
1. 计算机视觉和深度学习领域
2. 教育场景的适配性
3. 算法性能和准确率提升
4. 实际应用可行性

请用简洁的中文回答，每条建议用"-"开头："""

            response = await ai_engine.generate_text(
                prompt=prompt,
                max_tokens=300,
            )
            return response

        except Exception as e:
            self._logger.warning("ai_summary_failed", error=str(e))
            return "AI生成摘要失败"

    def _build_response(self, **kwargs) -> Dict[str, Any]:
        return {
            "agent": self.get_name(),
            "timestamp": datetime.utcnow().isoformat(),
            "data": kwargs,
        }


class ProductInnovationAgent(BaseAgent):
    """逍虓 - AI新产品智能体.

    Analyzes latest AI products and suggests new features for our education products.
    """

    def get_name(self) -> str:
        return "逍虓 (AI产品创新)"

    async def analyze(self) -> Dict[str, Any]:
        """Analyze AI products and suggest new features."""
        self._logger.info("starting_analysis")

        try:
            # Fetch recent product news
            from sqlalchemy import select, desc

            query = (
                select(IntelligenceItem)
                .where(IntelligenceItem.category.in_([
                    "product",
                    "industry_news",
                ]))
                .where(IntelligenceItem.relevance_score >= 0.6)
                .order_by(desc(IntelligenceItem.created_at))
                .limit(15)
            )

            result = await self._db.execute(query)
            items = result.scalars().all()

            if not items:
                return self._build_response(
                    status="no_data",
                    recommendations=["暂无相关产品信息"],
                )

            insights = []
            recommendations = []

            for item in items:
                insights.append({
                    "title": item.title,
                    "summary": item.summary,
                    "source": item.source_name,
                    "tags": item.tags,
                })

                # Generate product feature suggestions
                if item.tags and any(t in item.tags for t in ["教育", "education", "learning", "teaching"]):
                    recommendations.append(
                        f"参考 {item.title} 的功能设计，考虑在我们的产品中实现类似特性"
                    )
                elif item.summary and ("AI" in item.summary or "智能" in item.summary):
                    recommendations.append(
                        f"分析 {item.title} 的应用场景，寻找与我们教育产品结合的机会"
                    )

            ai_summary = await self._generate_ai_summary(insights)

            return self._build_response(
                status="success",
                insights=insights[:8],
                recommendations=recommendations[:5] or [
                    "建议更多关注教育科技领域的新产品动态",
                    "定期分析竞品功能，寻找差异化创新点",
                ],
                ai_summary=ai_summary,
            )

        except Exception as e:
            self._logger.error("analysis_failed", error=str(e))
            return self._build_response(
                status="error",
                error=str(e),
            )

    async def _generate_ai_summary(self, insights: List[Dict]) -> str:
        """Generate AI-powered product innovation summary."""
        try:
            content = "\n".join([
                f"【{i['title']}】\n{i['summary']}\nTags: {', '.join(i.get('tags', []))}"
                for i in insights[:5]
            ])

            prompt = f"""你是一位产品创新专家，正在为码隆科技的教育AI产品寻找创新灵感。

基于以下新产品信息，请给出3-5条具体的产品功能创新建议：

{content}

考虑因素：
1. 我们的产品：慧瞳 I3、AI教学助手、学习空间等
2. 目标用户：学生、教师、学校
3. 教育场景：课堂、自习、在线学习
4. 技术可行性：结合我们现有的AI能力

请用简洁的中文回答，每条建议用"-"开头，包括：
- 具体功能描述
- 目标用户/场景
- 预期价值"""

            response = await ai_engine.generate_text(
                prompt=prompt,
                max_tokens=400,
            )
            return response

        except Exception as e:
            self._logger.warning("ai_summary_failed", error=str(e))
            return "AI生成摘要失败"

    def _build_response(self, **kwargs) -> Dict[str, Any]:
        return {
            "agent": self.get_name(),
            "timestamp": datetime.utcnow().isoformat(),
            "data": kwargs,
        }


class GeneralTechnologyAgent(BaseAgent):
    """通用技术趋势智能体.

    Monitors general AI and technology trends and provides strategic insights.
    """

    def get_name(self) -> str:
        return "通用技术趋势"

    async def analyze(self) -> Dict[str, Any]:
        """Monitor general AI trends and provide strategic insights."""
        self._logger.info("starting_analysis")

        try:
            from sqlalchemy import select, desc, func

            # Get statistics
            total_result = await self._db.execute(
                select(func.count()).select_from(IntelligenceItem)
            )
            total_items = total_result.scalar()

            # Get recent items across all categories
            query = (
                select(IntelligenceItem)
                .where(IntelligenceItem.created_at >= datetime.utcnow() - timedelta(days=7))
                .order_by(desc(IntelligenceItem.relevance_score))
                .limit(10)
            )

            result = await self._db.execute(query)
            top_items = result.scalars().all()

            insights = []
            for item in top_items:
                insights.append({
                    "title": item.title,
                    "category": item.category,
                    "source": item.source_name,
                    "relevance": item.relevance_score,
                    "summary": item.summary,
                })

            return self._build_response(
                status="success",
                statistics={
                    "total_items": total_items,
                    "recent_7_days": len(top_items),
                    "high_relevance": len([i for i in top_items if i.relevance_score >= 0.8]),
                },
                top_insights=insights,
                recommendations=[
                    "建议定期查看高相关度情报，把握技术趋势",
                    "关注跨领域技术融合机会",
                    "建立技术雷达机制，系统化跟踪新技术",
                ],
            )

        except Exception as e:
            self._logger.error("analysis_failed", error=str(e))
            return self._build_response(
                status="error",
                error=str(e),
            )

    def _build_response(self, **kwargs) -> Dict[str, Any]:
        return {
            "agent": self.get_name(),
            "timestamp": datetime.utcnow().isoformat(),
            "data": kwargs,
        }


# Agent registry
AGENT_REGISTRY = {
    "development_practice": DevelopmentPracticeAgent,
    "algorithm_research": AlgorithmResearchAgent,
    "product_innovation": ProductInnovationAgent,
    "general_technology": GeneralTechnologyAgent,
}


def create_agent(agent_type: str, db_session: AsyncSession) -> BaseAgent:
    """Create agent instance.

    Args:
        agent_type: Type of agent to create
        db_session: Database session

    Returns:
        Agent instance

    Raises:
        ValueError: If agent type is not supported
    """
    agent_class = AGENT_REGISTRY.get(agent_type)
    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}")
    return agent_class(db_session)


async def run_all_agents(db_session: AsyncSession) -> Dict[str, Any]:
    """Run all agents and aggregate results.

    Args:
        db_session: Database session

    Returns:
        Aggregated analysis results from all agents
    """
    logger.info("running_all_agents")

    results = {}
    for agent_type, agent_class in AGENT_REGISTRY.items():
        try:
            agent = agent_class(db_session)
            results[agent_type] = await agent.analyze()
            logger.info("agent_completed", agent=agent_type)
        except Exception as e:
            logger.error("agent_failed", agent=agent_type, error=str(e))
            results[agent_type] = {
                "agent": agent_class.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "status": "error",
                    "error": str(e),
                },
            }

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "agents": results,
    }

"""AI Engine Service - High-level AI operations for business logic.

This module provides business-friendly AI operations including:
- Document summarization
- Report generation
- Decision analysis
- Code review
- Text analysis
"""

import json
from typing import AsyncGenerator, Dict, List, Optional

import structlog

from src.services.ai_engine.base import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
)
from src.services.ai_engine.router import model_router

logger = structlog.get_logger()


class AIEngineService:
    """High-level AI engine service for business operations.

    Usage:
        >>> service = AIEngineService()
        >>> summary = await service.summarize_document(doc_text)
        >>> report = await service.generate_weekly_report(data)
    """

    def __init__(self):
        """Initialize AI engine service."""
        self._logger = logger.bind(component="AIEngineService")
        self._router = model_router

    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> ChatCompletionResponse:
        """Send chat messages to AI model.

        Args:
            messages: List of chat messages
            model: Specific model to use (optional)
            temperature: Sampling temperature (0-2)
            stream: Whether to stream response

        Returns:
            Chat completion response
        """
        client, selected_model = await self._router.get_client_for_task(
            task_type="chat",
            preferred_model=model,
        )

        request = ChatCompletionRequest(
            messages=messages,
            model=selected_model,
            temperature=temperature,
            stream=stream,
        )

        self._logger.debug(
            "sending_chat_request",
            model=selected_model,
            message_count=len(messages),
        )

        return await client.chat_complete(request)

    async def chat_stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Stream chat response.

        Args:
            messages: List of chat messages
            model: Specific model to use
            temperature: Sampling temperature

        Yields:
            Response text chunks
        """
        client, selected_model = await self._router.get_client_for_task(
            task_type="chat",
            preferred_model=model,
        )

        request = ChatCompletionRequest(
            messages=messages,
            model=selected_model,
            temperature=temperature,
            stream=True,
        )

        async for chunk in client.chat_complete_stream(request):
            yield chunk

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text from a prompt.

        Args:
            prompt: User prompt
            system_prompt: System instructions (optional)
            model: Specific model to use
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        messages = []

        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))

        messages.append(Message(role="user", content=prompt))

        response = await self.chat(messages, model=model, temperature=temperature)
        return response.content

    async def summarize_document(
        self,
        text: str,
        max_length: int = 500,
        style: str = "concise",
    ) -> str:
        """Summarize a document.

        Args:
            text: Document text to summarize
            max_length: Maximum summary length in characters
            style: Summary style (concise/detailed/key_points)

        Returns:
            Summary text
        """
        style_prompts = {
            "concise": "Provide a concise summary in 2-3 sentences.",
            "detailed": "Provide a comprehensive summary with main points and conclusions.",
            "key_points": "List the key points in bullet format.",
            "executive": "Provide an executive summary for management decision-making.",
        }

        system_prompt = f"""You are a document summarization assistant.
{style_prompts.get(style, style_prompts["concise"])}
Maximum length: {max_length} characters."""

        prompt = f"Please summarize the following document:\n\n{text[:8000]}"

        client, model = await self._router.get_client_for_task(
            task_type="summarization"
        )

        response = await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=0.3,  # Lower temperature for consistency
        )

        return response

    async def analyze_data(
        self,
        data: Dict,
        analysis_type: str = "general",
        context: Optional[str] = None,
    ) -> Dict:
        """Analyze structured data and return insights.

        Args:
            data: Structured data to analyze
            analysis_type: Type of analysis (trends/anomalies/summary)
            context: Additional context about the data

        Returns:
            Analysis results as dictionary
        """
        system_prompt = """You are a data analysis assistant.
Analyze the provided data and return insights in JSON format with the following structure:
{
    "summary": "Brief summary of findings",
    "key_insights": ["insight 1", "insight 2", ...],
    "recommendations": ["recommendation 1", ...],
    "risk_factors": ["risk 1", ...] (if applicable)
}"""

        data_str = json.dumps(data, ensure_ascii=False, indent=2)

        prompt = f"Analyze the following data:\n\n{data_str}"

        if context:
            prompt += f"\n\nContext: {context}"

        prompt += f"\n\nAnalysis type: {analysis_type}"

        client, model = await self._router.get_client_for_task(
            task_type="analysis"
        )

        response = await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=0.2,
        )

        # Try to parse as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Return as text if not valid JSON
            return {
                "summary": response,
                "key_insights": [],
                "recommendations": [],
            }

    async def generate_report_section(
        self,
        section_type: str,
        data: Dict,
        tone: str = "professional",
    ) -> str:
        """Generate a section of a management report.

        Args:
            section_type: Type of section (summary/metrics/issues/recommendations)
            data: Data for the section
            tone: Writing tone (professional/casual/technical)

        Returns:
            Generated report section
        """
        tone_instructions = {
            "professional": "Use professional business language suitable for management reports.",
            "casual": "Use conversational but clear language.",
            "technical": "Use technical terminology appropriate for technical teams.",
        }

        section_prompts = {
            "summary": "Generate an executive summary of the current situation.",
            "metrics": "Summarize key metrics and their trends.",
            "issues": "Identify and describe current issues or risks.",
            "achievements": "Highlight key achievements and milestones.",
            "recommendations": "Provide actionable recommendations.",
            "next_steps": "Outline specific next steps and action items.",
        }

        system_prompt = f"""You are a management report writing assistant.
{tone_instructions.get(tone, tone_instructions["professional"])}
{section_prompts.get(section_type, "Generate appropriate content.")}
Keep the response concise and focused."""

        data_str = json.dumps(data, ensure_ascii=False, indent=2)
        prompt = f"Generate a {section_type} section based on this data:\n\n{data_str}"

        client, model = await self._router.get_client_for_task(
            task_type="writing"
        )

        return await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=0.5,
        )

    async def code_review(
        self,
        code: str,
        language: str = "python",
        focus: str = "general",
    ) -> Dict:
        """Perform AI-powered code review.

        Args:
            code: Code to review
            language: Programming language
            focus: Review focus (security/performance/style/general)

        Returns:
            Review results with issues and suggestions
        """
        system_prompt = """You are a code review assistant.
Review the provided code and return findings in JSON format:
{
    "overall_assessment": "Brief overall assessment",
    "issues": [
        {
            "severity": "high/medium/low",
            "category": "security/performance/style/maintainability",
            "description": "Issue description",
            "suggestion": "Suggested fix"
        }
    ],
    "strengths": ["positive aspect 1", ...],
    "recommendations": ["general recommendation 1", ...]
}"""

        prompt = f"Review the following {language} code:\n\n```{language}\n{code}\n```"

        if focus != "general":
            prompt += f"\n\nFocus areas: {focus}"

        client, model = await self._router.get_client_for_task(
            task_type="code_review"
        )

        response = await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=0.2,
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "overall_assessment": response,
                "issues": [],
                "strengths": [],
                "recommendations": [],
            }

    async def decision_analysis(
        self,
        decision_context: str,
        options: List[str],
        criteria: Optional[List[str]] = None,
    ) -> Dict:
        """Analyze a decision with multiple options.

        Args:
            decision_context: Context and background of the decision
            options: List of options to consider
            criteria: Evaluation criteria (optional)

        Returns:
            Analysis of each option with recommendation
        """
        system_prompt = """You are a decision analysis assistant.
Analyze the provided options and return analysis in JSON format:
{
    "summary": "Brief summary of the decision",
    "option_analysis": [
        {
            "option": "option description",
            "pros": ["pro 1", ...],
            "cons": ["con 1", ...],
            "risk_level": "high/medium/low",
            "effort_estimate": "high/medium/low"
        }
    ],
    "recommendation": "Recommended option with reasoning",
    "key_considerations": ["consideration 1", ...]
}"""

        options_str = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])

        prompt = f"""Decision Context:
{decision_context}

Options to Consider:
{options_str}"""

        if criteria:
            prompt += f"\n\nEvaluation Criteria:\n" + "\n".join([f"- {c}" for c in criteria])

        client, model = await self._router.get_client_for_task(
            task_type="analysis"
        )

        response = await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=0.3,
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "summary": response,
                "option_analysis": [],
                "recommendation": "",
                "key_considerations": [],
            }

    async def close(self) -> None:
        """Close service resources."""
        await self._router.close_all()


# Global service instance
ai_engine = AIEngineService()

"""Feishu notification service for AI intelligence reports.

Sends daily/weekly intelligence reports to Feishu via card messages.
"""

from datetime import datetime
from typing import List, Optional

import structlog

from src.services.feishu.client import FeishuClient

logger = structlog.get_logger()


class FeishuNotificationService:
    """Service for sending notifications to Feishu.

    Supports:
    - Card messages for reports
    - Text messages for alerts
    - Group and individual chat
    """

    def __init__(
        self,
        feishu_client: Optional[FeishuClient] = None,
        webhook_url: Optional[str] = None,
    ):
        """Initialize notification service.

        Args:
            feishu_client: Feishu API client
            webhook_url: Optional webhook URL for group notifications
        """
        self._client = feishu_client
        self._webhook_url = webhook_url
        self._logger = logger.bind(component="FeishuNotificationService")

    async def _get_client(self) -> FeishuClient:
        """Get or create Feishu client."""
        if self._client is None:
            self._client = FeishuClient()
            await self._client.__aenter__()
        return self._client

    def _build_daily_report_card(
        self,
        title: str,
        summary: str,
        highlights: List[dict],
        stats: dict,
    ) -> dict:
        """Build Feishu card message for daily report.

        Args:
            title: Report title
            summary: Executive summary
            highlights: Top highlights
            stats: Statistics

        Returns:
            Card message JSON
        """
        # Build highlight elements
        highlight_elements = []
        for i, h in enumerate(highlights[:5], 1):
            relevance_emoji = "🔥" if h.get("relevance_score", 0) > 0.8 else "📌"
            highlight_elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{relevance_emoji} **{h.get('title', 'Untitled')[:50]}...**\n"
                               f"   分类: {h.get('category', 'N/A')} | "
                               f"相关度: {h.get('relevance_score', 0):.0%}"
                }
            })
            highlight_elements.append({"tag": "hr"})

        # Remove last hr
        if highlight_elements:
            highlight_elements.pop()

        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 {title}"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📋 概览**\n{summary}"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📈 统计**\n"
                                   f"• 今日新增: {stats.get('items_today', 0)} 条\n"
                                   f"• 高相关度: {stats.get('high_relevance', 0)} 条\n"
                                   f"• 未读情报: {stats.get('unread', 0)} 条"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**🌟 重点推荐**"
                    }
                },
                *highlight_elements,
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "查看完整报告"
                            },
                            "type": "primary",
                            "url": "http://localhost:8000/dashboard"
                        }
                    ]
                }
            ]
        }

        return card

    def _build_intelligence_alert_card(
        self,
        title: str,
        item: dict,
    ) -> dict:
        """Build card for high-relevance intelligence alert.

        Args:
            title: Alert title
            item: Intelligence item

        Returns:
            Card message JSON
        """
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🎯 {title}"
                },
                "template": "red"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**[{item.get('category', 'N/A').upper()}]** {item.get('title', 'Untitled')}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"相关度: {'🔥' * int(item.get('relevance_score', 0) * 5)} ({item.get('relevance_score', 0):.0%})"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**摘要**\n{item.get('summary', 'N/A')[:200]}..."
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**关联分析**\n{item.get('relevance_reasoning', 'N/A')[:200]}"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "查看详情"
                            },
                            "type": "primary",
                            "url": item.get('url', '#')
                        }
                    ]
                }
            ]
        }

        return card

    async def send_daily_report(
        self,
        chat_id: str,
        report_data: dict,
    ) -> bool:
        """Send daily report to Feishu chat.

        Args:
            chat_id: Feishu chat ID
            report_data: Report data

        Returns:
            True if sent successfully
        """
        self._logger.info("sending_daily_report", chat_id=chat_id)

        try:
            client = await self._get_client()

            card = self._build_daily_report_card(
                title=report_data.get("title", "AI情报日报"),
                summary=report_data.get("summary", ""),
                highlights=report_data.get("highlights", []),
                stats=report_data.get("stats", {}),
            )

            # Send card message
            await self._send_card_message(chat_id, card)

            self._logger.info("daily_report_sent", chat_id=chat_id)
            return True

        except Exception as e:
            self._logger.error("daily_report_failed", chat_id=chat_id, error=str(e))
            return False

    async def send_intelligence_alert(
        self,
        chat_id: str,
        item: dict,
    ) -> bool:
        """Send high-relevance intelligence alert.

        Args:
            chat_id: Feishu chat ID
            item: Intelligence item

        Returns:
            True if sent successfully
        """
        self._logger.info(
            "sending_intelligence_alert",
            chat_id=chat_id,
            item_id=item.get("id"),
        )

        try:
            card = self._build_intelligence_alert_card(
                title="高相关度AI情报",
                item=item,
            )

            await self._send_card_message(chat_id, card)

            self._logger.info("alert_sent", chat_id=chat_id, item_id=item.get("id"))
            return True

        except Exception as e:
            self._logger.error("alert_failed", chat_id=chat_id, error=str(e))
            return False

    async def _send_card_message(
        self,
        chat_id: str,
        card: dict,
    ) -> None:
        """Send card message via Feishu API.

        Args:
            chat_id: Target chat ID
            card: Card message content
        """
        client = await self._get_client()

        # Use im/v1/messages API to send card
        url = f"/im/v1/messages"

        payload = {
            "receive_id": chat_id,
            "content": json.dumps(card),
            "msg_type": "interactive",
        }

        await client._make_request("POST", url, json=payload)

    async def close(self) -> None:
        """Close service resources."""
        if self._client:
            await self._client.close()
            self._client = None

    async def send_weekly_report(
        self,
        chat_id: str,
        report: WeeklyReport,
    ) -> bool:
        """Send weekly report to Feishu chat.

        Args:
            chat_id: Feishu chat ID
            report: Weekly report instance

        Returns:
            True if sent successfully
        """
        self._logger.info(
            "sending_weekly_report",
            chat_id=chat_id,
            period=f"{report.period_start} to {report.period_end}",
        )

        try:
            client = await self._get_client()

            card = self._build_weekly_report_card(report)

            await self._send_card_message(chat_id, card)

            self._logger.info(
                "weekly_report_sent",
                chat_id=chat_id,
                period=report.period_start,
            )
            return True

        except Exception as e:
            self._logger.error(
                "weekly_report_failed",
                chat_id=chat_id,
                error=str(e),
            )
            return False

    def _build_weekly_report_card(self, report: WeeklyReport) -> dict:
        """Build card for weekly report.

        Args:
            report: Weekly report data

        Returns:
            Card message JSON
        """
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 研发管理周报 - {report.period_start} 至 {report.period_end}",
                },
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**总体健康度**: {report.overall_health:.0%}",
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**关键指标**",
                    },
                },
            ],
        }

        # Add key metrics
        metrics_text = ""
        for key, value in report.key_metrics.items():
            metrics_text += f"- {key}: {value}\n"
        card["elements"].append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": metrics_text},
            }
        )

        # Add summary statistics
        card["elements"].append({"tag": "hr"})
        card["elements"].append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**本周概览**",
                },
            }
        )
        card["elements"].append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"- ✅ 完成任务: {report.tasks_completed} 个\n"
                        f"- 📋 进行中任务: {report.tasks_in_progress} 个\n"
                        f"- 🎯 项目正常: {report.projects_on_track} 个\n"
                        f"- ⚠️ 项目风险: {report.projects_at_risk} 个"
                    ),
                },
            }
        )

        # Add achievements
        if report.achievements:
            card["elements"].append({"tag": "hr"})
            card["elements"].append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**🎉 本周成就**",
                    },
                }
            )
            achievements_text = ""
            for item in report.achievements:
                achievements_text += f"- {item}\n"
            card["elements"].append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": achievements_text,
                    },
                }
            )

        # Add challenges
        if report.challenges:
            card["elements"].append({"tag": "hr"})
            card["elements"].append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**⚠️ 面临挑战**",
                    },
                }
            )
            challenges_text = ""
            for item in report.challenges:
                challenges_text += f"- {item}\n"
            card["elements"].append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": challenges_text,
                    },
                }
            )

        # Add recommendations
        if report.recommendations:
            card["elements"].append({"tag": "hr"})
            card["elements"].append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**💡 建议**",
                    },
                }
            )
            recommendations_text = ""
            for item in report.recommendations:
                recommendations_text += f"- {item}\n"
            card["elements"].append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": recommendations_text,
                    },
                }
            )

        # Add highlights
        if report.highlights:
            card["elements"].append({"tag": "hr"})
            card["elements"].append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**🌟 AI情报亮点**",
                    },
                }
            )
            highlights_text = ""
            for highlight in report.highlights[:3]:
                title = highlight.get("title", "")
                desc = highlight.get("description", "")
                highlights_text += f"- **{title}**: {desc}\n"
            card["elements"].append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": highlights_text,
                    },
                }
            )

        # Add footer
        card["elements"].append({"tag": "hr"})
        card["elements"].append(
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    }
                ],
            }
        )

        return card

    async def send_ai_intelligence_summary(
        self,
        chat_id: str,
        agent_name: str,
        summary: str,
        insights: List[dict],
    ) -> bool:
        """Send AI intelligence summary from agents.

        Args:
            chat_id: Feishu chat ID
            agent_name: Name of the agent (e.g., "仕杰", "运明", "逍虓")
            summary: AI-generated summary
            insights: List of insights

        Returns:
            True if sent successfully
        """
        self._logger.info(
            "sending_ai_intelligence_summary",
            chat_id=chat_id,
            agent=agent_name,
        )

        try:
            client = await self._get_client()

            card = {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"🤖 {agent_name} 的智能洞察",
                    },
                    "template": "green",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**AI生成摘要**",
                        },
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": summary,
                        },
                    },
                ],
            }

            if insights:
                card["elements"].append({"tag": "hr"})
                card["elements"].append(
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**关键洞察**",
                        },
                    }
                )

                for insight in insights[:3]:
                    title = insight.get("title", "N/A")
                    summary_text = insight.get("summary", "")
                    card["elements"].append(
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"- **{title}**: {summary_text}",
                            },
                        }
                    )

            card["elements"].append({"tag": "hr"})
            card["elements"].append(
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        }
                    ],
                }
            )

            await self._send_card_message(chat_id, card)

            self._logger.info(
                "ai_intelligence_summary_sent",
                chat_id=chat_id,
                agent=agent_name,
            )
            return True

        except Exception as e:
            self._logger.error(
                "ai_intelligence_summary_failed",
                chat_id=chat_id,
                agent=agent_name,
                error=str(e),
            )
            return False


import json
from src.services.report.report_generation import WeeklyReport

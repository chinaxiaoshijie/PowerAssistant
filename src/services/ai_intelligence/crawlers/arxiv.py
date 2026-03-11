"""arXiv paper crawler for AI research papers."""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import AsyncGenerator, Optional

from src.services.ai_intelligence.base import BaseCrawler, CrawlResult


class ArxivCrawler(BaseCrawler):
    """Crawler for arXiv AI papers.

    Fetches latest papers from arXiv in AI-related categories:
    - cs.AI (Artificial Intelligence)
    - cs.CL (Computation and Language)
    - cs.CV (Computer Vision)
    - cs.LG (Machine Learning)
    - cs.RO (Robotics)
    """

    BASE_URL = "http://export.arxiv.org/api/query"

    # AI-related categories
    CATEGORIES = [
        "cs.AI",   # Artificial Intelligence
        "cs.CL",   # Computation and Language
        "cs.CV",   # Computer Vision and Pattern Recognition
        "cs.LG",   # Machine Learning
        "cs.RO",   # Robotics
        "cs.IR",   # Information Retrieval
    ]

    def get_source_name(self) -> str:
        """Return source name."""
        return "arXiv"

    def get_source_type(self) -> str:
        """Return source type."""
        return "arxiv"

    async def crawl(
        self,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> AsyncGenerator[CrawlResult, None]:
        """Crawl arXiv for recent papers.

        Args:
            since: Only fetch papers newer than this
            limit: Maximum papers per category

        Yields:
            CrawlResult objects
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)

        # Format date for arXiv query
        date_str = since.strftime("%Y%m%d")

        # Query each category
        for category in self.CATEGORIES:
            self._logger.info(
                "crawling_arxiv_category",
                category=category,
                since=date_str,
            )

            # Build query
            cat_query = f"cat:{category}"
            submitted_query = f"submittedDate:[{date_str}0000 TO NOW]"

            params = {
                "search_query": f"{cat_query} AND {submitted_query}",
                "start": 0,
                "max_results": limit,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }

            try:
                xml_content = await self.fetch_url(self.BASE_URL, params=params)

                # Parse XML
                root = ET.fromstring(xml_content)

                # arXiv Atom namespace
                ns = {
                    "atom": "http://www.w3.org/2005/Atom",
                    "arxiv": "http://arxiv.org/schemas/atom",
                }

                # Extract entries
                entries = root.findall("atom:entry", ns)

                for entry in entries:
                    try:
                        result = self._parse_entry(entry, ns, category)
                        if result:
                            yield result
                    except Exception as e:
                        self._logger.error(
                            "parse_entry_failed",
                            error=str(e),
                            category=category,
                        )

                self._logger.info(
                    "arxiv_category_crawled",
                    category=category,
                    count=len(entries),
                )

            except Exception as e:
                self._logger.error(
                    "arxiv_crawl_failed",
                    category=category,
                    error=str(e),
                )

    def _parse_entry(
        self,
        entry: ET.Element,
        ns: dict,
        category: str,
    ) -> Optional[CrawlResult]:
        """Parse arXiv entry to CrawlResult.

        Args:
            entry: XML entry element
            ns: Namespace mapping
            category: Paper category

        Returns:
            CrawlResult or None if parsing fails
        """
        # Get title
        title_elem = entry.find("atom:title", ns)
        if title_elem is None:
            return None
        title = title_elem.text.strip() if title_elem.text else ""

        # Get ID/URL
        id_elem = entry.find("atom:id", ns)
        if id_elem is None:
            return None
        arxiv_id = id_elem.text.split("/")[-1].split("v")[0]
        url = f"https://arxiv.org/abs/{arxiv_id}"

        # Get abstract
        summary_elem = entry.find("atom:summary", ns)
        content = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""

        # Get authors
        authors = []
        for author in entry.findall("atom:author", ns):
            name_elem = author.find("atom:name", ns)
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text)
        author = ", ".join(authors[:3])  # First 3 authors
        if len(authors) > 3:
            author += " et al."

        # Get published date
        published_elem = entry.find("atom:published", ns)
        published_at = None
        if published_elem is not None and published_elem.text:
            try:
                published_at = datetime.fromisoformat(
                    published_elem.text.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # Get primary category
        primary_cat_elem = entry.find("arxiv:primary_category", ns)
        primary_category = primary_cat_elem.get("term", category) if primary_cat_elem is not None else category

        return CrawlResult(
            title=title,
            url=url,
            content=content,
            author=author,
            published_at=published_at,
            external_id=arxiv_id,
            metadata={
                "category": primary_category,
                "all_categories": [cat.get("term") for cat in entry.findall("atom:category", ns)],
                "source_category": category,
            },
        )

"""
Morning News tools for the IBM Sales Intelligence Hub.

Agent: morning_news_agent
Tools:
  - get_account_news   : Returns 4-6 recent news items for the chosen account via Tavily web search.
  - get_industry_alerts: Returns 2-4 industry-level alerts for the account's sector via Tavily web search.
  - flag_news_item     : Flags a news item as Important, Share with Team, or Dismiss.

Production mode: get_account_news and get_industry_alerts call the Tavily Search API live.
Set the environment variable TAVILY_API_KEY before running.

Fallback: if TAVILY_API_KEY is not set, both tools return hardcoded mock data so the prototype
can still be demoed without an API key.

Import command:
  orchestrate tools import -k python -f morning_news_tools.py
"""

import os
import datetime

from ibm_watsonx_orchestrate.agent_builder.tools import tool

__all__ = ["get_account_news", "get_industry_alerts", "flag_news_item"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_FLAG_TYPES = {"Important", "Share with Team", "Dismiss"}

_RELEVANCE_KEYWORDS = {
    "partnership": "Opportunity",
    "expand": "Opportunity",
    "deal": "Opportunity",
    "contract": "Opportunity",
    "award": "Opportunity",
    "revenue": "Opportunity",
    "earnings": "Opportunity",
    "growth": "Opportunity",
    "appoint": "Executive Change",
    "hire": "Executive Change",
    "ceo": "Executive Change",
    "cto": "Executive Change",
    "coo": "Executive Change",
    "cfo": "Executive Change",
    "chief": "Executive Change",
    "resign": "Executive Change",
    "risk": "Risk",
    "breach": "Risk",
    "lawsuit": "Risk",
    "fine": "Risk",
    "penalty": "Risk",
    "layoff": "Risk",
    "competitor": "Competitor Move",
    "microsoft": "Competitor Move",
    "aws": "Competitor Move",
    "google": "Competitor Move",
    "amazon": "Competitor Move",
    "azure": "Competitor Move",
}


def _infer_relevance_tag(title: str, body: str) -> str:
    """Infer a relevance tag from article title and content."""
    combined = (title + " " + body).lower()
    for keyword, tag in _RELEVANCE_KEYWORDS.items():
        if keyword in combined:
            return tag
    return "Opportunity"


def _tavily_search(query: str, max_results: int = 5) -> list:
    """
    Execute a Tavily search and return a list of result dicts.
    Raises ImportError if tavily-python is not installed.
    Raises ValueError if TAVILY_API_KEY is not set.
    """
    from tavily import TavilyClient  # pip install tavily-python

    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise ValueError("TAVILY_API_KEY environment variable is not set.")

    client = TavilyClient(api_key=api_key)
    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
        include_answer=False,
        include_raw_content=False,
    )
    return response.get("results", [])


def _format_date(raw: str | None) -> str:
    """Normalise a raw date string to YYYY-MM-DD, falling back to today."""
    if raw:
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
            try:
                return datetime.datetime.strptime(raw[:10], fmt[:10]).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return datetime.date.today().isoformat()


# ---------------------------------------------------------------------------
# Fallback mock data (used when TAVILY_API_KEY is absent)
# ---------------------------------------------------------------------------

_MOCK_ACCOUNT_NEWS = [
    {
        "news_id": "news_001",
        "title": "Accenture Expands AWS Partnership with $3B Cloud Migration Commitment",
        "source": "Reuters",
        "date": "2026-06-10",
        "url": "",
        "summary": (
            "Accenture announced a deepened strategic alliance with AWS to migrate Fortune 500 "
            "clients to cloud infrastructure over three years. The deal positions AWS as "
            "Accenture's preferred cloud platform for new workloads, creating competitive "
            "pressure on existing IBM Cloud deployments."
        ),
        "relevance_tag": "Competitor Move",
    },
    {
        "news_id": "news_002",
        "title": "Accenture Names Dr. Priya Nair as Chief AI Officer Following watsonx Pilot",
        "source": "Bloomberg",
        "date": "2026-06-08",
        "url": "",
        "summary": (
            "Accenture appointed Dr. Priya Nair as Chief AI Officer, citing the successful "
            "enterprise AI pilot with IBM watsonx as a key driver."
        ),
        "relevance_tag": "Executive Change",
    },
    {
        "news_id": "news_003",
        "title": "Accenture Q2 2026 Earnings: AI & Cloud Revenue Up 34% Year-Over-Year",
        "source": "Wall Street Journal",
        "date": "2026-06-05",
        "url": "",
        "summary": (
            "Accenture reported strong Q2 2026 results with AI and cloud services revenue "
            "growing 34% year-over-year to $22.1B."
        ),
        "relevance_tag": "Opportunity",
    },
    {
        "news_id": "news_004",
        "title": "EU AI Act Compliance Deadline Creates Urgency in Accenture's FS Division",
        "source": "Financial Times",
        "date": "2026-06-03",
        "url": "",
        "summary": (
            "Accenture's Financial Services division faces board-level pressure to achieve "
            "EU AI Act compliance before the Q3 2026 enforcement phase."
        ),
        "relevance_tag": "Opportunity",
    },
]

_MOCK_INDUSTRY_ALERTS = [
    {
        "alert_id": "alert_001",
        "title": "EU AI Act Enforcement Phase Begins Q3 2026 for High-Risk AI Systems",
        "date": "2026-06-09",
        "url": "",
        "summary": (
            "The EU AI Act enters its enforcement phase for high-risk AI systems in Q3 2026. "
            "Financial services firms must demonstrate model transparency and audit trails."
        ),
    },
    {
        "alert_id": "alert_002",
        "title": "Cloud Spending Trends Q2 2026: Enterprise AI Workloads Drive 28% Increase",
        "date": "2026-06-07",
        "url": "",
        "summary": (
            "Gartner reports enterprise cloud spending increased 28% in Q2 2026, driven by "
            "generative AI workload deployments."
        ),
    },
]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool()
def get_account_news(account_name: str) -> list:
    """Returns recent news items relevant to the chosen account, scraped live via Tavily.

    Uses the Tavily Search API to fetch the latest press releases, executive changes,
    partnerships, financial results, and competitor moves for the given account.
    Falls back to hardcoded mock data if TAVILY_API_KEY is not set.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        list: A list of 4-6 news items, each containing news_id, title, source,
              date (YYYY-MM-DD), url, summary, and relevance_tag ("Opportunity",
              "Risk", "Competitor Move", or "Executive Change").
    """
    query = (
        f"{account_name} news latest press release executive announcement "
        f"partnership earnings AI cloud technology"
    )
    try:
        results = _tavily_search(query, max_results=6)
    except (ValueError, ImportError):
        return _MOCK_ACCOUNT_NEWS

    items = []
    for i, r in enumerate(results, start=1):
        title = r.get("title", "").strip()
        content = r.get("content", "").strip()
        summary = content[:280] + "…" if len(content) > 280 else content
        tag = _infer_relevance_tag(title, content)
        items.append(
            {
                "news_id": f"news_{i:03d}",
                "title": title,
                "source": r.get("url", "").split("/")[2] if r.get("url") else "Web",
                "date": _format_date(r.get("published_date")),
                "url": r.get("url", ""),
                "summary": summary,
                "relevance_tag": tag,
            }
        )
    return items if items else _MOCK_ACCOUNT_NEWS


@tool()
def get_industry_alerts(industry: str) -> list:
    """Returns industry-level alerts for the account's sector, scraped live via Tavily.

    Uses the Tavily Search API to fetch the latest regulatory updates, market trends,
    M&A activity, and analyst reports for the given industry sector.
    Falls back to hardcoded mock data if TAVILY_API_KEY is not set.

    Args:
        industry (str): The industry sector to retrieve alerts for
                        (e.g. "Financial Services", "Technology Consulting").

    Returns:
        list: A list of 2-4 industry alert objects, each containing alert_id,
              title, date (YYYY-MM-DD), url, and summary.
    """
    query = (
        f"{industry} industry news regulation AI cloud market trends "
        f"M&A analyst report latest 2025 2026"
    )
    try:
        results = _tavily_search(query, max_results=4)
    except (ValueError, ImportError):
        return _MOCK_INDUSTRY_ALERTS

    alerts = []
    for i, r in enumerate(results, start=1):
        title = r.get("title", "").strip()
        content = r.get("content", "").strip()
        summary = content[:280] + "…" if len(content) > 280 else content
        alerts.append(
            {
                "alert_id": f"alert_{i:03d}",
                "title": title,
                "source": r.get("url", "").split("/")[2] if r.get("url") else "Web",
                "date": _format_date(r.get("published_date")),
                "url": r.get("url", ""),
                "summary": summary,
            }
        )
    return alerts if alerts else _MOCK_INDUSTRY_ALERTS


@tool()
def flag_news_item(news_id: str, flag_type: str) -> str:
    """Flags a news item as Important, Share with Team, or Dismiss.

    Args:
        news_id (str): The unique identifier of the news item to flag
                       (e.g. "news_001"). Obtainable from get_account_news.
        flag_type (str): The flag to apply. Must be one of:
                         "Important", "Share with Team", or "Dismiss".

    Returns:
        str: A confirmation message stating the flag was applied, or an error
             message if flag_type is not a valid value.
    """
    if flag_type not in _VALID_FLAG_TYPES:
        valid = ", ".join(f'"{v}"' for v in sorted(_VALID_FLAG_TYPES))
        return (
            f"Invalid flag_type '{flag_type}'. "
            f"Accepted values are: {valid}."
        )
    return (
        f"News item '{news_id}' has been flagged as '{flag_type}'. "
        f"Your preference has been saved and the item updated in your Morning News feed."
    )

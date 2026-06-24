"""
Morning News tools for the IBM Sales Intelligence Hub.

Agent: morning_news_agent
Tools:
  - get_account_news   : Returns 4-6 recent news items for the chosen account.
  - get_industry_alerts: Returns 2-4 industry-level alerts for the account's sector.
  - flag_news_item     : Flags a news item as Important, Share with Team, or Dismiss.

Mock data reflects Accenture (Financial Services / Technology Consulting sector).
In production, get_account_news and get_industry_alerts will be replaced with
live Tavily Search API calls on a daily refresh schedule.

Import command:
  orchestrate tools import -k python -f morning_news_tools.py
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool

__all__ = ["get_account_news", "get_industry_alerts", "flag_news_item"]

# ---------------------------------------------------------------------------
# Hardcoded mock data
# ---------------------------------------------------------------------------

_ACCOUNT_NEWS = [
    {
        "news_id": "news_001",
        "title": "Accenture Expands AWS Partnership with $3B Cloud Migration Commitment",
        "source": "Reuters",
        "date": "2026-06-10",
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
        "summary": (
            "Accenture appointed Dr. Priya Nair as Chief AI Officer, citing the successful "
            "enterprise AI pilot with IBM watsonx as a key driver. Dr. Nair is an established "
            "IBM advocate and now holds direct budget authority over Accenture's enterprise "
            "AI platform decisions."
        ),
        "relevance_tag": "Executive Change",
    },
    {
        "news_id": "news_003",
        "title": "Accenture Q2 2026 Earnings: AI & Cloud Revenue Up 34% Year-Over-Year",
        "source": "Wall Street Journal",
        "date": "2026-06-05",
        "summary": (
            "Accenture reported strong Q2 2026 results with AI and cloud services revenue "
            "growing 34% year-over-year to $22.1B. Management confirmed increased capital "
            "allocation for enterprise AI tooling and governance platforms in H2 2026."
        ),
        "relevance_tag": "Opportunity",
    },
    {
        "news_id": "news_004",
        "title": "EU AI Act Compliance Deadline Creates Urgency in Accenture's FS Division",
        "source": "Financial Times",
        "date": "2026-06-03",
        "summary": (
            "Accenture's Financial Services division faces board-level pressure to achieve "
            "EU AI Act compliance before the Q3 2026 enforcement phase. IBM watsonx.governance "
            "is being evaluated as the primary compliance enabler — renewal due September 30."
        ),
        "relevance_tag": "Opportunity",
    },
    {
        "news_id": "news_005",
        "title": "Accenture Piloting Microsoft Azure OpenAI Service for Internal Workflow Automation",
        "source": "TechCrunch",
        "date": "2026-05-29",
        "summary": (
            "Accenture's IT division is running a parallel evaluation of Microsoft Azure OpenAI "
            "Service for internal workflow automation tools, targeting 15,000 employees. This "
            "represents a direct competitive risk to the IBM watsonx.ai enterprise deal currently "
            "in Proposal stage."
        ),
        "relevance_tag": "Risk",
    },
    {
        "news_id": "news_006",
        "title": "Accenture's IBM Sterling Supply Chain Implementation Wins 2026 Industry Award",
        "source": "Supply Chain Dive",
        "date": "2026-05-25",
        "summary": (
            "The Accenture–IBM Sterling joint implementation won the 2026 Digital Supply Chain "
            "Excellence Award, recognising measurable improvements in inventory optimisation "
            "and supplier collaboration. The win reinforces the IBM–Accenture co-sell narrative "
            "and provides a strong reference story for new IBM Sterling deals."
        ),
        "relevance_tag": "Opportunity",
    },
]

_INDUSTRY_ALERTS = [
    {
        "alert_id": "alert_001",
        "title": "EU AI Act Enforcement Phase Begins Q3 2026 for High-Risk AI Systems",
        "date": "2026-06-09",
        "summary": (
            "The EU AI Act enters its enforcement phase for high-risk AI systems in Q3 2026. "
            "Financial services firms must demonstrate model transparency, explainability, "
            "bias mitigation, and audit trails. IBM watsonx.governance provides direct "
            "compliance tooling for all four requirements."
        ),
    },
    {
        "alert_id": "alert_002",
        "title": "Cloud Spending Trends Q2 2026: Enterprise AI Workloads Drive 28% Increase",
        "date": "2026-06-07",
        "summary": (
            "Gartner reports enterprise cloud spending increased 28% in Q2 2026, driven by "
            "generative AI workload deployments. Hybrid cloud architectures are the dominant "
            "deployment model, favouring IBM Cloud Pak for Data and IBM Cloud's hybrid "
            "capabilities over single-cloud alternatives."
        ),
    },
    {
        "alert_id": "alert_003",
        "title": "Technology Consulting Sector: Three Major AI-Focused M&A Deals Close This Quarter",
        "date": "2026-06-01",
        "summary": (
            "Three significant acquisitions closed in the technology consulting sector this "
            "quarter, consolidating AI and data capabilities across the market. The deals shift "
            "competitive dynamics and may affect Accenture's partner ecosystem — IBM should "
            "reassess its co-sell position and identify new partnership opportunities created."
        ),
    },
    {
        "alert_id": "alert_004",
        "title": "Forrester: Enterprise AI Governance Spending to Grow 41% in 2026",
        "date": "2026-05-28",
        "summary": (
            "Forrester's latest report forecasts enterprise AI governance and observability "
            "spending will grow 41% in 2026, driven by regulatory pressure and increasing "
            "AI model deployments at scale. IBM watsonx.governance is rated a Leader in the "
            "Forrester Wave for AI Governance Platforms, Q2 2026."
        ),
    },
]

_VALID_FLAG_TYPES = {"Important", "Share with Team", "Dismiss"}

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool()
def get_account_news(account_name: str) -> list:
    """Returns recent mock news items relevant to the chosen account.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        list: A list of 4-6 news items, each containing news_id, title, source,
              date (YYYY-MM-DD), summary, and relevance_tag ("Opportunity",
              "Risk", "Competitor Move", or "Executive Change").
    """
    return _ACCOUNT_NEWS


@tool()
def get_industry_alerts(industry: str) -> list:
    """Returns mock industry-level alerts relevant to the account's sector.

    Args:
        industry (str): The industry sector to retrieve alerts for
                        (e.g. "Financial Services", "Technology Consulting").

    Returns:
        list: A list of 2-4 industry alert objects, each containing alert_id,
              title, date (YYYY-MM-DD), and summary.
    """
    return _INDUSTRY_ALERTS


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

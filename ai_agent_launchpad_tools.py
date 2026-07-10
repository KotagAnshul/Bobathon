"""
AI Agent Launchpad tools for the IBM Sales Intelligence Hub.

Agent: ai_agent_launchpad_agent
Tools:
  - run_lead_identification  : Identifies and scores 3-5 leads within the account.
  - run_client_outreach_draft: Generates a personalised outreach email draft.
  - run_client_search        : Returns D&B firmographic and technographic data.
  - get_crm_snapshot         : Returns a Salesforce CRM pipeline snapshot.
  - update_crm_record        : Updates a field on a Salesforce CRM record.
  - get_enablement_content   : Returns Seismic content recommendations for a topic.
  - run_sales_research       : Returns a consolidated D&B + news + IBM internal brief.

Mock data reflects Accenture (Financial Services / Technology Consulting sector).
In production, tools will connect to Salesforce CRM API, Seismic API, Dun & Bradstreet
Direct+ API, and the IBM Sales Research AI Agent.

Import command:
  orchestrate tools import -k python -f ai_agent_launchpad_tools.py
"""

import datetime

from ibm_watsonx_orchestrate.agent_builder.tools import tool

__all__ = [
    "run_lead_identification",
    "run_client_outreach_draft",
    "run_client_search",
    "get_crm_snapshot",
    "update_crm_record",
    "get_enablement_content",
    "run_sales_research",
]

# ---------------------------------------------------------------------------
# Hardcoded mock data
# ---------------------------------------------------------------------------

_SEISMIC_CATALOGUE = {
    "watsonx": [
        {
            "content_id": "SEI-WX-001",
            "title": "IBM watsonx — Enterprise AI Platform Value Proposition 2026",
            "content_type": "Sales Presentation",
            "relevance_score": 98,
            "last_updated": "2026-06-01",
            "seismic_url": "https://ibm.seismic.com/content/sei-wx-001",
        },
        {
            "content_id": "SEI-WX-002",
            "title": "IBM watsonx vs Microsoft Azure OpenAI — Competitive Battlecard",
            "content_type": "Battlecard",
            "relevance_score": 95,
            "last_updated": "2026-06-01",
            "seismic_url": "https://ibm.seismic.com/content/sei-wx-002",
        },
        {
            "content_id": "SEI-WX-003",
            "title": "Accenture × IBM watsonx Financial Services AI Success Story",
            "content_type": "Case Study",
            "relevance_score": 91,
            "last_updated": "2026-05-10",
            "seismic_url": "https://ibm.seismic.com/content/sei-wx-003",
        },
    ],
    "governance": [
        {
            "content_id": "SEI-GOV-001",
            "title": "IBM watsonx.governance — EU AI Act Compliance Solution Brief",
            "content_type": "Solution Brief",
            "relevance_score": 99,
            "last_updated": "2026-05-20",
            "seismic_url": "https://ibm.seismic.com/content/sei-gov-001",
        },
        {
            "content_id": "SEI-GOV-002",
            "title": "AI Governance ROI Calculator — Financial Services Template",
            "content_type": "Interactive Tool",
            "relevance_score": 93,
            "last_updated": "2026-04-15",
            "seismic_url": "https://ibm.seismic.com/content/sei-gov-002",
        },
        {
            "content_id": "SEI-GOV-003",
            "title": "IBM watsonx.governance vs Competitors — Forrester Wave Summary 2026",
            "content_type": "Analyst Report",
            "relevance_score": 90,
            "last_updated": "2026-05-30",
            "seismic_url": "https://ibm.seismic.com/content/sei-gov-003",
        },
    ],
    "cloud pak": [
        {
            "content_id": "SEI-CPD-001",
            "title": "IBM Cloud Pak for Data — Enterprise Data Fabric Value Proposition 2026",
            "content_type": "Sales Presentation",
            "relevance_score": 97,
            "last_updated": "2026-05-15",
            "seismic_url": "https://ibm.seismic.com/content/sei-cpd-001",
        },
        {
            "content_id": "SEI-CPD-002",
            "title": "IBM Cloud Pak for Data vs Google BigQuery ML — Competitive Battlecard",
            "content_type": "Battlecard",
            "relevance_score": 92,
            "last_updated": "2026-06-01",
            "seismic_url": "https://ibm.seismic.com/content/sei-cpd-002",
        },
        {
            "content_id": "SEI-CPD-003",
            "title": "Hybrid Cloud Data Modernisation with IBM Cloud Pak for Data",
            "content_type": "White Paper",
            "relevance_score": 87,
            "last_updated": "2026-04-20",
            "seismic_url": "https://ibm.seismic.com/content/sei-cpd-003",
        },
    ],
    "sterling": [
        {
            "content_id": "SEI-STR-001",
            "title": "IBM Sterling Supply Chain Suite — 2026 Enterprise Overview Deck",
            "content_type": "Sales Presentation",
            "relevance_score": 96,
            "last_updated": "2026-05-01",
            "seismic_url": "https://ibm.seismic.com/content/sei-str-001",
        },
        {
            "content_id": "SEI-STR-002",
            "title": "IBM Sterling vs AWS Supply Chain — Competitive Battlecard",
            "content_type": "Battlecard",
            "relevance_score": 94,
            "last_updated": "2026-06-05",
            "seismic_url": "https://ibm.seismic.com/content/sei-str-002",
        },
        {
            "content_id": "SEI-STR-003",
            "title": "Accenture × IBM Sterling — 2026 Digital Supply Chain Award Case Study",
            "content_type": "Case Study",
            "relevance_score": 97,
            "last_updated": "2026-06-03",
            "seismic_url": "https://ibm.seismic.com/content/sei-str-003",
        },
    ],
}

_SEISMIC_DEFAULT = [
    {
        "content_id": "SEI-GEN-001",
        "title": "IBM Sales Intelligence Hub — Account Overview Presentation Template",
        "content_type": "Sales Presentation",
        "relevance_score": 85,
        "last_updated": "2026-05-15",
        "seismic_url": "https://ibm.seismic.com/content/sei-gen-001",
    },
    {
        "content_id": "SEI-GEN-002",
        "title": "IBM Enterprise AI — Competitive Positioning Guide 2026",
        "content_type": "Battlecard",
        "relevance_score": 82,
        "last_updated": "2026-06-01",
        "seismic_url": "https://ibm.seismic.com/content/sei-gen-002",
    },
    {
        "content_id": "SEI-GEN-003",
        "title": "IBM & Accenture Strategic Partnership — Joint Value Narrative",
        "content_type": "Partner Brief",
        "relevance_score": 79,
        "last_updated": "2026-04-20",
        "seismic_url": "https://ibm.seismic.com/content/sei-gen-003",
    },
]

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool()
def run_lead_identification(account_name: str) -> list:
    """Identifies and scores the top leads within the chosen account.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        list: A list of 3-5 lead objects sorted by descending lead_score, each
              containing contact_name, title, department, lead_score (integer 1-100),
              and rationale (string explaining why the contact is a high-priority lead).
    """
    return [
        {
            "contact_name": "Dr. Priya Nair",
            "title": "Chief AI Officer",
            "department": "Technology & Innovation",
            "lead_score": 96,
            "rationale": (
                "New CAO appointment driven by the IBM watsonx pilot success. Direct budget "
                "authority over Accenture's enterprise AI platform decisions. Confirmed IBM "
                "advocate — highest-priority engagement target."
            ),
        },
        {
            "contact_name": "Mark Henderson",
            "title": "VP Technology, Financial Services",
            "department": "Financial Services Division",
            "lead_score": 84,
            "rationale": (
                "Primary budget holder for watsonx.governance in the FS division. "
                "Under board-level pressure to achieve EU AI Act compliance by Q3 2026. "
                "Renewal conversation must be led here."
            ),
        },
        {
            "contact_name": "Lisa Tran",
            "title": "Procurement Lead",
            "department": "Procurement",
            "lead_score": 72,
            "rationale": (
                "Key procurement gatekeeper for all deals above $1M. Her absence from "
                "the Azure OpenAI loss is a lesson — she must be engaged before the "
                "watsonx expansion proposal is submitted."
            ),
        },
        {
            "contact_name": "David Osei",
            "title": "Chief Financial Officer",
            "department": "Finance",
            "lead_score": 68,
            "rationale": (
                "CFO controls final budget sign-off for all deals above $5M. No IBM "
                "touchpoint since November 2025. An executive-level IBM outreach is "
                "needed before tabling the $8.4M watsonx expansion proposal."
            ),
        },
        {
            "contact_name": "Sophie Andersen",
            "title": "Head of Data & Analytics",
            "department": "Enterprise Technology",
            "lead_score": 61,
            "rationale": (
                "Internal sponsor of the IBM Cloud Pak for Data deployment. Usage at 88% "
                "gives her a data-backed justification to request capacity expansion — "
                "the upsell conversation should be initiated through her."
            ),
        },
    ]


@tool()
def run_client_outreach_draft(contact_name: str, context: str) -> dict:
    """Generates a personalised outreach email draft for the specified client contact.

    Args:
        contact_name (str): The full name of the client contact to address
                            (e.g. "Dr. Priya Nair").
        context (str): The focus or topic of the email, such as a product name,
                       recent news event, or specific business situation
                       (e.g. "watsonx.governance and EU AI Act compliance deadline").

    Returns:
        dict: An email draft containing to, from_address, subject, body (formatted
              string with line breaks), recommended_send_time, and powered_by.
    """
    first_name = contact_name.split()[-1] if contact_name else contact_name
    return {
        "to": f"{contact_name} <{contact_name.lower().replace(' ', '.').replace('dr.', '').strip('.')}"
              f"@accenture.com>",
        "from_address": "Sarah Mitchell <sarah.mitchell@ibm.com>",
        "subject": f"IBM & Accenture — A Timely Opportunity on {context}",
        "body": (
            f"Dear {contact_name},\n\n"
            f"I hope this note finds you well. I'm reaching out directly because recent "
            f"developments around {context} create a compelling and time-sensitive opportunity "
            f"for Accenture that I'd like to walk you through personally.\n\n"
            f"IBM has just released a set of capabilities specifically designed for {context} "
            f"at enterprise scale — and given Accenture's leadership position in Financial "
            f"Services AI and the Q3 2026 EU AI Act enforcement timeline, I believe the timing "
            f"could not be more relevant.\n\n"
            f"Several of our joint clients are already using these capabilities to meet "
            f"regulatory deadlines ahead of schedule — I'd be glad to share the details and "
            f"a relevant success story from a comparable account.\n\n"
            f"Would you have 30 minutes available the week of June 23rd for a focused "
            f"conversation? I'll keep it crisp and practical.\n\n"
            f"Warm regards,\n"
            f"Sarah Mitchell\n"
            f"Global Account Executive, IBM\n"
            f"sarah.mitchell@ibm.com | +1 (212) 555-0182\n"
            f"IBM Sales Intelligence Hub | Accenture Account Team"
        ),
        "recommended_send_time": "Tuesday or Wednesday, 9–11 AM recipient local time",
        "powered_by": "IBM Client Outreach AI Agent (Salesforce CRM + Seismic content)",
    }


@tool()
def run_client_search(account_name: str) -> dict:
    """Returns enriched company and contact data from a mock Dun & Bradstreet source.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        dict: D&B data containing source, account_name, duns_number, firmographics
              (dict with revenue, employees, SIC/NAICS codes, HQ, public status,
              ticker, and credit rating), technographics (dict with cloud providers,
              AI/ML platforms, CRM, ERP, collaboration tools, and supply chain platform),
              and key_contacts (list of dicts with name, title, and linkedin URL).
    """
    return {
        "source": "Dun & Bradstreet Direct+ (Mock)",
        "account_name": "Accenture",
        "duns_number": "04-976-2510",
        "firmographics": {
            "revenue_usd": "$64.9B (FY2025)",
            "employees": "774,000+",
            "industry_sic": "7374 — Computer Processing and Data Preparation",
            "naics_code": "541512 — Computer Systems Design Services",
            "hq": "1 Grand Canal Square, Grand Canal Harbour, Dublin 2, Ireland",
            "public": True,
            "ticker": "ACN (NYSE)",
            "credit_rating": "AA",
            "year_founded": 1989,
        },
        "technographics": {
            "cloud_providers": ["Microsoft Azure", "AWS", "Google Cloud Platform", "IBM Cloud"],
            "ai_ml_platforms": [
                "IBM watsonx (Enterprise)",
                "Microsoft Azure OpenAI Service (PoC)",
                "Google Vertex AI (Evaluation)",
            ],
            "crm": "Salesforce Sales Cloud (Enterprise)",
            "erp": "SAP S/4HANA",
            "collaboration": ["Microsoft Teams", "Slack"],
            "supply_chain": "IBM Sterling Supply Chain Suite (Enterprise)",
            "data_analytics": "IBM Cloud Pak for Data (Enterprise)",
        },
        "key_contacts": [
            {
                "name": "Dr. Priya Nair",
                "title": "Chief AI Officer",
                "linkedin": "https://linkedin.com/in/priyanair-accenture",
            },
            {
                "name": "David Osei",
                "title": "Chief Financial Officer",
                "linkedin": "https://linkedin.com/in/davidosei-accenture",
            },
            {
                "name": "Mark Henderson",
                "title": "VP Technology, Financial Services",
                "linkedin": "https://linkedin.com/in/markhenderson-accenture",
            },
            {
                "name": "Rachel Park",
                "title": "Head of Supply Chain",
                "linkedin": "https://linkedin.com/in/rachelpark-accenture",
            },
        ],
    }


@tool()
def get_crm_snapshot(account_name: str) -> dict:
    """Returns a mock Salesforce CRM pipeline snapshot for the chosen account.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        dict: CRM snapshot containing account_name, crm_source, open_opportunities
              (list of opportunity dicts with opp_id, name, stage, amount_usd,
              close_date, forecast_category, last_activity_date, and owner),
              total_open_pipeline_usd (string), and last_crm_sync (ISO 8601 timestamp).
    """
    return {
        "account_name": "Accenture",
        "crm_source": "Salesforce Sales Cloud (Mock)",
        "open_opportunities": [
            {
                "opp_id": "SF-OPP-20240801",
                "name": "watsonx Enterprise Expansion — Accenture FS Division",
                "stage": "Proposal",
                "amount_usd": "$8,400,000",
                "close_date": "2026-09-30",
                "forecast_category": "Best Case",
                "last_activity_date": "2026-06-04",
                "owner": "Sarah Mitchell",
            },
            {
                "opp_id": "SF-OPP-20240802",
                "name": "IBM Cloud Pak for Data — Capacity Tier Upgrade",
                "stage": "Needs Analysis",
                "amount_usd": "$1,200,000",
                "close_date": "2026-08-15",
                "forecast_category": "Pipeline",
                "last_activity_date": "2026-05-22",
                "owner": "James Okonkwo",
            },
            {
                "opp_id": "SF-OPP-20240803",
                "name": "IBM watsonx.governance Renewal + EU AI Act Upsell",
                "stage": "Value Proposition",
                "amount_usd": "$2,700,000",
                "close_date": "2026-08-31",
                "forecast_category": "Commit",
                "last_activity_date": "2026-06-11",
                "owner": "Sarah Mitchell",
            },
        ],
        "total_open_pipeline_usd": "$12,300,000",
        "last_crm_sync": "2026-06-12T08:00:00Z",
    }


@tool()
def update_crm_record(record_id: str, field: str, value: str) -> str:
    """Updates a single field on a Salesforce CRM record and confirms the change.

    Args:
        record_id (str): The Salesforce record ID to update (e.g. "SF-OPP-20240801").
                         Obtainable from get_crm_snapshot.
        field (str): The Salesforce field name to update
                     (e.g. "Stage", "Forecast_Category", "Close_Date").
        value (str): The new value to set for the specified field
                     (e.g. "Proposal", "Commit", "2026-09-30").

    Returns:
        str: Confirmation message with record ID, field name, new value, timestamp,
             and rep name confirming the Salesforce record was updated.
    """
    today = datetime.date.today().isoformat()
    return (
        f"Salesforce CRM record updated successfully.\n"
        f"Record ID  : {record_id}\n"
        f"Field      : {field}\n"
        f"New Value  : {value}\n"
        f"Updated by : Sarah Mitchell\n"
        f"Date       : {today}"
    )


@tool()
def get_enablement_content(topic: str) -> list:
    """Returns Seismic content recommendations for the given sales topic or IBM product.

    Args:
        topic (str): The sales topic or IBM product name to find enablement content for
                     (e.g. "IBM Cloud Pak for Data", "watsonx.governance",
                     "EU AI Act compliance", "IBM Sterling").

    Returns:
        list: A list of 2-3 Seismic content recommendation objects, each containing
              content_id, title, content_type, relevance_score (integer 0-100),
              last_updated (YYYY-MM-DD), and seismic_url. Sorted by descending
              relevance_score.
    """
    topic_lower = topic.lower()
    if "watsonx" in topic_lower and "governance" not in topic_lower:
        return _SEISMIC_CATALOGUE["watsonx"]
    if "governance" in topic_lower or "eu ai act" in topic_lower or "compliance" in topic_lower:
        return _SEISMIC_CATALOGUE["governance"]
    if "cloud pak" in topic_lower or "cpd" in topic_lower or "data platform" in topic_lower:
        return _SEISMIC_CATALOGUE["cloud pak"]
    if "sterling" in topic_lower or "supply chain" in topic_lower:
        return _SEISMIC_CATALOGUE["sterling"]
    return _SEISMIC_DEFAULT


@tool()
def run_sales_research(account_name: str) -> dict:
    """Returns a consolidated mock research brief for the chosen account.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        dict: Research brief containing account_name, brief_generated (today's date,
              ISO format), powered_by, executive_snapshot (string), top_signals
              (list of strings), recommended_ibm_actions (list of strings), and
              data_sources (list of strings).
    """
    return {
        "account_name": "Accenture",
        "brief_generated": datetime.date.today().isoformat(),
        "powered_by": "IBM Sales Research AI Agent (D&B Direct+ · News Signals · IBM ISC Cloud)",
        "executive_snapshot": (
            "Accenture is a $64.9B global technology consulting leader with 774,000+ employees, "
            "publicly listed on NYSE (ACN, credit: AA). The firm has made a board-level "
            "commitment to enterprise AI expansion in FY2026. IBM is one of Accenture's top 3 "
            "enterprise AI platform partners with active production deployments of IBM watsonx.ai, "
            "IBM Cloud Pak for Data, and IBM Sterling Supply Chain Suite."
        ),
        "top_signals": [
            "New Chief AI Officer Dr. Priya Nair appointed — strong IBM watsonx advocate with "
            "direct budget authority. Highest-priority executive engagement target.",
            "EU AI Act enforcement begins Q3 2026 — watsonx.governance renewal (Sept 30) is on "
            "the critical path for Accenture's FS division compliance deadline.",
            "$3B Accenture–AWS partnership announced — competitive pressure on IBM Cloud workloads "
            "and IBM Sterling. Requires proactive response in the next 30 days.",
            "Q2 2026 AI/cloud budget up 34% YoY — Accenture has capital allocated to expand "
            "enterprise AI platform investments in H2 2026.",
            "IBM Cloud Pak for Data at 88% utilisation — capacity upgrade conversation is overdue "
            "and has a clear, data-backed ROI justification.",
            "Two Cold C-suite contacts (CFO David Osei, Procurement Lead Lisa Tran) must be "
            "re-engaged before the $8.4M watsonx expansion proposal is submitted.",
        ],
        "recommended_ibm_actions": [
            "Prioritise the watsonx Enterprise Expansion proposal — $8.4M, Proposal stage, "
            "Q3 2026 close target. Submit no later than June 20.",
            "Engage Dr. Priya Nair as executive champion for AI governance immediately — "
            "schedule within 2 weeks.",
            "Escalate Sev 2 IBM Cloud Pak for Data ticket INC0042871 to show delivery quality "
            "before the expansion proposal meeting.",
            "Re-engage CFO David Osei at IBM executive level before tabling the $8.4M deal.",
            "Prepare watsonx.governance renewal + EU AI Act upsell brief — frame around the "
            "Q3 compliance deadline to create genuine urgency.",
        ],
        "data_sources": [
            "Dun & Bradstreet Direct+",
            "Reuters",
            "Bloomberg",
            "Financial Times",
            "IBM ISC Cloud APIs",
            "Salesforce CRM",
        ],
    }

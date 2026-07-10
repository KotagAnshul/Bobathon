"""
Account Intelligence tools for the IBM Sales Intelligence Hub.

Agent: account_intelligence_agent
Tools:
  - get_account_details  : Returns the account profile for the chosen account.
  - get_isc_cloud_data   : Returns IBM ISC Cloud product, license, and support data.
  - get_executive_summary: Returns a call-prep executive summary with priorities and next steps.

Mock data reflects Accenture (Financial Services / Technology Consulting sector) with
active IBM licenses for watsonx.ai, watsonx.governance, IBM Cloud Pak for Data, and
IBM Sterling Supply Chain Suite.

In production, get_isc_cloud_data will be replaced with live IBM ISC Cloud API calls
(ILMT, IBM Passport Advantage, IBM Support APIs).

Import command:
  orchestrate tools import -k python -f account_intelligence_tools.py
"""

import datetime

from ibm_watsonx_orchestrate.agent_builder.tools import tool

__all__ = ["get_account_details", "get_isc_cloud_data", "get_executive_summary"]

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool()
def get_account_details(account_name: str) -> dict:
    """Returns mock account profile data for the chosen enterprise account.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        dict: Account profile containing account_name, company_overview, industry,
              hq_location, annual_revenue_usd, employee_count, ibm_account_tier,
              primary_ibm_contact, secondary_ibm_contact, current_sales_cycle_stage,
              account_since, and ibm_relationship_score (float, 0-10).
    """
    return {
        "account_name": "Accenture",
        "company_overview": (
            "Accenture plc is a global professional services company specialising in IT services "
            "and consulting. It operates across more than 120 countries, serves clients in over "
            "40 industries, and is publicly listed on the NYSE (ACN). Deep practices span "
            "Financial Services, Technology, Health, and Public Service."
        ),
        "industry": "Technology Consulting / Financial Services",
        "hq_location": "Dublin, Ireland (Principal offices: New York, London, Mumbai, Singapore)",
        "annual_revenue_usd": "$64.9B (FY2025)",
        "employee_count": "774,000+",
        "ibm_account_tier": "Strategic",
        "primary_ibm_contact": "Sarah Mitchell, IBM Global Account Executive",
        "secondary_ibm_contact": "James Okonkwo, IBM Technical Sales Lead",
        "current_sales_cycle_stage": "Proposal — watsonx Enterprise Expansion",
        "account_since": "2004",
        "ibm_relationship_score": 8.2,
    }


@tool()
def get_isc_cloud_data(account_name: str) -> dict:
    """Returns mock IBM ISC Cloud data for the chosen account.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        dict: IBM ISC Cloud data containing account_name, active_products (list of
              product dicts with product name, license_type, seats, renewal_date,
              usage_percent, and status), open_support_tickets (list of ticket dicts
              with ticket_id, product, severity, title, opened_date, and status),
              upcoming_renewals_90_days (list of strings), and upsell_signals
              (list of strings).
    """
    return {
        "account_name": "Accenture",
        "active_products": [
            {
                "product": "IBM watsonx.ai",
                "license_type": "Enterprise",
                "seats": 2500,
                "renewal_date": "2026-12-31",
                "usage_percent": 74,
                "status": "Active",
            },
            {
                "product": "IBM watsonx.governance",
                "license_type": "Professional",
                "seats": 800,
                "renewal_date": "2026-09-30",
                "usage_percent": 61,
                "status": "Active — Renewal Alert (90 days)",
            },
            {
                "product": "IBM Cloud Pak for Data",
                "license_type": "Enterprise",
                "seats": 1200,
                "renewal_date": "2027-03-15",
                "usage_percent": 88,
                "status": "Active — Upsell Opportunity",
            },
            {
                "product": "IBM Sterling Supply Chain Suite",
                "license_type": "Enterprise",
                "seats": 450,
                "renewal_date": "2026-11-01",
                "usage_percent": 93,
                "status": "Active — Upsell Opportunity",
            },
        ],
        "open_support_tickets": [
            {
                "ticket_id": "INC0042871",
                "product": "IBM Cloud Pak for Data",
                "severity": "Sev 2",
                "title": "DataStage pipeline latency spike in production cluster",
                "opened_date": "2026-06-08",
                "status": "In Progress",
            },
            {
                "ticket_id": "INC0044102",
                "product": "IBM watsonx.ai",
                "severity": "Sev 3",
                "title": "API rate limit errors on batch inference jobs",
                "opened_date": "2026-06-11",
                "status": "Assigned",
            },
        ],
        "upcoming_renewals_90_days": [
            "IBM watsonx.governance — renewal date 2026-09-30 (109 days remaining)",
        ],
        "upsell_signals": [
            "IBM Cloud Pak for Data at 88% utilisation — candidate for capacity tier expansion.",
            "IBM Sterling Supply Chain Suite at 93% utilisation — evaluate premium tier upgrade.",
        ],
    }


@tool()
def get_executive_summary(account_name: str) -> dict:
    """Returns a mock executive summary for a sales rep preparing for a client call.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        dict: Executive summary containing account_name, prepared_for, summary_date
              (today's date, ISO format), key_priorities (list of strings), recent_wins
              (list of strings), open_opportunities (list of strings), and
              recommended_next_steps (list of strings).
    """
    return {
        "account_name": "Accenture",
        "prepared_for": "Sarah Mitchell, IBM Global Account Executive",
        "summary_date": datetime.date.today().isoformat(),
        "key_priorities": [
            "EU AI Act compliance urgency — IBM watsonx.governance renewal (Sept 30, 2026) "
            "is a critical near-term milestone and directly tied to a board-level deadline.",
            "Q2 2026 earnings signal a 34% increase in AI/cloud spend — Accenture has "
            "allocated budget to expand its enterprise AI platform in H2 2026.",
            "New Chief AI Officer Dr. Priya Nair was appointed following the successful "
            "watsonx pilot. She is an IBM advocate with direct budget authority and should "
            "be engaged immediately as the executive champion.",
        ],
        "recent_wins": [
            "IBM Sterling Supply Chain Suite renewal and expansion closed February 2026 ($4.1M) "
            "— award-winning implementation reinforces the IBM–Accenture partnership.",
            "watsonx.ai Financial Services AI pilot converted to production (Q1 2026, $3.2M) "
            "— successful PoC outcome directly drove Dr. Priya Nair's CAO appointment.",
        ],
        "open_opportunities": [
            "watsonx Enterprise Expansion — Proposal stage, est. $8.4M TCV, close target Q3 2026.",
            "Cloud Pak for Data capacity upgrade — est. $1.2M, driven by 88% utilisation signal.",
            "watsonx.governance renewal + governance module upsell — $2.1M renewal + $600K add-on.",
        ],
        "recommended_next_steps": [
            "Schedule intro call with Dr. Priya Nair (new CAO) within the next 2 weeks.",
            "Prepare watsonx.governance renewal proposal — frame around EU AI Act Q3 deadline.",
            "Escalate Sev 2 Cloud Pak for Data ticket INC0042871 — use resolution as a "
            "relationship and delivery quality proof point ahead of the expansion proposal.",
            "Share updated Seismic Microsoft Azure OpenAI battlecard with the Accenture account "
            "team to counter the parallel Azure OpenAI PoC underway.",
        ],
    }

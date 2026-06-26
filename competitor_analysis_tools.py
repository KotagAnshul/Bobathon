"""
Competitor Analysis tools for the IBM Sales Intelligence Hub.

Agent: competitor_analysis_agent
Tools:
  - get_competitors           : Returns 3-5 active competitors at the chosen account.
  - get_competitor_battlecard : Returns a full IBM competitive battlecard for a named competitor.
  - get_win_loss_summary      : Returns IBM win/loss history at the chosen account.

Mock data reflects Accenture. Full battlecards are provided for Microsoft, AWS,
Google Cloud, and Salesforce — the four active competitors identified at Accenture.

Import command:
  orchestrate tools import -k python -f competitor_analysis_tools.py
"""

from ibm_watsonx_orchestrate.agent_builder.tools import tool

__all__ = ["get_competitors", "get_competitor_battlecard", "get_win_loss_summary"]

# ---------------------------------------------------------------------------
# Hardcoded mock data
# ---------------------------------------------------------------------------

_BATTLECARDS = {
    "Microsoft": {
        "competitor": "Microsoft",
        "ibm_differentiators": [
            "IBM watsonx.governance provides enterprise-grade AI explainability, bias detection, "
            "and full audit trails — Azure OpenAI Service has no comparable governance layer, "
            "creating a direct compliance gap for EU AI Act regulated workloads.",
            "IBM watsonx is built on open-source foundations (Hugging Face, open LLMs) and "
            "supports any cloud or on-premises deployment — avoiding the proprietary GPT "
            "dependency and Azure-only lock-in inherent to Microsoft's stack.",
            "IBM has 30+ years of enterprise data management, integration, and AI expertise "
            "at financial services firms. Microsoft's enterprise AI capabilities date from 2023 "
            "and lack comparable battle-tested deployments in regulated industries.",
            "IBM Cloud Pak for Data provides hybrid, multi-cloud data fabric capabilities "
            "that Azure Synapse and Microsoft Fabric cannot replicate in on-premises or "
            "sovereign cloud environments — critical for Accenture's FS clients.",
        ],
        "competitor_weaknesses": [
            "Azure OpenAI lacks transparent model lineage, explainability reports, and "
            "the audit trail capabilities required under the EU AI Act for high-risk systems.",
            "Heavy ecosystem lock-in: Microsoft's AI stack is deeply tied to Azure, M365, "
            "and Teams, creating vendor concentration risk for Accenture's enterprise clients.",
            "Limited hybrid and on-premises deployment options — a barrier for regulated "
            "financial services workloads that cannot move fully to public cloud.",
            "Microsoft Copilot for M365 is not a replacement for IBM's domain-specific "
            "enterprise AI fine-tuning and customisation capabilities in watsonx.ai.",
        ],
        "suggested_talking_points": [
            "'How will Accenture demonstrate EU AI Act model explainability to regulators "
            "using Azure OpenAI?' — this is an unanswered question. Position watsonx.governance "
            "as the answer with a Q3 deadline already in place.",
            "Emphasise that IBM watsonx already has a proven deployment inside Accenture's FS "
            "division — the pilot succeeded, the CAO appointment proves it. Azure OpenAI is "
            "unproven at Accenture scale.",
            "Position IBM as the only vendor offering a complete, governed AI platform "
            "that spans data (Cloud Pak for Data), AI (watsonx.ai), and compliance "
            "(watsonx.governance) in a single integrated stack.",
        ],
        "ibm_products_to_position": [
            "IBM watsonx.ai",
            "IBM watsonx.governance",
            "IBM Cloud Pak for Data",
        ],
    },
    "AWS": {
        "competitor": "AWS",
        "ibm_differentiators": [
            "IBM Sterling Supply Chain Suite has 20+ years of enterprise supply chain "
            "integration expertise, thousands of pre-built connectors, and an award-winning "
            "Accenture implementation — AWS Supply Chain launched in 2022 and has a fraction "
            "of Sterling's integration depth and enterprise track record.",
            "IBM's hybrid cloud architecture supports on-premises, private cloud, and "
            "true multi-cloud deployment. AWS is inherently AWS-centric and pushes all "
            "workloads toward its own infrastructure.",
            "IBM is Accenture's long-term co-sell partner; AWS has now positioned itself "
            "as a direct competitor to Accenture in consulting and managed services, creating "
            "an internal tension that IBM can leverage.",
            "IBM watsonx.governance provides responsible AI governance and EU AI Act "
            "compliance capabilities that Amazon Bedrock and SageMaker do not offer.",
        ],
        "competitor_weaknesses": [
            "AWS Supply Chain is a nascent product with limited EDI integration, supplier "
            "onboarding, and order management capabilities compared to IBM Sterling.",
            "The $3B Accenture–AWS partnership creates internal tension: Accenture consulting "
            "staff selling AWS compete directly with Accenture's own services revenue, giving "
            "IBM an opportunity to exploit the multi-vendor leverage argument.",
            "Amazon Bedrock lacks enterprise AI governance tooling — no explainability layer, "
            "no bias detection, no audit trails for regulated-industry deployments.",
            "AWS enterprise support and professional services depth is weaker than IBM's "
            "co-delivery model with Accenture on the ground.",
        ],
        "suggested_talking_points": [
            "Accenture signed an AWS partnership, but IBM remains their proven AI and supply "
            "chain platform with an active, award-winning Sterling deployment. Reinforce "
            "that IBM's investment is already delivering value today.",
            "Position the $3B AWS deal as a consulting channel play, not a technology "
            "replacement — Accenture needs IBM's technology stack regardless of which "
            "cloud they migrate workloads to.",
            "Ask Accenture: 'Where does Amazon Bedrock's AI governance story leave you "
            "for EU AI Act compliance?' — then position IBM watsonx.governance.",
        ],
        "ibm_products_to_position": [
            "IBM Sterling Supply Chain Suite",
            "IBM watsonx.ai",
            "IBM watsonx.governance",
            "IBM Cloud Pak for Data",
        ],
    },
    "Google Cloud": {
        "competitor": "Google Cloud",
        "ibm_differentiators": [
            "IBM Cloud Pak for Data provides a unified, governed data fabric with deep "
            "hybrid and on-premises support. Google BigQuery ML and Vertex AI are "
            "cloud-native and lack comparable on-premises or sovereign cloud capabilities "
            "required by Accenture's FS clients.",
            "IBM watsonx.governance addresses EU AI Act compliance requirements with "
            "purpose-built model cards, bias detection, and audit trails. Vertex AI has "
            "no equivalent enterprise AI governance layer.",
            "IBM has over two decades of Financial Services industry expertise, regulatory "
            "certifications (FedRAMP, ISO 27001, SOC 2), and dedicated FS solution teams. "
            "Google Cloud's enterprise financial services practice is significantly newer.",
            "IBM's partnership with Accenture is a proven co-delivery relationship with "
            "hundreds of certified consultants. Google Cloud's Accenture partnership is "
            "newer and less deeply resourced.",
        ],
        "competitor_weaknesses": [
            "Google Vertex AI requires significant MLOps expertise and custom integration "
            "work to connect to legacy enterprise data sources — IBM's managed capabilities "
            "reduce this burden substantially.",
            "Google Cloud's enterprise support model receives consistent criticism at "
            "large accounts. IBM's dedicated account team and 24x7 support SLAs are "
            "materially stronger.",
            "Gemini Enterprise's integration with legacy enterprise systems (SAP, mainframe, "
            "Sterling) is immature. IBM watsonx integrates natively across the IBM portfolio.",
            "Google Cloud has limited on-premises and private cloud options — a barrier "
            "for Accenture's regulated financial services client workloads.",
        ],
        "suggested_talking_points": [
            "Position IBM's Financial Services AI experience and regulatory certifications "
            "against Google's consumer-origin, cloud-first approach to enterprise AI.",
            "Ask Accenture: 'How does Vertex AI handle the EU AI Act requirements your "
            "FS division faces?' — IBM watsonx.governance has a direct answer.",
            "Highlight IBM Cloud Pak for Data's hybrid deployment capability versus "
            "BigQuery ML's GCP-only architecture for FS workloads that cannot move to "
            "public cloud.",
        ],
        "ibm_products_to_position": [
            "IBM Cloud Pak for Data",
            "IBM watsonx.ai",
            "IBM watsonx.governance",
        ],
    },
    "Salesforce": {
        "competitor": "Salesforce",
        "ibm_differentiators": [
            "IBM watsonx operates across the entire enterprise data estate — structured, "
            "unstructured, and streaming — not just CRM data. Salesforce Einstein AI and "
            "Agentforce are tightly scoped to data within the Salesforce platform.",
            "IBM Cloud Pak for Data provides enterprise-grade data integration, cataloguing, "
            "lineage, and governance across multi-cloud and on-premises environments. "
            "Salesforce Data Cloud is limited to customer and marketing data.",
            "IBM watsonx.governance addresses EU AI Act compliance with model explainability "
            "and audit trails. Salesforce has no equivalent enterprise AI governance product.",
            "IBM's long-term Accenture relationship, co-sell track record, and certified "
            "consultant base is materially deeper than Salesforce's Accenture partnership.",
        ],
        "competitor_weaknesses": [
            "Salesforce Einstein AI is tightly coupled to Salesforce CRM — it cannot access "
            "Accenture's supply chain, HR, finance, or operational data sources.",
            "Agentforce is a recently launched product with limited enterprise production "
            "deployments and no proven track record at Accenture's scale.",
            "Salesforce Data Cloud has a narrow focus on customer data and marketing "
            "use cases — it cannot replace IBM Cloud Pak for Data's analytics breadth.",
            "High total cost of ownership for AI capabilities outside the Salesforce "
            "ecosystem, and limited hybrid/on-premises deployment options.",
        ],
        "suggested_talking_points": [
            "Position IBM watsonx and Salesforce as complementary, not competitive: "
            "'IBM powers the enterprise AI and data fabric; Salesforce powers the CRM.' "
            "This avoids a binary choice and expands IBM's footprint.",
            "Ask Accenture: 'For AI use cases outside of CRM — supply chain, risk, "
            "compliance, analytics — where does Salesforce's story end?' "
            "IBM watsonx is the answer.",
            "Highlight that Accenture is already a Salesforce partner — IBM can co-exist "
            "and extend Salesforce data with watsonx without displacement.",
        ],
        "ibm_products_to_position": [
            "IBM watsonx.ai",
            "IBM Cloud Pak for Data",
            "IBM watsonx.governance",
        ],
    },
}

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool()
def get_competitors(account_name: str) -> list:
    """Returns a list of competitors currently engaged with or evaluated by the account.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        list: A list of 3-5 competitor objects, each containing competitor name,
              products_considered (list of strings), estimated_deal_size_usd (string),
              ibm_competitive_position ("Advantaged", "Even", or "At Risk"), and
              notes (string with deal context).
    """
    return [
        {
            "competitor": "Microsoft",
            "products_considered": [
                "Azure OpenAI Service",
                "Microsoft Copilot for M365",
                "Azure ML",
            ],
            "estimated_deal_size_usd": "$5.2M",
            "ibm_competitive_position": "At Risk",
            "notes": (
                "Accenture's IT division is running a parallel Azure OpenAI PoC for internal "
                "workflow automation targeting 15,000 employees. Microsoft's existing M365 "
                "footprint creates a natural low-friction expansion path."
            ),
        },
        {
            "competitor": "AWS",
            "products_considered": [
                "Amazon Bedrock",
                "AWS SageMaker",
                "AWS Supply Chain",
            ],
            "estimated_deal_size_usd": "$7.8M",
            "ibm_competitive_position": "At Risk",
            "notes": (
                "The newly announced $3B Accenture–AWS strategic partnership is the most "
                "significant competitive threat this cycle. AWS Supply Chain is being "
                "positioned directly against IBM Sterling for Accenture's next supply "
                "chain modernisation wave."
            ),
        },
        {
            "competitor": "Google Cloud",
            "products_considered": [
                "Vertex AI",
                "BigQuery ML",
                "Gemini Enterprise",
            ],
            "estimated_deal_size_usd": "$3.1M",
            "ibm_competitive_position": "Even",
            "notes": (
                "Google is pitching Vertex AI as an alternative to IBM Cloud Pak for Data "
                "for Accenture's analytics modernisation programme. The evaluation is at "
                "early-stage RFI phase; IBM has the incumbent advantage."
            ),
        },
        {
            "competitor": "Salesforce",
            "products_considered": [
                "Einstein AI",
                "Salesforce Data Cloud",
                "Agentforce",
            ],
            "estimated_deal_size_usd": "$1.4M",
            "ibm_competitive_position": "Advantaged",
            "notes": (
                "Salesforce is competing primarily on CRM AI augmentation. IBM is well-positioned "
                "given watsonx's broader enterprise data integration scope. An IBM + Salesforce "
                "complementary positioning could neutralise the competitive risk entirely."
            ),
        },
    ]


@tool()
def get_competitor_battlecard(competitor_name: str) -> dict:
    """Returns a competitive battlecard for the specified competitor.

    Args:
        competitor_name (str): The name of the competitor to retrieve a battlecard for.
                               Supported values: "Microsoft", "AWS", "Google Cloud",
                               "Salesforce".

    Returns:
        dict: Battlecard containing competitor name, ibm_differentiators (list of strings),
              competitor_weaknesses (list of strings), suggested_talking_points (list of
              strings), and ibm_products_to_position (list of strings).
    """
    card = _BATTLECARDS.get(competitor_name)
    if card:
        return card

    # Generic fallback for any competitor not in the primary dataset
    return {
        "competitor": competitor_name,
        "ibm_differentiators": [
            "IBM offers a fully integrated, enterprise-grade AI and data platform spanning "
            "watsonx.ai, watsonx.governance, and IBM Cloud Pak for Data — with 30+ years of "
            "enterprise deployment expertise.",
            "IBM watsonx.governance provides EU AI Act and FedRAMP-compliant AI governance "
            "tooling that most competitors do not offer as a native product.",
            "IBM's co-sell relationship with Accenture, certified consultant base, and "
            "dedicated account team provide a delivery advantage over newer entrants.",
            "IBM supports hybrid, multi-cloud, and on-premises deployments — avoiding the "
            "vendor lock-in risk inherent in cloud-native-only competitors.",
        ],
        "competitor_weaknesses": [
            "Limited enterprise track record at the scale and complexity of Accenture deployments.",
            "Newer entrant to the enterprise AI market without IBM's regulatory certifications "
            "or Financial Services industry depth.",
            "Likely lacks a dedicated Accenture co-sell partnership and certified consultant base.",
            "No equivalent to IBM watsonx.governance for EU AI Act compliance.",
        ],
        "suggested_talking_points": [
            "Position IBM's end-to-end data and AI platform — data, AI, governance — "
            "as the only integrated stack that covers Accenture's full enterprise AI lifecycle.",
            "Ask Accenture about the competitor's EU AI Act compliance story — then present "
            "IBM watsonx.governance as the definitive answer.",
            "Remind Accenture of IBM's proven delivery track record at their account "
            "versus the risk of adopting an unproven vendor at this scale.",
        ],
        "ibm_products_to_position": [
            "IBM watsonx.ai",
            "IBM watsonx.governance",
            "IBM Cloud Pak for Data",
        ],
    }


@tool()
def get_win_loss_summary(account_name: str) -> dict:
    """Returns a mock summary of recent IBM wins and losses at the chosen account.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        dict: Win/loss summary containing account_name, period (string), overall_record
              (dict with wins, losses, and pending counts), recent_wins (list of deal dicts
              with deal, value_usd, close_date, and reason), and recent_losses (list of
              deal dicts with deal, value_usd, close_date, and reason).
    """
    return {
        "account_name": "Accenture",
        "period": "Last 12 months (June 2025 – June 2026)",
        "overall_record": {"wins": 3, "losses": 2, "pending": 2},
        "recent_wins": [
            {
                "deal": "IBM Sterling Supply Chain Suite — Enterprise Renewal & Expansion",
                "value_usd": "$4.1M",
                "close_date": "2026-02-15",
                "reason": (
                    "IBM's 20+ year supply chain integration depth and the award-winning "
                    "Accenture delivery team outweighed AWS Supply Chain's initial cost pitch. "
                    "The 2026 industry award was cited by Accenture procurement as a key factor."
                ),
            },
            {
                "deal": "IBM watsonx.ai — Financial Services AI Pilot to Production",
                "value_usd": "$3.2M",
                "close_date": "2025-11-30",
                "reason": (
                    "Successful PoC results and IBM's EU AI Act compliance capabilities "
                    "were decisive over Google Vertex AI. The pilot directly led to "
                    "Dr. Priya Nair's appointment as Chief AI Officer."
                ),
            },
            {
                "deal": "IBM Cloud Pak for Data — Analytics Platform Capacity Expansion",
                "value_usd": "$1.8M",
                "close_date": "2025-08-20",
                "reason": (
                    "Utilisation metrics (now at 88%) provided a clear, data-backed "
                    "justification for expansion. No credible competitive alternative "
                    "was presented at the time of renewal."
                ),
            },
        ],
        "recent_losses": [
            {
                "deal": "Internal Automation Platform — Azure OpenAI vs IBM watsonx",
                "value_usd": "$2.4M",
                "close_date": "2026-01-10",
                "reason": (
                    "Microsoft's existing M365 footprint at Accenture and bundled pricing "
                    "reduced the switching cost below IBM's price premium. The procurement "
                    "team (Lisa Tran) was not engaged early enough in the cycle."
                ),
            },
            {
                "deal": "HR Analytics Platform — Workday AI vs IBM watsonx",
                "value_usd": "$900K",
                "close_date": "2025-09-05",
                "reason": (
                    "Workday's native HR data integration was preferred over a standalone "
                    "watsonx deployment. IBM did not have a Workday integration story ready "
                    "for this specific HR use case."
                ),
            },
        ],
    }

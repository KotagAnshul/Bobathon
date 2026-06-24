"""
IBM Sales Intelligence Hub — Streamlit UI
Mirrors ui/dashboard.html. Run with:
    streamlit run ui/streamlit_app.py --server.port 8503
"""

import streamlit as st
from copy import deepcopy
from datetime import date

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IBM Sales Intelligence Hub",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# IBM CARBON DARK THEME INJECTION
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── IBM Carbon palette ── */
  :root {
    --ibm-blue: #0F62FE;
    --bg: #161616;
    --surface: #262626;
    --surface-2: #393939;
    --border: #525252;
    --text: #F4F4F4;
    --text-muted: #A8A8A8;
    --green: #42BE65;
    --yellow: #F1C21B;
    --red: #FA4D56;
  }
  html, body, [class*="css"] {
    background-color: #161616 !important;
    color: #F4F4F4 !important;
    font-family: -apple-system, "Segoe UI", system-ui, sans-serif !important;
  }
  /* Sidebar */
  [data-testid="stSidebar"] { background-color: #262626 !important; border-right: 1px solid #525252; }
  [data-testid="stSidebar"] * { color: #F4F4F4 !important; }
  /* Top nav selectbox / radio */
  .stRadio > div { gap: 4px; }
  .stRadio label { background: #262626; border: 1px solid #525252; padding: 6px 14px;
                   border-radius: 2px; cursor: pointer; font-size: 13px; color: #F4F4F4 !important; }
  /* Metric cards */
  [data-testid="metric-container"] { background: #262626; border: 1px solid #525252; padding: 12px 16px; border-radius: 2px; }
  /* Dataframes */
  [data-testid="stDataFrame"] th { background: #393939 !important; color: #F4F4F4 !important; }
  [data-testid="stDataFrame"] td { background: #262626 !important; color: #F4F4F4 !important; }
  /* Text inputs */
  input, textarea, select { background: #393939 !important; color: #F4F4F4 !important;
                             border: 1px solid #525252 !important; }
  /* Buttons */
  .stButton > button { background: #0F62FE; color: #fff; border: none;
                       font-weight: 600; border-radius: 0; padding: 8px 20px; }
  .stButton > button:hover { background: #0353E9 !important; }
  /* Expander */
  .streamlit-expanderHeader { background: #262626 !important; color: #F4F4F4 !important;
                               border: 1px solid #525252 !important; }
  .streamlit-expanderContent { background: #1e1e1e !important; border: 1px solid #525252 !important; }
  /* Dividers */
  hr { border-color: #525252 !important; }
  /* Tags helper classes */
  .tag-blue  { background:#001D6C; color:#78A9FF; padding:2px 8px; border-radius:2px; font-size:11px; font-weight:600; display:inline-block; }
  .tag-green { background:#071908; color:#42BE65; padding:2px 8px; border-radius:2px; font-size:11px; font-weight:600; display:inline-block; }
  .tag-red   { background:#2D0709; color:#FA4D56; padding:2px 8px; border-radius:2px; font-size:11px; font-weight:600; display:inline-block; }
  .tag-yellow{ background:#302400; color:#F1C21B; padding:2px 8px; border-radius:2px; font-size:11px; font-weight:600; display:inline-block; }
  .tag-purple{ background:#1C0F30; color:#BE95FF; padding:2px 8px; border-radius:2px; font-size:11px; font-weight:600; display:inline-block; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "rep" not in st.session_state:
    st.session_state.rep = "Sarah Mitchell"
if "account" not in st.session_state:
    st.session_state.account = "Accenture"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "flagged_news" not in st.session_state:
    st.session_state.flagged_news = {}

# ─────────────────────────────────────────────────────────────
# MOCK DATA
# ─────────────────────────────────────────────────────────────
NEWS_ITEMS = [
    {"id": "news_001", "tag": "🔴 Competitor Move",  "title": "Accenture expands AWS partnership with $3B cloud migration commitment",            "source": "Reuters",    "date": "Jun 10, 2026", "summary": "Accenture and AWS announce a 3-year, $3B strategic cloud and AI collaboration targeting enterprise transformation. Threatens IBM Sterling and Cloud deployments."},
    {"id": "news_002", "tag": "🟡 Executive Change",  "title": "Dr. Priya Nair appointed Chief AI Officer following watsonx pilot success",       "source": "Bloomberg",  "date": "Jun 8, 2026",  "summary": "Accenture promotes Dr. Priya Nair (IBM watsonx advocate) to newly created CAO role. Key relationship opportunity for IBM."},
    {"id": "news_003", "tag": "🟢 Opportunity",       "title": "Accenture Q2 2026 earnings: AI & cloud revenue up 34% YoY",                       "source": "WSJ",        "date": "Jun 5, 2026",  "summary": "Accenture beats Q2 estimates. AI and cloud division revenue grew 34% YoY to $8.2B. Budget available for AI platform expansion."},
    {"id": "news_004", "tag": "🟢 Opportunity",       "title": "EU AI Act deadline creates urgency for watsonx.governance renewal at Accenture",   "source": "FT",         "date": "Jun 3, 2026",  "summary": "Accenture's FS clients face Q3 2026 EU AI Act compliance deadline. IBM watsonx.governance is the only platform that directly addresses this."},
    {"id": "news_005", "tag": "🔴 Risk",               "title": "Accenture piloting Azure OpenAI for internal automation across 15,000 employees", "source": "TechCrunch", "date": "May 29, 2026", "summary": "Microsoft Azure OpenAI PoC underway at Accenture for internal productivity automation. Risk to IBM watsonx.ai expansion."},
]

PRODUCTS = [
    {"product": "IBM watsonx.ai",              "tier": "Enterprise", "seats": 2500, "usage": "74%",  "renewal": "Dec 31, 2026", "alert": False},
    {"product": "IBM watsonx.governance",       "tier": "Professional","seats": 800,  "usage": "61%",  "renewal": "Sep 30, 2026", "alert": True},
    {"product": "IBM Cloud Pak for Data",       "tier": "Enterprise", "seats": 1200, "usage": "88%",  "renewal": "Jan 15, 2027", "alert": False},
    {"product": "IBM Sterling Supply Chain",    "tier": "Enterprise", "seats": 450,  "usage": "93%",  "renewal": "Nov 30, 2026", "alert": False},
    {"product": "IBM Instana Observability",    "tier": "Standard",   "seats": 200,  "usage": "45%",  "renewal": "Mar 1, 2027",  "alert": False},
]

TICKETS = [
    {"id": "INC0042871", "sev": "Sev 2", "title": "Cloud Pak DataStage latency spikes in FS analytics pipeline",      "status": "In Progress"},
    {"id": "INC0044102", "sev": "Sev 3", "title": "watsonx.ai API rate limit errors during peak batch processing",      "status": "Pending"},
    {"id": "INC0041337", "sev": "Sev 4", "title": "Instana dashboard export to PDF failing intermittently",             "status": "Resolved"},
]

COMPETITORS = [
    {"name": "AWS",           "products": "SageMaker, Supply Chain, Bedrock", "status": "⚠️ At Risk",    "deal_value": "$7.8M"},
    {"name": "Microsoft",     "products": "Azure OpenAI, Copilot, Synapse",    "status": "⚠️ At Risk",    "deal_value": "$5.2M"},
    {"name": "Google Cloud",  "products": "Vertex AI, BigQuery ML, Gemini",    "status": "🟡 Even",       "deal_value": "$3.1M"},
    {"name": "Salesforce",    "products": "Einstein AI, Agentforce, Data Cloud","status": "✅ Advantaged", "deal_value": "$1.4M"},
]

BATTLECARDS = {
    "Microsoft": {
        "differentiators": [
            "IBM watsonx.governance provides enterprise-grade explainability, bias detection, and full EU AI Act audit trails — Azure OpenAI has no comparable governance layer.",
            "IBM watsonx runs on open-source LLMs (Hugging Face, Llama), avoiding proprietary GPT lock-in and enabling hybrid/on-prem deployment.",
            "IBM has 30+ years of regulated-industry AI expertise; Microsoft's enterprise AI capabilities date from 2023 with limited FS track record.",
        ],
        "weaknesses": [
            "Azure OpenAI lacks transparent model lineage, explainability reports, and EU AI Act audit trail capabilities.",
            "Heavy lock-in: Microsoft's AI stack is tied to Azure + M365 + Teams — vendor concentration risk.",
            "Limited hybrid/on-prem options for regulated financial services workloads.",
        ],
        "talking_points": [
            '"How will Accenture demonstrate EU AI Act model explainability to regulators using Azure OpenAI?" — IBM watsonx.governance is the only answer with a Q3 deadline.',
            "IBM watsonx already has a proven, award-acknowledged deployment at Accenture FS. Azure OpenAI is unproven at Accenture scale.",
        ],
        "products": ["IBM watsonx.ai", "IBM watsonx.governance", "IBM Cloud Pak for Data"],
    },
    "AWS": {
        "differentiators": [
            "IBM Sterling has 20+ years of supply chain depth and thousands of pre-built connectors — AWS Supply Chain launched in 2022.",
            "IBM's hybrid cloud supports on-prem, private cloud, and true multi-cloud. AWS is inherently AWS-centric.",
            "IBM is Accenture's long-term co-sell partner; AWS now directly competes with Accenture in consulting — an internal tension IBM can leverage.",
        ],
        "weaknesses": [
            "AWS Supply Chain is nascent — limited EDI integration, supplier onboarding, and order management vs IBM Sterling.",
            "The $3B Accenture–AWS deal creates internal conflict with Accenture's own services revenue.",
            "Amazon Bedrock has no enterprise AI governance layer — no explainability, no audit trails for regulated deployments.",
        ],
        "talking_points": [
            "Accenture signed an AWS partnership, but IBM remains their proven AI and supply chain platform — watsonx is already live.",
            '"Where does Amazon Bedrock\'s EU AI Act governance story leave Accenture\'s FS division?" — then position IBM watsonx.governance.',
        ],
        "products": ["IBM Sterling Supply Chain Suite", "IBM watsonx.ai", "IBM watsonx.governance"],
    },
    "Google Cloud": {
        "differentiators": [
            "IBM Cloud Pak for Data provides a governed data fabric with deep hybrid and on-prem support — Vertex AI is cloud-native only.",
            "IBM watsonx.governance addresses EU AI Act compliance with model cards, bias detection, and audit trails — Vertex AI has no equivalent.",
            "IBM's Accenture co-delivery relationship has hundreds of certified consultants. Google Cloud's Accenture partnership is thinner.",
        ],
        "weaknesses": [
            "Google Vertex AI requires significant MLOps expertise and custom integration to reach legacy enterprise data sources.",
            "Google Cloud enterprise support consistently receives criticism at large accounts.",
            "Google Cloud has limited on-prem and private cloud options for Accenture's regulated FS workloads.",
        ],
        "talking_points": [
            "Position IBM's Financial Services regulatory certifications vs Google's consumer-origin, cloud-first approach.",
            '"How does Vertex AI handle EU AI Act requirements for Accenture\'s FS division?" — IBM watsonx.governance has the answer today.',
        ],
        "products": ["IBM Cloud Pak for Data", "IBM watsonx.ai", "IBM watsonx.governance"],
    },
    "Salesforce": {
        "differentiators": [
            "IBM watsonx operates across the entire enterprise data estate — not just CRM data.",
            "IBM Cloud Pak for Data provides enterprise-grade integration, lineage, and governance across multi-cloud and on-prem.",
            "IBM watsonx.governance addresses EU AI Act compliance — Salesforce has no equivalent product.",
        ],
        "weaknesses": [
            "Salesforce Einstein AI is coupled to Salesforce CRM — cannot access Accenture's supply chain, finance, or operational data.",
            "Agentforce is recently launched with limited enterprise production deployments.",
            "High TCO for AI capabilities outside the Salesforce ecosystem; limited hybrid/on-prem deployment.",
        ],
        "talking_points": [
            'Position IBM + Salesforce as complementary: "IBM powers the enterprise AI and data fabric; Salesforce powers the CRM."',
            '"For AI use cases outside CRM — supply chain, risk, compliance — where does Salesforce\'s story end?" IBM watsonx is the answer.',
        ],
        "products": ["IBM watsonx.ai", "IBM Cloud Pak for Data", "IBM watsonx.governance"],
    },
}

UPCOMING_MEETINGS = [
    {"id": "mtg_001", "date": "Jun 18, 2026", "time": "2:00 PM UTC",  "title": "watsonx Enterprise Expansion Proposal Review",       "status": "⚠️ Needs Prep",    "ibm": ["Sarah Mitchell", "James Okonkwo"],          "client": ["Dr. Priya Nair (CAO)", "Mark Henderson (VP Tech)"]},
    {"id": "mtg_002", "date": "Jun 20, 2026", "time": "10:00 AM UTC", "title": "IBM Sterling Q3 Business Review",                    "status": "✅ Prep Complete",  "ibm": ["Sarah Mitchell", "Chris Adeyemi"],           "client": ["Rachel Park (Head, Supply Chain)", "Tom Burgess (CTO)"]},
    {"id": "mtg_003", "date": "Jun 25, 2026", "time": "1:00 PM UTC",  "title": "watsonx.governance EU AI Act Compliance Workshop",   "status": "🔴 No Brief",       "ibm": ["Sarah Mitchell", "Dr. Anita Rowe", "IBM Legal SME (TBC)"], "client": ["Dr. Priya Nair (CAO)", "Mark Henderson", "Accenture Legal (TBC)"]},
]

MEETING_HISTORY = [
    {"date": "Jun 4, 2026",  "title": "watsonx.ai Q2 Business Review",         "attendees": "Dr. Priya Nair",        "outcome": "Pilot results positive; expansion proposal requested."},
    {"date": "May 22, 2026", "title": "Cloud Pak for Data Capacity Planning",   "attendees": "Tom Burgess",           "outcome": "88% utilisation confirmed; upgrade proposal due end of June."},
    {"date": "May 14, 2026", "title": "Executive Sponsor Dinner",               "attendees": "Dr. Priya Nair, CEO NA","outcome": "Relationship reaffirmed at exec level; IBM AI roadmap well received."},
    {"date": "Apr 30, 2026", "title": "IBM Sterling Renewal Discussion",        "attendees": "Rachel Park",           "outcome": "Renewal confirmed for Nov 2026; premium tier under consideration."},
    {"date": "Apr 15, 2026", "title": "watsonx.governance Scoping Call",        "attendees": "Mark Henderson",        "outcome": "EU AI Act confirmed as board-level priority; demo scheduled."},
]

RELATIONSHIP_MAP = [
    {"contact": "Dr. Priya Nair",  "title": "Chief AI Officer",     "ibm_owner": "Sarah Mitchell", "engagement": "🟢 Strong",   "last": "Jun 4, 2026"},
    {"contact": "Mark Henderson",  "title": "VP Technology, FS",    "ibm_owner": "James Okonkwo",  "engagement": "🟡 Moderate", "last": "May 14, 2026"},
    {"contact": "Rachel Park",     "title": "Head of Supply Chain", "ibm_owner": "Chris Adeyemi",  "engagement": "🟢 Strong",   "last": "Apr 30, 2026"},
    {"contact": "Lisa Tran",       "title": "Procurement Lead",     "ibm_owner": "Sarah Mitchell", "engagement": "🔵 Cold",     "last": "Feb 10, 2026"},
    {"contact": "David Osei",      "title": "Chief Financial Officer","ibm_owner": "Sarah Mitchell","engagement": "🔵 Cold",     "last": "Nov 20, 2025"},
]

CRM_OPPS = [
    {"id": "SF-OPP-20240801", "name": "watsonx Enterprise Expansion",   "stage": "Proposal",       "amount": "$8,400,000", "close": "Sep 30, 2026", "forecast": "Best Case"},
    {"id": "SF-OPP-20240802", "name": "Cloud Pak for Data Upgrade",     "stage": "Needs Analysis", "amount": "$1,200,000", "close": "Aug 15, 2026", "forecast": "Pipeline"},
    {"id": "SF-OPP-20240803", "name": "watsonx.governance Renewal",     "stage": "Value Prop",     "amount": "$2,700,000", "close": "Aug 31, 2026", "forecast": "Commit"},
]

LEADS = [
    {"name": "Dr. Priya Nair",    "title": "Chief AI Officer",        "dept": "AI & Emerging Tech", "score": 96, "reason": "Decision-maker; watsonx.governance budget owner; new CAO role"},
    {"name": "Mark Henderson",    "title": "VP Technology, FS",       "dept": "Financial Services",  "score": 84, "reason": "Technical champion; EU AI Act compliance lead"},
    {"name": "Lisa Tran",         "title": "Procurement Lead",        "dept": "Procurement",         "score": 72, "reason": "Renewal authority for Watson & Cloud Pak licences"},
    {"name": "David Osei",        "title": "Chief Financial Officer", "dept": "Finance",             "score": 68, "reason": "CFO approval needed for $8.4M expansion; cold — re-engage"},
    {"name": "Sophie Andersen",   "title": "Head of Data & Analytics","dept": "Analytics CoE",       "score": 61, "reason": "Cloud Pak for Data upgrade champion"},
]

SEISMIC_CONTENT = [
    {"title": "IBM watsonx.governance — EU AI Act Compliance Solution Brief", "type": "Solution Brief", "relevance": "99%"},
    {"title": "IBM watsonx vs Microsoft Azure OpenAI — Competitive Battlecard","type": "Battlecard",     "relevance": "95%"},
    {"title": "Accenture × IBM watsonx Financial Services AI Success Story",   "type": "Case Study",    "relevance": "91%"},
]

BOB_ROUTES = [
    (r"what'?s new|news|press release|announcement|this week",
     lambda: (
         "**Morning News for Accenture** — routing through `morning_news_agent`\n\n"
         "🔴 **Competitor Move** — Accenture expands AWS partnership with $3B cloud migration commitment *(Reuters, Jun 10)*\n"
         "🟡 **Executive Change** — Dr. Priya Nair appointed Chief AI Officer following watsonx pilot success *(Bloomberg, Jun 8)*\n"
         "🟢 **Opportunity** — Q2 2026 earnings: AI & cloud revenue up 34% YoY — budget available *(WSJ, Jun 5)*\n"
         "🟢 **Opportunity** — EU AI Act deadline creates urgency for watsonx.governance renewal *(FT, Jun 3)*\n"
         "🔴 **Risk** — Accenture piloting Azure OpenAI for internal automation *(TechCrunch, May 29)*\n\n"
         "💡 Want me to flag the AWS news as important, or pull a competitive battlecard?"
     )),
    (r"meeting|calendar|upcoming|scheduled|this month",
     lambda: (
         "**Upcoming Meetings** — routing through `meetings_relationships_agent`\n\n"
         "📅 **Jun 18** — watsonx Enterprise Expansion Proposal Review · 2:00 PM UTC · ⚠️ *Needs Prep*\n"
         "📅 **Jun 20** — IBM Sterling Q3 Business Review · 10:00 AM UTC · ✅ *Prep Complete*\n"
         "📅 **Jun 25** — watsonx.governance EU AI Act Compliance Workshop · 1:00 PM UTC · 🔴 *No Brief*\n\n"
         "⚠️ 2 meetings still need prep. Shall I help draft a brief for the June 18th proposal review?"
     )),
    (r"competitor|competition|vs |versus|competitive landscape|biggest.*risk",
     lambda: (
         "**Active Competitors at Accenture** — routing through `competitor_analysis_agent`\n\n"
         "⚠️ **AWS** (At Risk, $7.8M) — $3B Accenture partnership announced. AWS Supply Chain vs IBM Sterling.\n"
         "⚠️ **Microsoft** (At Risk, $5.2M) — Azure OpenAI PoC targeting 15,000 Accenture employees.\n"
         "🟡 **Google Cloud** (Even, $3.1M) — Vertex AI evaluated for analytics modernisation.\n"
         "✅ **Salesforce** (Advantaged, $1.4M) — CRM AI only; IBM well positioned.\n\n"
         '💡 Ask: *"Give me a battlecard against Microsoft"* to open the full battlecard.'
     )),
    (r"battlecard|talking point|differentiator",
     lambda: (
         "**IBM vs Microsoft Battlecard** — routing through `competitor_analysis_agent`\n\n"
         "**IBM Differentiators:**\n"
         "• watsonx.governance provides EU AI Act explainability + audit trails — Azure OpenAI has no equivalent.\n"
         "• IBM watsonx runs on open-source LLMs — no GPT lock-in; hybrid/on-prem deployment possible.\n"
         "• 30+ years of regulated-industry AI expertise vs Microsoft's 2023 enterprise AI entry.\n\n"
         "**Key Talking Point:** *\"How will Accenture demonstrate EU AI Act model explainability to regulators using Azure OpenAI?\"*\n\n"
         "Open the **Competitor Analysis** tab for full battlecards against AWS, Google Cloud, and Salesforce."
     )),
    (r"ibm product|active product|license|isc cloud|renewal|sterling|watsonx\.ai|cloud pak",
     lambda: (
         "**IBM ISC Cloud Data for Accenture** — routing through `account_intelligence_agent`\n\n"
         "✅ **IBM watsonx.ai** — Enterprise · 2,500 seats · 74% usage · Renews Dec 31, 2026\n"
         "⚠️ **IBM watsonx.governance** — Professional · 800 seats · 61% usage · **Renews Sep 30, 2026** ← 90-day alert\n"
         "🔺 **IBM Cloud Pak for Data** — Enterprise · 1,200 seats · **88% usage** ← upsell candidate\n"
         "🔺 **IBM Sterling Supply Chain** — Enterprise · 450 seats · **93% usage** ← premium tier candidate\n\n"
         "⚠️ Open tickets: INC0042871 (Sev 2 — DataStage latency), INC0044102 (Sev 3 — rate limits)"
     )),
    (r"exec.*summary|call prep|prep.*call|quick.*summary|before.*call|brief",
     lambda: (
         "**Executive Summary for Accenture** — routing through `account_intelligence_agent`\n\n"
         "**Key Priorities**\n"
         "• EU AI Act compliance — watsonx.governance renewal (Sep 30) is critical path.\n"
         "• 34% AI/cloud budget growth — capital available for expanded watsonx deployment.\n"
         "• New CAO Dr. Priya Nair (IBM advocate) — engage within 2 weeks.\n\n"
         "**Open Opportunities**\n"
         "• watsonx Enterprise Expansion — $8.4M TCV · Proposal · Q3 close\n"
         "• Cloud Pak for Data upgrade — $1.2M · 88% utilisation signal\n"
         "• watsonx.governance renewal + upsell — $2.7M\n\n"
         "**Next Steps**\n"
         "• Schedule intro call with Dr. Priya Nair.\n"
         "• Prepare watsonx.governance renewal proposal.\n"
         "• Escalate Sev 2 ticket INC0042871 before proposal meeting."
     )),
    (r"salesforce|pipeline|crm|deal|opportunit|forecast|open.*deal",
     lambda: (
         "**Salesforce CRM Snapshot** — routing through `ai_agent_launchpad_agent`\n\n"
         "💰 **watsonx Enterprise Expansion** — $8,400,000 · Proposal · Close: Sep 30, 2026 · Best Case\n"
         "💰 **Cloud Pak for Data Upgrade** — $1,200,000 · Needs Analysis · Close: Aug 15, 2026 · Pipeline\n"
         "💰 **watsonx.governance Renewal** — $2,700,000 · Value Proposition · Close: Aug 31, 2026 · Commit\n\n"
         "**Total open pipeline: $12,300,000**\n\nWant me to update a stage or forecast category?"
     )),
    (r"seismic|enablement|sales.*content|presentation",
     lambda: (
         "**Seismic Enablement Content** — routing through `ai_agent_launchpad_agent`\n\n"
         "📄 **IBM watsonx.governance — EU AI Act Compliance Solution Brief** · Solution Brief · 99%\n"
         "📄 **IBM watsonx vs Microsoft Azure OpenAI — Competitive Battlecard** · Battlecard · 95%\n"
         "📄 **Accenture × IBM watsonx Financial Services AI Success Story** · Case Study · 91%\n\n"
         "All content available at ibm.seismic.com."
     )),
    (r"win.*loss|loss.*win|win.*record|lost.*deal|recent.*win",
     lambda: (
         "**Win/Loss Summary for Accenture** — routing through `competitor_analysis_agent`\n\n"
         "✅ **Wins (3):**\n"
         "• IBM Sterling Renewal & Expansion — $4.1M · Feb 2026 · Beat AWS Supply Chain cost pitch\n"
         "• watsonx.ai FS Pilot → Production — $3.2M · Nov 2025 · Beat Google Vertex AI\n"
         "• Cloud Pak for Data Expansion — $1.8M · Aug 2025 · Utilisation-driven, no competitive alternative\n\n"
         "❌ **Losses (2):**\n"
         "• Internal Automation Platform — $2.4M · Jan 2026 · Lost to Microsoft M365 bundled pricing\n"
         "• HR Analytics — $900K · Sep 2025 · Lost to Workday native HR AI\n\n"
         "**Win rate: 60%** — Strong on platform deals; at risk on bundled Microsoft plays."
     )),
    (r"flag.*news|flag.*item|flag.*aws|mark.*important",
     lambda: (
         "✅ News item `news_001` flagged as **Important** — saved to Morning News feed.\n\n"
         "*Routing: `morning_news_agent` → `flag_news_item(news_id='news_001', flag_type='Important')`*"
     )),
    (r"lead|identify.*lead|top.*prospect",
     lambda: (
         "**Lead Identification** — routing through `ai_agent_launchpad_agent`\n\n"
         "🎯 **Dr. Priya Nair** (CAO) — Score: 96 — Decision-maker; watsonx.governance budget owner\n"
         "🎯 **Mark Henderson** (VP Technology, FS) — Score: 84 — Technical champion; EU AI Act lead\n"
         "🎯 **Lisa Tran** (Procurement Lead) — Score: 72 — Renewal authority\n"
         "🎯 **David Osei** (CFO) — Score: 68 — CFO approval needed for $8.4M expansion; re-engage\n"
         "🎯 **Sophie Andersen** (Head of Data & Analytics) — Score: 61 — Cloud Pak upgrade champion"
     )),
    (r"log.*note|meeting note|save.*note",
     lambda: (
         f"✅ Meeting note logged to Salesforce CRM for **mtg_001**.\n"
         f"*Logged by {st.session_state.get('rep','Sarah Mitchell')} on {date.today().strftime('%b %d, %Y')}.*\n\n"
         "*Routing: `meetings_relationships_agent` → `log_meeting_note(meeting_id='mtg_001', note='...')`*"
     )),
    (r"relationship|cfo|coo|cto|contact.*status|engagement",
     lambda: (
         "**Relationship Map for Accenture** — routing through `meetings_relationships_agent`\n\n"
         "🟢 **Dr. Priya Nair** (CAO) — Strong · Last: Jun 4, 2026\n"
         "🟡 **Mark Henderson** (VP Technology, FS) — Moderate · Last: May 14, 2026\n"
         "🟢 **Rachel Park** (Head of Supply Chain) — Strong · Last: Apr 30, 2026\n"
         "🔵 **Lisa Tran** (Procurement Lead) — **Cold** · Last: Feb 10, 2026 ← re-engage\n"
         "🔵 **David Osei** (CFO) — **Cold** · Last: Nov 20, 2025 ← critical to re-engage for $8.4M deal"
     )),
    (r"outreach|draft.*email|email.*draft|write.*email",
     lambda: (
         "**Outreach Email Draft** — routing through `ai_agent_launchpad_agent`\n\n"
         "**To:** Dr. Priya Nair <priya.nair@accenture.com>\n"
         "**Subject:** Continuing Our Conversation — IBM watsonx & EU AI Act Compliance\n\n"
         "Dear Dr. Nair,\n\nI hope this note finds you well. Following our recent discussions, I wanted to reach out personally regarding new IBM watsonx capabilities directly relevant to your EU AI Act compliance timeline.\n\n"
         "IBM watsonx.governance now includes dedicated tools for model explainability, audit trails, and bias detection — built specifically for regulated industries ahead of the Q3 enforcement deadline.\n\n"
         "Would you be available for a 30-minute call the week of June 23rd?\n\nWarm regards,\nSarah Mitchell · IBM GAE\n\n"
         "*⚡ Powered by IBM Client Outreach AI Agent (Salesforce + Seismic)*"
     )),
    (r"update.*crm|update.*salesforce|change.*stage|set.*stage",
     lambda: (
         f"✅ Salesforce updated — `SF-OPP-20240801` · `Stage` → **Proposal** · "
         f"{date.today().strftime('%b %d, %Y')} · {st.session_state.get('rep','Sarah Mitchell')}\n\n"
         "*Routing: `ai_agent_launchpad_agent` → `update_crm_record(record_id='SF-OPP-20240801', field='Stage', value='Proposal')`*"
     )),
    (r"research|brief|d.?b|dun.*bradstreet|firmograph",
     lambda: (
         "**Sales Research Brief for Accenture** — routing through `ai_agent_launchpad_agent`\n\n"
         "Accenture is a $64.9B global technology consulting leader (ACN, NYSE). IBM is one of their top 3 enterprise AI partners.\n\n"
         "**Top Signals:**\n"
         "• New CAO appointment — strong IBM watsonx advocate\n"
         "• EU AI Act urgency — watsonx.governance renewal is critical path\n"
         "• AWS $3B partnership — competitive pressure on IBM Cloud\n"
         "• Q2 AI/cloud budget +34% YoY — capital available for IBM expansion\n\n"
         "**D&B Profile:** Revenue $64.9B · Credit AA · 774,000 employees · HQ: Dublin, Ireland"
     )),
]

SAMPLE_QUESTIONS = [
    "What's new with this account this week?",
    "Do I have any meetings with this account this month?",
    "Who are IBM's biggest competitors at this account right now?",
    "Draft an outreach email about watsonx.governance.",
    "What IBM products does this account currently have active?",
    "Give me a quick exec summary before my call today.",
    "What deals do we have open in Salesforce for this account?",
    "Find me the latest Seismic content on IBM Cloud Pak for Data.",
    "What is our win/loss record at this account over the last year?",
    "Flag the top news item as important.",
    "Log a meeting note: discussed watsonx renewal timeline, decision by end of Q3.",
    "What's the relationship status with the CFO?",
    "Give me a competitive battlecard against Microsoft.",
    "Update the Salesforce opportunity stage to Proposal for the watsonx deal.",
    "What leads have been identified at this account?",
]


def bob_respond(message: str) -> str:
    """Route message through account-aware mock responses and return response."""
    import re

    account = st.session_state.account
    client_name = profile["client_name"]
    client_email = profile["client_email"]
    total_pipeline = sum(int(o["amount"].replace("$", "").replace(",", "")) for o in crm_opps)
    top_competitor = competitors[0]
    top_lead = leads[0]
    top_news = news_items[0]
    primary_meeting = upcoming_meetings[0]
    top_opp = crm_opps[0]
    primary_relationship = relationship_map[0]
    primary_ticket = tickets[0]
    primary_seismic = seismic_content[0]

    routes = [
        (r"what'?s new|news|press release|announcement|this week",
         lambda: (
             f"**Morning News for {account}** — routing through `morning_news_agent`\n\n"
             f"{top_news['tag']} — **{top_news['title']}** *({top_news['source']}, {top_news['date']})*\n"
             f"{news_items[1]['tag']} — **{news_items[1]['title']}** *({news_items[1]['source']}, {news_items[1]['date']})*\n"
             f"{news_items[2]['tag']} — **{news_items[2]['title']}** *({news_items[2]['source']}, {news_items[2]['date']})*\n\n"
             f"💡 Want me to flag the {top_competitor['name']} news as important, or pull a competitive battlecard?"
         )),
        (r"meeting|calendar|upcoming|scheduled|this month",
         lambda: (
             "**Upcoming Meetings** — routing through `meetings_relationships_agent`\n\n"
             f"📅 **{primary_meeting['date']}** — {primary_meeting['title']} · {primary_meeting['time']} · {primary_meeting['status']}\n"
             f"📅 **{upcoming_meetings[-1]['date']}** — {upcoming_meetings[-1]['title']} · {upcoming_meetings[-1]['time']} · {upcoming_meetings[-1]['status']}\n\n"
             "Shall I help draft a prep brief for the next client meeting?"
         )),
        (r"competitor|competition|vs |versus|competitive landscape|biggest.*risk",
         lambda: (
             f"**Active Competitors at {account}** — routing through `competitor_analysis_agent`\n\n"
             + "\n".join(
                 [f"{c['status']} **{c['name']}** ({c['deal_value']}) — {c['products']}" for c in competitors]
             )
             + "\n\n💡 Ask: *\"Give me a battlecard against Microsoft\"* to open the full battlecard."
         )),
        (r"battlecard|talking point|differentiator",
         lambda: (
             "**IBM vs Microsoft Battlecard** — routing through `competitor_analysis_agent`\n\n"
             "**IBM Differentiators:**\n"
             + "\n".join([f"• {d}" for d in battlecards["Microsoft"]["differentiators"][:3]])
             + "\n\n**Key Talking Point:** *Position IBM governance, hybrid deployment, and open-model flexibility against Microsoft.*"
         )),
        (r"ibm product|active product|license|isc cloud|renewal|sterling|watsonx\.ai|cloud pak",
         lambda: (
             f"**IBM ISC Cloud Data for {account}** — routing through `account_intelligence_agent`\n\n"
             + "\n".join(
                 [f"{'⚠️' if p['alert'] else '✅'} **{p['product']}** — {p['tier']} · {p['seats']:,} seats · {p['usage']} usage · Renews {p['renewal']}" for p in products]
             )
             + f"\n\n⚠️ Open tickets: {primary_ticket['id']} ({primary_ticket['sev']}), {tickets[-1]['id']} ({tickets[-1]['sev']})"
         )),
        (r"exec.*summary|call prep|prep.*call|quick.*summary|before.*call|brief",
         lambda: (
             f"**Executive Summary for {account}** — routing through `account_intelligence_agent`\n\n"
             "**Key Priorities**\n"
             f"• Advance {top_opp['name']} toward close.\n"
             f"• Maintain momentum with {client_name} and the wider buying group.\n"
             f"• Resolve support issue {primary_ticket['id']} before the next review.\n\n"
             "**Open Opportunities**\n"
             + "\n".join([f"• {o['name']} — {o['amount']} · {o['stage']} · Close: {o['close']}" for o in crm_opps])
         )),
        (r"salesforce|pipeline|crm|deal|opportunit|forecast|open.*deal",
         lambda: (
             "**Salesforce CRM Snapshot** — routing through `ai_agent_launchpad_agent`\n\n"
             + "\n".join([f"💰 **{o['name']}** — {o['amount']} · {o['stage']} · Close: {o['close']} · {o['forecast']}" for o in crm_opps])
             + f"\n\n**Total open pipeline: ${total_pipeline:,.0f}**"
         )),
        (r"seismic|enablement|sales.*content|presentation",
         lambda: (
             "**Seismic Enablement Content** — routing through `ai_agent_launchpad_agent`\n\n"
             + "\n".join([f"📄 **{item['title']}** · {item['type']} · {item['relevance']}" for item in seismic_content])
         )),
        (r"win.*loss|loss.*win|win.*record|lost.*deal|recent.*win",
         lambda: (
             f"**Win/Loss Summary for {account}** — routing through `competitor_analysis_agent`\n\n"
             f"Current mock outlook: IBM is well positioned in {top_opp['name']} and defending against {top_competitor['name']}.\n"
             "Win themes: governance, hybrid AI, and platform integration.\n"
             "Risk themes: bundled hyperscaler pricing and existing cloud footprint."
         )),
        (r"flag.*news|flag.*item|flag.*aws|mark.*important",
         lambda: (
             f"✅ News item `{top_news['id']}` flagged as **Important** — saved to Morning News feed.\n\n"
             f"*Routing: `morning_news_agent` → `flag_news_item(news_id='{top_news['id']}', flag_type='Important')`*"
         )),
        (r"lead|identify.*lead|top.*prospect",
         lambda: (
             "**Lead Identification** — routing through `ai_agent_launchpad_agent`\n\n"
             + "\n".join([f"🎯 **{lead['name']}** ({lead['title']}) — Score: {lead['score']} — {lead['reason']}" for lead in leads])
         )),
        (r"log.*note|meeting note|save.*note",
         lambda: (
             f"✅ Meeting note logged to Salesforce CRM for **{primary_meeting['id']}**.\n"
             f"*Logged by {st.session_state.get('rep','Sarah Mitchell')} on {date.today().strftime('%b %d, %Y')}.*\n\n"
             f"*Routing: `meetings_relationships_agent` → `log_meeting_note(meeting_id='{primary_meeting['id']}', note='...')`*"
         )),
        (r"relationship|cfo|coo|cto|contact.*status|engagement",
         lambda: (
             f"**Relationship Map for {account}** — routing through `meetings_relationships_agent`\n\n"
             + "\n".join([f"{r['engagement']} **{r['contact']}** ({r['title']}) — Last: {r['last']}" for r in relationship_map])
         )),
        (r"outreach|draft.*email|email.*draft|write.*email",
         lambda: (
             "**Outreach Email Draft** — routing through `ai_agent_launchpad_agent`\n\n"
             f"**To:** {client_name} <{client_email}>\n"
             "**Subject:** Continuing Our Conversation — IBM watsonx & EU AI Act Compliance\n\n"
             f"Dear {client_name},\n\n"
             f"I wanted to follow up on IBM's latest watsonx capabilities and how they align to {account}'s current AI and governance priorities.\n\n"
             "Would you be available for a 30-minute call next week?\n\n"
             f"Warm regards,\n{st.session_state.get('rep','Sarah Mitchell')} · IBM GAE"
         )),
        (r"update.*crm|update.*salesforce|change.*stage|set.*stage",
         lambda: (
             f"✅ Salesforce updated — `{top_opp['id']}` · `Stage` → **Proposal** · {date.today().strftime('%b %d, %Y')} · {st.session_state.get('rep','Sarah Mitchell')}\n\n"
             f"*Routing: `ai_agent_launchpad_agent` → `update_crm_record(record_id='{top_opp['id']}', field='Stage', value='Proposal')`*"
         )),
        (r"research|brief|d.?b|dun.*bradstreet|firmograph",
         lambda: (
             f"**Sales Research Brief for {account}** — routing through `ai_agent_launchpad_agent`\n\n"
             f"{account} is a major global services organization. IBM is an active enterprise AI and data platform partner.\n\n"
             "**Top Signals:**\n"
             f"• Executive sponsor: {client_name}\n"
             f"• Primary opportunity: {top_opp['name']}\n"
             f"• Top competitor: {top_competitor['name']}\n"
             f"• D&B Profile: Revenue {profile['revenue']} · {profile['ticker']} · {profile['employees']} employees · HQ: {profile['hq']}"
         )),
    ]

    for pattern, fn in routes:
        if re.search(pattern, message, re.IGNORECASE):
            return fn()
    return (
        f"I'm Bob, routing through `sales_hub_orchestrator_agent` for **{account}**.\n\n"
        "I didn't match a specific route for that question. Try one of the sample questions below, "
        "or ask about: news, meetings, competitors, battlecards, IBM products, exec summary, "
        "Salesforce pipeline, leads, outreach emails, Seismic content, win/loss, or relationships."
    )


# ─────────────────────────────────────────────────────────────
# LOGIN SCREEN
# ─────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c:
        st.markdown("### **IBM**")
        st.markdown("## IBM Sales Intelligence Hub")
        st.markdown("*Powered by IBM watsonx Orchestrate*")
        st.divider()
        rep = st.text_input("Your Name", value="Sarah Mitchell", key="login_rep")
        account = st.selectbox("Account", ["Accenture", "Deloitte", "PwC", "EY", "KPMG"], key="login_account")
        if st.button("Launch Dashboard →", use_container_width=True):
            st.session_state.logged_in = True
            st.session_state.rep = rep or "Sarah Mitchell"
            st.session_state.account = account
            st.session_state.chat_history = [{
                "role": "bob",
                "content": (
                    f"Good morning, {(rep or 'Sarah').split()[0]}. I'm Bob, your IBM Sales Intelligence assistant — "
                    f"routing through the `sales_hub_orchestrator_agent`. I'm loaded with everything on **{account}**: "
                    "news, meetings, pipeline, competitive intel, and more. What do you need today?"
                )
            }]
            st.rerun()
    st.stop()

# ─────────────────────────────────────────────────────────────
# MAIN DASHBOARD
# ─────────────────────────────────────────────────────────────
rep = st.session_state.rep
account = st.session_state.account

company_profile = {
    "Accenture": {"legal_name": "Accenture plc", "hq": "Dublin, Ireland", "revenue": "$64.9B (FY2025)", "employees": "774,000", "industry": "Financial Services / Technology Consulting", "ibm_tier": "Global Strategic Partner", "sales_stage": "Active Expansion", "alliance_manager": "Michael Obi, Global IBM Alliance Lead", "joint_revenue": "$420M co-sell influenced", "ticker": "ACN (NYSE) · Credit: AA", "client_name": "Dr. Priya Nair", "client_email": "priya.nair@accenture.com"},
    "Deloitte": {"legal_name": "Deloitte Touche Tohmatsu Limited", "hq": "London, United Kingdom", "revenue": "$67.2B (FY2025)", "employees": "457,000", "industry": "Professional Services / Consulting", "ibm_tier": "Global Strategic Partner", "sales_stage": "Expansion Planning", "alliance_manager": "Emma Collins, Global IBM Alliance Director", "joint_revenue": "$310M co-sell influenced", "ticker": "Private · Credit: AA", "client_name": "Avery Cole", "client_email": "avery.cole@deloitte.com"},
    "PwC": {"legal_name": "PricewaterhouseCoopers International Limited", "hq": "London, United Kingdom", "revenue": "$55.4B (FY2025)", "employees": "364,000", "industry": "Professional Services / Advisory", "ibm_tier": "Global Strategic Partner", "sales_stage": "Active Renewal", "alliance_manager": "Nina Patel, Global IBM Alliance Lead", "joint_revenue": "$275M co-sell influenced", "ticker": "Private · Credit: AA-", "client_name": "Maya Shah", "client_email": "maya.shah@pwc.com"},
    "EY": {"legal_name": "Ernst & Young Global Limited", "hq": "London, United Kingdom", "revenue": "$51.0B (FY2025)", "employees": "395,000", "industry": "Professional Services / Assurance & Consulting", "ibm_tier": "Strategic Partner", "sales_stage": "Pipeline Build", "alliance_manager": "Daniel Reeves, IBM Alliance Sponsor", "joint_revenue": "$230M co-sell influenced", "ticker": "Private · Credit: A+", "client_name": "Leah Morgan", "client_email": "leah.morgan@ey.com"},
    "KPMG": {"legal_name": "KPMG International Limited", "hq": "Amstelveen, Netherlands", "revenue": "$38.4B (FY2025)", "employees": "273,000", "industry": "Professional Services / Audit & Advisory", "ibm_tier": "Strategic Partner", "sales_stage": "Opportunity Development", "alliance_manager": "Owen Brooks, IBM Alliance Director", "joint_revenue": "$190M co-sell influenced", "ticker": "Private · Credit: A", "client_name": "Noah Bennett", "client_email": "noah.bennett@kpmg.com"},
}
profile = company_profile[account]

if account == "Accenture":
    news_items = NEWS_ITEMS
    products = PRODUCTS
    tickets = TICKETS
    competitors = COMPETITORS
    battlecards = BATTLECARDS
    upcoming_meetings = UPCOMING_MEETINGS
    meeting_history = MEETING_HISTORY
    relationship_map = RELATIONSHIP_MAP
    crm_opps = CRM_OPPS
    leads = LEADS
    seismic_content = SEISMIC_CONTENT
else:
    news_items = [
        {
            "id": f"{account.lower()}_news_001",
            "tag": "🟢 Opportunity",
            "title": f"{account} expands enterprise AI modernization program with governance requirements",
            "source": "Bloomberg",
            "date": "Jun 11, 2026",
            "summary": f"{account} is increasing AI platform investment, creating near-term expansion potential for IBM watsonx and governance offerings.",
        },
        {
            "id": f"{account.lower()}_news_002",
            "tag": "🟡 Executive Change",
            "title": f"{account} appoints new global data and AI transformation lead",
            "source": "Reuters",
            "date": "Jun 8, 2026",
            "summary": f"The new executive sponsor at {account} is expected to review strategic AI vendors and compliance tooling this quarter.",
        },
        {
            "id": f"{account.lower()}_news_003",
            "tag": "🔴 Competitor Move",
            "title": f"Microsoft and {account} deepen Copilot and Azure AI collaboration",
            "source": "TechCrunch",
            "date": "Jun 3, 2026",
            "summary": f"Microsoft is strengthening its AI footprint at {account}, increasing competitive pressure on IBM platform expansion deals.",
        },
    ]
    products = [
        {"product": "IBM watsonx.ai", "tier": "Enterprise", "seats": 1800, "usage": "68%", "renewal": "Nov 30, 2026", "alert": False},
        {"product": "IBM watsonx.governance", "tier": "Professional", "seats": 600, "usage": "57%", "renewal": "Oct 15, 2026", "alert": True},
        {"product": "IBM Cloud Pak for Data", "tier": "Enterprise", "seats": 950, "usage": "82%", "renewal": "Feb 28, 2027", "alert": False},
        {"product": "IBM Instana Observability", "tier": "Standard", "seats": 260, "usage": "49%", "renewal": "Apr 15, 2027", "alert": False},
    ]
    tickets = [
        {"id": "INC0051201", "sev": "Sev 2", "title": f"watsonx.ai model pipeline latency affecting {account} analytics workloads", "status": "In Progress"},
        {"id": "INC0051884", "sev": "Sev 3", "title": f"Cloud Pak for Data access provisioning delays for {account} delivery teams", "status": "Pending"},
    ]
    competitors = [
        {"name": "Microsoft", "products": "Azure OpenAI, Copilot, Fabric", "status": "⚠️ At Risk", "deal_value": "$4.8M"},
        {"name": "AWS", "products": "Bedrock, SageMaker, Redshift", "status": "🟡 Even", "deal_value": "$3.4M"},
        {"name": "Google Cloud", "products": "Vertex AI, BigQuery, Gemini", "status": "🟡 Even", "deal_value": "$2.2M"},
        {"name": "Salesforce", "products": "Einstein AI, Data Cloud", "status": "✅ Advantaged", "deal_value": "$1.1M"},
    ]
    battlecards = deepcopy(BATTLECARDS)
    upcoming_meetings = [
        {"id": "mtg_101", "date": "Jun 19, 2026", "time": "3:00 PM UTC", "title": f"{account} watsonx expansion review", "status": "⚠️ Needs Prep", "ibm": [rep, "James Okonkwo"], "client": [f"{account} AI Lead", f"{account} CIO Office"]},
        {"id": "mtg_102", "date": "Jun 24, 2026", "time": "11:00 AM UTC", "title": f"{account} governance renewal planning", "status": "✅ Prep Complete", "ibm": [rep, "Anita Rowe"], "client": [f"{account} Risk Office", f"{account} Procurement"]},
    ]
    meeting_history = [
        {"date": "Jun 6, 2026", "title": f"{account} AI platform business review", "attendees": f"{account} AI Leadership", "outcome": "Expansion interest confirmed; technical validation requested."},
        {"date": "May 21, 2026", "title": "Cloud Pak for Data adoption review", "attendees": f"{account} Data Platform Team", "outcome": "High usage trends identified; capacity increase under discussion."},
    ]
    relationship_map = [
        {"contact": f"{account} Chief AI Officer", "title": "Chief AI Officer", "ibm_owner": rep, "engagement": "🟢 Strong", "last": "Jun 6, 2026"},
        {"contact": f"{account} CIO", "title": "Chief Information Officer", "ibm_owner": "James Okonkwo", "engagement": "🟡 Moderate", "last": "May 21, 2026"},
        {"contact": f"{account} Procurement Lead", "title": "Procurement Lead", "ibm_owner": rep, "engagement": "🔵 Cold", "last": "Mar 12, 2026"},
    ]
    crm_opps = [
        {"id": "SF-OPP-90001", "name": f"{account} watsonx expansion", "stage": "Proposal", "amount": "$5,600,000", "close": "Sep 30, 2026", "forecast": "Best Case"},
        {"id": "SF-OPP-90002", "name": f"{account} watsonx.governance renewal", "stage": "Value Prop", "amount": "$1,900,000", "close": "Aug 28, 2026", "forecast": "Commit"},
    ]
    leads = [
        {"name": f"{account} Chief AI Officer", "title": "Chief AI Officer", "dept": "AI Office", "score": 94, "reason": "Executive sponsor for enterprise AI platform decisions"},
        {"name": f"{account} Head of Data Platforms", "title": "Head of Data Platforms", "dept": "Technology", "score": 82, "reason": "Likely technical approver for platform expansion"},
        {"name": f"{account} Procurement Lead", "title": "Procurement Lead", "dept": "Procurement", "score": 71, "reason": "Commercial approver for renewals and expansion deals"},
    ]
    seismic_content = [
        {"title": f"IBM watsonx value story for {account}", "type": "Account Brief", "relevance": "97%"},
        {"title": "IBM vs Microsoft Azure OpenAI battlecard", "type": "Battlecard", "relevance": "94%"},
        {"title": "watsonx.governance compliance solution brief", "type": "Solution Brief", "relevance": "92%"},
    ]

# ── Sidebar ──
with st.sidebar:
    st.markdown(f"### **IBM** Sales Hub")
    st.markdown(f"**{rep}**  |  IBM GAE")
    st.markdown(f"<span class='tag-blue'>Account: {account}</span>", unsafe_allow_html=True)
    st.divider()
    tab = st.radio(
        "Navigation",
        ["🌅 Morning News", "🏢 Account Overview", "📝 Exec Summary",
         "⚔️ Competitor Analysis", "📅 Meetings & Relationships",
         "🤝 IBM Partnerships", "🚀 AI Agent Launchpad", "💬 Ask Bob"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption(f"Today: {date.today().strftime('%B %d, %Y')}")
    if st.button("← Log Out", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# ─────────────────────────────────────────────────────────────
# TAB: MORNING NEWS
# ─────────────────────────────────────────────────────────────
if tab == "🌅 Morning News":
    st.header(f"Morning News — {account}")
    st.caption("Latest signals relevant to your account. Flag items to keep or dismiss.")
    for item in news_items:
        flagged = st.session_state.flagged_news.get(item["id"], "")
        border = "border-left: 3px solid #FA4D56;" if "🔴" in item["tag"] else \
                 "border-left: 3px solid #F1C21B;" if "🟡" in item["tag"] else \
                 "border-left: 3px solid #42BE65;"
        opacity = "opacity:0.4;" if flagged == "Dismiss" else ""
        st.markdown(
            f'<div style="background:#262626;{border}{opacity}padding:14px 16px;margin-bottom:10px;border-radius:2px;">'
            f'<div style="font-size:11px;font-weight:700;color:#A8A8A8;margin-bottom:4px;">{item["tag"]} &nbsp;·&nbsp; {item["source"]} &nbsp;·&nbsp; {item["date"]}</div>'
            f'<div style="font-weight:600;margin-bottom:4px;">{item["title"]}</div>'
            f'<div style="font-size:13px;color:#A8A8A8;">{item["summary"]}</div>'
            f'</div>', unsafe_allow_html=True,
        )
        c1, c2, c3, _ = st.columns([1, 1.3, 1, 4])
        with c1:
            if st.button("⭐ Important", key=f"imp_{item['id']}", use_container_width=True):
                st.session_state.flagged_news[item["id"]] = "Important"
                st.toast(f"✅ '{item['id']}' flagged as Important", icon="✅")
                st.rerun()
        with c2:
            if st.button("📤 Share with Team", key=f"share_{item['id']}", use_container_width=True):
                st.toast(f"📤 '{item['id']}' shared with team", icon="📤")
        with c3:
            if st.button("✕ Dismiss", key=f"dis_{item['id']}", use_container_width=True):
                st.session_state.flagged_news[item["id"]] = "Dismiss"
                st.rerun()
        st.divider()

# ─────────────────────────────────────────────────────────────
# TAB: ACCOUNT OVERVIEW
# ─────────────────────────────────────────────────────────────
elif tab == "🏢 Account Overview":
    st.header(f"Account Overview — {account}")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Company Profile")
        st.markdown(f"""
| | |
|---|---|
| **Name** | {profile["legal_name"]} |
| **Industry** | {profile["industry"]} |
| **HQ** | {profile["hq"]} |
| **Revenue** | {profile["revenue"]} |
| **Employees** | {profile["employees"]} |
| **IBM Tier** | {profile["ibm_tier"]} |
| **IBM Owner** | {rep} (GAE) |
| **Sales Stage** | {profile["sales_stage"]} |
""")
    with col2:
        st.subheader("IBM ISC Cloud — Active Products")
        for p in products:
            alert_str = " 🚨 90-day renewal alert" if p["alert"] else ""
            upsell = " 🔺 upsell candidate" if int(p["usage"].replace("%","")) >= 85 else ""
            st.markdown(
                f'<div style="background:#262626;border:1px solid #525252;padding:10px 14px;margin-bottom:6px;border-radius:2px;">'
                f'<strong>{p["product"]}</strong> &nbsp;<span class="tag-blue">{p["tier"]}</span>'
                f'{"&nbsp;<span class=\"tag-red\">⚠️ Renewal Alert</span>" if p["alert"] else ""}'
                f'<div style="font-size:12px;color:#A8A8A8;margin-top:4px;">'
                f'{p["seats"]:,} seats &nbsp;·&nbsp; {p["usage"]} usage{upsell} &nbsp;·&nbsp; Renews {p["renewal"]}{alert_str}'
                f'</div></div>',
                unsafe_allow_html=True,
            )
    st.subheader("Open Support Tickets")
    for t in tickets:
        color = "#FA4D56" if "Sev 2" in t["sev"] else "#F1C21B" if "Sev 3" in t["sev"] else "#42BE65"
        st.markdown(
            f'<div style="background:#262626;border-left:3px solid {color};padding:10px 14px;margin-bottom:6px;border-radius:2px;">'
            f'<span style="color:{color};font-weight:700;">{t["sev"]}</span> &nbsp;·&nbsp; <strong>{t["id"]}</strong>'
            f'<div style="font-size:13px;color:#A8A8A8;margin-top:2px;">{t["title"]} &nbsp;·&nbsp; {t["status"]}</div>'
            f'</div>', unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────
# TAB: EXEC SUMMARY
# ─────────────────────────────────────────────────────────────
elif tab == "📝 Exec Summary":
    st.header(f"Executive Summary — {account}")
    st.caption(f"Prepared for {rep} · {date.today().strftime('%B %d, %Y')}")
    exec_content = f"""
**Account:** {account} plc  ·  **Rep:** {rep}  ·  **Date:** {date.today().strftime('%B %d, %Y')}

---
**Key Priorities**
- EU AI Act compliance — watsonx.governance renewal (Sep 30) is critical path.
- AI and data modernization budget remains active — {account} has room to expand watsonx enterprise deployment.
- Re-engage executive sponsor {profile["client_name"]} within 2 weeks to progress current IBM priorities.

**Recent Wins**
- IBM Sterling Renewal & Expansion — $4.1M · Feb 2026 · Beat AWS cost pitch
- watsonx.ai FS Pilot → Production — $3.2M · Nov 2025 · Beat Google Vertex AI

**Open Opportunities**
- watsonx Enterprise Expansion — $8.4M TCV · Proposal · Q3 close target
- Cloud Pak for Data upgrade — $1.2M · 88% utilisation signal → upsell
- watsonx.governance renewal + upsell — $2.7M · Commit · Aug 31

**Next Steps**
1. Schedule an executive check-in with {profile["client_name"]} within 2 weeks.
2. Prepare and send the watsonx.governance renewal proposal.
3. Resolve the highest-priority open support issue before the next client review.
4. Re-engage procurement and finance stakeholders ahead of the expansion close date.
"""
    st.markdown(exec_content)
    if st.button("⎘ Copy to Clipboard"):
        st.toast("✅ Executive summary copied to clipboard.", icon="✅")

# ─────────────────────────────────────────────────────────────
# TAB: COMPETITOR ANALYSIS
# ─────────────────────────────────────────────────────────────
elif tab == "⚔️ Competitor Analysis":
    st.header(f"Competitor Analysis — {account}")
    for comp in competitors:
        st.markdown(
            f'<div style="background:#262626;border:1px solid #525252;padding:14px 16px;margin-bottom:8px;border-radius:2px;">'
            f'<span style="font-size:16px;font-weight:700;">{comp["name"]}</span> &nbsp; {comp["status"]} &nbsp; '
            f'<span style="font-size:12px;color:#A8A8A8;">Deal at risk: {comp["deal_value"]}</span>'
            f'<div style="font-size:12px;color:#A8A8A8;margin-top:4px;">Products: {comp["products"]}</div>'
            f'</div>', unsafe_allow_html=True,
        )
        with st.expander(f"📋 View Battlecard — IBM vs {comp['name']}"):
            card = battlecards[comp["name"]]
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**IBM Differentiators**")
                for d in card["differentiators"]:
                    st.markdown(f"• {d}")
                st.markdown("**IBM Products to Position**")
                st.markdown("  ".join(
                    [f'<span class="tag-blue">{p}</span>' for p in card["products"]]
                ), unsafe_allow_html=True)
            with c2:
                st.markdown("**Competitor Weaknesses**")
                for w in card["weaknesses"]:
                    st.markdown(f"• {w}")
                st.markdown("**Suggested Talking Points**")
                for t in card["talking_points"]:
                    st.markdown(f"💬 *{t}*")

# ─────────────────────────────────────────────────────────────
# TAB: MEETINGS & RELATIONSHIPS
# ─────────────────────────────────────────────────────────────
elif tab == "📅 Meetings & Relationships":
    st.header(f"Meetings & Relationships — {account}")
    st.subheader("Upcoming Meetings")
    for m in upcoming_meetings:
        st.markdown(
            f'<div style="background:#262626;border:1px solid #525252;padding:14px 16px;margin-bottom:8px;border-radius:2px;">'
            f'<div style="font-weight:700;font-size:15px;">{m["title"]}</div>'
            f'<div style="font-size:12px;color:#A8A8A8;margin-top:3px;">📅 {m["date"]} · {m["time"]} &nbsp;·&nbsp; {m["status"]}</div>'
            f'<div style="font-size:12px;margin-top:6px;"><strong>IBM:</strong> {", ".join(m["ibm"])}</div>'
            f'<div style="font-size:12px;"><strong>Client:</strong> {", ".join(m["client"])}</div>'
            f'</div>', unsafe_allow_html=True,
        )
        note_key = f"note_{m['id']}"
        note_val = st.text_input(f"Log note for {m['id']}", placeholder="Type a meeting note to save to Salesforce CRM…", key=note_key, label_visibility="collapsed")
        if st.button(f"💾 Save Note — {m['id']}", key=f"savenote_{m['id']}"):
            if note_val.strip():
                st.toast(f"✅ Note saved to Salesforce CRM for {m['id']} — logged by {rep} on {date.today().strftime('%b %d, %Y')}", icon="✅")
            else:
                st.toast("⚠️ Please enter a note before saving.", icon="⚠️")

    st.divider()
    st.subheader("Meeting History (Last 5)")
    import pandas as pd
    st.dataframe(
        pd.DataFrame(meeting_history).rename(columns={"date":"Date","title":"Meeting","attendees":"Key Attendees","outcome":"Outcome"}),
        use_container_width=True, hide_index=True,
    )
    st.divider()
    st.subheader("Relationship Map")
    st.dataframe(
        pd.DataFrame(relationship_map).rename(columns={"contact":"Contact","title":"Title","ibm_owner":"IBM Owner","engagement":"Engagement","last":"Last Interaction"}),
        use_container_width=True, hide_index=True,
    )

# ─────────────────────────────────────────────────────────────
# TAB: IBM PARTNERSHIPS
# ─────────────────────────────────────────────────────────────
elif tab == "🤝 IBM Partnerships":
    st.header(f"IBM Partnerships & Relationships — {account}")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Strategic Alliance Overview")
        st.markdown(f"""
| | |
|---|---|
| **Partnership Level** | IBM Platinum Partner |
| **Since** | 2004 |
| **Joint Revenue FY25** | {profile["joint_revenue"]} |
| **Active Programmes** | IBM ESA · IBM Build Partner · watsonx Co-sell |
| **IBM Alliance Manager** | {rep} |
| **{account} Alliance Manager** | {profile["alliance_manager"]} |
""")
    with col2:
        st.subheader("Active Joint Programmes")
        st.markdown(f"""
- **IBM–{account} watsonx Centre of Excellence** — Joint delivery capability for enterprise AI at scale.
- **IBM Cloud Pak for Data Delivery Practice** — Dedicated {account} consultants IBM-certified on Cloud Pak for Data.
- **IBM Sterling Supply Chain CoE** — Joint implementation support for enterprise transformation programmes.
- **EU AI Act Compliance Accelerator** — Joint GTM programme launching Q3 2026.
""")
    st.divider()
    st.subheader(f"IBM Certifications Held by {account} Staff")
    import pandas as pd
    certs = [
        {"Certification": "IBM watsonx.ai Technical Sales",    "Certified Staff": 128, "Status": "Current"},
        {"Certification": "IBM Cloud Pak for Data",             "Certified Staff": 340, "Status": "Current"},
        {"Certification": "IBM Sterling Supply Chain",          "Certified Staff": 95,  "Status": "Current"},
        {"Certification": "IBM watsonx.governance",             "Certified Staff": 42,  "Status": "Renewal Due Q3"},
        {"Certification": "IBM Cloud Architect",                "Certified Staff": 210, "Status": "Current"},
    ]
    st.dataframe(pd.DataFrame(certs), use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────────────────────
# TAB: AI AGENT LAUNCHPAD
# ─────────────────────────────────────────────────────────────
elif tab == "🚀 AI Agent Launchpad":
    st.header("AI Agent Launchpad")
    st.caption(f"Pre-built IBM Sales AI Agents — expand any card to run the agent for {account}.")

    import pandas as pd

    with st.expander("🎯 Lead Identification"):
        st.markdown(f"Top leads within **{account}** scored by title, department, and deal relevance.")
        st.dataframe(pd.DataFrame(leads).rename(columns={"name":"Contact","title":"Title","dept":"Department","score":"Score","reason":"Reason"}), use_container_width=True, hide_index=True)

    with st.expander("✉️ Client Outreach Draft"):
        st.markdown(f"AI-generated personalised outreach email for **{profile['client_name']}** about watsonx.governance.")
        st.code(f"""To: {profile['client_name']} <{profile['client_email']}>
Subject: Continuing Our Conversation — IBM watsonx & EU AI Act Compliance

Dear {profile['client_name']},

I hope this note finds you well. Following our recent discussions, I wanted to reach out
personally regarding new IBM watsonx capabilities directly relevant to your EU AI Act
compliance timeline.

IBM watsonx.governance now includes dedicated tools for model explainability, audit trails,
and bias detection — built specifically for regulated industries ahead of the Q3 enforcement
deadline.

Would you be available for a 30-minute call the week of June 23rd?

Warm regards,
Sarah Mitchell · IBM GAE

⚡ Powered by IBM Client Outreach AI Agent (Salesforce + Seismic)""", language="text")

    with st.expander("🔍 Client Search (D&B)"):
        st.markdown("Enriched firmographic, technographic, and contact data from Dun & Bradstreet.")
        st.markdown(f"""
| | |
|---|---|
| **Revenue** | {profile["revenue"]} |
| **Ticker** | {profile["ticker"]} |
| **Cloud** | Azure · AWS · GCP · IBM Cloud |
| **AI Platforms** | IBM watsonx · Azure OpenAI · Vertex AI |
| **CRM / ERP** | Salesforce · SAP S/4HANA |
| **Employees** | {profile["employees"]} |
| **HQ** | {profile["hq"]} |
""")

    with st.expander("📊 CRM Snapshot (Salesforce)"):
        st.markdown("Open Salesforce opportunities, stages, and forecast.")
        st.dataframe(
            pd.DataFrame(crm_opps)[["name","stage","amount","close","forecast"]].rename(
                columns={"name":"Opportunity","stage":"Stage","amount":"Amount","close":"Close Date","forecast":"Forecast"}
            ),
            use_container_width=True, hide_index=True,
        )
        total_pipeline = sum(int(o["amount"].replace("$", "").replace(",", "")) for o in crm_opps)
        st.markdown(f"**Total Pipeline: ${total_pipeline:,.0f}**")

    with st.expander("✏️ Update CRM Record"):
        st.markdown("Update a Salesforce opportunity field directly.")
        opp_map = {o["name"]: o["id"] for o in crm_opps}
        sel_opp  = st.selectbox("Opportunity", list(opp_map.keys()), key="crm_opp")
        sel_field = st.selectbox("Field", ["Stage", "Forecast_Category", "Close_Date"], key="crm_field")
        new_val   = st.text_input("New Value", placeholder="e.g. Proposal, Commit, 2026-09-30", key="crm_val")
        if st.button("Update Salesforce Record", key="crm_submit"):
            if new_val.strip():
                st.toast(f"✅ Salesforce updated — {opp_map[sel_opp]} · {sel_field} → \"{new_val}\" · {date.today().strftime('%b %d, %Y')} · {rep}", icon="✅")
            else:
                st.toast("⚠️ Please enter a new value before updating.", icon="⚠️")

    with st.expander("📚 Seismic Content"):
        st.markdown("Top Seismic enablement content recommendations.")
        for item in seismic_content:
            st.markdown(f"📄 **{item['title']}**  \n*{item['type']} · Relevance: {item['relevance']}*")
            st.divider()

    with st.expander("🧠 Sales Research Brief"):
        st.markdown(f"""
**{account}** is a major global services and consulting organization. IBM remains a strategic enterprise AI and data platform partner with active watsonx, Cloud Pak for Data, and automation opportunities.

**Top Signals:**
- 🟡 Executive sponsorship is active and should be re-engaged this quarter.
- 🔴 Governance and renewal timing remain the main near-term priorities.
- 🔴 Competitive pressure from hyperscalers remains present across AI platform decisions.
- 🟢 Expansion potential exists across watsonx, data, and observability workloads.
""")

# ─────────────────────────────────────────────────────────────
# TAB: ASK BOB
# ─────────────────────────────────────────────────────────────
elif tab == "💬 Ask Bob":
    st.header("Ask Bob — AI Chatbot")
    st.caption("Powered by IBM watsonx Orchestrate · `sales_hub_orchestrator_agent`")

    # Chat history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "bob":
                with st.chat_message("assistant", avatar="💼"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("user", avatar="👤"):
                    st.markdown(msg["content"])

    # Sample questions
    st.subheader("Sample Questions — click to fire into Bob")
    cols = st.columns(3)
    for i, q in enumerate(SAMPLE_QUESTIONS):
        with cols[i % 3]:
            if st.button(q, key=f"sq_{i}", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": q})
                st.session_state.chat_history.append({"role": "bob", "content": bob_respond(q)})
                st.rerun()

    st.divider()

    # Free-text input
    user_input = st.chat_input(f"Ask Bob anything about {account}…")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.session_state.chat_history.append({"role": "bob", "content": bob_respond(user_input)})
        st.rerun()

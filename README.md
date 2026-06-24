# IBM Sales Intelligence Hub

> **"Ask Bob"** — A watsonx Orchestrate–powered sales intelligence dashboard for IBM Sales Representatives.
> Prototype v1.0 · Sample account: **Accenture** · LLM: `watsonx/meta-llama/llama-3-3-70b-instruct`

---

## Table of Contents

1. [What it does](#what-it-does)
2. [Architecture](#architecture)
3. [Agents](#agents)
4. [Tools](#tools)
5. [Web UI](#web-ui)
6. [Chatbot — Ask Bob](#chatbot--ask-bob)
7. [Production Integration Notes](#production-integration-notes)
8. [Deployment](#deployment)
9. [Project Structure](#project-structure)

---

## What it does

The IBM Sales Intelligence Hub gives an IBM Sales Representative a single pane of glass across every
data source they need before, during, and after a client interaction. A conversational AI assistant
called **Bob** (powered by `sales_hub_orchestrator_agent`) answers natural language questions by
dynamically routing to five specialised sub-agents, each backed by Python tool functions that wrap
real external systems (mocked in this prototype).

**Rep workflow:**
1. Log in → select account (Accenture)
2. Dashboard auto-populates with news, account data, meetings, competitive intel, and AI-generated summaries
3. Type any question in "Ask Bob" → Bob routes to the right agent, calls the tool, returns a response
4. Side-effects update the dashboard in real time (flagged news, logged notes, CRM updates, toasts)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     IBM Sales Intelligence Hub                       │
│               Web UI  ·  ui/dashboard.html  (no build)               │
└────────────────────────────┬─────────────────────────────────────────┘
                             │  Natural language via Ask Bob chat panel
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│             sales_hub_orchestrator_agent  ("Bob")                    │
│    style: react  ·  llm: watsonx/meta-llama/llama-3-3-70b-instruct  │
│    Routes queries to sub-agents; synthesises multi-domain responses  │
└──┬──────────────┬──────────────┬──────────────┬──────────────────────┘
   │              │              │              │              │
   ▼              ▼              ▼              ▼              ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐
│ morning  │ │ account  │ │competitor│ │  meetings_   │ │ ai_agent_   │
│  _news   │ │_intelli- │ │_analysis │ │relationships │ │ launchpad   │
│  _agent  │ │ gence_   │ │  _agent  │ │   _agent     │ │   _agent    │
└────┬─────┘ │  _agent  │ └────┬─────┘ └──────┬───────┘ └──────┬──────┘
     │       └────┬─────┘      │              │                │
     ▼            ▼            ▼              ▼                ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐
│ morning  │ │ account  │ │competitor│ │  meetings_   │ │  ai_agent_  │
│  _news_  │ │_intelli- │ │_analysis │ │relationships │ │ launchpad_  │
│ tools.py │ │gence_    │ │_tools.py │ │  _tools.py   │ │  tools.py   │
│  3 tools │ │tools.py  │ │  3 tools │ │   4 tools    │ │   7 tools   │
└──────────┘ │  3 tools │ └──────────┘ └──────────────┘ └─────────────┘
             └──────────┘
                                              ▲ (production integrations)
             Tavily          IBM ISC Cloud    │ MS Graph API   Salesforce + Seismic
             (news)          (products/lic.)  │ (calendar)     (CRM + enablement)
```

### Data flow for a single Ask Bob question

```
Rep types: "Give me a competitive battlecard against Microsoft at Accenture."
    │
    ▼  sales_hub_orchestrator_agent detects: competitor domain
    │
    ▼  delegates to: competitor_analysis_agent
    │
    ▼  calls: get_competitor_battlecard(competitor_name="Microsoft")
    │
    ▼  tool returns: IBM differentiators, weaknesses, 5 talk-tracks, IBM products to position
    │
    ▼  orchestrator formats & returns response to chat panel
```

---

## Agents

All agents use:
- **LLM:** `watsonx/meta-llama/llama-3-3-70b-instruct`
- **Style:** `react` (ReAct reasoning loop)
- **Schema:** watsonx Orchestrate agent YAML (no `spec_version`)

---

### 1. `morning_news_agent`

**File:** [`agents/morning_news_agent.yaml`](agents/morning_news_agent.yaml)

Surfaces timely, account-relevant news and industry alerts. Supports per-item flagging and dismissal
so the rep can curate their morning intelligence feed before calls.

**Routing triggers:** "news", "what's new", "press release", "alerts", "flag this item"

**Tools:**

| Tool | Signature | What it returns |
|------|-----------|-----------------|
| `get_account_news` | `(account_name)` | 4–6 news items: title, source, date, summary, relevance tag |
| `get_industry_alerts` | `(industry)` | 2–4 sector alerts: regulation, M&A, spend trends |
| `flag_news_item` | `(news_id, flag_type)` | Confirmation; `flag_type` ∈ `{Important, Share with Team, Dismiss}` |

**Production backend:** [Tavily Search API](https://docs.tavily.com) — daily scheduled refresh,
LLM-powered relevance classification.

---

### 2. `account_intelligence_agent`

**File:** [`agents/account_intelligence_agent.yaml`](agents/account_intelligence_agent.yaml)

The core account dossier. Combines public company data with IBM's own ISC Cloud product and
licensing records to give the rep a complete picture of what Accenture already owns, what's
expiring, and what's underused.

**Routing triggers:** "account overview", "IBM products", "licenses", "renewals", "support tickets",
"ISC Cloud", "exec summary", "call prep"

**Tools:**

| Tool | Signature | What it returns |
|------|-----------|-----------------|
| `get_account_details` | `(account_name)` | Company overview, industry, HQ, revenue, tier, primary IBM contact, sales stage |
| `get_isc_cloud_data` | `(account_name)` | Active IBM products, renewal dates, usage metrics, open support tickets |
| `get_executive_summary` | `(account_name)` | Call-prep summary: priorities, recent wins, open opportunities, next steps |

**Production backend:** IBM ISC Cloud APIs — IBM License Metric Tool (ILMT), IBM Passport Advantage,
IBM Cloud Monitoring, IBM Subscription & Licensing APIs. Auth via IBM Cloud IAM API key.

---

### 3. `competitor_analysis_agent`

**File:** [`agents/competitor_analysis_agent.yaml`](agents/competitor_analysis_agent.yaml)

Competitive intelligence at the deal level. Surfaces who is competing for the account's business,
full battlecards with IBM talk-tracks, and historical win/loss patterns.

**Routing triggers:** "competitors", "battlecard", "win/loss", "vs Microsoft", "vs AWS",
"vs Google", "vs Salesforce", "how do we compare"

**Tools:**

| Tool | Signature | What it returns |
|------|-----------|-----------------|
| `get_competitors` | `(account_name)` | 3–5 active competitors with products in play and IBM's position |
| `get_competitor_battlecard` | `(competitor_name)` | IBM differentiators, competitor weaknesses, 5 talk-tracks, products to position |
| `get_win_loss_summary` | `(account_name)` | Recent IBM wins and losses with deal values and key reasoning |

**Battlecard coverage:** Microsoft Azure · AWS · Google Cloud · Salesforce

---

### 4. `meetings_relationships_agent`

**File:** [`agents/meetings_relationships_agent.yaml`](agents/meetings_relationships_agent.yaml)

Meeting intelligence and relationship health tracking. Surfaces what's on the calendar,
who the key contacts are, their engagement levels, and allows the rep to log notes directly
to Salesforce CRM without leaving the dashboard.

**Routing triggers:** "meetings", "calendar", "upcoming", "relationship", "contacts",
"engagement level", "log a note", "meeting history"

**Tools:**

| Tool | Signature | What it returns |
|------|-----------|-----------------|
| `get_upcoming_meetings` | `(account_name)` | 2–4 upcoming meetings: date, attendees, topic, prep status |
| `get_meeting_history` | `(account_name)` | Last 5 meetings: date, attendees, topic, outcome |
| `get_relationship_map` | `(account_name)` | Key contacts: title, seniority, engagement level, last interaction date |
| `log_meeting_note` | `(meeting_id, note)` | Writes note to Salesforce CRM; returns confirmation with timestamp |

**Production backend:** Microsoft Graph API (`/me/calendarview`, `/me/contacts`, `/me/messages`).
Requires `Calendars.Read`, `Contacts.Read`, `Mail.Read` Graph permissions. Auth via MSAL OAuth 2.0.

---

### 5. `ai_agent_launchpad_agent`

**File:** [`agents/ai_agent_launchpad_agent.yaml`](agents/ai_agent_launchpad_agent.yaml)

Coordinates IBM's portfolio of pre-built sales AI agents for prospecting, outreach, CRM,
enablement content discovery, and consolidated research briefing. The most tool-rich sub-agent.

**Routing triggers:** "leads", "outreach email", "draft email", "Dun & Bradstreet", "Salesforce",
"CRM", "pipeline", "opportunities", "update CRM", "Seismic", "enablement content", "research brief"

**Tools:**

| Tool | Signature | What it returns |
|------|-----------|-----------------|
| `run_lead_identification` | `(account_name)` | 3–5 leads with contact, title, department, lead score, reason |
| `run_client_outreach_draft` | `(contact_name, context)` | Personalised email draft with subject, body, and CTA |
| `run_client_search` | `(account_name)` | D&B firmographic, technographic, and contact enrichment data |
| `get_crm_snapshot` | `(account_name)` | Open Salesforce opportunities: stage, ARR, forecast category, last activity |
| `update_crm_record` | `(record_id, field, value)` | Updates a Salesforce field; returns field, old value, new value, timestamp |
| `get_enablement_content` | `(topic)` | 2–3 Seismic content recommendations with asset type and relevance score |
| `run_sales_research` | `(account_name)` | Consolidated research brief: D&B + news + IBM internal data |

**Production backends:** Salesforce REST API (CRM), Seismic Content API (enablement),
Dun & Bradstreet Direct+ API (firmographics).

---

### 6. `sales_hub_orchestrator_agent` — "Bob"

**File:** [`agents/sales_hub_orchestrator_agent.yaml`](agents/sales_hub_orchestrator_agent.yaml)

The master orchestrator. Receives every natural language query from the rep via the "Ask Bob"
chat panel, applies routing logic to identify the correct sub-agent(s), delegates, then
synthesises a unified, rep-ready response.

**Key behaviours:**
- **Single-domain:** routes directly to the owning sub-agent
- **Multi-domain:** calls all relevant sub-agents in parallel, merges output coherently
- **Proactive mode:** when the rep says "what should I focus on today", surfaces the three
  highest-priority items across all agents (urgent renewals, cold relationships, competitor moves)
- **Graceful degradation:** if a sub-agent errors, acknowledges it and proposes an alternative

**Collaborators (sub-agents):**

| Sub-agent | Domain |
|-----------|--------|
| `morning_news_agent` | News, alerts, flagging |
| `account_intelligence_agent` | Account profile, IBM products, exec summaries |
| `competitor_analysis_agent` | Competitors, battlecards, win/loss |
| `meetings_relationships_agent` | Calendar, relationships, CRM notes |
| `ai_agent_launchpad_agent` | Leads, outreach, Salesforce, Seismic, research |

---

## Tools

All 20 tools are implemented in Python using the `@tool()` decorator from
`ibm_watsonx_orchestrate.agent_builder.tools`. Every function has full type annotations,
a docstring, and structured dict/list return types compatible with watsonx Orchestrate's
tool response schema.

Mock data represents **Accenture** — a $64.9B global technology consulting firm.

**Import command:**
```bash
orchestrate tools import -k python -f <file>.py
```

| File | # Tools | Tools |
|------|---------|-------|
| [`tools/morning_news_tools.py`](tools/morning_news_tools.py) | 3 | `get_account_news`, `get_industry_alerts`, `flag_news_item` |
| [`tools/account_intelligence_tools.py`](tools/account_intelligence_tools.py) | 3 | `get_account_details`, `get_isc_cloud_data`, `get_executive_summary` |
| [`tools/competitor_analysis_tools.py`](tools/competitor_analysis_tools.py) | 3 | `get_competitors`, `get_competitor_battlecard`, `get_win_loss_summary` |
| [`tools/meetings_relationships_tools.py`](tools/meetings_relationships_tools.py) | 4 | `get_upcoming_meetings`, `get_meeting_history`, `get_relationship_map`, `log_meeting_note` |
| [`tools/ai_agent_launchpad_tools.py`](tools/ai_agent_launchpad_tools.py) | 7 | `run_lead_identification`, `run_client_outreach_draft`, `run_client_search`, `get_crm_snapshot`, `update_crm_record`, `get_enablement_content`, `run_sales_research` |

---

## Web UI

**File:** [`ui/dashboard.html`](ui/dashboard.html) · 1,462 lines · zero build dependencies

Open in any modern browser. Uses the **IBM Carbon Design System** dark-mode palette:
`#0F62FE` (IBM blue), `#161616` (background), `#262626` (surface), `#F4F4F4` (text).

**Sections (sidebar tabs):**

| Tab | Content |
|-----|---------|
| Morning News | News feed with relevance tags, flag / dismiss actions per item |
| Account Overview | Company profile, IBM products table, renewal alert badges, upsell signals |
| Executive Summary | AI-generated call prep bullet points, Copy to Clipboard |
| Competitor Analysis | Active competitor list, battlecard modals per competitor |
| Meetings & Relationships | Upcoming meetings with attendee chips + prep status, meeting history, relationship map, log-note inputs |
| AI Agent Launchpad | Clickable agent cards: lead identification, outreach draft, D&B search, CRM snapshot, update CRM, Seismic content, sales research |
| Ask Bob | Full chat panel with typing indicator, sample question chips, and `BOB_ROUTES`-powered responses |

**UI features:**
- Login screen with account selector — wires account name into all section headers
- Toast notification system for CRM updates, logged notes, and flagged news
- `BOB_ROUTES` client-side intent matcher — 15+ intents, each with mock response + optional side-effect function

---

## Chatbot — Ask Bob

The Ask Bob panel is accessible from every tab. The orchestrator (`sales_hub_orchestrator_agent`)
handles routing in production. In the prototype, the UI's `BOB_ROUTES` array pattern-matches
user input via regex and returns realistic mock responses with live dashboard side-effects.

### Sample questions

These questions are pre-loaded as clickable chips in the Ask Bob tab, and work end-to-end
in both the prototype UI and against the live `sales_hub_orchestrator_agent`:

| # | Question | Agent routed to |
|---|----------|-----------------|
| 1 | "What's new with Accenture this week?" | `morning_news_agent` |
| 2 | "Do I have any meetings with Accenture this month?" | `meetings_relationships_agent` |
| 3 | "Who are IBM's biggest competitors at Accenture right now?" | `competitor_analysis_agent` |
| 4 | "Draft an outreach email to the CTO at Accenture about watsonx." | `ai_agent_launchpad_agent` |
| 5 | "What IBM products does Accenture currently have active?" | `account_intelligence_agent` |
| 6 | "Give me a quick exec summary before my call with Accenture today." | `account_intelligence_agent` |
| 7 | "What deals do we have open in Salesforce for Accenture?" | `ai_agent_launchpad_agent` |
| 8 | "Find me the latest Seismic content on IBM Cloud Pak for Data." | `ai_agent_launchpad_agent` |
| 9 | "What is our win/loss record at Accenture over the last year?" | `competitor_analysis_agent` |
| 10 | "Flag the news item about Accenture's AWS partnership as important." | `morning_news_agent` |
| 11 | "What leads have been identified at Accenture?" | `ai_agent_launchpad_agent` |
| 12 | "Log a meeting note: discussed watsonx renewal, decision by end of Q3." | `meetings_relationships_agent` |
| 13 | "What's the relationship status with the CFO at Accenture?" | `meetings_relationships_agent` |
| 14 | "Give me a competitive battlecard against Microsoft at Accenture." | `competitor_analysis_agent` |
| 15 | "Update the Salesforce opportunity stage to 'Proposal' for the watsonx deal." | `ai_agent_launchpad_agent` |

### Extending `BOB_ROUTES` (prototype only)

Each route entry in `ui/dashboard.html` follows this shape:

```js
{
  pattern: /battlecard|microsoft|competitive/i,
  response: `**Competitive Battlecard — Microsoft vs IBM at Accenture** ...`,
  action: () => { /* optional: flag news item, fire toast, update DOM */ }
}
```

Add new entries to the `BOB_ROUTES` array in the `<script>` block at the bottom of
`dashboard.html` to expand Bob's conversational range in the prototype.

---

## Production Integration Notes

### Tavily → `morning_news_agent`

```python
import tavily, os

client = tavily.TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def get_account_news(account_name: str) -> list:
    results = client.search(
        query=f"{account_name} press release product announcement executive news",
        search_depth="advanced",
        max_results=6,
        days=7,
    )
    # Map to standard news item schema, then classify relevance tags via LLM
    ...
```

Schedule on a daily refresh cycle using watsonx Orchestrate's built-in scheduled triggers.

---

### IBM ISC Cloud APIs → `account_intelligence_agent`

| Data | API |
|------|-----|
| Products & Licenses | IBM License Metric Tool (ILMT) API / IBM Passport Advantage Portal |
| Usage Metrics | IBM Cloud Monitoring (Sysdig-based) / CloudPak Metering APIs |
| Support Tickets | IBM Support API — `/case-management/v1/cases` |
| Renewals | IBM Subscription & Licensing APIs |

```python
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

authenticator = IAMAuthenticator(os.environ["IBM_CLOUD_API_KEY"])
```

---

### Microsoft Graph API → `meetings_relationships_agent`

```python
import msal, requests

app = msal.ConfidentialClientApplication(
    client_id=os.environ["MS_CLIENT_ID"],
    client_credential=os.environ["MS_CLIENT_SECRET"],
    authority=f"https://login.microsoftonline.com/{os.environ['MS_TENANT_ID']}",
)
token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
headers = {"Authorization": f"Bearer {token['access_token']}"}

# Upcoming meetings
requests.get("https://graph.microsoft.com/v1.0/me/calendarview", headers=headers,
             params={"startDateTime": "...", "endDateTime": "..."})
```

Required permissions: `Calendars.Read`, `Contacts.Read`, `Mail.Read`

---

### Salesforce REST API → `ai_agent_launchpad_agent`

```python
from simple_salesforce import Salesforce

sf = Salesforce(
    username=os.environ["SF_USERNAME"],
    password=os.environ["SF_PASSWORD"],
    security_token=os.environ["SF_SECURITY_TOKEN"],
)

# Read opportunities
sf.query("SELECT Id, Name, StageName, Amount FROM Opportunity WHERE AccountId = '...'")

# Update a record
sf.Opportunity.update("OPP-001", {"StageName": "Proposal"})
```

---

## Deployment

### Prerequisites

```bash
pip install ibm-watsonx-orchestrate
orchestrate login  # authenticates against your watsonx Orchestrate instance
```

### Step 1 — Import tools (one command per file)

```bash
orchestrate tools import -k python -f tools/morning_news_tools.py
orchestrate tools import -k python -f tools/account_intelligence_tools.py
orchestrate tools import -k python -f tools/competitor_analysis_tools.py
orchestrate tools import -k python -f tools/meetings_relationships_tools.py
orchestrate tools import -k python -f tools/ai_agent_launchpad_tools.py
```

### Step 2 — Import sub-agents

```bash
orchestrate agents import -f agents/morning_news_agent.yaml
orchestrate agents import -f agents/account_intelligence_agent.yaml
orchestrate agents import -f agents/competitor_analysis_agent.yaml
orchestrate agents import -f agents/meetings_relationships_agent.yaml
orchestrate agents import -f agents/ai_agent_launchpad_agent.yaml
```

### Step 3 — Import orchestrator (must be last)

```bash
# The orchestrator references the sub-agents as collaborators.
# They must be registered before this import.
orchestrate agents import -f agents/sales_hub_orchestrator_agent.yaml
```

### Step 4 — Open the UI

```bash
open ui/dashboard.html   # macOS
# or just double-click dashboard.html in any file manager
```

No server required — the prototype runs entirely in the browser.

---

## Project Structure

```
ibm-sales-intelligence-hub/
├── agents/
│   ├── morning_news_agent.yaml              # News, alerts, flagging
│   ├── account_intelligence_agent.yaml      # Account profile, ISC Cloud, exec summary
│   ├── competitor_analysis_agent.yaml       # Battlecards, win/loss, competitors
│   ├── meetings_relationships_agent.yaml    # Calendar, relationships, CRM notes
│   ├── ai_agent_launchpad_agent.yaml        # Leads, outreach, Salesforce, Seismic
│   └── sales_hub_orchestrator_agent.yaml    # Master orchestrator ("Bob")
├── tools/
│   ├── morning_news_tools.py                # 3 tools
│   ├── account_intelligence_tools.py        # 3 tools
│   ├── competitor_analysis_tools.py         # 3 tools  (MS, AWS, GCP, Salesforce)
│   ├── meetings_relationships_tools.py      # 4 tools
│   └── ai_agent_launchpad_tools.py          # 7 tools
├── ui/
│   └── dashboard.html                       # Full self-contained prototype UI
├── specs/
│   └── IBM_Sales_Intelligence_Hub_Bob_spec.txt
└── README.md
```

---

*IBM Sales Intelligence Hub — Prototype v1.0 | Powered by IBM watsonx Orchestrate*

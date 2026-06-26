"""
Meetings & Relationships tools for the IBM Sales Intelligence Hub.

Agent: meetings_relationships_agent
Tools:
  - get_upcoming_meetings: Returns 2-4 upcoming meetings with the chosen account.
  - get_meeting_history  : Returns the last 5 meetings held with the account.
  - get_relationship_map : Returns key client contacts and IBM relationship health.
  - log_meeting_note     : Saves a rep note to Salesforce CRM for a specific meeting.

Mock data reflects Accenture. In production, get_upcoming_meetings, get_meeting_history,
and get_relationship_map will be replaced with live Microsoft Graph API calls
(Outlook Calendar, Teams, Contacts).

Import command:
  orchestrate tools import -k python -f meetings_relationships_tools.py
"""

import datetime

from ibm_watsonx_orchestrate.agent_builder.tools import tool

__all__ = [
    "get_upcoming_meetings",
    "get_meeting_history",
    "get_relationship_map",
    "log_meeting_note",
]

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool()
def get_upcoming_meetings(account_name: str) -> list:
    """Returns mock upcoming meetings scheduled with the chosen account.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        list: A list of 2-4 upcoming meeting objects, each containing meeting_id,
              title, date_time (ISO 8601 UTC), duration_minutes, location,
              ibm_attendees (list of strings), client_attendees (list of strings),
              and prep_status ("Prep Complete", "Needs Prep", or "No Brief").
    """
    return [
        {
            "meeting_id": "mtg_001",
            "title": "watsonx Enterprise Expansion — Proposal Review",
            "date_time": "2026-06-18T14:00:00Z",
            "duration_minutes": 60,
            "location": "Microsoft Teams",
            "ibm_attendees": [
                "Sarah Mitchell (Global Account Executive)",
                "James Okonkwo (Technical Sales Lead)",
                "Dr. Anita Rowe (watsonx Solutions Architect)",
            ],
            "client_attendees": [
                "Dr. Priya Nair (Chief AI Officer, Accenture)",
                "Mark Henderson (VP Technology, Accenture FS)",
                "Lisa Tran (Procurement Lead, Accenture)",
            ],
            "prep_status": "Needs Prep",
        },
        {
            "meeting_id": "mtg_002",
            "title": "IBM Sterling Supply Chain — Q3 Business Review",
            "date_time": "2026-06-20T10:00:00Z",
            "duration_minutes": 90,
            "location": "Accenture HQ, New York — Conference Room 12B",
            "ibm_attendees": [
                "Sarah Mitchell (Global Account Executive)",
                "Chris Adeyemi (IBM Sterling Customer Success Manager)",
            ],
            "client_attendees": [
                "Rachel Park (Head of Supply Chain, Accenture)",
                "Tom Burgess (Enterprise Architect, Accenture)",
            ],
            "prep_status": "Prep Complete",
        },
        {
            "meeting_id": "mtg_003",
            "title": "watsonx.governance — EU AI Act Compliance Workshop",
            "date_time": "2026-06-25T13:00:00Z",
            "duration_minutes": 120,
            "location": "Microsoft Teams",
            "ibm_attendees": [
                "Sarah Mitchell (Global Account Executive)",
                "Dr. Anita Rowe (watsonx Solutions Architect)",
                "IBM Legal & Compliance SME (TBC)",
            ],
            "client_attendees": [
                "Dr. Priya Nair (Chief AI Officer, Accenture)",
                "Accenture Legal Counsel (TBC)",
                "Mark Henderson (VP Technology, Accenture FS)",
            ],
            "prep_status": "No Brief",
        },
    ]


@tool()
def get_meeting_history(account_name: str) -> list:
    """Returns the last 5 meetings held with the chosen account.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        list: A list of up to 5 past meeting objects, each containing meeting_id,
              date (YYYY-MM-DD), title, attendees (list of strings), and outcome
              (one-sentence summary string).
    """
    return [
        {
            "meeting_id": "hist_001",
            "date": "2026-06-04",
            "title": "watsonx.ai Q2 Business Review",
            "attendees": [
                "Sarah Mitchell (IBM GAE)",
                "James Okonkwo (IBM TSL)",
                "Dr. Priya Nair (Accenture CAO)",
            ],
            "outcome": (
                "Pilot results reviewed positively; Dr. Priya Nair requested a formal "
                "enterprise expansion proposal by June 20."
            ),
        },
        {
            "meeting_id": "hist_002",
            "date": "2026-05-22",
            "title": "IBM Cloud Pak for Data — Capacity Planning Session",
            "attendees": [
                "James Okonkwo (IBM TSL)",
                "Tom Burgess (Accenture Enterprise Architect)",
            ],
            "outcome": (
                "88% utilisation confirmed across production clusters; capacity upgrade "
                "proposal to be delivered by end of June 2026."
            ),
        },
        {
            "meeting_id": "hist_003",
            "date": "2026-05-14",
            "title": "Executive Sponsor Dinner — Annual IBM–Accenture Relationship Review",
            "attendees": [
                "Sarah Mitchell (IBM GAE)",
                "IBM VP Strategic Accounts",
                "Dr. Priya Nair (Accenture CAO)",
                "Accenture CEO North America",
            ],
            "outcome": (
                "IBM–Accenture strategic relationship reaffirmed at executive level; "
                "IBM's AI roadmap and watsonx roadmap well received by Accenture leadership."
            ),
        },
        {
            "meeting_id": "hist_004",
            "date": "2026-04-30",
            "title": "IBM Sterling Supply Chain Suite — Renewal Discussion",
            "attendees": [
                "Chris Adeyemi (IBM Sterling CSM)",
                "Rachel Park (Accenture Head of Supply Chain)",
            ],
            "outcome": (
                "Renewal confirmed for November 2026; Rachel Park indicated openness to "
                "premium tier upgrade subject to Q3 budget approval."
            ),
        },
        {
            "meeting_id": "hist_005",
            "date": "2026-04-15",
            "title": "watsonx.governance — Initial Scoping Call",
            "attendees": [
                "James Okonkwo (IBM TSL)",
                "Dr. Anita Rowe (IBM Solutions Architect)",
                "Mark Henderson (Accenture VP Technology, FS)",
            ],
            "outcome": (
                "Accenture confirmed EU AI Act compliance is a board-level priority; "
                "watsonx.governance product demo scheduled for Q2."
            ),
        },
    ]


@tool()
def get_relationship_map(account_name: str) -> list:
    """Returns a mock relationship map of key client contacts at the chosen account.

    Args:
        account_name (str): The name of the enterprise account (e.g. "Accenture").

    Returns:
        list: A list of contact objects, each containing contact_name, title,
              seniority ("C-Suite", "VP", "Director", or "Manager"),
              ibm_relationship_owner (string), engagement_level ("Strong",
              "Moderate", or "Cold"), last_interaction (YYYY-MM-DD), and
              notes (string with relationship context).
    """
    return [
        {
            "contact_name": "Dr. Priya Nair",
            "title": "Chief AI Officer",
            "seniority": "C-Suite",
            "ibm_relationship_owner": "Sarah Mitchell",
            "engagement_level": "Strong",
            "last_interaction": "2026-06-04",
            "notes": (
                "IBM advocate; championed the watsonx pilot internally. Appointment as CAO "
                "directly driven by pilot success. Direct budget authority over AI platform decisions."
            ),
        },
        {
            "contact_name": "Mark Henderson",
            "title": "VP Technology, Financial Services",
            "seniority": "VP",
            "ibm_relationship_owner": "James Okonkwo",
            "engagement_level": "Moderate",
            "last_interaction": "2026-05-14",
            "notes": (
                "Primary budget holder for watsonx.governance in the FS division. "
                "Actively evaluating EU AI Act compliance options. Needs regular technical "
                "engagement from the IBM solutions architect team."
            ),
        },
        {
            "contact_name": "Rachel Park",
            "title": "Head of Supply Chain",
            "seniority": "Director",
            "ibm_relationship_owner": "Chris Adeyemi",
            "engagement_level": "Strong",
            "last_interaction": "2026-04-30",
            "notes": (
                "Long-term IBM Sterling advocate and internal sponsor for the November "
                "2026 renewal. Cited the 2026 industry award win publicly. Supportive "
                "of premium tier upgrade pending Q3 budget approval."
            ),
        },
        {
            "contact_name": "Lisa Tran",
            "title": "Procurement Lead",
            "seniority": "Manager",
            "ibm_relationship_owner": "Sarah Mitchell",
            "engagement_level": "Cold",
            "last_interaction": "2026-02-10",
            "notes": (
                "Key procurement gatekeeper for all deals above $1M. Was not engaged "
                "early enough in the Azure OpenAI loss (Jan 2026) — this must not repeat. "
                "Needs immediate re-engagement before the watsonx expansion proposal is submitted."
            ),
        },
        {
            "contact_name": "David Osei",
            "title": "Chief Financial Officer",
            "seniority": "C-Suite",
            "ibm_relationship_owner": "Sarah Mitchell",
            "engagement_level": "Cold",
            "last_interaction": "2025-11-20",
            "notes": (
                "CFO controls final budget approval for all deals above $5M. No IBM "
                "touchpoint since the executive sponsor dinner (Nov 2025). A direct "
                "executive outreach from IBM VP level is recommended before the "
                "$8.4M watsonx expansion proposal is tabled."
            ),
        },
    ]


@tool()
def log_meeting_note(meeting_id: str, note: str) -> str:
    """Saves a rep-authored note to Salesforce CRM for the specified meeting.

    Args:
        meeting_id (str): The unique identifier of the meeting to attach the note to
                          (e.g. "mtg_001"). Obtainable from get_upcoming_meetings
                          or get_meeting_history.
        note (str): The note content to be saved, such as discussion points, action
                    items, or follow-up commitments.

    Returns:
        str: Confirmation message with the meeting ID, note content, timestamp,
             and rep name confirming the note was saved to Salesforce CRM.
    """
    today = datetime.date.today().isoformat()
    return (
        f"Meeting note saved to Salesforce CRM.\n"
        f"Meeting ID : {meeting_id}\n"
        f"Note       : \"{note}\"\n"
        f"Logged by  : Sarah Mitchell\n"
        f"Date       : {today}"
    )

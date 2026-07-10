"""
IBM Sales Intelligence Hub — Streamlit UI
Mirrors ui/dashboard.html. Run with:
    streamlit run ui/streamlit_app.py --server.port 8503
"""

import os
import re
import datetime
import streamlit as st
from copy import deepcopy
from datetime import date

# ── Load .env from project root (one level up from ui/) if present ──
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.isfile(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

# ─────────────────────────────────────────────────────────────
# TAVILY HELPERS  (Morning News live scraping)
# ─────────────────────────────────────────────────────────────

_RELEVANCE_KEYWORDS = {
    "partnership": "🟢 Opportunity",
    "expand": "🟢 Opportunity",
    "deal": "🟢 Opportunity",
    "contract": "🟢 Opportunity",
    "award": "🟢 Opportunity",
    "revenue": "🟢 Opportunity",
    "earnings": "🟢 Opportunity",
    "growth": "🟢 Opportunity",
    "appoint": "🟡 Executive Change",
    "hire": "🟡 Executive Change",
    "ceo": "🟡 Executive Change",
    "cto": "🟡 Executive Change",
    "coo": "🟡 Executive Change",
    "cfo": "🟡 Executive Change",
    "chief": "🟡 Executive Change",
    "resign": "🟡 Executive Change",
    "risk": "🔴 Risk",
    "breach": "🔴 Risk",
    "lawsuit": "🔴 Risk",
    "fine": "🔴 Risk",
    "penalty": "🔴 Risk",
    "layoff": "🔴 Risk",
    "competitor": "🔴 Competitor Move",
    "microsoft": "🔴 Competitor Move",
    "aws": "🔴 Competitor Move",
    "google": "🔴 Competitor Move",
    "amazon": "🔴 Competitor Move",
    "azure": "🔴 Competitor Move",
}


def _infer_tag(title: str, body: str) -> str:
    combined = (title + " " + body).lower()
    for kw, tag in _RELEVANCE_KEYWORDS.items():
        if kw in combined:
            return tag
    return "🟢 Opportunity"


def _fmt_date(raw):
    if raw:
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(raw[:10], fmt[:10]).strftime("%b %d, %Y")
            except ValueError:
                continue
    return datetime.date.today().strftime("%b %d, %Y")


def _hostname(url: str) -> str:
    try:
        return url.split("/")[2].replace("www.", "")
    except Exception:
        return "Web"


def _clean_content(raw: str) -> str:
    """Strip markdown headings, boilerplate, HTML tags and excess whitespace from Tavily content."""
    # Remove markdown headings (# ## ### etc.)
    text = re.sub(r"^#+\s*", "", raw, flags=re.MULTILINE)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove Cloudflare/CDN email-protection spans and encoded links
    text = re.sub(r"/cdn-cgi/[^\s)\"']*", "", text)
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace per line
    lines = [l.strip() for l in text.splitlines()]
    return "\n".join(l for l in lines if l)


# Patterns that indicate boilerplate / non-article sentences to skip
_SKIP_PATTERNS = re.compile(
    r"^(https?://|www\.|"                                         # URLs
    r"contact[s]?:|press contact|"                                # press contacts
    r"[+\d]{7,}|"                                                  # phone numbers
    r"@|"                                                           # email fragments
    r"\d{1,2}[/,\s]\s*\d{2,4}|"                                   # date fragment: 9, 2025 or 9/21/2025
    r"(new york|london|paris|chicago|san francisco|dublin)[;,\s]|" # city bylines
    r"january|february|march|april|may|june|july|august|"
    r"september|october|november|december\s+\d|"                   # Month DD
    r"# # #|###)",                                                 # PR end markers
    re.IGNORECASE
)

# Words found in press-release byline sentences to deprioritise as bullets
_BYLINE_RE = re.compile(
    r"\b(NYSE|NASDAQ|NYSE:\s*\w+|Inc\.\s*\(NYSE|Plc\s*\(NYSE)\b",
    re.IGNORECASE
)


_BULLET_MAX_CHARS = 115  # hard cap per bullet — keep them scannable


def _trim_bullet(s: str) -> str:
    """Trim a sentence to _BULLET_MAX_CHARS, breaking at the last word boundary."""
    if len(s) <= _BULLET_MAX_CHARS:
        return s
    cut = s[:_BULLET_MAX_CHARS].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


def _extract_bullets(content: str, n: int = 3) -> list[str]:
    """
    Extract up to n short bullet-point highlights from cleaned article content.
    """
    text = _clean_content(content)
    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    candidates = []
    byline_fallbacks = []
    for s in sentences:
        s = s.strip()
        # Skip very short or boilerplate fragments
        if len(s) < 55:
            continue
        if _SKIP_PATTERNS.match(s):
            continue
        # Skip Tavily truncation markers and PR footer content
        if re.match(r"^\[…\]|\[\.\.\.?\]", s) or "# # #" in s or "Contacts:" in s:
            continue
        # Skip sentences that look like all-caps titles
        cap_ratio = sum(1 for c in s if c.isupper()) / max(len(s), 1)
        if cap_ratio > 0.55:
            continue
        # Deprioritise press-release byline openers (NYSE: ACN) — collect as fallback
        if _BYLINE_RE.search(s[:80]):
            byline_fallbacks.append(_trim_bullet(s))
            continue
        candidates.append(_trim_bullet(s))
        if len(candidates) >= n:
            break
    # If not enough good sentences, pad with byline fallbacks
    if len(candidates) < n:
        candidates += byline_fallbacks[: n - len(candidates)]
    return candidates[:n]


def _short_preview(content: str, chars: int = 200) -> str:
    """Return a clean, plain-text preview of the article body (skips date/title/byline header)."""
    text = _clean_content(content)
    # Many press-release articles from Tavily begin with:
    #   "Month DD, YYYY\nArticle Title\nCITY; Month DD, YYYY – Actual body..."
    # Strategy: if text contains a em-dash / en-dash dateline pattern, start from there.
    # Strip everything before the first "CITY; ... – " or "CITY, ... – " intro.
    _dateline_re = re.compile(
        r"(?:^|\n)"
        r"(?:new york|london|paris|chicago|san francisco|dublin|amsterdam|singapore|"
        r"washington|seattle|tokyo|sydney|toronto|mumbai|zurich|riyadh|new delhi|bozeman|"
        r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)"  # any city-like proper noun as fallback
        r"(?:\s+and\s+\S+)?"                # optional "and <other-city>"
        r"[;,/].*?[–—]\s*",
        re.IGNORECASE
    )
    m = _dateline_re.search(text)
    if m:
        body = text[m.end():].strip()
        if len(body) >= 60:
            flat = " ".join(body.split())
            return (flat[:chars] + "…") if len(flat) > chars else flat

    # Fallback: iterate paragraphs, skip anything that looks like a header block
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for para in paragraphs:
        if len(para) < 80:
            continue
        # Skip if starts with a month name (press release dateline) or a year
        if re.match(
            r"^(january|february|march|april|may|june|july|august|"
            r"september|october|november|december|\d{4})",
            para, re.IGNORECASE
        ):
            continue
        return (para[:chars] + "…") if len(para) > chars else para

    # Last resort: flatten
    flat = " ".join(text.split())
    return (flat[:chars] + "…") if len(flat) > chars else flat


def fetch_tavily_news(account_name: str, industry: str):
    """
    Calls Tavily Search API for account news + industry alerts.
    Returns (news_items, industry_alerts, error_msg).
    Falls back to mock data if TAVILY_API_KEY is not set or tavily-python is not installed.
    """
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return None, None, "no_key"

    try:
        from tavily import TavilyClient
    except ImportError:
        return None, None, "no_package"

    client = TavilyClient(api_key=api_key)

    try:
        news_resp = client.search(
            query=(
                f"{account_name} latest news press release executive announcement "
                f"partnership earnings AI cloud technology"
            ),
            search_depth="advanced",
            max_results=6,
            include_answer=False,
            include_raw_content=False,
        )
        industry_resp = client.search(
            query=(
                f"{industry} industry news regulation AI cloud market trends "
                f"M&A analyst report latest 2025 2026"
            ),
            search_depth="advanced",
            max_results=4,
            include_answer=False,
            include_raw_content=False,
        )
    except Exception as exc:
        return None, None, str(exc)

    news_items = []
    for i, r in enumerate(news_resp.get("results", []), start=1):
        title   = r.get("title", "").strip()
        content = r.get("content", "").strip()
        url     = r.get("url", "")
        news_items.append({
            "id":      f"live_news_{i:03d}",
            "tag":     _infer_tag(title, content),
            "title":   title,
            "source":  _hostname(url),
            "url":     url,
            "date":    _fmt_date(r.get("published_date")),
            "bullets": _extract_bullets(content, n=3),
            "preview": _short_preview(content, chars=220),
        })

    alerts = []
    for i, r in enumerate(industry_resp.get("results", []), start=1):
        title   = r.get("title", "").strip()
        content = r.get("content", "").strip()
        url     = r.get("url", "")
        alerts.append({
            "id":      f"live_alert_{i:03d}",
            "title":   title,
            "source":  _hostname(url),
            "url":     url,
            "date":    _fmt_date(r.get("published_date")),
            "preview": _short_preview(content, chars=160),
        })

    return news_items or None, alerts or None, None


def fetch_linkedin_prospects(account_name: str, industry: str):
    """
    Calls Tavily Search API to find publicly indexed LinkedIn profiles of
    people at the chosen account who would be valuable new connections for
    an IBM sales rep.
    Returns (prospects, error_msg).
    Falls back gracefully if TAVILY_API_KEY is not set.
    """
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        return None, "no_key"

    try:
        from tavily import TavilyClient
    except ImportError:
        return None, "no_package"

    client = TavilyClient(api_key=api_key)

    try:
        resp = client.search(
            query=(
                f'site:linkedin.com/in "{account_name}" '
                f'("Chief" OR "VP" OR "Vice President" OR "Head of" OR '
                f'"Director" OR "Procurement" OR "CTO" OR "CFO" OR "CIO" OR '
                f'"Chief AI" OR "Chief Data" OR "Chief Digital" OR "Managing Director")'
            ),
            search_depth="advanced",
            max_results=8,
            include_raw_content=False,
        )
    except Exception as exc:
        return None, str(exc)

    # ── Role → IBM relevance reason mapping ──────────────────────────────────
    _ROLE_REASONS = [
        (["chief ai", "chief artificial", "cai officer"],
         "AI budget authority — key decision-maker for watsonx expansion"),
        (["chief data", "chief digital", "chief information", "cio", "chief technology", "cto"],
         "Technology authority — strategic influence over cloud & AI platforms"),
        (["chief financial", "cfo", "finance director"],
         "Budget approval required for deals above $5M — critical relationship"),
        (["procurement", "sourcing", "vendor management", "supply chain"],
         "Procurement gatekeeper — must be engaged before proposal submission"),
        (["vp", "vice president", "svp", "evp"],
         "Senior budget holder — champion potential for IBM solutions"),
        (["head of data", "head of analytics", "head of ai", "head of cloud",
          "head of technology", "head of digital"],
         "Technical champion — likely Cloud Pak / watsonx.ai end-user sponsor"),
        (["managing director", "director"],
         "Delivery sponsor — key influencer for renewal and upsell decisions"),
    ]

    def _infer_reason(name: str, title: str) -> str:
        combined = (name + " " + title).lower()
        for keywords, reason in _ROLE_REASONS:
            if any(kw in combined for kw in keywords):
                return reason
        return "Senior stakeholder — potential IBM relationship expansion opportunity"

    def _parse_profile(result: dict, idx: int) -> dict:
        """Extract name, title, location, and headline from a Tavily LinkedIn result."""
        raw_title = result.get("title", "").strip()
        content   = result.get("content", "").strip()
        url       = result.get("url", "")

        # Title field formats:
        #   "Firstname Lastname - Job Title - Company"   → parts[0]=name, parts[1]=role
        #   "Firstname Lastname - Company"               → parts[0]=name only
        #   "Firstname Lastname | Company"               → parts[0]=name only
        title_parts = re.split(r"\s*[-|]\s*", raw_title)
        name = title_parts[0].strip() or raw_title

        # If Tavily gives us a middle segment that looks like a job title (not the account name
        # and not a country/city), use it directly — this is the most reliable source.
        role_from_title = ""
        if len(title_parts) >= 3:
            candidate = title_parts[1].strip()
            if (
                candidate
                and candidate.lower() != account_name.lower()
                and len(candidate) < 80
                and not re.match(r"^(united|new york|london|chicago|washington)", candidate, re.I)
            ):
                role_from_title = candidate

        # Content first non-empty lines as fallback
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]

        # Extract role from content only if not found in title
        role = role_from_title
        if not role:
            skip_fragments = {account_name.lower(), name.lower()}
            _BAD_ROLE = re.compile(
                r"^(people also viewed|#|\-\s|\*\s|https?://|\d+\s+(connection|follower)|about|experience|education)",
                re.IGNORECASE,
            )
            for ln in lines[:10]:
                clean = re.sub(r"^#+\s*", "", ln)  # strip markdown headers
                low   = clean.lower()
                if (
                    low not in skip_fragments
                    and 5 < len(clean) < 90          # short enough to be a title
                    and not _BAD_ROLE.match(clean)
                    and account_name.lower() not in low[:30]
                    and not clean.startswith("-")     # skip list items
                    and not re.search(r"<br|&nbsp|linkedin\.com", low)
                ):
                    role = clean
                    break

        # Location: look for a line matching "City, State/Country"
        location = ""
        for ln in lines[:8]:
            clean = re.sub(r"^#+\s*", "", ln)
            if (
                re.search(r",\s+[A-Z][a-zA-Z]", clean)
                and len(clean) < 60
                and not clean.startswith("-")
            ):
                location = clean
                break

        # Fallback name from "# Name" markdown header in content
        if not name or name.lower() == account_name.lower():
            for ln in lines[:3]:
                candidate = re.sub(r"^#+\s*", "", ln).strip()
                if candidate and candidate.lower() != account_name.lower():
                    name = candidate
                    break

        reason = _infer_reason(name, role)

        return {
            "id":       f"li_prospect_{idx:03d}",
            "name":     name or "Unknown",
            "role":     role or "Role not identified",
            "location": location,
            "url":      url,
            "reason":   reason,
        }

    prospects = [
        _parse_profile(r, i)
        for i, r in enumerate(resp.get("results", []), start=1)
        if r.get("url", "").startswith("https://www.linkedin.com/in/")
    ]

    return prospects or None, None

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
# IBM CARBON LIGHT THEME
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ══════════════════════════════════════════
     ROOT — white/light background everywhere
  ══════════════════════════════════════════ */
  .stApp, .stApp > *, section[data-testid="stMain"],
  .main, .main > *, div[data-testid="stAppViewContainer"],
  div[data-testid="stAppViewBlockContainer"] {
    background-color: #f4f4f4 !important;
  }
  /* Wipe any lingering dark from Streamlit's default injected styles */
  .stApp { color: #161616 !important; }
  .block-container { padding: 24px 28px !important; max-width: 1100px !important; padding-top: 72px !important; }

  /* Collapse Streamlit's native header to zero height so our iframe
     topbar starts flush at the very top of the viewport. */
  header[data-testid="stHeader"] {
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    border: none !important;
    overflow: visible !important;
    background: transparent !important;
  }
  #stDecoration { display: none !important; }

  /* ── Move Streamlit's native sidebar buttons offscreen (keep clickable) ── */
  [data-testid="stSidebarCollapseButton"],
  [data-testid="stSidebarCollapsedControl"] {
    position: fixed !important;
    top: -9999px !important;
    left: -9999px !important;
    opacity: 0 !important;
    pointer-events: auto !important;
  }

  /* ── Root CSS vars ── */
  :root {
    --ibm-blue:#0F62FE; --ibm-blue-hover:#0353E9;
    --bg:#f4f4f4; --surface:#ffffff; --surface-2:#e0e0e0;
    --border:#e0e0e0; --text:#161616; --text-muted:#525252; --text-disabled:#8d8d8d;
    --green:#198038; --yellow:#b28600; --red:#da1e28;
    font-family: -apple-system, "Segoe UI", system-ui, sans-serif;
  }

  /* ── Global text & bg ── */
  html, body { background: #f4f4f4 !important; color: #161616 !important; }
  p, span, div, label, li, td, th { color: #161616; }
  .stMarkdown, .stMarkdown p { color: #161616 !important; }

  /* ── Sidebar shell ── */
  [data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e8e8e8 !important;
    padding: 0 !important;
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    transform: none !important;
    min-width: 240px !important;
    top: 48px !important;
    z-index: 999 !important;
  }
  /* ── Nuke every padding/margin layer Streamlit injects in the sidebar ── */
  [data-testid="stSidebar"] > div:first-child,
  [data-testid="stSidebarContent"],
  [data-testid="stSidebarUserContent"],
  [data-testid="stSidebar"] section,
  [data-testid="stSidebar"] .block-container {
    padding: 0 !important;
    padding-top: 0 !important;
    margin: 0 !important;
    margin-top: 0 !important;
  }

  /* Pull content up to sit just below the 48px topbar — offset the 6rem Streamlit adds */
  [data-testid="stSidebarUserContent"] > div:first-child {
    margin-top: -4.5rem !important;
    padding-top: 0 !important;
  }

  /* Collapse all inter-element gaps */
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"]       { gap: 0 !important; }
  [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div { margin: 0 !important; padding: 0 !important; }
  [data-testid="stSidebar"] [data-testid="element-container"]     { margin: 0 !important; padding: 0 !important; }
  [data-testid="stSidebar"] [data-testid="stButtonGroup"]         { margin: 0 !important; padding: 0 !important; }
  [data-testid="stSidebar"] .stButton                             { margin: 0 !important; padding: 0 !important; }
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"]   { margin: 0 !important; padding: 0 !important; }

  /* ── Section group labels ── */
  .sb-section-label {
    display: block;
    font-size: 10.5px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.4px !important;
    color: #aaaaaa !important;
    padding: 20px 16px 6px !important;
    margin: 0 !important;
    font-family: -apple-system, "Segoe UI", system-ui, sans-serif !important;
  }

  /* ── Nav buttons — base ── */
  [data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 15px !important;
    font-weight: 400 !important;
    font-family: -apple-system, "Segoe UI", system-ui, sans-serif !important;
    padding: 11px 16px !important;
    width: 100% !important;
    text-align: left !important;
    justify-content: flex-start !important;
    letter-spacing: 0 !important;
    box-shadow: none !important;
    color: #374151 !important;
    line-height: 1.4 !important;
    margin: 2px 0 !important;
    gap: 10px !important;
  }
  [data-testid="stSidebar"] .stButton > button:hover {
    background: #f3f4f6 !important;
    color: #111827 !important;
    box-shadow: none !important;
  }
  [data-testid="stSidebar"] .stButton > button p,
  [data-testid="stSidebar"] .stButton > button span {
    color: inherit !important;
    font-size: inherit !important;
    font-weight: inherit !important;
    font-family: inherit !important;
    letter-spacing: inherit !important;
  }

  /* ── Active item — full-width blue, white bold text ── */
  [data-testid="stSidebar"] .nav-active .stButton > button {
    background: #2451e3 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 8px !important;
  }
  [data-testid="stSidebar"] .nav-active .stButton > button p,
  [data-testid="stSidebar"] .nav-active .stButton > button span { color: #ffffff !important; }
  [data-testid="stSidebar"] .nav-active .stButton > button:hover { background: #1e44cc !important; }

  /* ── Sidebar divider ── */
  [data-testid="stSidebar"] hr {
    border: none !important; border-top: 1px solid #eeeeee !important; margin: 8px 0 !important;
  }

  /* ── Logout button ── */
  [data-testid="stSidebar"] .sb-logout .stButton > button {
    background: #2451e3 !important; color: #fff !important;
    font-weight: 600 !important; padding: 9px 16px !important;
    margin: 0 16px !important; width: calc(100% - 32px) !important;
    border: none !important; box-shadow: none !important; border-radius: 6px !important;
  }
  [data-testid="stSidebar"] .sb-logout .stButton > button p,
  [data-testid="stSidebar"] .sb-logout .stButton > button span { color: #fff !important; }
  [data-testid="stSidebar"] .sb-logout .stButton > button:hover { background: #1e44cc !important; }

  /* ── Headings ── */
  h1, h2, h3 { color: #161616 !important; }
  h1 { font-size: 20px !important; font-weight: 600 !important; margin-bottom: 2px !important; }

  /* ── Dividers ── */
  hr { border: none !important; border-top: 1px solid #e0e0e0 !important; margin: 16px 0 !important; }

  /* ── Streamlit Buttons — primary IBM blue ── */
  .stButton > button {
    background: #0F62FE !important; color: #fff !important; border: none !important;
    font-weight: 600 !important; border-radius: 0 !important;
    padding: 7px 18px !important; font-size: 13px !important;
    width: 100% !important;
  }
  .stButton > button:hover { background: #0353E9 !important; }

  /* ── News action buttons — match "Read article" style ──
     Target the 2nd column in [10,2] news card rows           */
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) .stButton > button,
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) .stButton > button:focus,
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) .stButton > button:active {
    background: #ffffff !important;
    border: 1px solid #97c1ff !important;
    color: #0043ce !important;
    font-weight: 400 !important;
    font-size: 12px !important;
    padding: 5px 10px !important;
    margin-bottom: 6px !important;
    border-radius: 4px !important;
    width: 100% !important;
    box-shadow: none !important;
  }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) .stButton > button:hover {
    background: #edf5ff !important;
    color: #0043ce !important;
    border-color: #0043ce !important;
    box-shadow: none !important;
  }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) .stButton > button p,
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) .stButton > button span {
    color: #0043ce !important;
    font-size: 12px !important;
    font-weight: 400 !important;
  }

  /* ── View Notes / Save Note buttons — match "Read article" style ──
     [2,5,2] rows have exactly 3 columns; target 1st & 3rd only.
     [10,2] news rows only have 2 columns so :nth-child(3) never fires there. */
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3)) > [data-testid="stColumn"]:nth-child(1) .stButton > button,
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3)) > [data-testid="stColumn"]:nth-child(3) .stButton > button {
    background: #ffffff !important;
    border: 1px solid #97c1ff !important;
    color: #0043ce !important;
    font-weight: 400 !important;
    font-size: 12px !important;
    padding: 5px 10px !important;
    border-radius: 4px !important;
    width: 100% !important;
    box-shadow: none !important;
  }
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3)) > [data-testid="stColumn"]:nth-child(1) .stButton > button:hover,
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3)) > [data-testid="stColumn"]:nth-child(3) .stButton > button:hover {
    background: #edf5ff !important;
    color: #0043ce !important;
    border-color: #0043ce !important;
    box-shadow: none !important;
  }
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3)) > [data-testid="stColumn"]:nth-child(1) .stButton > button p,
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3)) > [data-testid="stColumn"]:nth-child(1) .stButton > button span,
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3)) > [data-testid="stColumn"]:nth-child(3) .stButton > button p,
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(3)) > [data-testid="stColumn"]:nth-child(3) .stButton > button span {
    color: #0043ce !important;
    font-size: 12px !important;
    font-weight: 400 !important;
  }

  /* ── Refresh button — smaller, ghost ── */
  div[data-testid="column"]:has(button[kind="secondary"]) .stButton > button,
  .refresh-btn .stButton > button {
    background: #ffffff !important; border: 1px solid #e0e0e0 !important;
    color: #525252 !important; font-weight: 400 !important; font-size: 12px !important;
    padding: 5px 12px !important;
  }
  .refresh-btn .stButton > button:hover {
    background: #f4f4f4 !important; color: #161616 !important;
  }

  /* ── Inputs ── */
  input, textarea, select {
    background: #ffffff !important; color: #161616 !important;
    border: 1px solid #e0e0e0 !important; border-radius: 0 !important; font-size: 13px !important;
  }
  input::placeholder, textarea::placeholder { color: #8d8d8d !important; opacity: 1 !important; }
  input:focus, textarea:focus { outline: 2px solid #0F62FE !important; outline-offset: 0 !important; }

  /* Streamlit text input wrapper */
  [data-testid="stTextInput"] > div > div {
    background: #ffffff !important; border-radius: 0 !important;
    border: 1px solid #e0e0e0 !important;
    overflow: hidden !important;
  }
  [data-testid="stTextInput"] input {
    background: #ffffff !important; color: #161616 !important;
    border: none !important;
  }
  [data-testid="stTextInput"] input::placeholder { color: #8d8d8d !important; opacity: 1 !important; }
  /* Hide "Press Enter to apply" hint globally */
  [data-testid="InputInstructions"],
  [data-testid="stTextInput"] > div > div > div:last-child:not(:first-child) {
    display: none !important;
  }
  [data-testid="stTextInput"] label,
  [data-testid="stTextInput"] label p { color: #161616 !important; }

  /* Streamlit text area wrapper */
  [data-testid="stTextArea"] > div > div {
    background: #ffffff !important; border-radius: 0 !important;
    border: 1px solid #e0e0e0 !important;
  }
  [data-testid="stTextArea"] textarea {
    background: #ffffff !important; color: #161616 !important;
    border: none !important;
  }
  [data-testid="stTextArea"] textarea::placeholder { color: #8d8d8d !important; opacity: 1 !important; }
  [data-testid="stTextArea"] label,
  [data-testid="stTextArea"] label p { color: #161616 !important; }

  /* ── Selectbox ── */
  [data-testid="stSelectbox"] > div > div {
    background: #ffffff !important; border: 1px solid #e0e0e0 !important; border-radius: 0 !important;
  }
  [data-testid="stSelectbox"] svg { fill: #525252 !important; }

  /* ── Expanders ── */
  [data-testid="stExpander"] {
    background: #ffffff !important; border: 1px solid #e0e0e0 !important; border-radius: 0 !important;
  }
  [data-testid="stExpander"] summary {
    color: #161616 !important; font-weight: 600 !important;
    background: #ffffff !important;
  }
  [data-testid="stExpander"] summary:hover,
  [data-testid="stExpander"] summary:focus,
  [data-testid="stExpander"] summary:active {
    background: #f4f4f4 !important;
    color: #161616 !important;
  }
  [data-testid="stExpander"] > div { background: #f9f9f9 !important; }

  /* ── DataFrames ── */
  [data-testid="stDataFrame"] th {
    background: #f4f4f4 !important; color: #525252 !important;
    font-size: 11px !important; font-weight: 600 !important;
    text-transform: uppercase !important; letter-spacing: .4px !important;
  }
  [data-testid="stDataFrame"] td { background: #ffffff !important; color: #161616 !important; }

  /* ── Chat messages ── */
  [data-testid="stChatMessage"] {
    background: #ffffff !important; border: 1px solid #e0e0e0 !important;
    border-radius: 0 !important;
  }
  /* ── Chat input bar — dark grey cohesive bar ── */
  [data-testid="stBottom"],
  [data-testid="stBottom"] > div,
  [data-testid="stBottom"] > div > div {
    background: #2d2d2d !important;
    border-top: none !important;
    padding-top: 0 !important;
    margin-top: 0 !important;
  }
  [data-testid="stChatInput"],
  [data-testid="stChatInput"] > div,
  [data-testid="stChatInput"] > div > div {
    background: #2d2d2d !important;
    border: none !important;
  }
  [data-testid="stChatInput"] textarea {
    background: #3d3d3d !important;
    color: #f4f4f4 !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 10px 16px !important;
    font-size: 14px !important;
  }
  [data-testid="stChatInput"] textarea::placeholder { color: #a8a8a8 !important; }
  [data-testid="stChatInput"] button svg path { fill: #ffffff !important; }

  /* ── Bob chat bubbles ── */
  .bob-msg-label { font-size: 11px; font-weight: 600; color: #525252; margin-bottom: 4px; }
  .bob-bubble {
    background: #ffffff; border: 1px solid #e0e0e0;
    border-radius: 0; padding: 12px 16px;
    font-size: 13px; line-height: 1.6; color: #161616;
    margin-bottom: 12px;
  }
  .user-bubble {
    background: #2451e3;
    padding: 10px 14px; font-size: 13px;
    line-height: 1.5; color: #ffffff;
    margin-bottom: 12px; text-align: right;
    border-radius: 0;
  }
  .user-msg-label { font-size: 11px; color: #525252; margin-bottom: 3px; text-align: right; }

  /* ── Metric cards ── */
  [data-testid="metric-container"] {
    background: #ffffff !important; border: 1px solid #e0e0e0 !important;
    padding: 16px !important; border-radius: 0 !important;
  }

  /* ══════════════════════════════════════════
     IBM DESIGN-SYSTEM COMPONENTS
     (all rendered via st.markdown unsafe_allow_html)
  ══════════════════════════════════════════ */

  /* Tags */
  .tag { display:inline-block; font-size:11px; font-weight:600; padding:2px 8px;
    border-radius:2px; text-transform:uppercase; letter-spacing:.4px; }
  .tag-opportunity { background:#defbe6; color:#198038; border:1px solid #a7f0ba; }
  .tag-risk        { background:#fff1f1; color:#da1e28; border:1px solid #ffb3b8; }
  .tag-competitor  { background:#f6f2ff; color:#6929c4; border:1px solid #d4bbff; }
  .tag-exec        { background:#fdf6c3; color:#684e00; border:1px solid #f1c21b; }
  .tag-blue        { background:#edf5ff; color:#0043ce; border:1px solid #97c1ff; }
  .tag-strong      { background:#defbe6; color:#198038; border:1px solid #a7f0ba; }
  .tag-moderate    { background:#fdf6c3; color:#684e00; border:1px solid #f1c21b; }
  .tag-cold        { background:#fff1f1; color:#da1e28; border:1px solid #ffb3b8; }
  .tag-advantaged  { background:#defbe6; color:#198038; border:1px solid #a7f0ba; }
  .tag-even        { background:#fdf6c3; color:#684e00; border:1px solid #f1c21b; }
  .tag-at-risk     { background:#fff1f1; color:#da1e28; border:1px solid #ffb3b8; }

  /* Cards */
  .ibm-card { background:#ffffff; border:1px solid #e0e0e0; padding:20px; margin-bottom:16px; }
  .card-title { font-size:11px; font-weight:600; color:#525252; text-transform:uppercase;
    letter-spacing:.5px; margin-bottom:12px; }

  /* News items */
  .news-item { background:#ffffff; border:1px solid #e0e0e0; border-left:3px solid #e0e0e0;
    padding:16px 18px; margin-bottom:12px; display:flex; gap:16px; align-items:flex-start; }
  .news-item.tag-border-risk { border-left-color:#da1e28; }
  .news-item.tag-border-exec { border-left-color:#f1c21b; }
  .news-item.tag-border-opp  { border-left-color:#198038; }
  .news-item.tag-border-comp { border-left-color:#6929c4; }
  .news-body  { flex:1; min-width:0; }
  .news-meta  { font-size:12px; color:#525252; margin-top:4px; }
  .news-summary { font-size:13px; color:#525252; margin-top:6px; line-height:1.5; }
  .news-actions { display:flex; flex-direction:column; gap:6px; flex-shrink:0; padding-top:2px; }
  .btn-sm {
    font-size:11px; padding:4px 10px; border:1px solid #e0e0e0;
    background:#ffffff; color:#525252; cursor:pointer; white-space:nowrap;
    font-family:-apple-system,"Segoe UI",sans-serif; text-align:center;
    display:block; width:96px;
  }
  .btn-sm:hover { background:#f4f4f4; color:#161616; }
  .btn-sm.flagged { background:#fdf6c3; color:#684e00; border-color:#f1c21b; }
  .dismissed { opacity:.35; }

  /* Stat grid */
  .stat-grid   { display:grid; gap:12px; margin-bottom:20px; }
  .stat-grid-4 { grid-template-columns:repeat(4,1fr); }
  .stat-grid-3 { grid-template-columns:repeat(3,1fr); }
  .stat-card   { background:#ffffff; border:1px solid #e0e0e0; padding:16px; }
  .stat-label  { font-size:11px; color:#525252; text-transform:uppercase; letter-spacing:.4px; margin-bottom:6px; }
  .stat-value  { font-size:22px; font-weight:700; color:#161616; }
  .stat-sub    { font-size:12px; color:#525252; margin-top:2px; }
  .text-green  { color:#198038 !important; }
  .text-red    { color:#da1e28 !important; }
  .text-yellow { color:#b28600 !important; }
  .text-blue   { color:#0043ce !important; }

  /* Progress bars */
  .progress-bar  { height:6px; background:#e0e0e0; width:100%; margin-top:5px; }
  .progress-fill { height:100%; background:#0F62FE; }
  .progress-fill.high { background:#da1e28; }
  .progress-fill.warn { background:#f1c21b; }

  /* Chips */
  .chip     { display:inline-block; background:#f4f4f4; border:1px solid #e0e0e0;
    color:#525252; font-size:11px; padding:2px 8px; border-radius:12px; margin:2px; }
  .chip.ibm { background:#edf5ff; color:#0043ce; border-color:#97c1ff; }
  .chip-row { display:flex; flex-wrap:wrap; gap:4px; margin-top:6px; }

  /* Meeting cards */
  .meeting-card   { background:#ffffff; border:1px solid #e0e0e0; padding:18px; margin-bottom:14px; }
  .meeting-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px; }
  .meeting-title  { font-size:15px; font-weight:600; color:#161616; }
  .meeting-meta   { font-size:12px; color:#525252; margin-top:3px; }
  .prep-badge     { font-size:11px; font-weight:600; padding:3px 10px; border-radius:2px; flex-shrink:0; }
  .prep-complete  { background:#defbe6; color:#198038; border:1px solid #a7f0ba; }
  .prep-needs     { background:#fdf6c3; color:#684e00; border:1px solid #f1c21b; }
  .prep-no        { background:#fff1f1; color:#da1e28; border:1px solid #ffb3b8; }
  .attendee-label { font-size:12px; color:#525252; margin-top:8px; margin-bottom:3px; }

  /* LinkedIn prospect cards */
  .li-card          { background:#ffffff; border:1px solid #e0e0e0; padding:16px 18px; margin-bottom:12px; }
  .li-card-header   { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px; }
  .li-card-info     { flex:1; min-width:0; }
  .li-card-name     { font-size:14px; font-weight:600; color:#161616; }
  .li-card-role     { font-size:12px; color:#525252; margin-top:2px; }
  .li-card-location { font-size:12px; color:#525252; margin-top:2px; }
  .li-card-reason   { font-size:12px; color:#0043ce; margin-bottom:10px; line-height:1.5; }
  .li-reason-label  { font-size:11px; color:#525252; text-transform:uppercase; letter-spacing:.4px; display:block; margin-bottom:2px; }
  .li-card-link     { font-size:12px; color:#0043ce; text-decoration:none; border:1px solid #97c1ff; padding:4px 12px; display:inline-block; }
  .li-card-badge    { flex-shrink:0; margin-left:10px; }

  /* Tables */
  .ibm-table { width:100%; border-collapse:collapse; font-size:13px; }
  .ibm-table th { text-align:left; font-size:11px; font-weight:600; color:#525252;
    text-transform:uppercase; letter-spacing:.4px; padding:8px 12px; border-bottom:1px solid #e0e0e0; }
  .ibm-table td { padding:10px 12px; border-bottom:1px solid #e8e8e8; vertical-align:top; color:#161616; }
  .ibm-table tr:last-child td { border-bottom:none; }
  .ibm-table tr:hover td { background:#f9f9f9; }
  .ibm-table td.muted { color:#525252; }

  /* Bullet list */
  .bullet-list { list-style:none; padding:0; margin:0; }
  .bullet-list li { padding:8px 0; border-bottom:1px solid #e8e8e8; font-size:13px;
    display:flex; gap:10px; align-items:flex-start; }
  .bullet-list li:last-child { border-bottom:none; }
  .bullet-dot { width:6px; height:6px; border-radius:50%; background:#0F62FE;
    margin-top:6px; flex-shrink:0; }
  .bullet-dot.green  { background:#198038; }
  .bullet-dot.yellow { background:#f1c21b; }
  .bullet-dot.blue   { background:#0F62FE; }

  /* Alert banners */
  .renewal-alert { background:#fdf6c3; border:1px solid #f1c21b; color:#684e00;
    font-size:12px; padding:6px 12px; margin-bottom:8px; }
  .upsell-alert  { background:#edf5ff; border:1px solid #97c1ff; color:#0043ce;
    font-size:12px; padding:6px 12px; margin-bottom:8px; }

  /* Grids */
  .grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  .grid-3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }

  /* Pill row */
  .pill-row { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }

  /* Section subtitle */
  .section-sub { font-size:13px; color:#525252; margin-top:2px; margin-bottom:20px; }

  /* Chat bubbles */
  .bubble-bob  { background:#f4f4f4; border:1px solid #e0e0e0; padding:10px 14px;
    font-size:13px; line-height:1.5; color:#161616; margin-bottom:8px; border-radius:10px; }
  .bubble-user { background:#2451e3; padding:10px 14px; font-size:13px;
    line-height:1.5; color:#fff; margin-bottom:8px; text-align:right; border-radius:10px; }
  .msg-name      { font-size:11px; color:#525252; margin-bottom:3px; }
  .msg-name-user { font-size:11px; color:#525252; margin-bottom:3px; text-align:right; }

  /* ── Selectbox / account-switcher dropdown popover ── */
  [data-baseweb="popover"] * { background: #ffffff !important; color: #161616 !important; }
  [data-baseweb="popover"] [role="option"],
  [data-baseweb="popover"] li {
    background: #ffffff !important;
    color: #161616 !important;
    font-size: 13px !important;
  }
  [data-baseweb="popover"] [role="option"]:hover,
  [data-baseweb="popover"] li:hover,
  [data-baseweb="popover"] [aria-selected="true"] {
    background: #e8f0ff !important;
    color: #0F62FE !important;
  }
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
if "tavily_news" not in st.session_state:
    st.session_state.tavily_news = None       # list of live news items or None
if "tavily_alerts" not in st.session_state:
    st.session_state.tavily_alerts = None     # list of live industry alerts or None
if "tavily_fetched_for" not in st.session_state:
    st.session_state.tavily_fetched_for = ""  # account name last fetched
if "linkedin_prospects" not in st.session_state:
    st.session_state.linkedin_prospects = None    # list of prospect dicts or None
if "linkedin_fetched_for" not in st.session_state:
    st.session_state.linkedin_fetched_for = ""    # account name last fetched
if "linkedin_error" not in st.session_state:
    st.session_state.linkedin_error = None        # last error message or None

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

MEETING_NOTES = {
    "mtg_001": {
        "notes": [
            {"date": "Jun 4, 2026",  "author": "Sarah Mitchell", "text": "Dr. Priya Nair confirmed EU AI Act compliance is a board-level priority for FY2026. She specifically asked for a demo of watsonx.governance audit trail capabilities before the proposal is finalised."},
            {"date": "May 30, 2026", "author": "James Okonkwo",  "text": "Technical pre-call with Mark Henderson — he raised concerns about latency on the current watsonx.ai inference API. Need to address INC0044102 resolution timeline in the proposal meeting."},
            {"date": "May 22, 2026", "author": "Sarah Mitchell", "text": "Lisa Tran (Procurement) reached out asking for a formal RFP response. She wants total cost of ownership figures and a comparison against Azure OpenAI. Include this in deck."},
            {"date": "May 14, 2026", "author": "Dr. Anita Rowe",  "text": "Executive sponsor dinner debrief: Accenture CEO NA confirmed Q3 close window is firm — any delays in proposal submission risk pushing to Q4 budget cycle. Must submit by Jun 25."},
            {"date": "Apr 30, 2026", "author": "Sarah Mitchell", "text": "Initial scoping call — Accenture is evaluating watsonx expansion to cover 5,000 additional seats across FS and Supply Chain divisions. Budget pre-approved at $8.4M TCV."},
        ],
        "ai_summary": [
            ("Key Theme", "This meeting centres on closing the watsonx Enterprise Expansion proposal at $8.4M TCV. All saved notes point to a high-urgency close window driven by the EU AI Act deadline and Accenture's Q3 budget cycle."),
            ("Critical Actions Before June 18", "Address the open watsonx.ai API latency issue (INC0044102) — Mark Henderson flagged this as a blocker. Prepare a TCO comparison against Azure OpenAI for Lisa Tran in Procurement, and include a live demo of the watsonx.governance audit trail for Dr. Priya Nair."),
            ("Risk Signal", "Any proposal delay beyond June 25 risks a Q4 push — the CEO's office has confirmed the Q3 budget window is firm. Lisa Tran's engagement as Procurement gatekeeper is critical; re-engage her proactively before the meeting."),
            ("Opportunity", "Priya Nair is an IBM advocate with board-level backing. Leading with the EU AI Act compliance story and watsonx.governance differentiators is the strongest opening for this proposal."),
        ],
    },
    "mtg_002": {
        "notes": [
            {"date": "Jun 10, 2026", "author": "Chris Adeyemi",  "text": "Rachel Park confirmed Sterling utilisation has hit 93% across the supplier onboarding module. She is actively building a business case for the premium tier upgrade — needs IBM pricing by end of June."},
            {"date": "Jun 2, 2026",  "author": "Sarah Mitchell", "text": "Tom Burgess (Architect) sent a list of 12 new supplier integrations they want to onboard in Q3. The current licence tier caps them at 8 concurrent EDI streams. This is a natural upsell entry point."},
            {"date": "May 22, 2026", "author": "Chris Adeyemi",  "text": "Prep note: IBM Sterling Supply Chain won the 2026 Digital Supply Chain Excellence Award in partnership with Accenture. Bring the award plaque photo and press release as a relationship reinforcement moment."},
            {"date": "Apr 30, 2026", "author": "Sarah Mitchell", "text": "Sterling renewal confirmed for November 2026 — Rachel Park signed off. Premium tier is under active consideration pending a Q3 2026 ROI review."},
            {"date": "Apr 10, 2026", "author": "Chris Adeyemi",  "text": "AWS Supply Chain sales rep contacted Tom Burgess directly with a competitive pitch. Tom forwarded the deck to Rachel — need to counter with IBM's 20-year track record and the award win at QBR."},
        ],
        "ai_summary": [
            ("Key Theme", "This is a strong, relationship-rich account with 93% Sterling utilisation creating a natural and well-timed upsell conversation. The November 2026 renewal is secured; the premium tier upgrade is the primary commercial objective for this QBR."),
            ("Upsell Angle", "Tom Burgess's 12 new supplier integrations exceed the current EDI stream cap — use this as the concrete business justification for the premium tier. Bring IBM pricing by end of June as Rachel Park has already started an internal business case."),
            ("Competitive Threat", "AWS Supply Chain has engaged Tom Burgess directly. Counter with IBM's 20-year enterprise depth, the award win, and the Accenture co-sell relationship — AWS Supply Chain is nascent with limited EDI integration track record."),
            ("Relationship Strength", "Rachel Park and Chris Adeyemi have a strong rapport. The 2026 Award win is a powerful relationship-reinforcement moment — lead with it to set a positive tone before the commercial discussion."),
        ],
    },
    "mtg_003": {
        "notes": [
            {"date": "Jun 8, 2026",  "author": "Dr. Anita Rowe",  "text": "Dr. Priya Nair requested a deep-dive into model explainability reports and how they satisfy Article 13 (transparency) and Article 17 (quality management) requirements of the EU AI Act. Need to build this into the workshop agenda."},
            {"date": "Jun 5, 2026",  "author": "Sarah Mitchell", "text": "Accenture Legal (TBC) needs to confirm attendance — if they cannot attend, request to record the session. The legal team's sign-off is required before any procurement action on the watsonx.governance renewal."},
            {"date": "May 28, 2026", "author": "Dr. Anita Rowe",  "text": "IBM Legal SME confirmed as available — waiting on internal clearance to share the full EU AI Act compliance framework document. This should be shared 48 hours before the workshop via secure channel."},
            {"date": "May 20, 2026", "author": "Sarah Mitchell", "text": "Mark Henderson confirmed that Accenture's FS division has 14 production AI models that fall under high-risk classification under the EU AI Act. All 14 require model cards and audit trail documentation before Q3 enforcement."},
            {"date": "May 10, 2026", "author": "James Okonkwo",  "text": "Pre-workshop scoping: watsonx.governance renewal (Sep 30) is 90 days out. Aligning the renewal proposal with this compliance workshop is the optimal path — Priya Nair has budget authority and urgency."},
        ],
        "ai_summary": [
            ("Key Theme", "This 120-minute workshop is the pivotal moment to align the watsonx.governance renewal ($2.1M + $600K add-on) with Accenture's EU AI Act compliance deadline. All notes indicate both urgency and strong executive buy-in from Dr. Priya Nair."),
            ("Must-Cover in Workshop", "EU AI Act Article 13 (transparency) and Article 17 (quality management) compliance via watsonx.governance — specifically model explainability reports, model cards, and automated audit trails. Accenture has 14 high-risk AI models requiring coverage before Q3 enforcement."),
            ("Legal Dependency", "Accenture Legal attendance is unconfirmed (TBC). If they cannot attend, ensure the session is recorded. Their sign-off is a procurement prerequisite — without it the renewal process cannot advance."),
            ("Timing Opportunity", "The watsonx.governance renewal is due September 30 — 90 days from now. Coupling the renewal proposal to the workshop output creates a natural, low-friction close path. Priya Nair has both budget authority and the urgency to act."),
        ],
    },
}

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
    account = st.session_state.account
    client_name = profile["client_name"]
    client_email = profile["client_email"]
    total_pipeline = sum(int(o["amount"].replace("$", "").replace(",", "")) for o in crm_opps)
    top_competitor = competitors[0]
    top_lead = leads[0]
    primary_meeting = upcoming_meetings[0]
    top_opp = crm_opps[0]
    primary_relationship = relationship_map[0]
    primary_ticket = tickets[0]
    primary_seismic = seismic_content[0]

    # ── Resolve live vs mock news for Bob ──────────────────────
    # If Tavily data is already cached (fetched from the Morning News tab), use it.
    # Otherwise fetch now so Bob always shows live results when the API key is set.
    if st.session_state.get("tavily_news") and st.session_state.get("tavily_fetched_for") == account:
        _bob_news = st.session_state.tavily_news
    elif bool(os.environ.get("TAVILY_API_KEY", "").strip()):
        _live, _alerts, _err = fetch_tavily_news(account, profile["industry"])
        if _live:
            st.session_state.tavily_news = _live
            st.session_state.tavily_alerts = _alerts
            st.session_state.tavily_fetched_for = account
            _bob_news = _live
        else:
            _bob_news = news_items
    else:
        _bob_news = news_items

    top_news = _bob_news[0]

    def _news_route():
        lines = [f"**Morning News for {account}** — routing through `morning_news_agent` ⚡ *live via Tavily*\n"]
        for item in _bob_news[:5]:
            url = item.get("url", "")
            src = f"[{item['source']}]({url})" if url else item["source"]
            lines.append(f"{item['tag']} — **{item['title']}** *({src}, {item['date']})*")
        lines.append(f"\n💡 Want me to flag the top news item as important, or pull a competitive battlecard?")
        return "\n".join(lines)

    routes = [
        (r"what'?s new|news|press release|announcement|this week", _news_route),
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
    st.markdown("""
<style>
  [data-testid="stSidebar"]          { display:none !important; }
  header[data-testid="stHeader"]     { display:none !important; }
  #stDecoration                      { display:none !important; }

  /* ── Page shell ── */
  .stApp, html, body                 { background:#f4f4f4 !important; }
  .block-container {
    padding: 0 !important;
    max-width: 100% !important;
  }

  /* ── Centre the whole login column ── */
  .login-heading {
    font-size: 28px;
    font-weight: 300;
    color: #161616;
    line-height: 1.25;
    margin: 0 0 6px;
    text-align: center;
  }
  .login-sub {
    font-size: 14px;
    color: #525252;
    margin: 0 0 28px;
    text-align: center;
  }

  /* ── Input fields ── */
  [data-testid="stTextInput"] label {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #161616 !important;
    margin-bottom: 4px !important;
  }
  [data-testid="stTextInput"] > div > div {
    background: #ffffff !important;
    border: 1px solid #8d8d8d !important;
    border-radius: 0 !important;
    overflow: hidden !important;
  }
  [data-testid="stTextInput"] input {
    background: #ffffff !important;
    color: #161616 !important;
    font-size: 14px !important;
    border: none !important;
  }
  [data-testid="stTextInput"] input::placeholder {
    color: #8d8d8d !important;
  }
  [data-testid="stTextInput"] > div > div:focus-within {
    border: 2px solid #0F62FE !important;
    outline: none !important;
    box-shadow: none !important;
  }
  /* Hide "Press Enter to apply" hint */
  [data-testid="stTextInput"] [data-testid="InputInstructions"],
  [data-testid="stTextInput"] div[class*="instructions"],
  [data-baseweb="input"] + div,
  small.st-emotion-cache-1dp5vir,
  [data-testid="stTextInput"] > div > div > div:last-child:not(:first-child) {
    display: none !important;
  }

  /* ── Sign-in button ── */
  .login-col .stButton > button {
    background: #0F62FE !important;
    color: #fff !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    padding: 0 !important;
    height: 48px !important;
    border-radius: 0 !important;
    border: none !important;
    width: 100% !important;
    letter-spacing: 0.1px;
  }
  .login-col .stButton > button:hover { background: #0353E9 !important; }

  /* ── Checkbox ── */
  [data-testid="stCheckbox"] label {
    color: #161616 !important;
    font-size: 14px !important;
  }
  [data-testid="stCheckbox"] p { color: #161616 !important; }

  /* ── Forgot password link ── */
  .login-forgot a {
    color: #0F62FE;
    font-size: 14px;
    text-decoration: none;
  }
  .login-forgot a:hover { text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

    # Centre column holds all login content — no card box wrapper
    _lg, _lc, _lr = st.columns([1, 2, 1])
    with _lc:
        st.markdown('<div class="login-col">', unsafe_allow_html=True)

        st.markdown("<div style='height:72px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<p class="login-heading">Welcome to IBM Sales Intelligence Hub</p>'
            '<p class="login-sub">Sign in with your w3id and password</p>',
            unsafe_allow_html=True,
        )

        w3id_email = st.text_input(
            "IBM email address",
            placeholder="e.g. jdoe@ibm.com",
            key="login_email",
        )
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        password = st.text_input(
            "Password",
            placeholder="Enter your password",
            type="password",
            key="login_password",
        )
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="login-forgot"><a href="#">Forgot password?</a></div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.checkbox("Remember my IBM email address", key="login_remember")
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

        if st.button("Sign in", use_container_width=True, key="login_btn"):
            if not w3id_email.strip():
                st.error("Please enter your IBM email address.")
            elif not password.strip():
                st.error("Please enter your password.")
            else:
                local_part = w3id_email.split("@")[0]
                display_name = " ".join(p.capitalize() for p in re.split(r"[._\-]", local_part))
                default_account = "Accenture"
                st.session_state.logged_in = True
                st.session_state.rep = display_name
                st.session_state.account = default_account
                st.session_state.chat_history = [{
                    "role": "bob",
                    "content": (
                        f"Good morning, {display_name.split()[0]}. I'm Bob, your IBM Sales Intelligence assistant — "
                        f"routing through the `sales_hub_orchestrator_agent`. I'm loaded with everything on **{default_account}**: "
                        "news, meetings, pipeline, competitive intel, and more. What do you need today?"
                    )
                }]
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
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
# Tab key stored in session_state so buttons can update it
if "tab" not in st.session_state:
    st.session_state.tab = "⊞ Morning News"

_NAV = [
    ("Intelligence", [
        ("⊞", "Morning News"),
        ("⊟", "Account Overview"),
        ("⊗", "Competitor Analysis"),
        ("≡", "Exec Summary"),
    ]),
    ("Relationships", [
        ("⊡", "Meetings & Relationships"),
        ("⊕", "IBM Partnerships"),
    ]),
    ("AI Tools", [
        ("⊙", "AI Agent Launchpad"),
        ("◉", "Ask Bob"),
    ]),
]

with st.sidebar:
    # ── Sidebar header ──────────────────────────────────────────
    st.markdown(f"""
<div style="padding:14px 20px 12px;border-bottom:1px solid #eeeeee;">
  <div style="font-size:18px;font-weight:700;color:#2451e3;letter-spacing:0.3px;margin-bottom:1px;font-family:-apple-system,'Segoe UI',sans-serif;">IBM</div>
  <div style="font-size:12px;color:#9e9e9e;letter-spacing:0.2px;margin-bottom:10px;font-family:-apple-system,'Segoe UI',sans-serif;">Sales Intelligence Hub</div>
  <div style="font-size:13px;font-weight:600;color:#222222;margin-bottom:1px;font-family:-apple-system,'Segoe UI',sans-serif;">{rep}</div>
  <div style="font-size:12px;color:#9e9e9e;margin-bottom:8px;font-family:-apple-system,'Segoe UI',sans-serif;">IBM Global Account Executive</div>
  <span style="display:inline-block;font-size:11px;font-weight:600;padding:3px 10px;
    background:#eef2ff;color:#2451e3;border:1px solid #c7d2fe;border-radius:4px;
    font-family:-apple-system,'Segoe UI',sans-serif;letter-spacing:.3px;">{account}</span>
</div>
""", unsafe_allow_html=True)

    # ── Grouped nav sections ──────────────────────────────────
    for section_label, items in _NAV:
        st.markdown(
            f'<div class="sb-section-label">{section_label}</div>',
            unsafe_allow_html=True,
        )
        for icon, label in items:
            full_label = f"{icon} {label}"
            is_active = st.session_state.tab == full_label
            # Wrap in a div with nav-active class when active so CSS can target it
            if is_active:
                st.markdown('<div class="nav-active">', unsafe_allow_html=True)
            if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
                st.session_state.tab = full_label
                st.rerun()
            if is_active:
                st.markdown('</div>', unsafe_allow_html=True)

    # ── Footer: date + logout ─────────────────────────────────
    st.markdown(
        f'<div style="border-top:1px solid #eeeeee;padding:12px 20px 8px;'
        f'font-size:12px;color:#9e9e9e;font-family:-apple-system,\'Segoe UI\',sans-serif;">'
        f'Today: {date.today().strftime("%B %d, %Y")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sb-logout">', unsafe_allow_html=True)
    if st.button("← Log Out", use_container_width=True, key="logout_btn"):
        st.session_state.logged_in = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

tab = st.session_state.tab

# ── Fixed top header bar ──────────────────────────────────────
# The IBM logo/title bar is a pure position:fixed HTML element.
# The account switcher is a real st.selectbox placed in a slim
# columns row; we give it a stable key so we can CSS-target its
# *element container* parent with position:fixed.
st.markdown(f"""
<style>
  /* ── Header bar ── */
  .ibm-topbar {{
    position: fixed; top: 0; left: 0; right: 0; height: 48px;
    background: #2451e3;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 20px; z-index: 9000;
    font-family: -apple-system,"Segoe UI",system-ui,sans-serif;
  }}

  /* ── Account switcher — pinned to topbar right ── */
  div[data-testid="element-container"][data-key="account_switcher"] {{
    position: fixed !important;
    top: 8px !important;
    right: 16px !important;
    width: 160px !important;
    z-index: 99999 !important;
  }}
  div[data-testid="element-container"][data-key="account_switcher"] label {{
    display: none !important;
  }}
  div[data-testid="element-container"][data-key="account_switcher"] [data-baseweb="select"] > div {{
    background: transparent !important; border: 1.5px solid rgba(255,255,255,0.7) !important;
    border-radius: 4px !important; min-height: 32px !important; padding: 0 8px !important;
  }}
  div[data-testid="element-container"][data-key="account_switcher"] [data-baseweb="select"] span {{
    color: #ffffff !important; font-weight: 700 !important; font-size: 13px !important;
  }}
  div[data-testid="element-container"][data-key="account_switcher"] svg {{
    fill: #ffffff !important;
  }}
</style>

<div class="ibm-topbar">
  <div style="display:flex;align-items:center;gap:0;">
    <button onclick="
      (document.querySelector('[data-testid=stSidebarCollapseButton] button')
      || document.querySelector('[data-testid=stSidebarCollapsedControl] button')
      || document.querySelector('button[aria-label=Close]')
      || document.querySelector('button[aria-label=Open]')
      || Array.from(document.querySelectorAll('button')).find(b => b.getAttribute('aria-expanded') !== null)
      )?.click();
    " style="background:transparent;border:none;cursor:pointer;color:#ffffff;
             font-size:18px;padding:0 16px 0 0;line-height:1;" title="Toggle sidebar">&#9776;</button>
    <span style="font-size:17px;font-weight:700;color:#ffffff;letter-spacing:0.5px;font-family:-apple-system,'Segoe UI',sans-serif;">IBM</span>
    <div style="width:1px;height:20px;background:rgba(255,255,255,0.35);margin:0 14px;"></div>
    <span style="font-size:14px;color:#ffffff;font-weight:400;font-family:-apple-system,'Segoe UI',sans-serif;">Sales Intelligence Hub</span>
  </div>
  <div style="display:flex;align-items:center;gap:12px;">
    <span style="font-size:13px;color:rgba(255,255,255,0.8);font-family:-apple-system,'Segoe UI',sans-serif;">Account: <strong style="color:#ffffff;">{account}</strong></span>
    <div style="width:1px;height:16px;background:rgba(255,255,255,0.35);"></div>
    <span style="font-size:13px;color:rgba(255,255,255,0.9);font-family:-apple-system,'Segoe UI',sans-serif;">{rep}</span>
  </div>
</div>
""", unsafe_allow_html=True)

_ACCOUNTS = ["Accenture", "Deloitte", "PwC", "EY", "KPMG"]
_current_idx = _ACCOUNTS.index(account) if account in _ACCOUNTS else 0
_selected_account = st.selectbox(
    "Account",
    _ACCOUNTS,
    index=_current_idx,
    key="account_switcher",
    label_visibility="collapsed",
)

if _selected_account != account:
    st.session_state.account = _selected_account
    st.session_state.tavily_news = None
    st.session_state.tavily_alerts = None
    st.session_state.tavily_fetched_for = ""
    st.session_state.linkedin_prospects = None
    st.session_state.linkedin_fetched_for = ""
    st.session_state.linkedin_error = None
    st.rerun()

# Re-read account after possible switch
account = st.session_state.account

# ─────────────────────────────────────────────────────────────
# TAB: MORNING NEWS
# ─────────────────────────────────────────────────────────────
def _tag_border(tag: str) -> str:
    if "Risk" in tag or "Competitor" in tag: return "tag-border-risk"
    if "Executive" in tag: return "tag-border-exec"
    if "Opportunity" in tag: return "tag-border-opp"
    return "tag-border-comp"

def _clean_tag(tag: str) -> str:
    """Strip emoji prefix, return bare label for rendering as HTML tag pill."""
    for prefix in ("🔴 ", "🟡 ", "🟢 ", "🔵 "):
        tag = tag.replace(prefix, "")
    return tag

def _tag_class(tag: str) -> str:
    t = _clean_tag(tag).lower()
    if "risk" in t: return "tag-risk"
    if "competitor" in t: return "tag-competitor"
    if "executive" in t: return "tag-exec"
    return "tag-opportunity"

def _pos_class(raw: str) -> str:
    s = raw.lower()
    if "at risk" in s or "⚠️" in s: return "tag-at-risk"
    if "even" in s or "🟡" in s: return "tag-even"
    return "tag-advantaged"

def _prep_class(status: str) -> str:
    s = status.lower()
    if "complete" in s: return "prep-complete"
    if "no brief" in s or "🔴" in s: return "prep-no"
    return "prep-needs"

def _eng_class(eng: str) -> str:
    e = eng.lower()
    if "strong" in e or "🟢" in e: return "tag-strong"
    if "cold" in e or "🔵" in e: return "tag-cold"
    return "tag-moderate"

if tab == "⊞ Morning News":
    st.markdown(f"""
<h1>Morning News &amp; Alerts — {account}</h1>
<p class="section-sub">Account-specific news and industry alerts — refreshed daily via Tavily.</p>
""", unsafe_allow_html=True)

    # ── Tavily live-refresh controls ──────────────────────────
    api_key_set = bool(os.environ.get("TAVILY_API_KEY", "").strip())
    hdr_col, refresh_col = st.columns([7, 1])
    with hdr_col:
        if api_key_set:
            st.markdown(
                f'<div style="font-size:12px;color:#198038;margin-bottom:12px;">'
                f'⚡ <strong>Live</strong> — Tavily web search · {account} · {profile["industry"]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div style="font-size:12px;color:#525252;margin-bottom:12px;">'
                '📋 <strong>Mock data</strong> — set <code>TAVILY_API_KEY</code> to enable live scraping.</div>',
                unsafe_allow_html=True
            )
    with refresh_col:
        refresh_clicked = st.button("🔄 Refresh", use_container_width=True, key="news_refresh")

    needs_fetch = api_key_set and (
        refresh_clicked
        or st.session_state.tavily_fetched_for != account
        or st.session_state.tavily_news is None
    )
    if needs_fetch:
        with st.spinner(f"Fetching live news for {account} via Tavily…"):
            live_news, live_alerts, err = fetch_tavily_news(account, profile["industry"])
        if err:
            st.warning(f"Tavily fetch failed: {err}. Showing mock data.")
        else:
            st.session_state.tavily_news = live_news
            st.session_state.tavily_alerts = live_alerts
            st.session_state.tavily_fetched_for = account
            if refresh_clicked:
                st.toast("✅ News refreshed via Tavily", icon="✅")

    display_news   = st.session_state.tavily_news if st.session_state.tavily_news else news_items
    display_alerts = st.session_state.tavily_alerts

    # ── Summary row ─────────────────────────────────────────
    opp_count  = sum(1 for n in display_news if "Opportunity" in n["tag"])
    risk_count = sum(1 for n in display_news if "Risk" in n["tag"])
    comp_count = sum(1 for n in display_news if "Competitor" in n["tag"])
    exec_count = sum(1 for n in display_news if "Executive" in n["tag"])

    alert_rows_html = ""
    for a in (display_alerts or [])[:3]:
        preview = a.get("preview", "")
        src_link = (
            f'<a href="{a["url"]}" target="_blank" style="color:#0043ce;font-size:12px;text-decoration:none;">'
            f'Read more →</a>' if a.get("url") else ""
        )
        alert_rows_html += (
            f'<div style="margin-bottom:12px;">'
            f'  <div style="font-size:13px;font-weight:600;color:#161616;margin-bottom:3px;">{a["title"]}</div>'
            f'  <div style="font-size:12px;color:#525252;">{a["date"]} · {a["source"]}</div>'
            f'  <div style="font-size:12px;color:#525252;margin-top:4px;line-height:1.5;">{preview}</div>'
            f'  <div style="margin-top:4px;">{src_link}</div>'
            f'</div><hr style="margin:10px 0;border-color:#e0e0e0;">'
        )
    if not alert_rows_html:
        alert_rows_html = '<div style="font-size:13px;color:#8d8d8d;">Live industry alerts appear here when Tavily is enabled.</div>'

    # Build top-3 headline rows for the summary card
    _headline_rows = ""
    for _item in (display_news or [])[:4]:
        _tc  = _tag_class(_item["tag"])
        _tl  = _clean_tag(_item["tag"])
        _dot_color = (
            "#da1e28" if "risk" in _tl.lower() or "competitor" in _tl.lower()
            else "#f1c21b" if "executive" in _tl.lower()
            else "#198038"
        )
        _headline_rows += (
            f'<div style="display:flex;gap:10px;align-items:flex-start;'
            f'padding:8px 0;border-bottom:1px solid #e0e0e0;">'
            f'  <span style="width:7px;height:7px;border-radius:50%;background:{_dot_color};'
            f'             flex-shrink:0;margin-top:5px;"></span>'
            f'  <div style="min-width:0;">'
            f'    <div style="font-size:12px;color:#161616;line-height:1.4;'
            f'               white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
            f'      {_item["title"]}</div>'
            f'    <div style="font-size:11px;color:#8d8d8d;margin-top:2px;">'
            f'      {_item.get("source","")} · {_item.get("date","")}</div>'
            f'  </div>'
            f'</div>'
        )

    st.markdown(f"""
<div class="grid-2" style="margin-bottom:24px;">
  <div class="ibm-card">
    <div class="card-title">News Summary — {account}</div>
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
      <span style="font-size:32px;font-weight:700;color:#161616;">{len(display_news)}</span>
      <span style="font-size:13px;color:#525252;">news items today</span>
    </div>
    <div class="pill-row" style="margin-bottom:16px;">
      <span class="tag tag-opportunity">{opp_count} Opportunit{"y" if opp_count==1 else "ies"}</span>
      <span class="tag tag-risk">{risk_count} Risk{"s" if risk_count!=1 else ""}</span>
      <span class="tag tag-competitor">{comp_count} Competitor Move{"s" if comp_count!=1 else ""}</span>
      <span class="tag tag-exec">{exec_count} Executive Change{"s" if exec_count!=1 else ""}</span>
    </div>
    <div style="border-top:1px solid #e0e0e0;padding-top:4px;">
      <div style="font-size:11px;font-weight:600;color:#8d8d8d;text-transform:uppercase;
                  letter-spacing:.5px;margin-bottom:2px;">Top Stories</div>
      {_headline_rows}
    </div>
  </div>
  <div class="ibm-card">
    <div class="card-title">Industry Alerts — {profile["industry"]}</div>
    {alert_rows_html}
  </div>
</div>
""", unsafe_allow_html=True)

    # ── News feed ────────────────────────────────────────────
    for item in display_news:
        flagged   = st.session_state.flagged_news.get(item["id"], "")
        dismissed = "opacity:0.4;" if flagged == "Dismiss" else ""
        border    = _tag_border(item["tag"])
        tag_cls   = _tag_class(item["tag"])
        tag_label = _clean_tag(item["tag"])

        # Source + article link
        url = item.get("url", "")
        src_display = item.get("source", "Web")
        src_link_html = (
            f'<a href="{url}" target="_blank" style="color:#0043ce;text-decoration:none;font-size:12px;">'
            f'{src_display}</a>' if url else f'<span style="font-size:12px;color:#525252;">{src_display}</span>'
        )
        read_more_html = (
            f'<a href="{url}" target="_blank" style="color:#0043ce;font-size:12px;text-decoration:none;'
            f'border:1px solid #97c1ff;padding:3px 10px;background:#edf5ff;">'
            f'Read article →</a>' if url else ""
        )

        # Important badge
        flag_badge = (
            '<span class="tag tag-exec" style="margin-left:8px;">⚑ Important</span>'
            if flagged == "Important" else ""
        )

        # Key bullet points
        bullets = item.get("bullets") or []
        if bullets:
            bullets_html = (
                '<div style="margin:10px 0 8px;padding:10px 12px;background:#f4f4f4;'
                'border-left:2px solid #e0e0e0;">'
                '<div style="font-size:11px;font-weight:600;color:#8d8d8d;text-transform:uppercase;'
                'letter-spacing:.5px;margin-bottom:6px;">Key Highlights</div>'
                + "".join(
                    f'<div style="display:flex;gap:8px;margin-bottom:5px;">'
                    f'  <span style="color:#0F62FE;font-size:12px;flex-shrink:0;margin-top:1px;">›</span>'
                    f'  <span style="font-size:13px;color:#525252;line-height:1.5;">{b}</span>'
                    f'</div>'
                    for b in bullets
                )
                + "</div>"
            )
        else:
            bullets_html = ""

        # Article preview
        preview = item.get("preview") or item.get("summary", "")
        preview_html = (
            f'<div style="font-size:12px;color:#525252;line-height:1.5;margin-top:8px;'
            f'padding-top:8px;border-top:1px solid #e0e0e0;">{preview}</div>'
            if preview else ""
        )

        # Card + side buttons in a flex row
        card_col, btn_col = st.columns([10, 2])

        with card_col:
            st.markdown(
                f'<div style="{dismissed}background:#ffffff;border:1px solid #e0e0e0;'
                f'border-left:3px solid transparent;padding:16px 18px;" class="{border}">'
                f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">'
                f'<span class="tag {tag_cls}">{tag_label}</span>'
                f'{flag_badge}'
                f'<span style="flex:1;"></span>'
                f'{src_link_html} &nbsp;<span style="color:#8d8d8d;font-size:12px;">·</span>&nbsp;'
                f'<span style="font-size:12px;color:#525252;">{item["date"]}</span>'
                f'</div>'
                f'<div style="font-size:14px;font-weight:600;color:#161616;line-height:1.4;margin-bottom:2px;">{item["title"]}</div>'
                f'{bullets_html}'
                f'{preview_html}'
                f'<div style="margin-top:10px;">{read_more_html}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with btn_col:
            if st.button("⚑  Mark Important", key=f"imp_{item['id']}", use_container_width=True):
                st.session_state.flagged_news[item["id"]] = "Important"
                st.toast("✅ Flagged as Important", icon="✅")
                st.rerun()
            if st.button("↗  Share with Team", key=f"share_{item['id']}", use_container_width=True):
                st.toast("📤 Shared with team", icon="📤")
            if st.button("✕  Dismiss", key=f"dis_{item['id']}", use_container_width=True):
                st.session_state.flagged_news[item["id"]] = "Dismiss"
                st.rerun()

        st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TAB: ACCOUNT OVERVIEW
# ─────────────────────────────────────────────────────────────
elif tab == "⊟ Account Overview":
    st.markdown(f"""
<h1>Account Overview — {account}</h1>
<p class="section-sub">IBM ISC Cloud data, active products, and account profile.</p>
""", unsafe_allow_html=True)

    # Stat row
    total_pipeline_str = "$" + "{:,.0f}".format(sum(int(o["amount"].replace("$","").replace(",","")) for o in crm_opps))
    st.markdown(f"""
<div class="stat-grid stat-grid-4">
  <div class="stat-card">
    <div class="stat-label">Annual Revenue</div>
    <div class="stat-value">{profile["revenue"].split()[0]}</div>
    <div class="stat-sub">{profile["revenue"].split("(")[-1].replace(")","") if "(" in profile["revenue"] else ""}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Employees</div>
    <div class="stat-value">{profile["employees"].replace(",000","K+")}</div>
    <div class="stat-sub">Global</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">IBM Account Tier</div>
    <div class="stat-value text-blue" style="font-size:16px;">{profile["ibm_tier"].split()[0]}</div>
    <div class="stat-sub">{profile["sales_stage"]}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Open Pipeline</div>
    <div class="stat-value text-green" style="font-size:18px;">{total_pipeline_str}</div>
    <div class="stat-sub">{len(crm_opps)} opportunities</div>
  </div>
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
<div class="ibm-card">
  <div class="card-title">Account Profile</div>
  <table class="ibm-table">
    <tr><td class="muted">Industry</td><td>{profile["industry"]}</td></tr>
    <tr><td class="muted">HQ</td><td>{profile["hq"]}</td></tr>
    <tr><td class="muted">Sales Stage</td><td><span class="tag tag-blue">{profile["sales_stage"]}</span></td></tr>
    <tr><td class="muted">Primary Contact</td><td>{profile["client_name"]}</td></tr>
    <tr><td class="muted">IBM Owner</td><td>{rep} (GAE)</td></tr>
    <tr><td class="muted">Alliance Manager</td><td>{profile["alliance_manager"]}</td></tr>
  </table>
</div>
""", unsafe_allow_html=True)

    with col2:
        tickets_html = ""
        for t in tickets:
            sev_cls = "tag-risk" if "Sev 2" in t["sev"] else "tag-exec" if "Sev 3" in t["sev"] else "tag-advantaged"
            tickets_html += (
                f'<div style="margin-bottom:12px;">'
                f'  <div style="display:flex;align-items:center;gap:8px;">'
                f'    <span class="tag {sev_cls}">{t["sev"]}</span>'
                f'    <strong>{t["id"]}</strong>'
                f'  </div>'
                f'  <div style="font-size:13px;margin-top:4px;">{t["title"]}</div>'
                f'  <div style="font-size:12px;color:#525252;margin-top:2px;">{t["status"]}</div>'
                f'</div><hr style="margin:8px 0;border-color:#e0e0e0;">'
            )
        st.markdown(f"""
<div class="ibm-card">
  <div class="card-title">Open Support Tickets</div>
  {tickets_html}
</div>
""", unsafe_allow_html=True)

    # Products table
    renewal_alerts = "".join(
        f'<div class="renewal-alert">⚠ Renewal Alert: {p["product"]} — due {p["renewal"]} (90 days)</div>'
        for p in products if p["alert"]
    )
    upsell_alerts = "".join(
        f'<div class="upsell-alert">↑ Upsell Signal: {p["product"]} at {p["usage"]} utilisation — capacity expansion candidate</div>'
        for p in products if int(p["usage"].replace("%","")) >= 85
    )
    rows = ""
    for p in products:
        pct = int(p["usage"].replace("%",""))
        fill_cls = "high" if pct >= 85 else "warn" if p["alert"] else ""
        st_cls = "tag-exec" if p["alert"] else "tag-at-risk" if pct >= 85 else "tag-advantaged"
        st_label = "Renewal Alert" if p["alert"] else "Upsell" if pct >= 85 else "Active"
        rows += (
            f'<tr>'
            f'  <td>{p["product"]}</td>'
            f'  <td><span class="tag tag-blue">{p["tier"]}</span></td>'
            f'  <td>{p["seats"]:,}</td>'
            f'  <td>{p["renewal"]}</td>'
            f'  <td>'
            f'    <div>{p["usage"]}</div>'
            f'    <div class="progress-bar"><div class="progress-fill {fill_cls}" style="width:{pct}%"></div></div>'
            f'  </td>'
            f'  <td><span class="tag {st_cls}">{st_label}</span></td>'
            f'</tr>'
        )
    st.markdown(f"""
<div class="ibm-card" style="margin-top:16px;">
  <div class="card-title">Active IBM Products &amp; Licenses</div>
  {renewal_alerts}{upsell_alerts}
  <table class="ibm-table" style="margin-top:8px;">
    <thead><tr><th>Product</th><th>License</th><th>Seats</th><th>Renewal</th><th>Usage</th><th>Status</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TAB: COMPETITOR ANALYSIS
# ─────────────────────────────────────────────────────────────
elif tab == "⊗ Competitor Analysis":
    st.markdown(f"""
<h1>Competitor Analysis — {account}</h1>
<p class="section-sub">Active competitors — expand any row to view the full IBM battlecard.</p>
""", unsafe_allow_html=True)

    wins  = sum(1 for _ in [1,2,3])  # mock
    losses = sum(1 for _ in [1,2])
    st.markdown(f"""
<div class="stat-grid stat-grid-3">
  <div class="stat-card"><div class="stat-label">Wins (12 mo)</div>
    <div class="stat-value text-green">3</div></div>
  <div class="stat-card"><div class="stat-label">Losses (12 mo)</div>
    <div class="stat-value text-red">2</div></div>
  <div class="stat-card"><div class="stat-label">Active Competitions</div>
    <div class="stat-value text-yellow">{len(competitors)}</div></div>
</div>
""", unsafe_allow_html=True)

    comp_rows = ""
    for comp in competitors:
        pos_cls = _pos_class(comp["status"])
        pos_label = comp["status"].replace("⚠️ ","").replace("🟡 ","").replace("✅ ","")
        comp_rows += (
            f'<tr>'
            f'  <td><strong>{comp["name"]}</strong></td>'
            f'  <td style="color:#525252;">{comp["products"]}</td>'
            f'  <td>{comp["deal_value"]}</td>'
            f'  <td><span class="tag {pos_cls}">{pos_label}</span></td>'
            f'</tr>'
        )
    st.markdown(f"""
<div class="ibm-card">
  <div class="card-title">Active Competitors</div>
  <table class="ibm-table">
    <thead><tr><th>Competitor</th><th>Products Considered</th><th>Est. Deal</th><th>IBM Position</th></tr></thead>
    <tbody>{comp_rows}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

    for comp in competitors:
        if comp["name"] not in battlecards:
            continue
        card = battlecards[comp["name"]]
        pos_cls = _pos_class(comp["status"])
        pos_label = comp["status"].replace("⚠️ ","").replace("🟡 ","").replace("✅ ","")
        with st.expander(f"📋 Battlecard — IBM vs {comp['name']}  ·  {comp['deal_value']}"):
            diff_items = "".join(f'<li><span class="bullet-dot blue"></span>{d}</li>' for d in card["differentiators"])
            weak_items = "".join(f'<li><span class="bullet-dot yellow"></span>{w}</li>' for w in card["weaknesses"])
            tp_items   = "".join(f'<li><span class="bullet-dot"></span><em>{t}</em></li>' for t in card["talking_points"])
            prods      = " ".join(f'<span class="tag tag-blue">{p}</span>' for p in card["products"])
            st.markdown(f"""
<div class="grid-2">
  <div>
    <div class="card-title">IBM Differentiators</div>
    <ul class="bullet-list">{diff_items}</ul>
    <div class="card-title" style="margin-top:16px;">IBM Products to Position</div>
    <div style="margin-top:6px;">{prods}</div>
  </div>
  <div>
    <div class="card-title">Competitor Weaknesses</div>
    <ul class="bullet-list">{weak_items}</ul>
    <div class="card-title" style="margin-top:16px;">Suggested Talking Points</div>
    <ul class="bullet-list">{tp_items}</ul>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TAB: EXEC SUMMARY
# ─────────────────────────────────────────────────────────────
elif tab == "≡ Exec Summary":
    top_opp_local = crm_opps[0]
    st.markdown(f"""
<h1>Executive Summary — {account}</h1>
<p class="section-sub">Call-prep brief for {rep} · Generated {date.today().strftime("%B %d, %Y")}</p>
""", unsafe_allow_html=True)

    copy_col, _ = st.columns([1, 5])
    with copy_col:
        if st.button("⎘ Copy to Clipboard"):
            st.toast("✅ Executive summary copied to clipboard.", icon="✅")

    st.markdown(f"""
<div class="ibm-card">
  <div class="card-title">Key Priorities</div>
  <ul class="bullet-list">
    <li><span class="bullet-dot blue"></span>{account} is accelerating EU AI Act compliance — IBM watsonx.governance renewal ({crm_opps[-1]["close"] if len(crm_opps) > 1 else "Sep 2026"}) is a critical near-term milestone.</li>
    <li><span class="bullet-dot blue"></span>AI and data modernization budget remains active — {account} has room to expand the watsonx enterprise deployment.</li>
    <li><span class="bullet-dot blue"></span>Re-engage executive sponsor {profile["client_name"]} within 2 weeks to progress IBM priorities.</li>
  </ul>
</div>
<div class="grid-2">
  <div class="ibm-card">
    <div class="card-title">Recent Wins</div>
    <ul class="bullet-list">
      <li><span class="bullet-dot green"></span>IBM Sterling Renewal &amp; Expansion — $4.1M · Feb 2026 · Beat AWS cost pitch</li>
      <li><span class="bullet-dot green"></span>watsonx.ai FS Pilot → Production — $3.2M · Nov 2025 · Beat Google Vertex AI</li>
    </ul>
  </div>
  <div class="ibm-card">
    <div class="card-title">Open Opportunities</div>
    <ul class="bullet-list">
      {"".join(f'<li><span class="bullet-dot yellow"></span>{o["name"]} — {o["amount"]} · {o["stage"]} · Close: {o["close"]}</li>' for o in crm_opps)}
    </ul>
  </div>
</div>
<div class="ibm-card">
  <div class="card-title">Recommended Next Steps</div>
  <ul class="bullet-list">
    <li><span class="bullet-dot blue"></span>Schedule intro call with {profile["client_name"]} within the next 2 weeks.</li>
    <li><span class="bullet-dot blue"></span>Prepare watsonx.governance renewal proposal — deadline pressure from EU AI Act.</li>
    <li><span class="bullet-dot blue"></span>Escalate highest-severity support ticket to demonstrate IBM support quality.</li>
    <li><span class="bullet-dot blue"></span>Share updated Seismic battlecard with the {account} account team.</li>
  </ul>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TAB: MEETINGS & RELATIONSHIPS
# ─────────────────────────────────────────────────────────────
elif tab == "⊡ Meetings & Relationships":
    st.markdown(f"""
<h1>Meetings &amp; Relationships — {account}</h1>
<p class="section-sub">Sourced from Outlook and Microsoft Teams. In production, live via Microsoft Graph API.</p>
""", unsafe_allow_html=True)

    st.markdown('<div class="card-title" style="margin-bottom:12px;">Upcoming Meetings</div>', unsafe_allow_html=True)

    if "expanded_meeting" not in st.session_state:
        st.session_state.expanded_meeting = None

    for m in upcoming_meetings:
        pc = _prep_class(m["status"])
        pl = m["status"].replace("⚠️ ","").replace("✅ ","").replace("🔴 ","")
        ibm_chips    = "".join(f'<span class="chip ibm">{a}</span>' for a in m["ibm"])
        client_chips = "".join(f'<span class="chip">{a}</span>' for a in m["client"])
        is_expanded  = st.session_state.expanded_meeting == m["id"]

        st.markdown(f"""
<div class="meeting-card" style="cursor:pointer;">
  <div class="meeting-header">
    <div>
      <div class="meeting-title">{m["title"]}</div>
      <div class="meeting-meta">📅 {m["date"]} · {m["time"]}</div>
    </div>
    <span class="prep-badge {pc}">{pl}</span>
  </div>
  <div class="attendee-label">IBM Attendees</div>
  <div class="chip-row">{ibm_chips}</div>
  <div class="attendee-label">Client Attendees</div>
  <div class="chip-row">{client_chips}</div>
</div>
""", unsafe_allow_html=True)

        # Initialise per-meeting note store in session state
        ss_key = f"saved_notes_{m['id']}"
        if ss_key not in st.session_state:
            st.session_state[ss_key] = []

        btn_col, note_col, save_col = st.columns([2, 5, 2])
        with btn_col:
            btn_label = "▲ Hide Notes" if is_expanded else "📋 View Notes"
            if st.button(btn_label, key=f"viewnotes_{m['id']}", use_container_width=True):
                st.session_state.expanded_meeting = None if is_expanded else m["id"]
                st.rerun()
        with note_col:
            note_counter = st.session_state.get(f"note_counter_{m['id']}", 0)
            note_val = st.text_input(
                f"Log note for {m['id']}",
                placeholder="Log a meeting note to save to Salesforce CRM…",
                key=f"note_{m['id']}_{note_counter}", label_visibility="collapsed"
            )
        with save_col:
            if st.button("💾 Save Note", key=f"savenote_{m['id']}", use_container_width=True):
                if note_val.strip():
                    today_str = date.today().strftime("%b %d, %Y")
                    st.session_state[ss_key].insert(0, {
                        "date":   today_str,
                        "author": rep,
                        "text":   note_val.strip(),
                        "new":    True,
                    })
                    # Clear the input by bumping its key via a counter
                    st.session_state[f"note_counter_{m['id']}"] = st.session_state.get(f"note_counter_{m['id']}", 0) + 1
                    # Keep notes panel open after save
                    st.session_state.expanded_meeting = m["id"]
                    st.toast(f"✅ Note saved to CRM for {m['id']} · {rep} · {today_str}", icon="✅")
                    st.rerun()
                else:
                    st.toast("⚠️ Please enter a note before saving.", icon="⚠️")

        if is_expanded:
            nd = MEETING_NOTES.get(m["id"], {})
            # User-added notes first, then mock notes
            user_notes = st.session_state.get(ss_key, [])
            mock_notes = nd.get("notes", [])
            notes      = user_notes + mock_notes
            ai_summ    = nd.get("ai_summary", [])

            # ── Saved notes ──────────────────────────────────────
            note_rows = "".join(
                f'<tr>'
                f'<td style="white-space:nowrap;color:#525252;font-size:11px;padding:8px 10px 8px 0;vertical-align:top;min-width:80px;">{n["date"]}</td>'
                f'<td style="white-space:nowrap;color:{"#198038" if n.get("new") else "#0043ce"};font-size:11px;padding:8px 10px 8px 0;vertical-align:top;min-width:110px;">{n["author"]}{"&nbsp;✓" if n.get("new") else ""}</td>'
                f'<td style="font-size:13px;line-height:1.55;padding:8px 0;color:#161616;">{n["text"]}</td>'
                f'</tr>'
                for n in notes
            )
            st.markdown(f"""
<div style="background:#ffffff;border:1px solid #e0e0e0;border-left:3px solid #0F62FE;padding:18px 20px;margin-bottom:4px;">
  <div style="font-size:11px;font-weight:600;color:#525252;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid #e0e0e0;">Saved Notes</div>
  <table style="width:100%;border-collapse:collapse;">
    <tbody>{note_rows}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

            # ── Bob AI Summary ────────────────────────────────────
            ai_paras = "".join(
                f'<p style="margin-bottom:10px;font-size:13px;line-height:1.65;color:#161616;">'
                f'<strong style="color:#0043ce;">{label}:</strong> {body}'
                f'</p>'
                for label, body in ai_summ
            )
            st.markdown(f"""
<div style="background:#edf5ff;border:1px solid #97c1ff;padding:18px 20px;margin-bottom:16px;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
    <span style="font-size:12px;font-weight:600;color:#0043ce;text-transform:uppercase;letter-spacing:0.5px;">Bob AI Summary</span>
    <span style="font-size:10px;background:#0F62FE;color:#fff;padding:2px 7px;font-weight:600;letter-spacing:0.3px;">watsonx Orchestrate</span>
  </div>
  {ai_paras}
  <div style="font-size:11px;color:#0043ce;margin-top:4px;opacity:0.7;">⚡ Generated by sales_hub_orchestrator_agent · meetings_relationships_agent</div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="card-title" style="margin-bottom:4px;">Key Contacts &amp; Interaction History</div>', unsafe_allow_html=True)
    st.markdown('<p class="section-sub" style="margin-bottom:16px;">Relationship status, IBM ownership, and last meeting outcome for each key contact.</p>', unsafe_allow_html=True)

    # Build a name → most-recent history entry lookup
    hist_by_contact = {}
    for h in meeting_history:
        for name in [r["contact"] for r in relationship_map]:
            if name.split()[1].lower() in h["attendees"].lower() or name.split()[0].lower() in h["attendees"].lower():
                if name not in hist_by_contact:
                    hist_by_contact[name] = h

    contact_cards = ""
    for r in relationship_map:
        ec  = _eng_class(r["engagement"])
        el  = r["engagement"].replace("🟢 ","").replace("🟡 ","").replace("🔵 ","")
        h   = hist_by_contact.get(r["contact"])

        # Engagement colour for the left border
        border_color = "#198038" if "Strong" in el else "#f1c21b" if "Moderate" in el else "#e0e0e0"

        last_meeting_html = (
            f'<div style="margin-top:10px;padding-top:10px;border-top:1px solid #e0e0e0;">'
            f'<div style="font-size:11px;font-weight:600;color:#525252;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Last Meeting</div>'
            f'<div style="font-size:12px;color:#525252;margin-bottom:3px;">{h["date"]} &nbsp;·&nbsp; {h["title"]}</div>'
            f'<div style="font-size:13px;color:#161616;line-height:1.5;">{h["outcome"]}</div>'
            f'</div>'
        ) if h else (
            f'<div style="margin-top:10px;padding-top:10px;border-top:1px solid #e0e0e0;">'
            f'<div style="font-size:12px;color:#8d8d8d;font-style:italic;">No meeting history found.</div>'
            f'</div>'
        )

        contact_cards += f"""
<div style="background:#ffffff;border:1px solid #e0e0e0;border-left:3px solid {border_color};padding:16px 18px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
    <div>
      <div style="font-size:15px;font-weight:600;color:#161616;">{r["contact"]}</div>
      <div style="font-size:12px;color:#525252;margin-top:2px;">{r["title"]}</div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <span class="tag {ec}" style="font-size:11px;">{el}</span>
      <span style="font-size:11px;color:#525252;">IBM Owner: <span style="color:#0043ce;">{r["ibm_owner"]}</span></span>
      <span style="font-size:11px;color:#525252;">Last contact: {r["last"]}</span>
    </div>
  </div>
  {last_meeting_html}
</div>"""

    st.markdown(contact_cards, unsafe_allow_html=True)

    # ── LinkedIn Prospects ────────────────────────────────────
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    li_api_key_set = bool(os.environ.get("TAVILY_API_KEY", "").strip())
    li_hdr_col, li_btn_col = st.columns([6, 2])
    with li_hdr_col:
        st.markdown(
            '<div class="card-title" style="margin-bottom:4px;">LinkedIn Prospect Finder</div>',
            unsafe_allow_html=True,
        )
        if li_api_key_set:
            st.markdown(
                '<div style="font-size:12px;color:#525252;margin-bottom:12px;">'
                'Surfaces publicly indexed LinkedIn profiles of people at this account '
                'who would be valuable new IBM connections — powered by Tavily web search.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="font-size:12px;color:#525252;margin-bottom:12px;">'
                '📋 Set <code>TAVILY_API_KEY</code> to enable live LinkedIn prospect search.</div>',
                unsafe_allow_html=True,
            )
    with li_btn_col:
        li_search_clicked = st.button(
            "🔍 Find Prospects",
            use_container_width=True,
            key="li_search_btn",
            disabled=not li_api_key_set,
        )

    # Fetch when button clicked or when account changes and we have no cached results
    li_needs_fetch = li_api_key_set and (
        li_search_clicked
        or st.session_state.linkedin_fetched_for != account
        or st.session_state.linkedin_prospects is None
    )
    if li_needs_fetch:
        with st.spinner(f"Searching LinkedIn profiles for {account} via Tavily…"):
            li_results, li_err = fetch_linkedin_prospects(account, profile["industry"])
        if li_err:
            st.session_state.linkedin_error = li_err
            st.session_state.linkedin_prospects = None
        else:
            st.session_state.linkedin_prospects = li_results
            st.session_state.linkedin_fetched_for = account
            st.session_state.linkedin_error = None
            if li_search_clicked:
                st.toast("✅ LinkedIn prospects refreshed via Tavily", icon="✅")

    # ── Render results ────────────────────────────────────────
    if st.session_state.linkedin_error:
        err = st.session_state.linkedin_error
        if err == "no_key":
            msg = "TAVILY_API_KEY is not set. Add it to your .env file to enable live search."
        elif err == "no_package":
            msg = "tavily-python package is not installed. Run: pip install tavily-python"
        else:
            msg = f"Tavily search failed: {err}"
        st.markdown(
            f'<div style="font-size:13px;color:#da1e28;padding:12px 0;">{msg}</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state.linkedin_prospects:
        prospects = st.session_state.linkedin_prospects

        # Cross-reference against existing relationship map to detect known contacts
        known_names = {r["contact"].lower() for r in relationship_map}

        # Build prospect cards in a 2-column grid
        li_cols = st.columns(2)
        for i, p in enumerate(prospects):
            is_known = any(
                p["name"].lower() in kn or kn in p["name"].lower()
                for kn in known_names
            )
            p_name     = p["name"]
            p_role     = p["role"]
            p_url      = p["url"]
            p_reason   = p["reason"]
            p_location = p["location"]
            status_cls   = "tag-moderate" if is_known else "tag-blue"
            status_label = "Already in Relationship Map" if is_known else "Suggested Connection"
            location_html = (
                f'<div class="li-card-location">&#128205; {p_location}</div>'
                if p_location else ""
            )
            with li_cols[i % 2]:
                st.markdown(
                    f'<div class="li-card">'
                    f'<div class="li-card-header">'
                    f'<div class="li-card-info">'
                    f'<div class="li-card-name">{p_name}</div>'
                    f'<div class="li-card-role">{p_role}</div>'
                    f'{location_html}'
                    f'</div>'
                    f'<div class="li-card-badge"><span class="tag {status_cls}">{status_label}</span></div>'
                    f'</div>'
                    f'<div class="li-card-reason">'
                    f'<span class="li-reason-label">IBM Relevance</span>'
                    f'{p_reason}'
                    f'</div>'
                    f'<a href="{p_url}" target="_blank" class="li-card-link">View on LinkedIn &#8594;</a>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown(
            '<div style="font-size:11px;color:#8d8d8d;padding:8px 0 4px;">'
            '⚠️ Results are publicly Google-indexed LinkedIn profiles only. '
            'Some senior profiles may not appear due to LinkedIn privacy settings. '
            'Not a complete directory.</div>',
            unsafe_allow_html=True,
        )
    elif li_api_key_set and not li_needs_fetch and st.session_state.linkedin_fetched_for != account:
        st.markdown(
            '<div style="font-size:13px;color:#525252;padding:12px 0;">'
            'Click <strong>Find Prospects</strong> to search for recommended LinkedIn connections at '
            f'{account}.</div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────
# TAB: IBM PARTNERSHIPS
# ─────────────────────────────────────────────────────────────
elif tab == "⊕ IBM Partnerships":
    st.markdown(f"""
<h1>IBM Partnerships &amp; Relationships — {account}</h1>
<p class="section-sub">IBM co-sell relationships, strategic alliances, and joint programmes.</p>
""", unsafe_allow_html=True)

    st.markdown(f"""
<div class="grid-2">
  <div class="ibm-card">
    <div class="card-title">Strategic Alliance Overview</div>
    <table class="ibm-table">
      <tr><td class="muted">Partnership Level</td><td><span class="tag tag-blue">IBM Platinum Partner</span></td></tr>
      <tr><td class="muted">Partnership Since</td><td>2004</td></tr>
      <tr><td class="muted">Joint Revenue (FY25)</td><td>{profile["joint_revenue"]}</td></tr>
      <tr><td class="muted">Active Programmes</td><td>IBM ESA · IBM Build Partner · watsonx Co-sell</td></tr>
      <tr><td class="muted">Alliance Manager (IBM)</td><td>{rep}</td></tr>
      <tr><td class="muted">Alliance Manager ({account})</td><td>{profile["alliance_manager"]}</td></tr>
    </table>
  </div>
  <div class="ibm-card">
    <div class="card-title">Active Joint Programmes</div>
    <ul class="bullet-list">
      <li><span class="bullet-dot"></span><div><strong>IBM–{account} watsonx Centre of Excellence</strong> — Joint delivery capability for enterprise AI at scale.</div></li>
      <li><span class="bullet-dot"></span><div><strong>IBM Cloud Pak for Data Delivery Practice</strong> — IBM-certified {account} consultants.</div></li>
      <li><span class="bullet-dot"></span><div><strong>IBM Sterling Supply Chain CoE</strong> — Award-winning joint implementation team.</div></li>
      <li><span class="bullet-dot"></span><div><strong>EU AI Act Compliance Accelerator</strong> — Joint GTM programme launching Q3 2026.</div></li>
    </ul>
  </div>
</div>
""", unsafe_allow_html=True)

    certs = [
        ("IBM watsonx.ai Technical Sales", 128, "tag-advantaged", "Current"),
        ("IBM Cloud Pak for Data", 340, "tag-advantaged", "Current"),
        ("IBM Sterling Supply Chain", 95, "tag-advantaged", "Current"),
        ("IBM watsonx.governance", 42, "tag-exec", "Renewal Due Q3"),
        ("IBM Cloud Architect", 210, "tag-advantaged", "Current"),
    ]
    cert_rows = "".join(
        f'<tr><td>{c[0]}</td><td>{c[1]}</td><td><span class="tag {c[2]}">{c[3]}</span></td></tr>'
        for c in certs
    )
    st.markdown(f"""
<div class="ibm-card" style="margin-top:16px;">
  <div class="card-title">IBM Certifications Held by {account} Staff</div>
  <table class="ibm-table">
    <thead><tr><th>Certification</th><th>Certified Staff</th><th>Status</th></tr></thead>
    <tbody>{cert_rows}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TAB: AI AGENT LAUNCHPAD
# ─────────────────────────────────────────────────────────────
elif tab == "⊙ AI Agent Launchpad":
    import pandas as pd
    st.markdown(f"""
<h1>AI Agent Launchpad</h1>
<p class="section-sub">Pre-built IBM Sales AI Agents — click any card to run the agent for {account}.</p>
""", unsafe_allow_html=True)

    # ── Agent definitions ──────────────────────────────────────
    AGENTS = [
        ("🎯", "Lead Identification",
         f"Identify and score the top leads within {account} based on title, department, and deal relevance.",
         "lead_id"),
        ("✉️", "Client Outreach Draft",
         f"Generate a personalised outreach email for {profile['client_name']} about watsonx.governance and EU AI Act compliance.",
         "outreach"),
        ("🔍", "Client Search (D&B)",
         f"Retrieve enriched firmographic, technographic, and key contact data from Dun & Bradstreet.",
         "dnb"),
        ("📊", "CRM Snapshot (Salesforce)",
         f"Pull the latest Salesforce opportunity pipeline, stages, and forecast for {account}.",
         "crm_snap"),
        ("✏️", "Update CRM Record",
         f"Update a Salesforce opportunity field directly from the dashboard — stage, forecast, close date.",
         "crm_upd"),
        ("📚", "Seismic Content",
         f"Find the most relevant Seismic sales content for IBM watsonx and EU AI Act compliance topics.",
         "seismic"),
        ("🧠", "Sales Research Brief",
         f"Generate a consolidated account research brief combining D&B, news signals, and IBM internal data.",
         "research"),
    ]

    # ── Session state ──────────────────────────────────────────
    if "launchpad_open" not in st.session_state:
        st.session_state.launchpad_open = None

    # ── Read button presses BEFORE rendering ──────────────────
    for _icon, _title, _desc, _key in AGENTS:
        if st.session_state.get(f"lp_btn_{_key}"):
            st.session_state.launchpad_open = None if st.session_state.launchpad_open == _key else _key

    open_key = st.session_state.launchpad_open

    # ── HTML content builder (pure HTML agents only) ──────────
    def _card_content_html(key):
        inner = 'style="background:#f4f4f4;border-radius:6px;padding:14px 16px;margin-top:14px;"'
        if key == "lead_id":
            rows = ""
            for lead in leads:
                sc = lead["score"]
                sc_color = "#24a148" if sc >= 85 else "#f1c21b" if sc >= 70 else "#da1e28"
                rows += (
                    f'<tr>'
                    f'<td style="padding:8px 10px 8px 0;font-size:13px;"><strong>{lead["name"]}</strong><br>'
                    f'<span style="font-size:11px;color:#525252;">{lead["title"]}</span></td>'
                    f'<td style="padding:8px 6px;font-size:12px;color:#525252;">{lead["dept"]}</td>'
                    f'<td style="padding:8px 6px;font-size:13px;font-weight:700;color:{sc_color};">{sc}</td>'
                    f'</tr>'
                )
            return f'''<div {inner}>
  <table style="width:100%;border-collapse:collapse;">
    <thead><tr>
      <th style="font-size:11px;font-weight:600;color:#525252;text-transform:uppercase;letter-spacing:.4px;padding:0 10px 8px 0;text-align:left;">Contact</th>
      <th style="font-size:11px;font-weight:600;color:#525252;text-transform:uppercase;letter-spacing:.4px;padding:0 6px 8px;text-align:left;">Dept</th>
      <th style="font-size:11px;font-weight:600;color:#525252;text-transform:uppercase;letter-spacing:.4px;padding:0 6px 8px;text-align:left;">Score</th>
    </tr></thead><tbody>{rows}</tbody>
  </table>
</div>'''
        elif key == "outreach":
            return f'''<div {inner}>
  <div style="font-size:11px;color:#525252;margin-bottom:8px;line-height:1.6;">
    <strong>To:</strong> {profile["client_name"]}<br>
    <strong>Subject:</strong> IBM watsonx &amp; EU AI Act Compliance
  </div>
  <div style="font-size:12px;line-height:1.7;color:#161616;">
    Dear {profile["client_name"]},<br><br>
    Following our recent discussions, I wanted to reach out regarding IBM watsonx.governance — now with model explainability, audit trails, and bias detection for regulated industries ahead of the Q3 EU AI Act enforcement deadline.<br><br>
    Available for a 30-min call the week of June 23rd?<br><br>
    <span style="color:#525252;">— {rep} · IBM GAE</span>
  </div>
  <div style="margin-top:8px;font-size:11px;color:#525252;">⚡ Powered by IBM Client Outreach AI Agent</div>
</div>'''
        elif key == "dnb":
            rows = "".join(
                f'<tr><td style="font-size:12px;color:#525252;padding:5px 12px 5px 0;white-space:nowrap;">{lbl}</td>'
                f'<td style="font-size:13px;color:#161616;padding:5px 0;">{val}</td></tr>'
                for lbl, val in [
                    ("Revenue", profile["revenue"]), ("Ticker", profile["ticker"]),
                    ("Employees", profile["employees"]), ("HQ", profile["hq"]),
                    ("Cloud", "Azure · AWS · GCP · IBM Cloud"),
                    ("AI Platforms", "IBM watsonx · Azure OpenAI · Vertex AI"),
                    ("CRM / ERP", "Salesforce · SAP S/4HANA"),
                ]
            )
            return f'<div {inner}><table style="width:100%;border-collapse:collapse;">{rows}</table></div>'
        elif key == "crm_snap":
            total_pipeline = sum(int(o["amount"].replace("$","").replace(",","")) for o in crm_opps)
            rows = "".join(
                f'<tr style="border-top:1px solid #e0e0e0;">'
                f'<td style="font-size:13px;padding:8px 10px 8px 0;">{o["name"]}</td>'
                f'<td style="padding:8px 10px 8px 0;"><span style="font-size:11px;font-weight:700;color:#0043ce;'
                f'border:1px solid #97c1ff;border-radius:12px;padding:2px 8px;white-space:nowrap;">{o["stage"].upper()}</span></td>'
                f'<td style="font-size:13px;font-weight:600;padding:8px 10px 8px 0;">{o["amount"]}</td>'
                f'<td style="font-size:13px;color:#525252;padding:8px 0;">{o["close"]}</td></tr>'
                for o in crm_opps
            )
            return f'''<div {inner}>
  <table style="width:100%;border-collapse:collapse;">
    <thead><tr>
      <th style="font-size:11px;font-weight:600;color:#525252;text-transform:uppercase;letter-spacing:.4px;padding:0 10px 8px 0;text-align:left;">Opportunity</th>
      <th style="font-size:11px;font-weight:600;color:#525252;text-transform:uppercase;letter-spacing:.4px;padding:0 10px 8px 0;text-align:left;">Stage</th>
      <th style="font-size:11px;font-weight:600;color:#525252;text-transform:uppercase;letter-spacing:.4px;padding:0 10px 8px 0;text-align:left;">Amount</th>
      <th style="font-size:11px;font-weight:600;color:#525252;text-transform:uppercase;letter-spacing:.4px;padding:0 0 8px;text-align:left;">Close</th>
    </tr></thead><tbody>{rows}</tbody>
  </table>
  <div style="margin-top:10px;font-size:13px;font-weight:700;">Total Pipeline: <span style="color:#24a148;">${total_pipeline:,.0f}</span></div>
</div>'''
        elif key == "seismic":
            items = "".join(
                f'<div style="padding:8px 0;border-top:1px solid #e0e0e0;">'
                f'<div style="font-size:13px;font-weight:600;color:#161616;">{s["title"]}</div>'
                f'<div style="font-size:11px;color:#525252;margin-top:2px;">{s["type"]} · Relevance: {s["relevance"]}</div>'
                f'</div>'
                for s in seismic_content
            )
            return f'<div {inner}>{items}</div>'
        elif key == "research":
            return f'''<div {inner}>
  <div style="font-size:13px;color:#161616;line-height:1.6;margin-bottom:10px;">
    <strong>{account}</strong> — strategic IBM enterprise AI &amp; data platform partner.
    Active: watsonx, Cloud Pak for Data, Sterling.
  </div>
  <div style="font-size:11px;font-weight:700;color:#525252;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px;">Top Signals</div>
  <div style="font-size:12px;color:#161616;line-height:1.8;">
    🟡 Re-engage executive sponsor {profile["client_name"]} this quarter<br>
    ⚪ Governance &amp; renewal timing are near-term priorities<br>
    🔴 Hyperscaler competitive pressure across AI platform decisions<br>
    🟢 Expansion potential: watsonx, data, observability
  </div>
</div>'''
        # crm_upd: needs Streamlit widgets, rendered separately below
        return ""

    # ── Work out which row the open card is in ────────────────
    open_row = None
    if open_key:
        open_idx = next((i for i, a in enumerate(AGENTS) if a[3] == open_key), None)
        if open_idx is not None:
            open_row = open_idx // 3

    # ── 3-column grid — cards collapsed by default ────────────
    cols_per_row = 3
    for row_idx, row_start in enumerate(range(0, len(AGENTS), cols_per_row)):
        row_agents = AGENTS[row_start: row_start + cols_per_row]
        grid_cols = st.columns(cols_per_row)
        for col, (icon, title, desc, key) in zip(grid_cols, row_agents):
            with col:
                is_open = open_key == key
                border = "#2451e3" if is_open else "#e0e0e0"
                # Only inject content HTML for non-CRM-upd agents when open
                content_html = _card_content_html(key) if (is_open and key != "crm_upd") else ""
                btn_label = "▲ Close" if is_open else "▶ Run Agent"
                st.markdown(f"""
<div style="background:#ffffff;border:1.5px solid {border};border-radius:8px;
            padding:22px 20px 18px;margin-bottom:4px;">
  <div style="font-size:28px;margin-bottom:10px;">{icon}</div>
  <div style="font-size:14px;font-weight:700;color:#161616;margin-bottom:6px;">{title}</div>
  <div style="font-size:13px;color:#525252;line-height:1.5;">{desc}</div>
  {content_html}
</div>""", unsafe_allow_html=True)
                st.button(btn_label, key=f"lp_btn_{key}", use_container_width=True)

        # CRM Update widgets open in-line below its row
        if open_key == "crm_upd" and open_row == row_idx:
            st.markdown('<div style="background:#ffffff;border:1.5px solid #2451e3;border-top:none;border-radius:0 0 8px 8px;padding:20px 22px;margin-bottom:12px;">', unsafe_allow_html=True)
            opp_map = {o["name"]: o["id"] for o in crm_opps}
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                sel_opp = st.selectbox("Opportunity", list(opp_map.keys()), key="crm_opp")
            with c2:
                sel_field = st.selectbox("Field", ["Stage", "Forecast_Category", "Close_Date"], key="crm_field")
            with c3:
                new_val = st.text_input("New Value", placeholder="e.g. Proposal, 2026-09-30", key="crm_val")
            if st.button("Update Salesforce Record", key="crm_submit"):
                if new_val.strip():
                    st.toast(f"✅ Salesforce updated — {opp_map[sel_opp]} · {sel_field} → \"{new_val}\" · {date.today().strftime('%b %d, %Y')} · {rep}", icon="✅")
                else:
                    st.toast("⚠️ Please enter a new value before updating.", icon="⚠️")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TAB: ASK BOB
# ─────────────────────────────────────────────────────────────
elif tab == "◉ Ask Bob":

    # ── Heading ───────────────────────────────────────────────
    st.markdown("""
<h1>Ask Bob — AI Chatbot</h1>
<p class="section-sub">Click any question below or type your own to ask Bob.</p>
""", unsafe_allow_html=True)

    # ── Bob greeting bubble (always shown) ────────────────────
    _first = rep.split()[0] if rep else "there"
    st.markdown(
        f'<div class="bob-msg-label">💼 Bob &nbsp;<span style="color:#198038;font-size:10px;">● Live</span></div>'
        f'<div class="bob-bubble">Good morning, {_first}. I\'m Bob, your IBM Sales Intelligence assistant — '
        f'routing through the <code>sales_hub_orchestrator_agent</code>. I\'m loaded with everything on '
        f'<strong>{account}</strong>: news, meetings, pipeline, competitive intel, and more. '
        f'What do you need today?</div>',
        unsafe_allow_html=True
    )

    st.markdown('<hr style="border:none;border-top:1px solid #e0e0e0;margin:16px 0 12px;">', unsafe_allow_html=True)

    # ── Sample questions ──────────────────────────────────────
    st.markdown('<div class="card-title" style="font-size:11px;letter-spacing:.5px;margin-bottom:10px;">SAMPLE QUESTIONS — CLICK TO ASK BOB</div>', unsafe_allow_html=True)
    sq_cols = st.columns(3)
    for i, q in enumerate(SAMPLE_QUESTIONS[:3]):
        with sq_cols[i]:
            if st.button(q, key=f"sq_{i}", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": q})
                st.session_state.chat_history.append({"role": "bob", "content": bob_respond(q)})
                st.rerun()

    # ── Chat history ──────────────────────────────────────────
    if st.session_state.chat_history:
        st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
        for msg in st.session_state.chat_history:
            if msg["role"] == "bob":
                st.markdown(
                    f'<div class="bob-msg-label">💼 Bob</div>'
                    f'<div class="bob-bubble">{msg["content"]}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="user-msg-label">You</div>'
                    f'<div class="user-bubble">{msg["content"]}</div>',
                    unsafe_allow_html=True
                )

    # ── Free-text input ───────────────────────────────────────
    user_input = st.chat_input(f"Ask Bob anything about {account}…")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.session_state.chat_history.append({"role": "bob", "content": bob_respond(user_input)})
        st.rerun()

# ─────────────────────────────────────────────────────────────
# FLOATING ASK BOB FAB — rendered on every tab via iframe
# Pin the component iframe itself to the viewport so position:fixed
# inside it works relative to the browser window, not the page scroll.
# ─────────────────────────────────────────────────────────────
import streamlit.components.v1 as _components

# Collapse the layout gap the iframe creates while keeping it visually fixed.
# We target the stCustomComponentV1 wrapper — the last one on the page is ours.
# Collapse the iframe's layout slot entirely — the panel is position:fixed inside.
st.markdown(
    """
    <style>
    div[data-testid="stCustomComponentV1"]:last-of-type {
        margin-top: -4px !important;
        height: 0px !important;
        min-height: 0px !important;
        overflow: visible !important;
        padding: 0 !important;
    }
    div[data-testid="stCustomComponentV1"]:last-of-type iframe {
        position: fixed !important;
        top: 0 !important;
        right: 0 !important;
        width: 400px !important;
        height: 100vh !important;
        border: none !important;
        z-index: 99990 !important;
        display: block !important;
        background: transparent !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

_fab_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    width: 100%; height: 100%;
    background: transparent;
    font-family: -apple-system,"Segoe UI",system-ui,sans-serif;
    overflow: hidden;
  }}

  /* ── "Ask Bob" trigger button — sits at top-right, same height as the app header */
  #fab {{
    position: fixed;
    top: 0; right: 0;
    height: 48px;
    padding: 0 20px;
    background: #0F62FE;
    border: none;
    border-left: 1px solid #0043CE;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
    font-family: inherit;
    letter-spacing: .2px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 7px;
    z-index: 10;
    transition: background .15s;
  }}
  #fab:hover {{ background: #0353E9; }}

  /* ── Chat panel — fills viewport below the button; hidden until .open ── */
  #panel {{
    position: fixed;
    top: 48px; right: 0;
    width: 400px;
    height: calc(100vh - 48px);
    background: #ffffff;
    border-left: 1px solid #e0e0e0;
    border-top: 1px solid #e0e0e0;
    display: none;
    flex-direction: column;
    box-shadow: -4px 0 20px rgba(0,0,0,0.12);
    z-index: 9;
  }}
  #panel.open {{ display: flex; }}

  /* Panel header */
  .ph {{
    padding: 0 16px;
    height: 52px;
    border-bottom: 1px solid #e0e0e0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
    background: #000;
  }}
  .ph-left {{ display: flex; flex-direction: column; gap: 2px; }}
  .ph-title {{ font-size: 14px; font-weight: 700; color: #ffffff; }}
  .ph-sub {{ font-size: 11px; color: #a8a8a8; }}
  .ph-right {{ display: flex; align-items: center; gap: 10px; }}
  .ph-live {{ font-size: 11px; color: #42be65; letter-spacing: .2px; }}
  .ph-close {{
    background: none; border: none; color: #a8a8a8;
    cursor: pointer; font-size: 20px; line-height: 1;
    padding: 4px; display: flex; align-items: center;
  }}
  .ph-close:hover {{ color: #ffffff; }}

  /* Context pill */
  .ctx {{
    padding: 7px 16px;
    background: #edf5ff;
    border-bottom: 1px solid #97c1ff;
    font-size: 11px; color: #0043ce;
    flex-shrink: 0;
    letter-spacing: .2px;
  }}

  /* Messages */
  #msgs {{
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    background: #f4f4f4;
  }}
  #msgs::-webkit-scrollbar {{ width: 3px; }}
  #msgs::-webkit-scrollbar-track {{ background: #f4f4f4; }}
  #msgs::-webkit-scrollbar-thumb {{ background: #c6c6c6; border-radius: 2px; }}

  .msg {{ display: flex; flex-direction: column; max-width: 86%; gap: 3px; }}
  .msg-bob {{ align-self: flex-start; }}
  .msg-user {{ align-self: flex-end; }}
  .msg-label {{
    font-size: 10px; color: #8d8d8d; font-weight: 600;
    letter-spacing: .4px; text-transform: uppercase;
  }}
  .msg-user .msg-label {{ text-align: right; }}
  .bubble {{
    padding: 10px 14px; font-size: 13px; line-height: 1.6;
    white-space: pre-wrap; word-break: break-word;
  }}
  .msg-bob .bubble {{
    background: #ffffff; border: 1px solid #e0e0e0; color: #161616;
  }}
  .msg-user .bubble {{
    background: #0F62FE; color: #fff;
  }}

  /* Typing dots */
  .typing-wrap {{
    display: flex; flex-direction: column; max-width: 86%;
    align-self: flex-start; gap: 3px;
  }}
  .typing {{
    display: flex; gap: 5px; align-items: center;
    padding: 12px 14px;
    background: #ffffff; border: 1px solid #e0e0e0;
  }}
  .dot {{
    width: 6px; height: 6px; border-radius: 50%; background: #8d8d8d;
    animation: pulse 1.3s infinite ease-in-out;
  }}
  .dot:nth-child(2) {{ animation-delay: .2s; }}
  .dot:nth-child(3) {{ animation-delay: .4s; }}
  @keyframes pulse {{ 0%,60%,100% {{ opacity:.2; transform:scale(.8); }} 30% {{ opacity:1; transform:scale(1); }} }}

  /* Sample questions */
  .sugg-wrap {{
    padding: 12px 16px 8px;
    border-top: 1px solid #e0e0e0;
    flex-shrink: 0;
    background: #ffffff;
  }}
  .sugg-label {{
    font-size: 10px; color: #8d8d8d; text-transform: uppercase;
    letter-spacing: .5px; margin-bottom: 8px; font-weight: 600;
  }}
  .sugg-pills {{ display: flex; flex-direction: column; gap: 5px; }}
  .sugg-btn {{
    background: #f4f4f4;
    border: 1px solid #e0e0e0;
    color: #525252;
    font-size: 12px;
    padding: 8px 12px;
    cursor: pointer;
    font-family: inherit;
    text-align: left;
    transition: border-color .12s, color .12s, background .12s;
  }}
  .sugg-btn:hover {{ border-color: #0F62FE; color: #161616; background: #edf5ff; }}

  /* Input */
  .inp-wrap {{
    padding: 12px 16px 14px;
    border-top: 1px solid #e0e0e0;
    display: flex;
    gap: 8px;
    flex-shrink: 0;
    background: #ffffff;
  }}
  #inp {{
    flex: 1;
    background: #f4f4f4;
    border: 1px solid #e0e0e0;
    color: #161616;
    padding: 10px 12px;
    font-size: 13px;
    font-family: inherit;
    outline: none;
  }}
  #inp:focus {{ border-color: #0F62FE; }}
  #inp::placeholder {{ color: #8d8d8d; }}
  #send-btn {{
    background: #0F62FE; color: #fff; border: none;
    padding: 10px 18px; cursor: pointer; font-size: 13px;
    font-family: inherit; font-weight: 600;
    flex-shrink: 0;
  }}
  #send-btn:hover {{ background: #0353E9; }}
</style>
</head>
<body>

<button id="fab" onclick="togglePanel()">&#128172; Ask Bob</button>

<div id="panel">
  <div class="ph">
    <div class="ph-left">
      <span class="ph-title">&#128172; Ask Bob</span>
      <span class="ph-sub">IBM watsonx Orchestrate</span>
    </div>
    <div class="ph-right">
      <span class="ph-live">&#9679; Live</span>
      <button class="ph-close" onclick="closePanel()" title="Close">&#x2715;</button>
    </div>
  </div>
  <div class="ctx">Account: <strong>{account}</strong> &nbsp;&middot;&nbsp; {rep}</div>
  <div id="msgs"></div>
  <div class="sugg-wrap">
    <div class="sugg-label">Suggested questions</div>
    <div class="sugg-pills">
      <button class="sugg-btn" onclick="suggest(this)">What&apos;s the exec summary for {account}?</button>
      <button class="sugg-btn" onclick="suggest(this)">What are the upcoming meetings?</button>
      <button class="sugg-btn" onclick="suggest(this)">What&apos;s the Salesforce pipeline?</button>
    </div>
  </div>
  <div class="inp-wrap">
    <input id="inp" placeholder="Ask Bob about {account}&#8230;"
           onkeydown="if(event.key==='Enter')send()"/>
    <button id="send-btn" onclick="send()">Send</button>
  </div>
</div>

<script>
  const ACCOUNT = {repr(account)};
  const REP     = {repr(rep)};

  const R = {{
    exec:       "Executive Summary for "+ACCOUNT+"\\n\\n\u2022 EU AI Act compliance \u2014 watsonx.governance renewal (Sep 30) is critical path.\\n\u2022 AI/cloud budget +34% YoY \u2014 capital available for expanded watsonx deployment.\\n\u2022 New CAO Dr. Priya Nair (IBM advocate) \u2014 engage within 2 weeks.\\n\\nOpen opportunities: watsonx Expansion $8.4M \u00b7 Cloud Pak Upgrade $1.2M \u00b7 Governance Renewal $2.7M\\n\\nOpen the Exec Summary tab for the full brief.",
    competitor: "Active Competitors at "+ACCOUNT+"\\n\\n\u26a0\ufe0f AWS (At Risk, $7.8M) \u2014 $3B Accenture partnership announced.\\n\u26a0\ufe0f Microsoft (At Risk, $5.2M) \u2014 Azure OpenAI PoC at 15,000 employees.\\n\U0001f7e1 Google Cloud (Even, $3.1M) \u2014 Vertex AI evaluation underway.\\n\u2705 Salesforce (Advantaged, $1.4M) \u2014 IBM well positioned.\\n\\nOpen Competitor Analysis tab for full battlecards.",
    meeting:    "Upcoming Meetings \u2014 "+ACCOUNT+"\\n\\n\U0001f4c5 Jun 18 \u2014 watsonx Enterprise Expansion Proposal Review \u00b7 \u26a0\ufe0f Needs Prep\\n\U0001f4c5 Jun 20 \u2014 IBM Sterling Q3 Business Review \u00b7 \u2705 Prep Complete\\n\U0001f4c5 Jun 25 \u2014 watsonx.governance EU AI Act Compliance Workshop \u00b7 \U0001f534 No Brief\\n\\n2 meetings still need prep. Open the Meetings tab for details.",
    pipeline:   "Salesforce CRM \u2014 "+ACCOUNT+"\\n\\n\U0001f4b0 watsonx Enterprise Expansion \u2014 $8,400,000 \u00b7 Proposal \u00b7 Sep 30\\n\U0001f4b0 Cloud Pak for Data Upgrade \u2014 $1,200,000 \u00b7 Needs Analysis \u00b7 Aug 15\\n\U0001f4b0 watsonx.governance Renewal \u2014 $2,700,000 \u00b7 Value Prop \u00b7 Aug 31\\n\\nTotal open pipeline: $12,300,000",
    news:       "Morning News \u2014 "+ACCOUNT+"\\n\\n\U0001f534 Competitor Move \u2014 Accenture expands AWS partnership with $3B cloud migration\\n\U0001f7e1 Executive Change \u2014 Dr. Priya Nair appointed Chief AI Officer\\n\U0001f7e2 Opportunity \u2014 Q2 2026 earnings: AI & cloud revenue up 34% YoY\\n\U0001f7e2 Opportunity \u2014 EU AI Act deadline creates urgency for watsonx.governance\\n\\nOpen Morning News tab for the live Tavily feed.",
    product:    "Active IBM Products \u2014 "+ACCOUNT+"\\n\\n\u2705 watsonx.ai \u2014 Enterprise \u00b7 2,500 seats \u00b7 74% \u00b7 Dec 2026\\n\u26a0\ufe0f watsonx.governance \u2014 800 seats \u00b7 61% \u00b7 Sep 2026 \u2190 renewal alert\\n\U0001f53a Cloud Pak for Data \u2014 1,200 seats \u00b7 88% \u2190 upsell candidate\\n\U0001f53a IBM Sterling \u2014 450 seats \u00b7 93% \u2190 premium tier candidate",
    fallback:   "I\u2019m Bob, routing through sales_hub_orchestrator_agent for "+ACCOUNT+".\\n\\nTry: news, meetings, competitors, IBM products, exec summary, or Salesforce pipeline.\\nOr open the Ask Bob tab for the full chat experience.",
  }};

  function getR(msg) {{
    const m = msg.toLowerCase();
    if (/exec|summary|brief|call.?prep/.test(m))                  return R.exec;
    if (/compet|\\bvs\\b|versus|\\baws\\b|microsoft|azure/.test(m))   return R.competitor;
    if (/meet|calendar|upcoming|scheduled/.test(m))                return R.meeting;
    if (/salesforce|pipeline|crm|deal|opport/.test(m))            return R.pipeline;
    if (/news|press|announce|this.?week/.test(m))                  return R.news;
    if (/product|licen|renew|watsonx|sterling|cloud.?pak/.test(m)) return R.product;
    return R.fallback;
  }}

  function togglePanel() {{
    const p = document.getElementById('panel');
    p.classList.toggle('open');
    if (p.classList.contains('open') && !document.getElementById('msgs').firstChild) {{
      addMsg('bob', 'Good morning, ' + REP.split(' ')[0] + '. I\u2019m Bob \u2014 your IBM Sales Intelligence assistant for ' + ACCOUNT + '. What do you need today?');
    }}
  }}

  function closePanel() {{
    document.getElementById('panel').classList.remove('open');
  }}

  function addMsg(role, text) {{
    const msgs = document.getElementById('msgs');
    const wrap = document.createElement('div');
    wrap.className = 'msg msg-' + role;
    const label = document.createElement('div');
    label.className = 'msg-label';
    label.textContent = role === 'bob' ? 'Bob' : 'You';
    const bub = document.createElement('div');
    bub.className = 'bubble';
    bub.textContent = text;
    wrap.appendChild(label);
    wrap.appendChild(bub);
    msgs.appendChild(wrap);
    msgs.scrollTop = msgs.scrollHeight;
  }}

  function showTyping() {{
    const msgs = document.getElementById('msgs');
    const t = document.createElement('div');
    t.id = 'typing'; t.className = 'typing-wrap';
    t.innerHTML = '<div class="msg-label">Bob</div><div class="typing"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>';
    msgs.appendChild(t);
    msgs.scrollTop = msgs.scrollHeight;
  }}

  function send() {{
    const inp = document.getElementById('inp');
    const msg = inp.value.trim();
    if (!msg) return;
    inp.value = '';
    addMsg('user', msg);
    showTyping();
    setTimeout(() => {{
      document.getElementById('typing')?.remove();
      addMsg('bob', getR(msg));
    }}, 700);
  }}

  function suggest(btn) {{
    const msg = btn.textContent.trim();
    addMsg('user', msg);
    showTyping();
    setTimeout(() => {{
      document.getElementById('typing')?.remove();
      addMsg('bob', getR(msg));
    }}, 700);
  }}
</script>
</body>
</html>"""

_components.html(_fab_html, height=1, scrolling=False)

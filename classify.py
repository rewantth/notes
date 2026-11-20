"""Rule-based classifier for job-application emails.

No AI / no API tokens: everything here is plain regex and sender-domain rules.
Input is a dict:  {id, threadId, from, subject, date (ISO string), body}
"""
from __future__ import annotations

import re
from email.utils import parseaddr

# ---------------------------------------------------------------- portals --
# id -> (label, sender-domain fragments)
JOB_BOARDS = {
    "linkedin": ("LinkedIn", ["linkedin.com"]),
    "naukri": ("Naukri", ["naukri.com", "naukrigulf.com"]),
    "indeed": ("Indeed", ["indeed.com", "indeedemail.com"]),
    "glassdoor": ("Glassdoor", ["glassdoor.com"]),
    "wellfound": ("Wellfound", ["wellfound.com", "angel.co"]),
    "instahyre": ("Instahyre", ["instahyre.com"]),
    "foundit": ("Foundit", ["foundit.in", "monsterindia.com", "monster.com"]),
    "internshala": ("Internshala", ["internshala.com"]),
    "cutshort": ("Cutshort", ["cutshort.io"]),
    "hirist": ("Hirist", ["hirist.com", "hirist.tech"]),
    "ziprecruiter": ("ZipRecruiter", ["ziprecruiter.com"]),
    "apna": ("Apna", ["apna.co"]),
    "unstop": ("Unstop", ["unstop.com"]),
}

# Applicant-tracking systems: mail comes from them but the application was made
# on the company's own careers site.
ATS_DOMAINS = [
    "greenhouse.io", "greenhouse-mail.io", "lever.co", "myworkday.com", "workday.com",
    "smartrecruiters.com", "ashbyhq.com", "icims.com", "taleo.net", "successfactors",
    "jobvite.com", "bamboohr.com", "zohorecruit.com", "zoho.com", "breezy.hr",
    "workable.com", "recruitee.com", "teamtailor.com", "pinpointhq.com", "oraclecloud.com",
    "eightfold.ai", "phenom.com", "hire.lever.co", "applytojob.com", "rippling.com",
    "freshteam.com", "darwinbox.in", "darwinbox.com", "keka.com", "turbohire.co",
    "hirevue.com", "paradox.ai", "avature.net", "dayforcehcm.com", "ultipro.com",
]

# Mail providers / bulk senders whose domain tells us nothing about the company.
GENERIC_DOMAINS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com", "yahoo.in",
    "icloud.com", "proton.me", "protonmail.com", "mailchimp.com", "sendgrid.net",
    "amazonses.com", "mandrillapp.com", "mailgun.org",
}

PORTAL_LABELS = {k: v[0] for k, v in JOB_BOARDS.items()}
PORTAL_LABELS["company"] = "Company website"
PORTAL_LABELS["other"] = "Other"


def _domain(addr: str) -> str:
    addr = parseaddr(addr)[1].lower()
    return addr.split("@", 1)[1] if "@" in addr else ""


def detect_portal(sender: str) -> tuple[str, str]:
    """Returns (portal_id, kind) where kind is 'board', 'ats' or 'direct'."""
    dom = _domain(sender)
    for pid, (_label, frags) in JOB_BOARDS.items():
        if any(dom == f or dom.endswith("." + f) for f in frags):
            return pid, "board"
    if any(f in dom for f in ATS_DOMAINS):
        return "company", "ats"
    return "company", "direct"


# ----------------------------------------------------------------- noise ---
NOISE_SUBJECT = re.compile(
    r"job alert|jobs? (?:for you|you may|recommend|picked)|new jobs?|recommended (?:job|for)|"
    r"similar jobs|top jobs|jobs? matching|people also viewed|viewed your profile|"
    r"appeared in \d+|who viewed|weekly (?:digest|job)|newsletter|webinar|premium|"
    r"connection request|invitation to connect|endorse|congratulate|birthday|work anniversary|"
    r"hiring now|is hiring|are hiring|apply now|apply today|complete your profile|"
    r"profile (?:strength|views)|resume (?:tips|builder)|career advice|salary|"
    r"\d+ new jobs?|jobs? in |openings? (?:at|in|for you)",
    re.I,
)
NOISE_SENDER_LOCAL = re.compile(r"jobalerts?|job-alerts?|jobs-listings|newsletter|digest|marketing|promo", re.I)

# Words that make a non-job-board email plausibly about a job application.
JOBISH = re.compile(
    r"\b(role|position|job|career|candidate|candidacy|hiring|recruit\w*|resume|cv|vacancy|"
    r"opening|talent|applicant|interview|employment)\b",
    re.I,
)
# For replies that move an application forward or close it, the word "application" is enough:
# a bank is very unlikely to write "we will not be moving forward with your application".
JOBISH_LOOSE = re.compile(JOBISH.pattern[:-3] + r"|application|applying|applied|candidates?)\b", re.I)

# ---------------------------------------------------------------- stages ---
STAGES = ["Applied", "In review", "Screening", "Assessment", "Interview", "Offer", "Rejected"]

_RX = {
    "Offer": re.compile(
        r"offer letter|pleased to offer|happy to offer|excited to offer|delighted to offer|"
        r"job offer|offer of employment|extend (?:you )?an offer|extending (?:you )?an offer|"
        r"formal offer|your offer",
        re.I,
    ),
    "Rejected": re.compile(
        r"unfortunately|regret to (?:inform|tell|let)|sorry to (?:inform|tell|let)|"
        r"not moving forward|not be moving forward|"
        r"(?:move|moving|proceed|proceeding|go|going|continue|continuing|pursue|pursuing|selected|chosen|hired)"
        r" (?:forward |ahead )?with (?:other|another|a different)|"
        r"pursu\w+ other (?:candidates|applicants)|"
        r"other (?:candidates|applicants) (?:whose|who|that) (?:more )?(?:closely )?(?:match|fit|align)|"
        r"not (?:been )?(?:selected|chosen|successful)|unsuccessful|unable to (?:offer|move|proceed|progress)|"
        r"position (?:has been|was|is) (?:now )?(?:filled|closed|no longer)|"
        r"not be (?:proceeding|progressing|offering|taking)|will not (?:proceed|be proceeding|progress)|"
        r"not shortlisted|no longer (?:being )?(?:considered|under consideration)|not (?:a|the right) (?:match|fit)|"
        r"decided not to|we will not be|won'?t be (?:moving|proceeding|taking)|"
        r"not able to (?:take|move) your application forward|did(?: not|n't) make (?:it|the cut)|"
        r"after careful consideration|keep your (?:resume|cv|details|profile) on file|"
        r"wish you (?:the best|every success|all the best|luck) (?:in|with) your",
        re.I,
    ),
    "Assessment": re.compile(
        r"assessment|coding (?:challenge|test|round)|hackerrank|codility|hackerearth|take[- ]home|"
        r"online test|aptitude|codesignal|testgorilla|mettl|case study|assignment",
        re.I,
    ),
    # Early contact from a recruiter: a first call, a chat, "next steps", being shortlisted.
    "Screening": re.compile(
        r"screening (?:call|interview|round|conversation|chat|test)|phone (?:screen|call|interview)|"
        r"initial (?:call|screen|chat|conversation|discussion)|intro(?:ductory)? (?:call|chat|conversation)|"
        r"quick (?:call|chat|intro)|recruiter (?:call|screen|chat|conversation)|"
        r"(?:call|chat|talk|speak) with (?:a|one of our|our|the) recruiter|"
        r"connect (?:for|over) a (?:call|chat)|(?:15|20|30)[- ]minute (?:call|chat|conversation)|"
        r"get to know you|learn more about your (?:background|experience)|"
        r"next steps|shortlisted|move(?:d)? (?:you )?forward|advance(?:d)? to the next|"
        r"like to (?:speak|talk|connect|chat)|reaching out (?:about|regarding|because)",
        re.I,
    ),
    "Interview": re.compile(
        r"interview|schedule a (?:call|chat|time|meeting)|invite you to|next round|"
        r"technical round|hr round|meet with (?:our|the) team|speak with you|availability|"
        r"calendly|zoom meeting|google meet|microsoft teams meeting|final round|on-?site",
        re.I,
    ),
    "In review": re.compile(
        r"application (?:was )?viewed|viewed your application|being reviewed|under review|"
        r"reviewing your (?:application|profile)|resume (?:was )?viewed|recruiter (?:has )?viewed|"
        r"your application is (?:being )?(?:reviewed|in progress)",
        re.I,
    ),
    "Applied": re.compile(
        r"thank(?:s| you) for (?:applying|your application|your interest|submitting)|"
        r"application (?:has been )?(?:received|submitted|sent)|we(?:'ve| have)? received your application|"
        r"your application (?:was|has been) (?:sent|submitted|received)|successfully applied|"
        r"you(?:'ve| have)? applied|application confirmation|applied (?:successfully|to)|"
        r"thanks for applying|we got your application|your application was sent|indeed application|"
        r"application (?:for|to) [^\n]{3,100}? (?:has been|was) (?:submitted|received|sent)",
        re.I,
    ),
}


# Subjects that are really status *updates* (the body decides what happened).
_AMBIGUOUS_SUBJECT = re.compile(
    r"your application (?:to|for|with|at)|application (?:for|update|status)|update on your|"
    r"your update from|regarding your application|an update",
    re.I,
)
_ORDER = ("Offer", "Rejected", "Assessment", "Screening", "Interview", "In review")


def _strongest(text: str, rejected_text: str) -> str | None:
    for stage in _ORDER:
        if _RX[stage].search(text):
            # "we will not be inviting you to interview" is a rejection, not an interview.
            if stage in ("Interview", "Assessment", "Screening") and _RX["Rejected"].search(rejected_text):
                return "Rejected"
            return stage
    return None


def detect_stage(subject: str, body: str) -> str | None:
    subj = subject or ""
    head = (body or "")[:1800]
    full = subj + " \n " + head

    hit = _strongest(subj, full)
    if hit:
        return hit
    # Clear confirmation subjects stay "Applied" even if the body mentions interviews
    # ("if shortlisted we will schedule an interview").
    if _RX["Applied"].search(subj) and not _AMBIGUOUS_SUBJECT.search(subj):
        return "Applied"
    hit = _strongest(head, full)
    if hit:
        return hit
    if _RX["Applied"].search(full) or _AMBIGUOUS_SUBJECT.search(subj):
        return "Applied"
    return None


# ------------------------------------------------------- company / role ----
_CLEAN_TAIL = re.compile(r"[\s\-–—|:;,.!?]+$")
_STOP_AFTER = re.compile(r"\s+(?:–|—|-|\||:|\(|\bposition\b|\brole\b|\bis\b|\bhas\b|\bwas\b|\bfor\b)\s*.*$", re.I)


def _tidy(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value).strip()
    value = _CLEAN_TAIL.sub("", value)
    value = re.sub(r"^(?:the|our)\s+", "", value, flags=re.I)
    return value.strip()


def _company_clip(value: str | None) -> str:
    value = _tidy(value)
    value = _STOP_AFTER.sub("", value)
    return _tidy(value)


LI_SENT = re.compile(r"(?:^|,\s*)your application was sent to (?P<company>.+)$", re.I)
LI_TO_AT = re.compile(r"your application to (?P<role>.+?) at (?P<company>.+)$", re.I)
LI_UPDATE = re.compile(r"your update from (?P<company>.+)$", re.I)
LI_VIEWED = re.compile(r"your application was viewed by (?P<company>.+)$", re.I)

SUBJ_PATTERNS = [
    re.compile(r"application (?:for|to) (?:the )?(?P<role>.+?) (?:at|with|@) (?P<company>.+)$", re.I),
    re.compile(r"(?:applying|applied) (?:to|at|with) (?P<company>.+)$", re.I),
    re.compile(r"your application (?:to|with|at) (?P<company>.+)$", re.I),
    re.compile(r"(?:interview|assessment|invitation|opportunity|update)[^|]*? (?:with|at|from) (?P<company>.+)$", re.I),
    re.compile(r"^(?P<role>[^|\-–—:]{4,70}?) (?:at|@) (?P<company>.+)$", re.I),
    re.compile(r"your (?P<company>[^|\-–—:]{2,40}?) application\b", re.I),
]

BODY_ROLE = [
    re.compile(r"(?:applying|applied) (?:for|to) (?:the )?(?P<role>[^.\n]{3,70}?) (?:role|position|opening|vacancy)\b", re.I),
    re.compile(r"(?:interest in|application for) (?:the )?(?P<role>[^.\n]{3,70}?) (?:role|position|opening|vacancy)\b", re.I),
    re.compile(r"(?:role|position) (?:of|as) (?:a |an )?(?P<role>[^.\n,]{3,60}?)(?: at | with | in |[.,\n])", re.I),
    re.compile(r"for the (?P<role>[^.\n]{3,60}?) (?:role|position)\b", re.I),
]
BODY_COMPANY = [
    re.compile(r"(?:interest in|joining|applying to|applied to|opportunity (?:at|with)|position at|role at|team at) (?P<company>[A-Z][\w&.'’ \-]{1,40}?)(?:[.,!\n]|\s+(?:and|for|as|we)\b)"),
    re.compile(r"(?:Team|team) at (?P<company>[A-Z][\w&.'’ \-]{1,40}?)(?:[.,!\n])"),
]

SENDER_JUNK = re.compile(
    r"\b(?:recruit(?:ing|ment|ers?)?|careers?|talent(?: acquisition)?|hr|human resources|hiring|jobs?|"
    r"team|noreply|no-reply|do not reply|notifications?|apply|applications?|people|staffing|workday|greenhouse|lever)\b",
    re.I,
)


def _company_from_sender(sender: str) -> str:
    name, addr = parseaddr(sender)
    name = re.sub(r"[\"']", "", name or "")
    # "Jane Doe at Acme" / "Acme Careers" / "Acme via Greenhouse"
    m = re.search(r"\bat\s+(.+)$", name, re.I)
    if m:
        name = m.group(1)
    name = re.sub(r"\bvia\b.*$", "", name, flags=re.I)
    name = _tidy(SENDER_JUNK.sub(" ", name))
    if len(name) >= 2 and not re.fullmatch(r"[\W\d_]+", name):
        return name
    dom = _domain(sender)
    if dom and dom not in GENERIC_DOMAINS and not any(f in dom for f in ATS_DOMAINS):
        parts = dom.split(".")
        label = parts[-3] if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "ac"} else parts[-2] if len(parts) >= 2 else parts[0]
        if label not in {"mail", "email", "careers", "jobs"}:
            return label.replace("-", " ").title()
    return ""


def _clean_role(role: str) -> str:
    """'Quick call about the Frontend Engineer role' -> 'Frontend Engineer'."""
    role = re.sub(r"^.*?\b(?:about|regarding|for) the\s+", "", role, flags=re.I)
    role = re.sub(r"^(?:interview|invitation|update|call|chat|screening)[^:]*:\s*", "", role, flags=re.I)
    role = re.sub(r"\s+(?:role|position|opening|opportunity|vacancy)$", "", role, flags=re.I)
    return _tidy(role)


def extract_company_role(sender: str, subject: str, body: str, portal: str) -> tuple[str, str, bool]:
    """Returns (company, role, confident)."""
    subject = re.sub(r"^(?:re|fwd?):\s*", "", subject or "", flags=re.I).strip()
    company = role = ""

    if portal == "linkedin":
        for rx in (LI_TO_AT, LI_SENT, LI_UPDATE, LI_VIEWED):
            m = rx.search(subject)
            if m:
                company = _company_clip(m.groupdict().get("company"))
                role = _tidy(m.groupdict().get("role"))
                break
        if company and not role:
            # LinkedIn confirmation bodies list the job title right under the headline.
            lines = [ln.strip() for ln in (body or "").splitlines() if ln.strip()]
            for i, ln in enumerate(lines[:12]):
                if re.search(r"application was sent|applied on", ln, re.I):
                    for cand in lines[i + 1 : i + 4]:
                        if 3 <= len(cand) <= 80 and company.lower() not in cand.lower() and "·" not in cand:
                            role = _tidy(cand)
                            break
                    break

    if not company:
        for rx in SUBJ_PATTERNS:
            m = rx.search(subject)
            if m:
                company = _company_clip(m.groupdict().get("company"))
                role = role or _tidy(m.groupdict().get("role"))
                if company:
                    break

    if not role:
        for rx in BODY_ROLE:
            m = rx.search((body or "")[:2500])
            if m:
                role = _tidy(m.group("role"))
                break

    if not company:
        for rx in BODY_COMPANY:
            m = rx.search((body or "")[:2500])
            if m:
                company = _company_clip(m.group("company"))
                break

    # Job-board senders (LinkedIn, Naukri…) say nothing about the company; company mail does.
    if not company and portal == "company":
        company = _company_from_sender(sender)

    company = company[:60]
    role = _clean_role(role)[:80]
    # Reject obviously wrong captures.
    if len(company) < 2 or re.fullmatch(r"[\W\d_]+", company) or company.lower() in {"you", "us", "your", "this"}:
        company = ""
    if len(role) < 3 or len(role.split()) > 12:
        role = ""
    return company or "Unknown", role, bool(company)


# -------------------------------------------------------------- pipeline ---
def classify(msg: dict) -> dict | None:
    """Turn one raw email into an event, or None if it isn't about a job application."""
    sender = msg.get("from", "")
    subject = msg.get("subject", "") or ""
    body = msg.get("body", "") or ""
    portal, kind = detect_portal(sender)

    local = parseaddr(sender)[1].split("@")[0]
    if NOISE_SUBJECT.search(subject) or NOISE_SENDER_LOCAL.search(local):
        # A status update inside a noisy-looking mail is still real if the subject says so.
        if not re.search(r"your application|application (?:was|has been|status)|interview|offer letter", subject, re.I):
            return None

    stage = detect_stage(subject, body)
    if stage is None:
        return None
    if kind == "direct":
        # The sender's name counts too: "Acme Recruiting" or "Talent Team" is a strong hint.
        text = f"{sender}\n{subject}\n{body[:1500]}"
        needed = JOBISH if stage == "Applied" else JOBISH_LOOSE
        if not needed.search(text):
            return None
    if kind == "direct" and stage == "Applied" and not re.search(r"appl", f"{subject}\n{body[:800]}", re.I):
        return None

    company, role, confident = extract_company_role(sender, subject, body, portal)
    return {
        "id": msg.get("id", ""),
        "thread": msg.get("threadId", ""),
        "date": msg.get("date", ""),
        "stage": stage,
        "portal": portal,
        "kind": kind,
        "company": company,
        "role": role,
        "confident": confident,
        "subject": subject[:140],
        "sender": parseaddr(sender)[1],
    }


def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\b(?:pvt|private|ltd|limited|inc|llc|llp|corp|corporation|technologies|technology|india|solutions)\b\.?", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def build_applications(events: list[dict]) -> list[dict]:
    """Group events into one row per application."""
    events = sorted(events, key=lambda e: e["date"])
    apps: list[dict] = []
    by_company: dict[str, list[dict]] = {}

    for ev in events:
        ckey = _norm(ev["company"])
        rkey = _norm(ev["role"])
        target = None
        candidates = by_company.get(ckey, []) if ev["company"] != "Unknown" else []
        if rkey:
            for app in candidates:
                if app["_rkey"] == rkey:
                    target = app
                    break
            if target is None:
                # Same company, role not known yet on that application -> same application.
                for app in reversed(candidates):
                    if not app["_rkey"]:
                        target = app
                        app["role"], app["_rkey"] = ev["role"], rkey
                        break
        elif candidates:
            target = candidates[-1]
        if target is None and ev["company"] == "Unknown":
            # Fall back to the email thread.
            for app in apps:
                if ev["thread"] and ev["thread"] in app["threads"]:
                    target = app
                    break

        if target is None:
            target = {
                "company": ev["company"], "role": ev["role"], "_rkey": rkey,
                "portal": ev["portal"], "first_date": ev["date"], "events": [],
                "threads": set(), "confident": ev["confident"],
            }
            apps.append(target)
            if ev["company"] != "Unknown":
                by_company.setdefault(ckey, []).append(target)

        target["events"].append(ev)
        target["threads"].add(ev["thread"])
        target["confident"] = target["confident"] and ev["confident"]
        # Portal = where the application started: prefer a job board seen on the earliest events.
        if target["portal"] == "company" and ev["portal"] not in ("company", "other") and ev["date"][:10] == target["first_date"][:10]:
            target["portal"] = ev["portal"]

    out = []
    for app in apps:
        evs = app["events"]
        applied = [e for e in evs if e["stage"] == "Applied"]
        latest = evs[-1]
        # Final states win; otherwise the most recent stage.
        status = latest["stage"]
        for e in reversed(evs):
            if e["stage"] in ("Offer", "Rejected"):
                status = e["stage"]
                break
        # An old "Applied" after a later stage never downgrades it (events are date-sorted).
        out.append({
            "company": app["company"],
            "role": app["role"] or "—",
            "portal": app["portal"],
            "portalLabel": PORTAL_LABELS.get(app["portal"], "Other"),
            "status": status,
            "applied": (applied[0] if applied else evs[0])["date"],
            "updated": latest["date"],
            "emails": len(evs),
            "review": (not app["confident"]) or app["company"] == "Unknown",
            "link": f"https://mail.google.com/mail/u/0/#all/{latest['thread'] or latest['id']}",
            "subject": latest["subject"],
            "history": [{"date": e["date"], "stage": e["stage"], "subject": e["subject"]} for e in evs][-8:],
        })
    out.sort(key=lambda a: a["updated"], reverse=True)
    return out

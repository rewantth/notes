"""Optional phone alerts through ntfy (https://ntfy.sh).

When a new screening call, test, interview, offer or rejection shows up, the update run
sends one short push notification. The message only counts what arrived, for example
"1 interview invite, 1 rejection". It never contains a company name or any email text.

How it knows what is new: the previous encrypted data file is still published on the page.
Each run downloads it, unlocks it with the same passphrase, and compares.

Alerts are off unless the NTFY_TOPIC secret is set.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter

ALERT_STAGES = ("Offer", "Interview", "Assessment", "Screening", "Rejected")
# Three levels, so each can have its own sound on an Android phone (ntfy gives every priority
# its own notification channel). Highest first: (ntfy priority, title, stages that belong here).
LEVELS = (
    ("5", "Job Hunt: interview or offer", ("Offer", "Interview")),
    ("4", "Job Hunt: a reply that needs you", ("Screening", "Assessment")),
    ("3", "Job Hunt: a rejection", ("Rejected",)),
)
LABELS = {
    "Offer": ("offer", "offers"),
    "Interview": ("interview invite", "interview invites"),
    "Screening": ("call request", "call requests"),
    "Assessment": ("test", "tests"),
    "Rejected": ("rejection", "rejections"),
}
MAX_AGE_DAYS = 3          # ignore older emails, so a rule change cannot cause a burst of old alerts
TOPIC_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


# ------------------------------------------------------------ previous data --
def decrypt_box(box: dict, passphrase: str) -> dict:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    key = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=base64.b64decode(box["salt"]), iterations=int(box["iter"])
    ).derive(passphrase.encode())
    plain = AESGCM(key).decrypt(base64.b64decode(box["iv"]), base64.b64decode(box["ct"]), None)
    return json.loads(plain)


def fetch_previous(url: str, passphrase: str) -> dict | None:
    """Download and unlock the data file from the last run. None if anything goes wrong."""
    try:
        req = urllib.request.Request(f"{url.rstrip('/')}/data.enc.json?t={int(dt.datetime.now().timestamp())}",
                                     headers={"Cache-Control": "no-cache", "User-Agent": "job-hunt-alerts"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return decrypt_box(json.loads(resp.read()), passphrase)
    except Exception:
        return None


# ----------------------------------------------------------------- the diff --
def _key(event: dict) -> tuple:
    return (event.get("stage"), event.get("date"), event.get("subject"))


def new_events(previous: dict, current: dict, now: dt.datetime | None = None) -> list[str]:
    """Stages of alert-worthy emails that are in `current` but were not in `previous`."""
    now = now or dt.datetime.now(dt.timezone.utc)
    seen = {_key(e) for a in previous.get("applications", []) for e in a.get("history", [])}
    found = []
    for app in current.get("applications", []):
        for e in app.get("history", []):
            if e.get("stage") not in ALERT_STAGES or _key(e) in seen:
                continue
            try:
                age = (now - dt.datetime.fromisoformat(e["date"])).total_seconds() / 86400
            except (KeyError, ValueError):
                continue
            if age <= MAX_AGE_DAYS:
                found.append(e["stage"])
    return found


# ---------------------------------------------------------------- the message --
def summarize(stages: list[str]) -> str:
    counts = Counter(stages)
    parts = []
    for stage in ALERT_STAGES:
        n = counts.get(stage, 0)
        if n:
            one, many = LABELS[stage]
            parts.append(f"{n} {one if n == 1 else many}")
    return ", ".join(parts)


def build_messages(stages: list[str], dashboard_url: str) -> list[dict]:
    """One message per level that has something new, loudest level first."""
    out = []
    for priority, title, members in LEVELS:
        mine = [s for s in stages if s in members]
        if mine:
            out.append({"title": title, "body": summarize(mine) + ". Tap to open your dashboard.",
                        "priority": priority, "click": dashboard_url})
    return out


def test_messages(dashboard_url: str) -> list[dict]:
    """Three test alerts, one per level, so the phone creates a sound channel for each."""
    body = "Test alert. Real ones say things like 1 interview invite."
    return [
        {"title": "Job Hunt test: loud (interviews and offers)", "body": body, "priority": "5", "click": dashboard_url},
        {"title": "Job Hunt test: medium (calls and tests)", "body": body, "priority": "4", "click": dashboard_url},
        {"title": "Job Hunt test: quiet (rejections)", "body": body, "priority": "3", "click": dashboard_url},
    ]


last_error = ""   # why the last send failed, for the log. Never contains anything about your jobs.


def send(topic: str, message: dict, server: str = "https://ntfy.sh") -> bool:
    global last_error
    if not TOPIC_RE.match(topic):
        last_error = "the NTFY_TOPIC secret has an invalid format (use 8 to 64 letters, numbers, - or _)"
        return False
    headers = {"Title": message["title"], "Priority": message["priority"], "Tags": "briefcase"}
    if message.get("click"):
        headers["Click"] = message["click"]
    req = urllib.request.Request(f"{server.rstrip('/')}/{topic}", data=message["body"].encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20):
            return True
    except urllib.error.HTTPError as e:
        last_error = f"ntfy answered HTTP {e.code}"
        return False
    except (urllib.error.URLError, OSError) as e:
        last_error = f"could not reach ntfy ({type(e).__name__})"
        return False


# ------------------------------------------------------------- orchestration --
def dashboard_url(env) -> str:
    if env.get("DASHBOARD_URL"):
        return env["DASHBOARD_URL"]
    repo = env.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}/"
    return ""


def maybe_alert(payload: dict, passphrase: str, env=os.environ) -> None:
    """Send an alert if the NTFY_TOPIC secret is set and something new arrived. Never raises."""
    topic = (env.get("NTFY_TOPIC") or "").strip()
    if not topic or payload.get("demo"):
        return
    server = env.get("NTFY_SERVER") or "https://ntfy.sh"
    url = dashboard_url(env)
    quiet = bool(env.get("GITHUB_ACTIONS"))
    try:
        if (env.get("ALERT_TEST") or "").lower() == "true":
            results = [send(topic, m, server) for m in test_messages(url)]
            # Safe to show even in public logs: it says nothing about your applications.
            print(f"Test alerts sent to ntfy: {sum(results)} of {len(results)}." + ("" if all(results) else f" Last problem: {last_error}."))
            return
        if not url:
            return
        previous = fetch_previous(url, passphrase)
        if previous is None:
            return          # first run, or the passphrase changed: do not guess
        stages = new_events(previous, payload)
        if stages and not quiet:
            print("New replies found:", summarize(stages))
        for message in build_messages(stages, url):
            if not send(topic, message, server):
                print(f"An alert could not be sent: {last_error}.")
    except Exception:
        if not quiet:
            print("Alerts hit a problem and were skipped.")

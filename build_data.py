"""Fetch job emails from Gmail, classify them, and write an ENCRYPTED data file.

Usage:
    python build_data.py           # real run (needs GMAIL_* env vars)
    python build_data.py --demo    # fake emails, for previewing the dashboard

Env vars:
    GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN   (real run)
    DASHBOARD_PASSPHRASE   passphrase that unlocks the dashboard (always required)
    LOOKBACK_DAYS          how far back to scan (default 365)
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import os
import re
import sys
import time
from email.utils import parsedate_to_datetime
from pathlib import Path

import alerts
from classify import build_applications, classify

SITE = Path(__file__).parent / "site"
PBKDF2_ITERATIONS = 600_000
MAX_MESSAGES = 1500

PORTAL_SENDERS = (
    "linkedin.com naukri.com indeed.com glassdoor.com wellfound.com instahyre.com foundit.in "
    "monsterindia.com internshala.com cutshort.io hirist.com ziprecruiter.com apna.co unstop.com"
)
GMAIL_QUERY = (
    "newer_than:{days}d -in:spam -in:trash -from:me ("
    'subject:(application OR applied OR applying OR interview OR assessment OR "offer letter" '
    'OR candidacy OR "your update" OR "an update" OR "update from" OR "update on" OR "thank you for your interest" '
    'OR "next steps" OR screening OR "phone screen" OR "recruiter" OR "your candidacy" OR "your interest" '
    'OR unfortunately OR "regarding your" OR "your resume" OR "your profile" OR invitation OR "schedule") '
    "OR from:({senders}))"
)


# ------------------------------------------------------------------ gmail --
def gmail_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")


def _body(payload: dict) -> str:
    plain, html_parts = [], []

    def walk(part):
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if data and mime == "text/plain":
            plain.append(_decode(data))
        elif data and mime == "text/html":
            html_parts.append(_decode(data))
        for sub in part.get("parts", []) or []:
            walk(sub)

    walk(payload)
    if plain:
        return "\n".join(plain)
    text = "\n".join(html_parts)
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|li|h\d)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"[ \t\r\f\v]+", " ", text)


def fetch_messages(days: int) -> list[dict]:
    svc = gmail_service()
    query = GMAIL_QUERY.format(days=days, senders=" OR ".join(PORTAL_SENDERS.split()))
    ids, token = [], None
    while len(ids) < MAX_MESSAGES:
        resp = svc.users().messages().list(userId="me", q=query, pageToken=token, maxResults=200).execute(num_retries=8)
        ids += [m["id"] for m in resp.get("messages", [])]
        token = resp.get("nextPageToken")
        if not token:
            break
    if not os.environ.get("GITHUB_ACTIONS"):
        print(f"Gmail returned {len(ids)} candidate emails", file=sys.stderr)

    out = []
    for mid in ids[:MAX_MESSAGES]:
        # Gmail throttles bursts; retry with backoff and keep a gentle pace.
        m = svc.users().messages().get(userId="me", id=mid, format="full").execute(num_retries=8)
        time.sleep(0.15)
        headers = {h["name"].lower(): h["value"] for h in m["payload"].get("headers", [])}
        try:
            date = parsedate_to_datetime(headers.get("date", "")).astimezone(dt.timezone.utc).isoformat()
        except (TypeError, ValueError):
            date = dt.datetime.fromtimestamp(int(m["internalDate"]) / 1000, dt.timezone.utc).isoformat()
        out.append({
            "id": m["id"], "threadId": m["threadId"], "from": headers.get("from", ""),
            "subject": headers.get("subject", ""), "date": date, "body": _body(m["payload"]),
        })
    return out


# ------------------------------------------------------------------- demo --
def demo_messages() -> list[dict]:
    now = dt.datetime.now(dt.timezone.utc)

    def d(days: float) -> str:
        return (now - dt.timedelta(days=days)).isoformat()

    li = "LinkedIn <jobs-noreply@linkedin.com>"
    return [
        {"id": "1", "threadId": "t1", "from": li, "date": d(40), "subject": "Your application was sent to Razorpay",
         "body": "Your application was sent to Razorpay\n\nBackend Engineer\nRazorpay · Bengaluru"},
        {"id": "2", "threadId": "t2", "from": li, "date": d(31), "subject": "Your application to Backend Engineer at Razorpay",
         "body": "Unfortunately, Razorpay will not be moving forward with your application."},
        {"id": "3", "threadId": "t3", "from": li, "date": d(26), "subject": "Your application was sent to Zomato",
         "body": "Your application was sent to Zomato\n\nSoftware Development Engineer\nZomato · Gurugram"},
        {"id": "4", "threadId": "t3b", "from": "Zomato Recruiting <recruiting@zomato.com>", "date": d(20),
         "subject": "Interview invitation - Software Development Engineer",
         "body": "Hi, we would like to invite you to an interview for the Software Development Engineer role. Please pick a slot on calendly."},
        {"id": "5", "threadId": "t5", "from": "Naukri <info@naukri.com>", "date": d(18), "subject": "Application sent to Swiggy for Data Analyst",
         "body": "You have successfully applied to the Data Analyst position at Swiggy."},
        {"id": "6", "threadId": "t6", "from": "Swiggy Careers <swiggy@myworkday.com>", "date": d(10), "subject": "Swiggy: assessment for Data Analyst",
         "body": "Thank you for your interest in the Data Analyst position. Please complete the HackerRank assessment within 5 days."},
        {"id": "7", "threadId": "t7", "from": "Stripe Recruiting <no-reply@greenhouse-mail.io>", "date": d(14),
         "subject": "Thank you for applying to Stripe",
         "body": "Thank you for applying for the Software Engineer, Payments role at Stripe. We received your application."},
        {"id": "8", "threadId": "t8", "from": "Indeed Apply <indeedapply@indeed.com>", "date": d(12), "subject": "Indeed Application: Python Developer",
         "body": "Your application for the Python Developer position at Freshworks has been submitted."},
        {"id": "9", "threadId": "t9", "from": "Freshworks Talent <talent@freshworks.com>", "date": d(5), "subject": "Offer letter - Python Developer",
         "body": "We are delighted to offer you the Python Developer position at Freshworks. Please find your offer letter attached."},
        {"id": "10", "threadId": "t10", "from": "Careers at Atlassian <careers@lever.co>", "date": d(4),
         "subject": "Application received - Frontend Engineer at Atlassian",
         "body": "We have received your application for the Frontend Engineer role. Our team will review it."},
        {"id": "11", "threadId": "t11", "from": li, "date": d(3), "subject": "Your application was sent to Postman",
         "body": "Your application was sent to Postman\n\nSoftware Engineer II\nPostman · Remote"},
        {"id": "12", "threadId": "t12", "from": "Wellfound <team@wellfound.com>", "date": d(2), "subject": "Your application to Notion has been submitted",
         "body": "You applied to the Product Engineer role at Notion."},
        {"id": "13", "threadId": "n1", "from": "LinkedIn Job Alerts <jobalerts-noreply@linkedin.com>", "date": d(1),
         "subject": "20 new jobs for you", "body": "Software Engineer at Acme..."},
        {"id": "14", "threadId": "n2", "from": "Some Bank <noreply@bank.com>", "date": d(1),
         "subject": "Your loan application has been received", "body": "We received your loan application."},
        {"id": "15", "threadId": "t15", "from": li, "date": d(22), "subject": "Your application was sent to Flipkart",
         "body": "Your application was sent to Flipkart\n\nSDE-1\nFlipkart · Bengaluru"},
        {"id": "16", "threadId": "t16", "from": "Flipkart HR <hr@flipkart.com>", "date": d(15), "subject": "Update on your application",
         "body": "Thank you for your interest. Unfortunately we have decided to move forward with other candidates for the SDE-1 role."},
        {"id": "17", "threadId": "t17", "from": "Naukri <info@naukri.com>", "date": d(36), "subject": "Application sent to Paytm for QA Engineer",
         "body": "You have successfully applied to the QA Engineer position at Paytm."},
        {"id": "18", "threadId": "t18", "from": "Paytm Hiring <jobs@paytm.com>", "date": d(30), "subject": "Application received - QA Engineer",
         "body": "We have received your application for the QA Engineer role at Paytm."},
        {"id": "19", "threadId": "t19", "from": "Cred Talent <talent@ashbyhq.com>", "date": d(60), "subject": "Thanks for applying to CRED",
         "body": "Thanks for applying for the Android Developer role at CRED."},
        {"id": "20", "threadId": "t20", "from": li, "date": d(6), "subject": "Your application was viewed by Zerodha",
         "body": "Your application was viewed by Zerodha"},
        {"id": "21", "threadId": "t21", "from": "Atlassian Recruiting <recruiting@lever.co>", "date": d(1.2),
         "subject": "Quick call about the Frontend Engineer role at Atlassian",
         "body": "Hi, I'd like to set up a quick call with a recruiter to learn more about your background. Are you free this week?"},
        {"id": "22", "threadId": "t22", "from": "Stripe Recruiting <no-reply@greenhouse-mail.io>", "date": d(2.5),
         "subject": "Update on your application to Stripe",
         "body": "Thank you for your interest in the Software Engineer, Payments role. Unfortunately we have decided to move forward with other candidates."},
        {"id": "23", "threadId": "t23", "from": "Postman Talent <talent@postman.com>", "date": d(0.4),
         "subject": "Interview invitation: Software Engineer II",
         "body": "We would like to invite you to an interview for the Software Engineer II role. Please share your availability for next week."},
    ]


# ------------------------------------------------------------- encryption --
def encrypt(plaintext: bytes, passphrase: str) -> dict:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=PBKDF2_ITERATIONS).derive(
        passphrase.encode()
    )
    ct = AESGCM(key).encrypt(iv, plaintext, None)  # ciphertext || 16-byte tag, as WebCrypto expects
    b64 = lambda b: base64.b64encode(b).decode()
    return {"v": 1, "iter": PBKDF2_ITERATIONS, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="use fake emails")
    ap.add_argument("--out", default=str(SITE / "data.enc.json"))
    args = ap.parse_args()

    passphrase = os.environ.get("DASHBOARD_PASSPHRASE", "")
    if len(passphrase) < 8:
        sys.exit("Set DASHBOARD_PASSPHRASE (at least 8 characters; a long phrase is best).")

    days = int(os.environ.get("LOOKBACK_DAYS", "365"))
    messages = demo_messages() if args.demo else fetch_messages(days)
    events = [e for e in (classify(m) for m in messages) if e]
    apps = build_applications(events)
    # Logs of public GitHub repos are public, so print nothing about your jobs when running in Actions.
    if not os.environ.get("GITHUB_ACTIONS"):
        from collections import Counter
        print(f"{len(messages)} emails -> {len(events)} job events -> {len(apps)} applications", file=sys.stderr)
        print("  portals:", dict(Counter(a["portalLabel"] for a in apps)), file=sys.stderr)
        print("  status: ", dict(Counter(a["status"] for a in apps)), file=sys.stderr)
        print("  needs review:", sum(a["review"] for a in apps), file=sys.stderr)

    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "demo": args.demo,
        "scanned": len(messages),
        "applications": apps,
    }
    alerts.maybe_alert(payload, passphrase)   # optional phone alert, does nothing unless NTFY_TOPIC is set
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(encrypt(json.dumps(payload).encode(), passphrase)))
    print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()

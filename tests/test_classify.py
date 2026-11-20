"""Checks that emails are sorted into the right stage and portal.

Run from the project folder with:   python tests/test_classify.py
(or with pytest, if you have it installed)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from classify import build_applications, classify  # noqa: E402

LI = "LinkedIn <jobs-noreply@linkedin.com>"
NAUKRI = "Naukri <info@naukri.com>"
CO = "Acme Recruiting <recruiting@acme.com>"
GH = "Acme <no-reply@greenhouse-mail.io>"

# (sender, subject, body, expected stage or None, expected portal)
CASES = [
    # Confirmations
    (LI, "Your application was sent to Acme", "Your application was sent to Acme\n\nSecurity Analyst", "Applied", "linkedin"),
    (GH, "Thank you for applying to Acme", "We received your application for the Security Analyst role. If shortlisted we will schedule an interview.", "Applied", "company"),
    (NAUKRI, "Application sent to Acme for Analyst", "You have successfully applied to the Analyst position at Acme.", "Applied", "naukri"),
    # Rejections, many ways of saying it
    (LI, "Your application to Security Analyst at Acme", "Unfortunately, Acme will not be moving forward with your application.", "Rejected", "linkedin"),
    (LI, "Your update from Acme", "Thank you for your interest in the Security Analyst position. We have decided to move forward with other candidates.", "Rejected", "linkedin"),
    (CO, "Update on your application", "We regret to inform you that we are not able to take your application forward.", "Rejected", "company"),
    (CO, "Your application for Security Analyst", "After careful consideration, we have chosen to pursue other applicants whose experience more closely matches.", "Rejected", "company"),
    (GH, "An update on your Acme application", "Thanks for your interest. The position has been filled. We wish you every success in your search.", "Rejected", "company"),
    (CO, "Regarding your application", "We will not be proceeding with your candidacy. We will keep your resume on file.", "Rejected", "company"),
    (NAUKRI, "Application status update: Acme", "Your profile was not shortlisted for the Analyst role.", "Rejected", "naukri"),
    (CO, "Re: Security Analyst application", "We will not be inviting you to interview at this time.", "Rejected", "company"),
    # Screening / early recruiter contact
    (CO, "Let's connect: Security Analyst at Acme", "Hi, I'd like to schedule a quick call to learn more about your background. Are you free this week?", "Screening", "company"),
    (CO, "Next steps for your application", "Thanks for applying. We'd like to move you forward with a phone screen with one of our recruiters.", "Screening", "company"),
    (GH, "Screening call invitation", "Please book a 20-minute call with a recruiter using the link below.", "Screening", "company"),
    (LI, "Acme: you've been shortlisted", "Your application for the Security Analyst role has been shortlisted.", "Screening", "linkedin"),
    # Assessments
    (GH, "Acme: assessment for Security Analyst", "Please complete the HackerRank test within 5 days.", "Assessment", "company"),
    # Interviews
    (CO, "Interview invitation: Security Analyst", "We would like to invite you to an interview. Please share your availability.", "Interview", "company"),
    (CO, "Your interview with Acme on Friday", "Here is the Zoom meeting link for your technical round.", "Interview", "company"),
    # Offers
    (CO, "Offer letter from Acme", "We are delighted to offer you the Security Analyst position.", "Offer", "company"),
    # Things that must be ignored
    ("LinkedIn Job Alerts <jobalerts-noreply@linkedin.com>", "20 new jobs for you", "Security Analyst at Acme...", None, None),
    (LI, "Acme is hiring a Security Engineer", "Apply now", None, None),
    (LI, "You may be a fit for Acme's Analyst role", "Based on your profile", None, None),
    ("Some Bank <noreply@bank.com>", "Your loan application has been received", "We received your loan application.", None, None),
    (LI, "Alex, your profile was viewed 5 times", "See who viewed your profile", None, None),
]


def run():
    failures = 0
    for sender, subject, body, want_stage, want_portal in CASES:
        ev = classify({"id": "x", "threadId": "t", "from": sender, "subject": subject, "date": "2026-01-01T00:00:00+00:00", "body": body})
        got_stage = ev["stage"] if ev else None
        got_portal = ev["portal"] if ev else None
        ok = got_stage == want_stage and (want_stage is None or got_portal == want_portal)
        if not ok:
            failures += 1
            print(f"FAIL  {subject!r}\n      wanted {want_stage}/{want_portal}  got {got_stage}/{got_portal}")
    # A story: applied, screening call, interview, then rejected -> final status is Rejected.
    story = [
        (LI, "Your application was sent to Acme", "Your application was sent to Acme\n\nSecurity Analyst", "2026-01-01"),
        (CO, "Screening call with Acme", "A quick call with a recruiter about the Security Analyst role at Acme.", "2026-01-05"),
        (CO, "Interview invitation: Security Analyst at Acme", "We would like to invite you to an interview.", "2026-01-10"),
        (CO, "Update on your application at Acme", "Unfortunately we have decided to move forward with other candidates.", "2026-01-20"),
    ]
    events = [classify({"id": str(i), "threadId": f"t{i}", "from": s, "subject": sub, "date": d + "T00:00:00+00:00", "body": b})
              for i, (s, sub, b, d) in enumerate(story)]
    apps = build_applications([e for e in events if e])
    if len(apps) != 1 or apps[0]["status"] != "Rejected" or apps[0]["portal"] != "linkedin":
        failures += 1
        print("FAIL  story:", [(a["company"], a["status"], a["portal"]) for a in apps])
    # Which website did it come from? A job board, a hiring system, or the company's own domain.
    from classify import detect_portal, detect_site
    site_cases = [
        ("LinkedIn <jobs-noreply@linkedin.com>", ("LinkedIn", "board")),
        ("Acme <no-reply@greenhouse-mail.io>", ("Greenhouse", "ats")),
        ("Acme <jobs@hire.lever.co>", ("Lever", "ats")),
        ("Swiggy <swiggy@myworkday.com>", ("Workday", "ats")),
        ("Acme Recruiting <recruiting@mail.careers.acme.com>", ("acme.com", "direct")),
        ("Acme <hr@acme.co.uk>", ("acme.co.uk", "direct")),
        ("A Person <someone@gmail.com>", ("Direct email", "direct")),
    ]
    site_failures = 0
    for sender, want in site_cases:
        portal, kind = detect_portal(sender)
        got = detect_site(sender, portal, kind)
        if got != want:
            site_failures += 1
            print(f"FAIL  site for {sender!r}: wanted {want} got {got}")
    total = len(CASES) + 1 + len(site_cases)
    failures += site_failures
    print(f"{total - failures} of {total} checks passed")
    return failures


def test_classifier():
    assert run() == 0


if __name__ == "__main__":
    sys.exit(1 if run() else 0)

"""Checks the optional phone-alert logic. Run with:   python tests/test_alerts.py"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import alerts  # noqa: E402
import build_data  # noqa: E402

NOW = dt.datetime(2026, 11, 20, 12, 0, tzinfo=dt.timezone.utc)


def ev(stage, days_ago, subject="s"):
    return {"stage": stage, "date": (NOW - dt.timedelta(days=days_ago)).isoformat(), "subject": subject}


def payload(*histories):
    return {"applications": [{"company": f"Secret Company {i}", "history": h} for i, h in enumerate(histories)]}


def run():
    failures = []

    def check(name, ok):
        if not ok:
            failures.append(name)
            print("FAIL ", name)

    old = payload([ev("Applied", 5, "a1"), ev("Interview", 2, "i1")])
    new = payload([ev("Applied", 5, "a1"), ev("Interview", 2, "i1"), ev("Rejected", 0.1, "r1")], [ev("Applied", 0.2, "a2")])
    check("only the new rejection is reported", alerts.new_events(old, new, NOW) == ["Rejected"])
    check("nothing new -> nothing reported", alerts.new_events(new, new, NOW) == [])
    check("plain confirmations never alert", alerts.new_events(payload(), payload([ev("Applied", 0.1, "x")]), NOW) == [])
    check("old emails never alert", alerts.new_events(payload(), payload([ev("Interview", 10, "x")]), NOW) == [])
    two = payload([ev("Interview", 0.1, "i"), ev("Screening", 0.1, "c")], [ev("Rejected", 0.1, "r1")], [ev("Rejected", 0.2, "r2")])
    check("counts and wording", alerts.summarize(alerts.new_events(payload(), two, NOW)) == "1 interview invite, 1 call request, 2 rejections")

    msgs = alerts.build_messages(["Interview", "Rejected", "Screening"], "https://x.github.io/job-tracker/")
    text = " ".join(" ".join(m.values()) for m in msgs)
    check("one message per level, loudest first", [m["priority"] for m in msgs] == ["5", "4", "3"])
    check("message never contains a company name", "Secret Company" not in text and "Company" not in text)
    check("interviews and offers are the loudest level", alerts.build_messages(["Offer"], "")[0]["priority"] == "5")
    check("rejections alone are normal priority", alerts.build_messages(["Rejected"], "")[0]["priority"] == "3")
    check("titles are plain ASCII (HTTP header)", all(m["title"].isascii() for m in msgs))
    check("nothing new -> no messages", alerts.build_messages([], "") == [])
    check("test alerts cover all three levels", [m["priority"] for m in alerts.test_messages("")] == ["5", "4", "3"])

    check("good topic accepted", bool(alerts.TOPIC_RE.match("jobhunt-0123456789abcdef")))
    check("short or odd topic rejected", not alerts.TOPIC_RE.match("a/b") and not alerts.TOPIC_RE.match("short"))
    check("no topic -> send refuses", alerts.send("../x", msgs[0]) is False)

    box = build_data.encrypt(b'{"applications": []}', "a long test passphrase")
    check("encrypt then decrypt round trip", alerts.decrypt_box(box, "a long test passphrase") == {"applications": []})
    try:
        alerts.decrypt_box(box, "the wrong one")
        check("wrong passphrase must fail", False)
    except Exception:
        pass

    # A tiny local server stands in for ntfy, so the real request can be inspected without any network.
    import http.server
    import threading

    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            got["path"] = self.path
            got["title"] = self.headers.get("Title")
            got["click"] = self.headers.get("Click")
            got["body"] = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()
    sent = alerts.send("jobhunt-0123456789abcdef", alerts.build_messages(["Interview"], "https://x.github.io/jt/")[0],
                       f"http://127.0.0.1:{server.server_port}")
    server.server_close()
    check("send posts to the topic path", sent and got.get("path") == "/jobhunt-0123456789abcdef")
    check("send carries title and click link", got.get("title", "").startswith("Job Hunt") and got.get("click") == "https://x.github.io/jt/")
    check("sent text is counts only", got.get("body") == "1 interview invite. Tap to open your dashboard.")

    env = {"GITHUB_REPOSITORY": "someone/job-tracker"}
    check("dashboard address from the repository name", alerts.dashboard_url(env) == "https://someone.github.io/job-tracker/")
    alerts.maybe_alert({"demo": False, "applications": []}, "pw", {})      # no topic: must do nothing and not raise
    alerts.maybe_alert({"demo": True, "applications": []}, "pw", {"NTFY_TOPIC": "jobhunt-0123456789abcdef"})

    print(f"{20 - len(failures)} of 20 checks passed")
    return len(failures)


def test_alerts():
    assert run() == 0


if __name__ == "__main__":
    sys.exit(1 if run() else 0)

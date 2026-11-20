"""Security checks. Run with:   python tests/test_security.py"""
import base64
import hashlib
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import alerts  # noqa: E402
import build_data  # noqa: E402
import build_site  # noqa: E402


def run():
    failures = []

    def check(name, ok):
        if not ok:
            failures.append(name)
            print("FAIL ", name)

    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

    # --- content security policy -------------------------------------------------
    sample = "<html><head><title>x</title></head><body><script>alert(1)</script></body></html>"
    body = "alert(1)"
    want = "'sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode() + "'"
    out = build_site.add_policy(sample)
    check("policy carries the script's own hash", want in out)
    check("policy forbids everything by default", "default-src 'none'" in out)
    check("policy only lets the page talk to itself", "connect-src 'self'" in out)
    check("policy is added once, inside <head>", out.count("Content-Security-Policy") == 1 and out.index("<head>") < out.index("Content-Security-Policy"))
    try:
        build_site.add_policy('<html><head></head><body><script src="https://evil.example/x.js"></script></body></html>')
        check("external scripts are refused", False)
    except SystemExit:
        pass
    check("the real page builds with a policy", "script-src 'sha256-" in build_site.add_policy(page))

    # --- the page itself ----------------------------------------------------------
    check("no inline event handler attributes", not re.search(r"\son(click|error|load|mouse\w+|key\w+|focus|change|submit)\s*=", page, re.I))
    check("no javascript: URLs", "javascript:" not in page.lower())
    check("no external scripts, styles or fonts", not re.search(r"<(script|link|img|iframe)[^>]+(src|href)=[\"']?(https?:)?//", page, re.I))
    check("no eval or Function constructor", not re.search(r"\beval\(|new Function\(", page))
    check("passphrase is never written to storage", "setItem(\"jt-pass\"" not in page and "setItem('jt-pass'" not in page)
    check("remembered login is a non-extractable key", '{ name: "AES-GCM", length: 256 }, false, ["decrypt"]' in page)
    check("page refuses to run inside a frame", "window.top !== window.self" in page)
    check("page sends no referrer", 'name="referrer" content="no-referrer"' in page)
    check("page is not indexed", 'name="robots" content="noindex' in page)

    # --- encryption ---------------------------------------------------------------
    os.environ["GITHUB_REPOSITORY"] = "someone/notes"
    a = build_data.encrypt(b'{"ok": true}', "a long test passphrase")
    b = build_data.encrypt(b'{"ok": true}', "a long test passphrase")
    check("salt is stable for a project, IV is fresh each time", a["salt"] == b["salt"] and a["iv"] != b["iv"] and a["ct"] != b["ct"])
    os.environ["GITHUB_REPOSITORY"] = "other/repo"
    other = build_data.encrypt(b'{"ok": true}', "a long test passphrase")
    os.environ["GITHUB_REPOSITORY"] = "someone/notes"
    check("a different project gets a different salt", other["salt"] != a["salt"])
    check("at least 1,000,000 key-derivation rounds", a["iter"] >= 1_000_000)
    check("round trip works", alerts.decrypt_box(a, "a long test passphrase") == {"ok": True})
    try:
        alerts.decrypt_box(a, "wrong passphrase here")
        check("wrong passphrase is rejected", False)
    except Exception:
        pass
    check("tampering is detected", _tamper_detected(a))

    # --- repository hygiene -------------------------------------------------------
    flow = (ROOT / ".github" / "workflows" / "update.yml").read_text(encoding="utf-8")
    uses = re.findall(r"uses:\s*(\S+)", flow)
    check("every action is pinned to a full commit hash", all(re.search(r"@[0-9a-f]{40}$", u) for u in uses))
    check("workflow starts with no permissions", "permissions: {}" in flow)
    reqs = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    pkgs = [ln for ln in reqs.splitlines() if ln.strip() and not ln.startswith("#")]
    check("every package is pinned to an exact version", all("==" in ln for ln in pkgs))
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    check("secrets files are git-ignored", all(x in gitignore for x in ("credentials.json", "github-secrets.txt")))

    total = 25
    print(f"{total - len(failures)} of {total} checks passed")
    return len(failures)


def _tamper_detected(box):
    bad = dict(box)
    ct = bytearray(base64.b64decode(box["ct"]))
    ct[0] ^= 1
    bad["ct"] = base64.b64encode(bytes(ct)).decode()
    try:
        alerts.decrypt_box(bad, "a long test passphrase")
        return False
    except Exception:
        return True


def test_security():
    assert run() == 0


if __name__ == "__main__":
    sys.exit(1 if run() else 0)

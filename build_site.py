"""Prepare the files that get published, adding a strict Content Security Policy.

GitHub Pages cannot send security headers, so the policy is written into each page as a
<meta> tag. It is computed here, from the page's own script, so only that exact script can run.
Anything injected later (an extra script, an inline handler, a remote file) is refused by the browser.

    python build_site.py            # copies site/ to dist/ with the policy added
"""
from __future__ import annotations

import base64
import hashlib
import re
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).parent / "site"
DST = Path(__file__).parent / "dist"

SCRIPT_RE = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)


def script_hashes(html: str) -> list[str]:
    hashes = []
    for m in SCRIPT_RE.finditer(html):
        if "src=" in m.group("attrs").lower():
            raise SystemExit("External scripts are not allowed. Put the code inline or in a hashed file.")
        digest = hashlib.sha256(m.group("body").encode("utf-8")).digest()
        hashes.append("'sha256-" + base64.b64encode(digest).decode() + "'")
    return hashes


def policy(html: str) -> str:
    scripts = " ".join(script_hashes(html)) or "'none'"
    return "; ".join([
        "default-src 'none'",
        f"script-src {scripts}",          # only this page's own script, matched by its hash
        "style-src 'unsafe-inline'",       # inline styles only. They cannot run code.
        "img-src 'self' data:",
        "connect-src 'self'",              # the page may only talk to its own site (to fetch the data file)
        "manifest-src 'self'",
        "base-uri 'none'",
        "form-action 'none'",
    ])


def add_policy(html: str) -> str:
    meta = f'<meta http-equiv="Content-Security-Policy" content="{policy(html)}">'
    if re.search(r"<head[^>]*>", html, re.I):
        return re.sub(r"(<head[^>]*>)", r"\1\n" + meta.replace("\\", "\\\\"), html, count=1, flags=re.I)
    raise SystemExit("No <head> found to put the security policy in.")


def main() -> None:
    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST)
    for page in DST.glob("*.html"):
        page.write_text(add_policy(page.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"Wrote {DST} with a Content Security Policy on {len(list(DST.glob('*.html')))} pages.", file=sys.stderr)


if __name__ == "__main__":
    main()

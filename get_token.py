"""One-time helper: log in to Google in your browser and print a refresh token.

    python get_token.py path/to/credentials.json

Needs:  pip install google-auth-oauthlib
Run it on your own computer. Nothing is uploaded; copy the three printed values
into GitHub -> Settings -> Secrets and variables -> Actions.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]  # read-only: cannot send or delete mail

if len(sys.argv) != 2:
    sys.exit("Usage: python get_token.py credentials.json")

flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
if not creds.refresh_token:
    sys.exit("No refresh token returned. Remove the app at myaccount.google.com/permissions and try again.")

info = json.load(open(sys.argv[1]))
info = info.get("installed") or info.get("web")
# Written to a git-ignored file so the values never appear in a terminal or chat.
with open("github-secrets.txt", "w", encoding="utf-8") as f:
    f.write(f"GMAIL_CLIENT_ID={info['client_id']}\n")
    f.write(f"GMAIL_CLIENT_SECRET={info['client_secret']}\n")
    f.write(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}\n")
print("\nDone. The three GitHub secrets were saved to github-secrets.txt in this folder.")
print("Treat that file like a password: never commit it or paste it in chat. Delete it after setup.")

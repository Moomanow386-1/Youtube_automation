"""Run this once to authenticate with YouTube."""
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(__file__))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

print("Starting YouTube authentication...")
print()

if not os.path.exists("client_secrets.json"):
    print("ERROR: client_secrets.json not found!")
    print("Place it in:", os.path.abspath("client_secrets.json"))
    sys.exit(1)

print("Found client_secrets.json OK")
print("Opening browser for Google login...")
print("(If browser does not open, copy the URL from the terminal and open manually)")
print()

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secrets.json",
    SCOPES,
    redirect_uri="urn:ietf:wg:oauth:2.0:oob"
)

auth_url, _ = flow.authorization_url(prompt="consent")

print("="*60)
print("Open this URL in your browser:")
print()
print(auth_url)
print()
print("="*60)
print("After login -> Allow -> copy the code shown and paste here:")
code = input("Paste code here: ").strip()

flow.fetch_token(code=code)
creds = flow.credentials

with open("token.pickle", "wb") as f:
    pickle.dump(creds, f)

print()
print("Authentication successful!")
print("token.pickle saved.")

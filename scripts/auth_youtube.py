"""Run this once to authenticate with YouTube."""
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
print()

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secrets.json",
    SCOPES
)

creds = flow.run_local_server(port=0, prompt="consent")

with open("token.pickle", "wb") as f:
    pickle.dump(creds, f)

print()
print("Authentication successful!")
print("token.pickle saved.")

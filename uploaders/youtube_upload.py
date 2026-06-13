import os
import json
import pickle
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS = "client_secrets.json"
TOKEN_FILE = "token.pickle"

_REFRESH_RETRIES = 4
_REFRESH_DELAYS = [15, 30, 60, 120]


def _get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            last_err = None
            for attempt, delay in enumerate((_REFRESH_DELAYS[:_REFRESH_RETRIES]), start=1):
                try:
                    creds.refresh(Request())
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    print(f"  Token refresh attempt {attempt} failed: {e}")
                    if attempt < _REFRESH_RETRIES:
                        print(f"  Retrying in {delay}s...")
                        time.sleep(delay)
            if last_err:
                raise last_err
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=8080, open_browser=True)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return creds


def upload_video(video_path: str, title: str, description: str, tags: list[str],
                 thumbnail_path: str = None, privacy: str = "public") -> str:
    """Upload video to YouTube. Returns video URL."""
    creds = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags[:500],
            "categoryId": "27",  # Education
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(video_path, chunksize=10 * 1024 * 1024,
                            mimetype="video/mp4", resumable=True)

    print(f"  Uploading: {os.path.basename(video_path)}")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Upload {int(status.progress() * 100)}%...")

    video_id = response["id"]
    print(f"  Uploaded: https://youtube.com/watch?v={video_id}")

    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            print("  Thumbnail set.")
        except Exception as e:
            print(f"  Thumbnail failed (need channel verification): {e}")

    return f"https://youtube.com/watch?v={video_id}"

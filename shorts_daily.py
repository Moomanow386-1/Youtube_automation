"""
Daily shorts uploader — run by Task Scheduler (separate from auto_daily.py).
Uploads exactly 1 pending Short from the queue, EP.1 first.
"""
import os
import sys
import json
import time
import datetime

sys.path.insert(0, os.path.dirname(__file__))

from shorts_queue import get_next_pending, mark_uploaded, queue_stats
from uploaders.youtube_upload import upload_video

LOG_FILE = "logs/shorts_upload_log.json"


def _log(entry: dict):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            log = json.load(f)
    log.append(entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log[-180:], f, indent=2, ensure_ascii=False)


def main():
    today = datetime.date.today().isoformat()
    print(f"\n{'='*60}")
    print(f"Shorts Daily Upload -- {today}")
    print(f"{'='*60}\n")

    stats = queue_stats()
    print(f"Queue: {stats['pending']} pending / {stats['uploaded']} uploaded / {stats['total']} total\n")

    item = get_next_pending()
    if not item:
        print("No pending shorts. Queue is empty.")
        _log({"date": today, "status": "queue_empty"})
        return

    print(f"Uploading: {item['title']}")
    print(f"  File: {item['video_path']}")
    print(f"  EP.{item['ep']} of {item['total']} | Series: {item['series']}\n")

    if not os.path.exists(item["video_path"]):
        print(f"ERROR: File not found: {item['video_path']}")
        _log({"date": today, "status": "file_missing", "item": item})
        sys.exit(1)

    upload_delays = [30, 60, 120]
    last_err = None
    url = None
    for attempt in range(1, len(upload_delays) + 2):
        try:
            url = upload_video(
                video_path=item["video_path"],
                title=item["title"],
                description=item["description"],
                tags=item["tags"],
                thumbnail_path=None,
                privacy="public",
            )
            last_err = None
            break
        except Exception as e:
            last_err = e
            print(f"Upload attempt {attempt} failed: {e}")
            if attempt <= len(upload_delays):
                delay = upload_delays[attempt - 1]
                print(f"Retrying in {delay}s...")
                time.sleep(delay)

    if last_err:
        _log({"date": today, "status": "upload_failed", "title": item["title"], "error": str(last_err)})
        print(f"All upload attempts failed: {last_err}")
        sys.exit(1)

    mark_uploaded(item["video_path"], url)
    _log({
        "date": today,
        "status": "uploaded",
        "title": item["title"],
        "ep": item["ep"],
        "series": item["series"],
        "url": url,
    })
    print(f"\nSUCCESS: {url}")


if __name__ == "__main__":
    main()

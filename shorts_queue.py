"""
Manages the shorts upload queue.
Each item = one Short episode waiting to be uploaded.
"""
import json
import os
import random

QUEUE_FILE = "data/shorts_queue.json"

_HOOKS = [
    "The full story — told one episode at a time.",
    "History's most gripping cases, broken into chapters.",
    "Every detail matters. Watch every episode.",
    "The real story behind the headlines. Watch in order.",
    "Too big for one video. Dive into the full series.",
]


def load_queue() -> list:
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_queue(q: list):
    os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(q, f, indent=2, ensure_ascii=False)


def _short_title(main_title: str, ep: int) -> str:
    """Build EP-numbered title within YouTube's 100-char limit."""
    suffix = f" EP.{ep}"
    max_title = 100 - len(suffix)
    if len(main_title) > max_title:
        truncated = main_title[:max_title].rsplit(" ", 1)[0]
    else:
        truncated = main_title
    return truncated + suffix


def _short_description(main_title: str, ep: int, total: int, base_desc: str) -> str:
    hook = random.choice(_HOOKS)
    next_ep = f"EP.{ep + 1}" if ep < total else "the full series"
    return (
        f"{main_title}\n"
        f"EP.{ep} of {total}\n\n"
        f"{hook}\n\n"
        f"Follow so you don't miss {next_ep}!\n\n"
        "#Shorts #History #Mystery #TrueStory #Documentary #HistoryShorts"
    ).strip()


def add_series_to_queue(
    short_paths: list[str],
    main_title: str,
    description: str,
    tags: list[str],
) -> int:
    """
    Append all shorts from one video to the queue.
    Returns number of items added.
    """
    q = load_queue()
    total = len(short_paths)
    shorts_tags = [t for t in tags if t] + ["Shorts", "YouTubeShorts"]

    for i, path in enumerate(short_paths, start=1):
        q.append({
            "video_path": os.path.abspath(path),
            "title": _short_title(main_title, i),
            "description": _short_description(main_title, i, total, description),
            "tags": shorts_tags,
            "ep": i,
            "total": total,
            "series": main_title,
            "status": "pending",
        })

    save_queue(q)
    return total


def get_next_pending() -> dict | None:
    """Return the next pending item (oldest first), or None if queue is empty."""
    for item in load_queue():
        if item.get("status") == "pending":
            return item
    return None


def mark_uploaded(video_path: str, url: str):
    q = load_queue()
    abs_path = os.path.abspath(video_path)
    for item in q:
        if os.path.abspath(item["video_path"]) == abs_path:
            item["status"] = "uploaded"
            item["url"] = url
            break
    save_queue(q)


def queue_stats() -> dict:
    q = load_queue()
    pending = sum(1 for x in q if x.get("status") == "pending")
    uploaded = sum(1 for x in q if x.get("status") == "uploaded")
    return {"total": len(q), "pending": pending, "uploaded": uploaded}

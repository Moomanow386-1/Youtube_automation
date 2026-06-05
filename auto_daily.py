"""
Daily automation script — run once by Task Scheduler.
Picks a topic -> generates video -> uploads to YouTube.
"""
import os
import sys
import json
import random
import datetime
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

import config
from main import run_pipeline
from uploaders.youtube_upload import upload_video

LOG_FILE = "daily_log.json"
TOPIC_HISTORY_FILE = "topic_history.json"

# ── Topic generation ───────────────────────────────────────────────────────────

SEED_TOPICS = [
    "The Lost City of Machu Picchu and the Inca Empire",
    "The Mystery of the Voynich Manuscript",
    "Jack the Ripper: The Unsolved Victorian Mystery",
    "The Sinking of the USS Indianapolis",
    "The Dyatlov Pass Incident",
    "The Rise of Genghis Khan and the Mongol Empire",
    "The Real Count Dracula: Vlad the Impaler",
    "The Disappearance of Amelia Earhart",
    "The Black Death: Europe's Deadliest Plague",
    "The Secret Society of the Freemasons",
    "The Lost Colony of Roanoke",
    "The True Story Behind Anastasia Romanov",
    "The Curse of Tutankhamun's Tomb",
    "The Marie Celeste: Ghost Ship of the Atlantic",
    "The Great Fire of London 1666",
    "The Assassination of Archduke Franz Ferdinand",
    "The Mystery of the Nazca Lines",
    "The Fall of Constantinople",
    "The Dark History of Alcatraz Prison",
    "The War of the Worlds Panic of 1938",
    "The Japanese Unit 731 Experiments",
    "The Real Story of the Knights Templar",
    "The Library of Alexandria: History's Greatest Loss",
    "The Spanish Inquisition's Dark Secrets",
    "The Sinking of the Lusitania",
    "The Philadelphia Experiment",
    "The Mystery of Easter Island's Moai Statues",
    "The Real Dracula Castle and Transylvania History",
    "The Zodiac Killer: America's Most Elusive Serial Killer",
    "The Tunguska Event: Siberia's Mysterious Explosion",
]


def _load_history() -> list[str]:
    if os.path.exists(TOPIC_HISTORY_FILE):
        with open(TOPIC_HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def _save_history(history: list[str]):
    with open(TOPIC_HISTORY_FILE, "w") as f:
        json.dump(history[-60:], f, indent=2)


def _pick_topic(history: list[str]) -> str:
    used = set(history)
    available = [t for t in SEED_TOPICS if t not in used]

    if available:
        return random.choice(available)

    # All seeds used — generate new topic with Ollama
    prompt = """Generate ONE unique YouTube video topic for a history/mystery channel.
Format: just the topic title, nothing else.
Make it intriguing, specific, and different from common topics.
Examples: "The Mysterious Death of Edgar Allan Poe", "How the Aztecs Built Tenochtitlan"
Topic:"""

    try:
        resp = requests.post(
            f"{config.OLLAMA_HOST}/api/generate",
            json={"model": config.OLLAMA_MODEL, "prompt": prompt,
                  "stream": False, "options": {"num_predict": 50}},
            timeout=60
        )
        topic = resp.json()["response"].strip().strip('"').strip("'")
        if len(topic) > 10:
            return topic
    except Exception:
        pass

    # Hard fallback: reuse oldest topic
    return history[0] if history else SEED_TOPICS[0]


# ── Log ────────────────────────────────────────────────────────────────────────

def _log(entry: dict):
    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            log = json.load(f)
    log.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(log[-90:], f, indent=2)


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    today = datetime.date.today().isoformat()
    print(f"\n{'='*60}")
    print(f"Daily Auto Run — {today}")
    print(f"{'='*60}\n")

    history = _load_history()
    topic = _pick_topic(history)
    print(f"Today's topic: {topic}\n")

    try:
        video_path, thumb_path = run_pipeline(topic)
    except Exception as e:
        _log({"date": today, "topic": topic, "status": "pipeline_failed", "error": str(e)})
        print(f"Pipeline failed: {e}")
        sys.exit(1)

    # Read script for upload metadata
    script_file = video_path.replace(".mp4", "_script.txt")
    title, description, tags = topic, "", []

    if os.path.exists(script_file):
        with open(script_file, encoding="utf-8") as f:
            content = f.read()
        for line in content.split("\n"):
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            elif line.startswith("TAGS:"):
                tags = [t.strip().lstrip('#') for t in line.replace("TAGS:", "").split(",")]
        desc_start = content.find("DESCRIPTION:\n")
        script_start = content.find("SCRIPT:\n")
        if desc_start != -1 and script_start != -1:
            description = content[desc_start + 13:script_start].strip()

    try:
        url = upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            thumbnail_path=thumb_path,
            privacy="public"
        )
        _log({"date": today, "topic": topic, "status": "uploaded", "url": url})
        history.append(topic)
        _save_history(history)
        print(f"\nSUCCESS: {url}")
    except Exception as e:
        _log({"date": today, "topic": topic, "status": "upload_failed",
              "video": video_path, "error": str(e)})
        print(f"Upload failed (video saved at {video_path}): {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
One-time setup: cut Dyatlov + all newer videos into Shorts and add to queue.
Run once: python setup_shorts_backlog.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from generators.shorts_gen import cut_shorts
from shorts_queue import add_series_to_queue, queue_stats

# Videos to process in chronological order (Dyatlov onwards)
BACKLOG_VIDEOS = [
    "The Dyatlov Pass Incident What REALLY Happened to.mp4",
    "The Terrifying Secret of Alcatraz Island.mp4",
    "The SHOCKING Truth About Genghis Khans Mother and.mp4",
    "The SHOCKING Truth About Easter Islands Giant Moai.mp4",
    "The SHOCKING Truth Behind Siberias Deadly Blast.mp4",
]


def _read_script_meta(video_path: str) -> tuple[str, str, list[str]]:
    """Read title, description, tags from the companion script .txt file."""
    script_path = video_path.replace(".mp4", "_script.txt")
    title = os.path.splitext(os.path.basename(video_path))[0]
    description = ""
    tags = []

    if not os.path.exists(script_path):
        return title, description, tags

    with open(script_path, encoding="utf-8") as f:
        content = f.read()

    for line in content.split("\n"):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("TAGS:"):
            tags = [t.strip().lstrip("#") for t in line.replace("TAGS:", "").split(",") if t.strip()]

    desc_start = content.find("DESCRIPTION:\n")
    script_start = content.find("SCRIPT:\n")
    if desc_start != -1 and script_start != -1:
        description = content[desc_start + 13:script_start].strip()

    return title, description, tags


def main():
    print("=" * 60)
    print("Shorts Backlog Setup")
    print("=" * 60)

    shorts_dir = os.path.join(config.OUTPUT_DIR, "shorts")
    total_queued = 0

    for filename in BACKLOG_VIDEOS:
        video_path = os.path.join(config.OUTPUT_DIR, filename)
        if not os.path.exists(video_path):
            print(f"\nSKIP (not found): {filename}")
            continue

        print(f"\nProcessing: {filename}")
        title, description, tags = _read_script_meta(video_path)
        print(f"  Title: {title}")

        try:
            short_paths = cut_shorts(video_path, shorts_dir)
            added = add_series_to_queue(short_paths, title, description, tags)
            total_queued += added
            print(f"  Queued {added} shorts.")
        except Exception as e:
            print(f"  ERROR: {e}")

    stats = queue_stats()
    print(f"\n{'='*60}")
    print(f"Done. Added {total_queued} shorts to queue.")
    print(f"Queue: {stats['pending']} pending / {stats['total']} total")
    print(f"At 1 Short/day = ~{stats['pending']} days to clear.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

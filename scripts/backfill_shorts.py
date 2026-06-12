"""
Backfill shorts for all existing long videos that don't have shorts in queue yet.
Run once from project root: python scripts/backfill_shorts.py
"""
import os
import sys
import json
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
from generators.shorts_gen import cut_shorts
from shorts_queue import add_series_to_queue, queue_stats, load_queue

OUTPUT_DIR = config.OUTPUT_DIR
SHORTS_DIR = os.path.join(OUTPUT_DIR, "shorts")
SCRIPT_DIR = OUTPUT_DIR  # _script.txt lives next to the mp4

# Only process videos from Dyatlov Pass onwards (2026-06-06)
# Videos before this date are not part of the shorts series
START_FROM_DATE = "2026-06-06"


def get_queued_video_paths() -> set:
    q = load_queue()
    paths = set()
    for item in q:
        # Derive long video path from short path pattern
        # short: .../shorts/SomeName_short_01.mp4
        # long:  .../SomeName.mp4
        short_path = item.get("video_path", "")
        if "_short_" in short_path:
            base = os.path.basename(short_path)
            long_name = base.split("_short_")[0] + ".mp4"
            paths.add(long_name.lower())
    return paths


def read_metadata(script_path: str) -> tuple[str, str, list]:
    title, description, tags = "", "", []
    if not os.path.exists(script_path):
        return title, description, tags
    with open(script_path, encoding="utf-8") as f:
        content = f.read()
    for line in content.split("\n"):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("TAGS:"):
            tags = [t.strip().lstrip("#") for t in line.replace("TAGS:", "").split(",")]
    desc_start = content.find("DESCRIPTION:\n")
    script_start = content.find("SCRIPT:\n")
    if desc_start != -1 and script_start != -1:
        description = content[desc_start + 13:script_start].strip()
    return title, description, tags


def main():
    queued = get_queued_video_paths()
    print(f"Already in queue (by video): {len(queued)} videos\n")

    import datetime
    cutoff = datetime.date.fromisoformat(START_FROM_DATE)
    all_mp4 = glob.glob(os.path.join(OUTPUT_DIR, "*.mp4"))
    # Sort by modification time (chronological) — NOT by filename
    all_mp4.sort(key=lambda p: os.path.getmtime(p))
    mp4_files = [
        p for p in all_mp4
        if datetime.date.fromtimestamp(os.path.getmtime(p)) >= cutoff
    ]
    print(f"Long videos from {START_FROM_DATE} onwards (chronological order):")
    for p in mp4_files:
        d = datetime.date.fromtimestamp(os.path.getmtime(p))
        print(f"  {d}  {os.path.basename(p)}")
    print()

    total_added = 0
    for mp4 in mp4_files:
        fname = os.path.basename(mp4)
        if fname.lower() in queued:
            print(f"SKIP (already queued): {fname}")
            continue

        print(f"\nProcessing: {fname}")
        script_path = mp4.replace(".mp4", "_script.txt")
        title, description, tags = read_metadata(script_path)
        if not title:
            title = os.path.splitext(fname)[0]

        try:
            short_paths = cut_shorts(mp4, SHORTS_DIR)
            if not short_paths:
                print(f"  WARNING: no shorts cut from {fname}")
                continue
            added = add_series_to_queue(short_paths, title, description, tags)
            total_added += added
            print(f"  Added {added} shorts (EP.1-{added}) for: {title}")
        except Exception as e:
            print(f"  ERROR: {e}")

    stats = queue_stats()
    print(f"\n{'='*60}")
    print(f"Done. Added {total_added} shorts total.")
    print(f"Queue now: {stats['pending']} pending / {stats['uploaded']} uploaded / {stats['total']} total")


if __name__ == "__main__":
    main()

"""
Upload a finished video to YouTube.
Usage: python upload_now.py "Video Title"
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(__file__))
from uploaders.youtube_upload import upload_video

def find_files(title_part: str):
    output = "output"
    matches = [f for f in os.listdir(output) if title_part.lower() in f.lower() and f.endswith(".mp4")]
    return matches

def read_metadata(script_path: str):
    title, description, tags = "", "", []
    if not os.path.exists(script_path):
        return title, description, tags
    with open(script_path, encoding="utf-8") as f:
        content = f.read()
    for line in content.split("\n"):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("TAGS:"):
            tags = [t.strip() for t in line.replace("TAGS:", "").split(",")]
    desc_start = content.find("DESCRIPTION:\n")
    script_start = content.find("SCRIPT:\n")
    if desc_start != -1:
        end = script_start if script_start != -1 else len(content)
        description = content[desc_start + 13:end].strip()
    return title, description, tags

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # List available videos
        print("Available videos in output/:")
        for f in sorted(os.listdir("output")):
            if f.endswith(".mp4"):
                print(f"  - {f}")
        print()
        print("Usage: python upload_now.py \"Dracula\"")
        sys.exit(0)

    search = " ".join(sys.argv[1:])
    matches = find_files(search)

    if not matches:
        print(f"No video found matching: {search}")
        sys.exit(1)

    video_file = matches[0]
    video_path = os.path.join("output", video_file)
    script_path = video_path.replace(".mp4", "_script.txt")
    thumb_path = video_path.replace(".mp4", "_thumbnail.jpg")

    title, description, tags = read_metadata(script_path)
    if not title:
        title = video_file.replace(".mp4", "")

    print(f"Uploading: {video_file}")
    print(f"Title: {title}")
    print()

    url = upload_video(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        thumbnail_path=thumb_path if os.path.exists(thumb_path) else None,
        privacy="public"
    )
    print(f"\nDone! {url}")

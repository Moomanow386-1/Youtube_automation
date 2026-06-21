import os
import sys
import time
import re
import shutil
import config
from generators.script_gen import generate_script
from generators.tts_gen import generate_audio
from generators.video_gen import create_video
from generators.thumbnail_gen import generate_thumbnail
from generators.topic_gen import pick_best_topic

def sanitize_filename(text: str) -> str:
    text = text.replace("'", "").replace("'", "")
    return re.sub(r'[<>:"/\\|?*]', '', text)[:50].strip()

def run_pipeline(topic: str):
    print(f"\n{'='*60}")
    print(f"Topic: {topic}")
    print(f"{'='*60}\n")

    # Step 1: Generate script
    print("[1/4] Generating script...")
    start = time.time()
    data = generate_script(topic)
    print(f"  Title: {data['title']}")
    print(f"  Script length: {len(data['script'].split())} words")
    print(f"  Time: {time.time()-start:.1f}s\n")

    slug = sanitize_filename(data["title"])
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.TEMP_DIR, exist_ok=True)

    # Save script + metadata
    script_file = os.path.join(config.OUTPUT_DIR, f"{slug}_script.txt")
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(f"TITLE: {data['title']}\n\n")
        f.write(f"DESCRIPTION:\n{data['description']}\n\n")
        f.write(f"TAGS: {', '.join('#' + t.lstrip('#') for t in data['tags'])}\n\n")
        if data.get("pinned_comment"):
            f.write(f"PINNED COMMENT:\n{data['pinned_comment']}\n\n")
        if data.get("cta_script"):
            f.write(f"END-SCREEN CTA (~10s spoken):\n{data['cta_script']}\n\n")
        f.write(f"SCRIPT:\n{data['script']}")
    print(f"  Script saved: {script_file}")

    # Step 2: Generate TTS + subtitles
    print("[2/4] Generating voice + subtitles...")
    start = time.time()
    audio_path = os.path.join(config.TEMP_DIR, f"{slug}_audio.mp3")
    audio_path, srt_path = generate_audio(data["script"], audio_path)
    print(f"  Audio: {audio_path}")
    print(f"  Subtitles: {srt_path}")
    print(f"  Time: {time.time()-start:.1f}s\n")

    # Step 3: Generate thumbnail
    print("[3/4] Generating thumbnail...")
    start = time.time()
    thumb_path = os.path.join(config.OUTPUT_DIR, f"{slug}_thumbnail.jpg")
    generate_thumbnail(data["title"], data.get("video_keywords", [topic]), thumb_path)
    print(f"  Thumbnail: {thumb_path}")
    print(f"  Time: {time.time()-start:.1f}s\n")

    # Step 4: Assemble video
    print("[4/4] Assembling video...")
    start = time.time()
    video_path = os.path.join(config.OUTPUT_DIR, f"{slug}.mp4")
    create_video(audio_path, srt_path, data["title"], data.get("video_keywords", [topic]), video_path)
    print(f"  Time: {time.time()-start:.1f}s\n")

    size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"{'='*60}")
    print(f"DONE!")
    print(f"  Video:     {video_path} ({size_mb:.1f} MB)")
    print(f"  Thumbnail: {thumb_path}")
    print(f"  Script:    {script_file}")
    print(f"{'='*60}\n")

    # Copy SRT to output before cleanup (needed for shorts subtitle burning)
    srt_output_path = os.path.join(config.OUTPUT_DIR, f"{slug}_subtitles.srt")
    if os.path.exists(srt_path):
        shutil.copy2(srt_path, srt_output_path)

    # Clean temp files (retry on Windows file-lock)
    if os.path.exists(config.TEMP_DIR):
        for attempt in range(5):
            try:
                shutil.rmtree(config.TEMP_DIR)
                break
            except PermissionError:
                time.sleep(2)
        os.makedirs(config.TEMP_DIR, exist_ok=True)

    return video_path, thumb_path, srt_output_path

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--auto":
            print("YouTube Automation Pipeline — AUTO TOPIC MODE")
            print("Picking best topic via AI...\n")
            topic = pick_best_topic()
        else:
            topic = " ".join(sys.argv[1:])
    else:
        print("YouTube Automation Pipeline")
        print("Examples:")
        print("  python main.py \"The Lost City of Atlantis\"")
        print("  python main.py --auto   (AI picks best topic)")
        print()
        topic = input("Enter topic (or press Enter for AI auto-pick): ").strip()
        if not topic:
            print("Auto-picking topic...\n")
            topic = pick_best_topic()

    run_pipeline(topic)

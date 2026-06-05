import subprocess
import os
import re
import json
import time
import requests
import random
import config

_FFMPEG_BIN = r"C:\Users\fusen\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
FFMPEG = os.path.join(_FFMPEG_BIN, "ffmpeg.exe")
FFPROBE = os.path.join(_FFMPEG_BIN, "ffprobe.exe")
USED_MEDIA_FILE = "used_media.json"


# ── Used media tracker (cross-video dedup) ────────────────────────────────────

def _load_used() -> set:
    if os.path.exists(USED_MEDIA_FILE):
        with open(USED_MEDIA_FILE) as f:
            return set(json.load(f))
    return set()

def _save_used(used: set):
    with open(USED_MEDIA_FILE, "w") as f:
        json.dump(list(used), f)


# ── Utilities ─────────────────────────────────────────────────────────────────

def _get_duration(path: str) -> float:
    result = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def _download_bytes(url: str, timeout: int = 120) -> bytes | None:
    try:
        r = requests.get(url, stream=True, timeout=timeout,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.content
    except Exception:
        return None


# ── Pexels Videos ─────────────────────────────────────────────────────────────

def _fetch_pexels_videos(keyword: str, count: int = 3, used: set = set()) -> list[tuple[str, str]]:
    """Returns list of (video_url, pexels_id)."""
    params = {"query": keyword, "per_page": 15, "orientation": "landscape"}
    try:
        r = requests.get("https://api.pexels.com/videos/search",
                         headers={"Authorization": config.PEXELS_API_KEY},
                         params=params, timeout=10)
        videos = r.json().get("videos", [])
        random.shuffle(videos)
        results = []
        for v in videos:
            pid = f"v_{v['id']}"
            if pid in used:
                continue
            files = sorted(v["video_files"], key=lambda f: f.get("width", 0), reverse=True)
            best = next((f for f in files if 1280 <= f.get("width", 0) <= 1920), None)
            if not best and files:
                best = files[0]
            if best:
                results.append((best["link"], pid))
            if len(results) >= count:
                break
        return results
    except Exception:
        return []


# ── Pexels Photos ─────────────────────────────────────────────────────────────

def _fetch_pexels_photos(keyword: str, count: int = 2, used: set = set()) -> list[tuple[str, str]]:
    """Returns list of (photo_url, pexels_id)."""
    params = {"query": keyword, "per_page": 15, "orientation": "landscape"}
    try:
        r = requests.get("https://api.pexels.com/v1/search",
                         headers={"Authorization": config.PEXELS_API_KEY},
                         params=params, timeout=10)
        photos = r.json().get("photos", [])
        random.shuffle(photos)
        results = []
        for p in photos:
            pid = f"p_{p['id']}"
            if pid in used:
                continue
            results.append((p["src"]["large2x"], pid))
            if len(results) >= count:
                break
        return results
    except Exception:
        return []


# ── Normalize ─────────────────────────────────────────────────────────────────

def _normalize_video(src: str, dst: str, max_duration: float = 40.0) -> float:
    actual = _get_duration(src)
    use_dur = min(actual, max_duration) if actual > 0 else max_duration
    vf = (
        f"scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1,fps={config.VIDEO_FPS}"
    )
    cmd = [FFMPEG, "-y", "-i", src, "-t", str(use_dur), "-vf", vf,
           "-c:v", "libx264", "-preset", "fast", "-crf", "26", "-an", dst]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return use_dur if result.returncode == 0 else 0.0

def _photo_to_clip(img_path: str, out_path: str, duration: float = 15.0) -> float:
    fps = config.VIDEO_FPS
    d = int(duration * fps)
    directions = [
        f"zoompan=z='min(zoom+0.0006,1.25)':d={d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        f"zoompan=z='if(lte(zoom,1.0),1.25,max(1.001,zoom-0.0006))':d={d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        f"zoompan=z='min(zoom+0.0006,1.25)':d={d}:x='0':y='0'",
        f"zoompan=z='min(zoom+0.0006,1.25)':d={d}:x='iw-iw/zoom':y='ih-ih/zoom'",
    ]
    vf = (
        f"scale=3840:-1,{random.choice(directions)},"
        f"scale={config.VIDEO_WIDTH}:{config.VIDEO_HEIGHT}:flags=lanczos,setsar=1,fps={fps}"
    )
    cmd = [FFMPEG, "-y", "-loop", "1", "-i", img_path,
           "-vf", vf, "-t", str(duration),
           "-c:v", "libx264", "-preset", "fast", "-crf", "26", "-an", out_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return duration if result.returncode == 0 else 0.0


# ── Pixabay Videos ────────────────────────────────────────────────────────────

def _fetch_pixabay_videos(keyword: str, count: int = 3, used: set = set()) -> list[tuple[str, str]]:
    """Returns list of (video_url, pixabay_id)."""
    if not config.PIXABAY_API_KEY:
        return []
    params = {"key": config.PIXABAY_API_KEY, "q": keyword, "per_page": 15,
              "video_type": "film", "orientation": "horizontal"}
    try:
        r = requests.get("https://pixabay.com/api/videos/", params=params, timeout=10)
        hits = r.json().get("hits", [])
        random.shuffle(hits)
        results = []
        for h in hits:
            pid = f"pbv_{h['id']}"
            if pid in used:
                continue
            vids = h.get("videos", {})
            best = vids.get("large") or vids.get("medium") or vids.get("small")
            if best and best.get("url"):
                results.append((best["url"], pid))
            if len(results) >= count:
                break
        return results
    except Exception:
        return []


# ── Pixabay Photos ────────────────────────────────────────────────────────────

def _fetch_pixabay_photos(keyword: str, count: int = 2, used: set = set()) -> list[tuple[str, str]]:
    """Returns list of (photo_url, pixabay_id)."""
    if not config.PIXABAY_API_KEY:
        return []
    params = {"key": config.PIXABAY_API_KEY, "q": keyword, "per_page": 15,
              "image_type": "photo", "orientation": "horizontal"}
    try:
        r = requests.get("https://pixabay.com/api/", params=params, timeout=10)
        hits = r.json().get("hits", [])
        random.shuffle(hits)
        results = []
        for h in hits:
            pid = f"pbp_{h['id']}"
            if pid in used:
                continue
            url = h.get("largeImageURL") or h.get("webformatURL")
            if url:
                results.append((url, pid))
            if len(results) >= count:
                break
        return results
    except Exception:
        return []


# ── Wikimedia Commons Photos ───────────────────────────────────────────────────

def _fetch_wikimedia_photos(keyword: str, count: int = 3, used: set = set()) -> list[tuple[str, str]]:
    """Returns list of (image_url, wikimedia_id). Public domain / CC."""
    params = {
        "action": "query",
        "generator": "search",
        "gsrnamespace": 6,
        "gsrsearch": f"filetype:bitmap {keyword}",
        "gsrlimit": 20,
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
        "iiurlwidth": 1920,
        "format": "json",
    }
    try:
        r = requests.get("https://commons.wikimedia.org/w/api.php",
                         params=params, timeout=15,
                         headers={"User-Agent": "YoutubeAutomation/1.0"})
        pages = r.json().get("query", {}).get("pages", {}).values()
        items = list(pages)
        random.shuffle(items)
        results = []
        for page in items:
            info = page.get("imageinfo", [{}])[0]
            mime = info.get("mime", "")
            if mime not in ("image/jpeg", "image/png"):
                continue
            width = info.get("thumbwidth") or info.get("width") or 0
            height = info.get("thumbheight") or info.get("height") or 0
            if width < 800 or height < 400:
                continue
            url = info.get("thumburl") or info.get("url")
            pid = f"wm_{page['pageid']}"
            if pid in used or not url:
                continue
            results.append((url, pid))
            if len(results) >= count:
                break
        return results
    except Exception:
        return []


# ── Pollinations.ai — script-specific AI images ───────────────────────────────

def _ai_image_to_clip(prompt: str, out_path: str, img_path: str, duration: float = 15.0) -> float:
    seed = random.randint(1000, 999999)
    clean = re.sub(r'[^\w\s]', '', prompt).replace(" ", "%20")[:120]
    url = f"https://image.pollinations.ai/prompt/{clean}%20cinematic%20dramatic?width=1920&height=1080&nologo=true&seed={seed}"
    data = _download_bytes(url, timeout=60)
    if not data or len(data) < 5000:
        return 0.0
    with open(img_path, "wb") as f:
        f.write(data)
    return _photo_to_clip(img_path, out_path, duration)


def _make_ai_prompts(topic: str, keywords: list[str]) -> list[str]:
    """Generate specific AI image prompts from topic + keywords."""
    prompts = []
    for kw in keywords[:6]:
        prompts.append(f"{kw} historical documentary photograph")
    prompts += [
        f"{topic} dramatic scene cinematic",
        f"{topic} newspaper headline vintage 1900s",
        f"{topic} artifact close up museum",
        f"{topic} location aerial view dramatic",
        f"{topic} black and white historical photograph",
        f"{topic} map old parchment",
    ]
    return prompts


# ── Main background builder ────────────────────────────────────────────────────

def _build_background(topic: str, keywords: list[str], duration: float, output_path: str):
    if not config.PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY missing")

    clips_dir = os.path.join(config.TEMP_DIR, "clips")
    os.makedirs(clips_dir, exist_ok=True)

    used = _load_used()
    newly_used = set()
    ready: list[tuple[str, float]] = []
    idx = 0

    def total_dur():
        return sum(d for _, d in ready)

    # Phase 1: Pexels videos — script-specific keywords only
    print(f"  [Phase 1] Pexels videos ({len(keywords)} keywords)...")
    for term in keywords:
        if total_dur() >= duration:
            break
        for url, pid in _fetch_pexels_videos(term, count=3, used=used | newly_used):
            if total_dur() >= duration:
                break
            raw = os.path.join(clips_dir, f"raw_{idx}.mp4")
            norm = os.path.join(clips_dir, f"clip_{idx:03d}.mp4")
            data = _download_bytes(url)
            if data:
                with open(raw, "wb") as f:
                    f.write(data)
                d = _normalize_video(raw, norm, max_duration=40.0)
                if d > 0:
                    ready.append((norm, d))
                    newly_used.add(pid)
                    print(f"    [video {idx:02d}] '{term}' {d:.0f}s -> {total_dur():.0f}/{duration:.0f}s")
                    idx += 1

    # Phase 2: Pixabay videos
    if total_dur() < duration and config.PIXABAY_API_KEY:
        print(f"  [Phase 2] Pixabay videos ({len(keywords)} keywords)...")
        for term in keywords:
            if total_dur() >= duration:
                break
            for url, pid in _fetch_pixabay_videos(term, count=3, used=used | newly_used):
                if total_dur() >= duration:
                    break
                raw = os.path.join(clips_dir, f"raw_{idx}.mp4")
                norm = os.path.join(clips_dir, f"clip_{idx:03d}.mp4")
                data = _download_bytes(url)
                if data:
                    with open(raw, "wb") as f:
                        f.write(data)
                    d = _normalize_video(raw, norm, max_duration=40.0)
                    if d > 0:
                        ready.append((norm, d))
                        newly_used.add(pid)
                        print(f"    [pbvideo {idx:02d}] '{term}' {d:.0f}s -> {total_dur():.0f}/{duration:.0f}s")
                        idx += 1

    # Phase 3: Pexels photos — same script keywords (NOT generic atmospheric)
    print(f"  [Phase 3] Pexels photos (script keywords)...")
    for term in keywords:
        if total_dur() >= duration:
            break
        for url, pid in _fetch_pexels_photos(term, count=2, used=used | newly_used):
            if total_dur() >= duration:
                break
            raw_img = os.path.join(clips_dir, f"img_{idx}.jpg")
            clip_out = os.path.join(clips_dir, f"clip_{idx:03d}.mp4")
            data = _download_bytes(url)
            if data:
                with open(raw_img, "wb") as f:
                    f.write(data)
                d = _photo_to_clip(raw_img, clip_out, duration=15.0)
                if d > 0:
                    ready.append((clip_out, d))
                    newly_used.add(pid)
                    print(f"    [photo {idx:02d}] '{term}' -> {total_dur():.0f}/{duration:.0f}s")
                    idx += 1

    # Phase 4: Pixabay photos
    if total_dur() < duration and config.PIXABAY_API_KEY:
        print(f"  [Phase 4] Pixabay photos...")
        for term in keywords:
            if total_dur() >= duration:
                break
            for url, pid in _fetch_pixabay_photos(term, count=2, used=used | newly_used):
                if total_dur() >= duration:
                    break
                raw_img = os.path.join(clips_dir, f"img_{idx}.jpg")
                clip_out = os.path.join(clips_dir, f"clip_{idx:03d}.mp4")
                data = _download_bytes(url)
                if data:
                    with open(raw_img, "wb") as f:
                        f.write(data)
                    d = _photo_to_clip(raw_img, clip_out, duration=15.0)
                    if d > 0:
                        ready.append((clip_out, d))
                        newly_used.add(pid)
                        print(f"    [pbphoto {idx:02d}] '{term}' -> {total_dur():.0f}/{duration:.0f}s")
                        idx += 1

    # Phase 5: Wikimedia Commons photos
    if total_dur() < duration:
        print(f"  [Phase 5] Wikimedia Commons photos...")
        for term in keywords:
            if total_dur() >= duration:
                break
            for url, pid in _fetch_wikimedia_photos(term, count=3, used=used | newly_used):
                if total_dur() >= duration:
                    break
                raw_img = os.path.join(clips_dir, f"img_{idx}.jpg")
                clip_out = os.path.join(clips_dir, f"clip_{idx:03d}.mp4")
                data = _download_bytes(url)
                if data:
                    with open(raw_img, "wb") as f:
                        f.write(data)
                    d = _photo_to_clip(raw_img, clip_out, duration=15.0)
                    if d > 0:
                        ready.append((clip_out, d))
                        newly_used.add(pid)
                        print(f"    [wiki {idx:02d}] '{term}' -> {total_dur():.0f}/{duration:.0f}s")
                        idx += 1

    # Phase 6: Pollinations AI — topic+keyword specific prompts
    if total_dur() < duration:
        ai_prompts = _make_ai_prompts(topic, keywords)
        print(f"  [Phase 6] AI images to fill {duration - total_dur():.0f}s...")
        for prompt in ai_prompts:
            if total_dur() >= duration:
                break
            img_path = os.path.join(clips_dir, f"ai_{idx}.jpg")
            clip_out = os.path.join(clips_dir, f"clip_{idx:03d}.mp4")
            d = _ai_image_to_clip(prompt, clip_out, img_path, duration=15.0)
            if d > 0:
                ready.append((clip_out, d))
                print(f"    [AI {idx:02d}] '{prompt[:60]}' -> {total_dur():.0f}/{duration:.0f}s")
                idx += 1
            time.sleep(0.5)

    if not ready:
        raise RuntimeError("No footage obtained")

    # Save used IDs
    _save_used(used | newly_used)

    total = total_dur()
    print(f"  Got {len(ready)} unique clips = {total:.0f}s for {duration:.0f}s video")

    concat_file = os.path.join(config.TEMP_DIR, "concat.txt")
    with open(concat_file, "w") as f:
        for clip_path, _ in ready:
            abs_p = os.path.abspath(clip_path).replace("\\", "/")
            f.write(f"file '{abs_p}'\n")

    cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
           "-t", str(duration + 2), "-c:v", "libx264", "-preset", "fast", "-crf", "24", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Concat failed:\n{result.stderr[-400:]}")


# ── Assemble ──────────────────────────────────────────────────────────────────

def _assemble_video(bg_video: str, audio: str, title: str, duration: float, output: str):
    cmd = [FFMPEG, "-y", "-i", bg_video, "-i", audio,
           "-shortest", "-t", str(duration),
           "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "fast", "-crf", "23",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", output]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg assemble failed:\n{result.stderr[-600:]}")


def create_video(audio_path: str, srt_path: str, title: str, keywords: list[str], output_path: str) -> str:
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    duration = _get_duration(audio_path)
    print(f"  Audio: {duration:.1f}s ({duration/60:.1f} min)")
    bg_path = os.path.join(config.TEMP_DIR, "background_final.mp4")
    _build_background(title, keywords, duration, bg_path)
    print("  Assembling final video...")
    _assemble_video(bg_path, audio_path, title, duration, output_path)
    return output_path

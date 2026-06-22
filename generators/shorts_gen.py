import re
import subprocess
import os
import config

_FFMPEG_BIN = r"C:\Users\fusen\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
FFMPEG = os.path.join(_FFMPEG_BIN, "ffmpeg.exe")
FFPROBE = os.path.join(_FFMPEG_BIN, "ffprobe.exe")

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
MIN_CHUNK = 45    # 0:45
MAX_CHUNK = 58    # 0:58 — stays under YouTube's 60s Shorts sweet spot
TARGET_CHUNK = 52  # 0:52
MAX_EPISODES = 10  # cap series length — beyond 10 EP drop-off spikes
HOOK_DURATION = 3.0  # seconds the hook PNG is visible (for log info only — PNG shown full duration)

# Subtitle style burned into shorts
_SUB_STYLE = (
    "FontName=Arial,Bold=1,FontSize=14,"
    "PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00000000,"
    "BackColour=&H80000000,"
    "Outline=3,Shadow=1,"
    "Alignment=2,MarginV=60"
)

_HOOK_FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
_HOOK_FONT_REG  = r"C:\Windows\Fonts\arial.ttf"


# ── SRT helpers ────────────────────────────────────────────────────────────────

def _srt_time_to_sec(t: str) -> float:
    h, m, rest = t.split(":")
    s, ms = rest.replace(",", ".").split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def _sec_to_srt_time(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _parse_srt(srt_path: str) -> list[tuple[float, float, str]]:
    with open(srt_path, encoding="utf-8-sig") as f:
        content = f.read()
    entries = []
    for block in re.split(r"\n\n+", content.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        try:
            start_str, end_str = lines[1].split(" --> ")
            entries.append((
                _srt_time_to_sec(start_str.strip()),
                _srt_time_to_sec(end_str.strip()),
                "\n".join(lines[2:]),
            ))
        except Exception:
            continue
    return entries


def _write_chunk_srt(entries: list, chunk_start: float, chunk_end: float, out_path: str):
    chunk_entries = []
    for start, end, text in entries:
        if end <= chunk_start or start >= chunk_end:
            continue
        chunk_entries.append((
            max(0.0, start - chunk_start),
            min(chunk_end - chunk_start, end - chunk_start),
            text,
        ))
    with open(out_path, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(chunk_entries, 1):
            f.write(f"{i}\n{_sec_to_srt_time(start)} --> {_sec_to_srt_time(end)}\n{text}\n\n")


def _escape_filter_path(path: str) -> str:
    return path.replace("\\", "/").replace(":", "\\:")


# ── Hook PNG (PIL) — bypasses fontconfig entirely ──────────────────────────────

def _make_hook_png(ep: int, total: int, series_title: str, out_path: str) -> bool:
    """Create a semi-transparent 'Part X of Y' banner PNG using PIL. Returns False on failure."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        w, h = SHORTS_WIDTH, 220
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Semi-transparent black background
        draw.rectangle([0, 0, w, h], fill=(0, 0, 0, 170))

        # Load fonts; fall back to default if file missing
        try:
            font_large = ImageFont.truetype(_HOOK_FONT_BOLD, 72)
        except Exception:
            font_large = ImageFont.load_default()
        try:
            font_small = ImageFont.truetype(_HOOK_FONT_REG, 36)
        except Exception:
            font_small = ImageFont.load_default()

        part_text = f"Part {ep} of {total}"
        bbox = draw.textbbox((0, 0), part_text, font=font_large)
        tw = bbox[2] - bbox[0]
        draw.text(((w - tw) // 2, 10), part_text, fill=(255, 255, 255, 255), font=font_large)

        title_short = series_title[:38] + ("..." if len(series_title) > 38 else "")
        bbox2 = draw.textbbox((0, 0), title_short, font=font_small)
        tw2 = bbox2[2] - bbox2[0]
        draw.text(((w - tw2) // 2, 100), title_short, fill=(255, 220, 0, 255), font=font_small)

        img.save(out_path, "PNG")
        return True
    except Exception as e:
        print(f"  [hook png] failed: {e}")
        return False


# ── Duration helpers ───────────────────────────────────────────────────────────

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


def _calc_n_chunks(total: float) -> tuple[int, float]:
    if total <= MAX_CHUNK:
        return 1, total

    n = max(1, round(total / TARGET_CHUNK))
    chunk = total / n

    while chunk > MAX_CHUNK:
        n += 1
        chunk = total / n

    while chunk < MIN_CHUNK and n > 1:
        n -= 1
        chunk = total / n

    if n > MAX_EPISODES:
        n = MAX_EPISODES
        chunk = total / n

    return n, chunk


# ── Main export ────────────────────────────────────────────────────────────────

def cut_shorts(
    video_path: str,
    output_dir: str,
    srt_path: str = None,
    series_title: str = None,
) -> list[str]:
    """
    Cut landscape video into vertical YouTube Shorts (1080x1920, ~52s each).
    - Burns subtitles if srt_path provided.
    - EP.2+: adds PIL-rendered hook PNG overlay (bypasses fontconfig).
    Returns list of output file paths.
    """
    os.makedirs(output_dir, exist_ok=True)

    total = _get_duration(video_path)
    if total <= 0:
        raise RuntimeError(f"Cannot read duration: {video_path}")

    n_chunks, chunk_dur = _calc_n_chunks(total)
    mins, secs = divmod(int(chunk_dur), 60)
    print(f"  Total: {total:.0f}s -> {n_chunks} chunks x {mins}:{secs:02d} each")

    srt_entries = _parse_srt(srt_path) if srt_path and os.path.exists(srt_path) else []
    burn_subs = bool(srt_entries)
    if burn_subs:
        print(f"  Subtitles: burning ({len(srt_entries)} cues)")
    if series_title:
        print(f"  Hook overlay: EP.2+ PNG banner ({n_chunks - 1} clips)")

    base = os.path.splitext(os.path.basename(video_path))[0]
    outputs = []

    for i in range(n_chunks):
        ep = i + 1
        start = i * chunk_dur
        chunk_end = start + chunk_dur
        out_path = os.path.join(output_dir, f"{base}_short_{ep:02d}.mp4")

        # Write chunk SRT if needed
        chunk_srt = None
        if burn_subs:
            chunk_srt = os.path.join(output_dir, f"_chunk_{ep:02d}.srt")
            _write_chunk_srt(srt_entries, start, chunk_end, chunk_srt)

        use_hook = (ep > 1 and series_title)

        if use_hook:
            # ── EP.2+: PIL hook PNG + overlay via filter_complex ──────────────
            hook_png = os.path.join(output_dir, f"_hook_{ep:02d}.png")
            has_hook = _make_hook_png(ep, n_chunks, series_title, hook_png)

            if has_hook:
                # Build filter_complex: crop/scale/subs on input 0, overlay hook from input 1
                base_filters = (
                    f"[0:v]crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
                    f"scale={SHORTS_WIDTH}:{SHORTS_HEIGHT}:flags=lanczos,setsar=1"
                )
                if burn_subs and chunk_srt:
                    srt_esc = _escape_filter_path(os.path.abspath(chunk_srt))
                    base_filters += f",subtitles='{srt_esc}':force_style='{_SUB_STYLE}'"
                base_filters += "[vid]"

                # Overlay PNG at ~35% from top; no enable= needed — shown full duration
                hook_y = int(SHORTS_HEIGHT * 0.35)
                fc = f"{base_filters};[vid][1:v]overlay=0:{hook_y}:shortest=1[vout]"

                cmd = [
                    FFMPEG, "-y",
                    "-ss", str(start), "-i", video_path,
                    "-loop", "1", "-i", hook_png,
                    "-t", str(chunk_dur),
                    "-filter_complex", fc,
                    "-map", "[vout]",
                    "-map", "0:a",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    out_path
                ]
            else:
                # Hook PNG failed — fall back to simple vf without hook
                use_hook = False

        if not use_hook:
            # ── EP.1 or no hook: simple -vf chain ────────────────────────────
            vf_parts = [
                "crop=ih*9/16:ih:(iw-ih*9/16)/2:0",
                f"scale={SHORTS_WIDTH}:{SHORTS_HEIGHT}:flags=lanczos",
                "setsar=1",
            ]
            if burn_subs and chunk_srt:
                srt_esc = _escape_filter_path(os.path.abspath(chunk_srt))
                vf_parts.append(f"subtitles='{srt_esc}':force_style='{_SUB_STYLE}'")

            vf = ",".join(vf_parts)
            cmd = [
                FFMPEG, "-y",
                "-ss", str(start),
                "-i", video_path,
                "-t", str(chunk_dur),
                "-vf", vf,
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                out_path
            ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Cleanup temp files
        if chunk_srt and os.path.exists(chunk_srt):
            os.remove(chunk_srt)
        if use_hook:
            hook_png_path = os.path.join(output_dir, f"_hook_{ep:02d}.png")
            if os.path.exists(hook_png_path):
                os.remove(hook_png_path)

        if result.returncode != 0:
            print(f"  [short {ep}] ffmpeg error: {result.stderr[-300:]}")
            continue

        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        s_m, s_s = divmod(int(start), 60)
        e_m, e_s = divmod(int(chunk_end), 60)
        print(f"  [short {ep}/{n_chunks}] {s_m}:{s_s:02d}-{e_m}:{e_s:02d} -> {out_path} ({size_mb:.1f} MB)")
        outputs.append(out_path)

    return outputs

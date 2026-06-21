import re
import subprocess
import os
import tempfile
import config

_FFMPEG_BIN = r"C:\Users\fusen\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
FFMPEG = os.path.join(_FFMPEG_BIN, "ffmpeg.exe")
FFPROBE = os.path.join(_FFMPEG_BIN, "ffprobe.exe")

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
MIN_CHUNK = 120  # 2:00 min
MAX_CHUNK = 150  # 2:30 min
TARGET_CHUNK = 135  # 2:15 min (ideal)

# Subtitle style burned into shorts (ASS force_style syntax)
_SUB_STYLE = (
    "FontName=Arial,Bold=1,FontSize=14,"
    "PrimaryColour=&H00FFFFFF,"   # white text
    "OutlineColour=&H00000000,"   # black outline
    "BackColour=&H80000000,"      # semi-transparent shadow
    "Outline=3,Shadow=1,"
    "Alignment=2,MarginV=60"      # bottom center, 60px from edge
)


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
    # ffmpeg filtergraph: escape backslash then colon (Windows drive letter)
    return path.replace("\\", "/").replace(":", "\\:")


# ── Duration helper ────────────────────────────────────────────────────────────

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

    return n, chunk


# ── Main export ────────────────────────────────────────────────────────────────

def cut_shorts(video_path: str, output_dir: str, srt_path: str = None) -> list[str]:
    """
    Cut landscape video into equal-length vertical YouTube Shorts (1080x1920).
    If srt_path is provided, burns subtitles into each chunk.
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
        print(f"  Subtitles: burning from {os.path.basename(srt_path)} ({len(srt_entries)} cues)")

    base = os.path.splitext(os.path.basename(video_path))[0]
    outputs = []

    for i in range(n_chunks):
        start = i * chunk_dur
        chunk_end = start + chunk_dur
        out_path = os.path.join(output_dir, f"{base}_short_{i+1:02d}.mp4")

        # Base crop+scale filter
        vf = (
            "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
            f"scale={SHORTS_WIDTH}:{SHORTS_HEIGHT}:flags=lanczos,"
            "setsar=1"
        )

        chunk_srt = None
        if burn_subs:
            chunk_srt = os.path.join(output_dir, f"_chunk_{i+1:02d}.srt")
            _write_chunk_srt(srt_entries, start, chunk_end, chunk_srt)
            srt_esc = _escape_filter_path(os.path.abspath(chunk_srt))
            vf += f",subtitles='{srt_esc}':force_style='{_SUB_STYLE}'"

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

        if chunk_srt and os.path.exists(chunk_srt):
            os.remove(chunk_srt)

        if result.returncode != 0:
            print(f"  [short {i+1}] ffmpeg error: {result.stderr[-300:]}")
            continue

        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        s_mins, s_secs = divmod(int(start), 60)
        e_mins, e_secs = divmod(int(chunk_end), 60)
        print(f"  [short {i+1}/{n_chunks}] {s_mins}:{s_secs:02d}-{e_mins}:{e_secs:02d} -> {out_path} ({size_mb:.1f} MB)")
        outputs.append(out_path)

    return outputs

import subprocess
import os
import config

_FFMPEG_BIN = r"C:\Users\fusen\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
FFMPEG = os.path.join(_FFMPEG_BIN, "ffmpeg.exe")
FFPROBE = os.path.join(_FFMPEG_BIN, "ffprobe.exe")

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
MIN_CHUNK = 120  # 2:00 min
MAX_CHUNK = 150  # 2:30 min
TARGET_CHUNK = 135  # 2:15 min (ideal)


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
    """
    Find N chunks so each chunk = total/N falls within [MIN_CHUNK, MAX_CHUNK].
    Starts from round(total/TARGET) and adjusts up/down until in range.
    Returns (n_chunks, chunk_duration).
    """
    if total <= MAX_CHUNK:
        return 1, total

    n = max(1, round(total / TARGET_CHUNK))
    chunk = total / n

    # Too long per chunk → add more chunks
    while chunk > MAX_CHUNK:
        n += 1
        chunk = total / n

    # Too short per chunk → remove chunks
    while chunk < MIN_CHUNK and n > 1:
        n -= 1
        chunk = total / n

    return n, chunk


def cut_shorts(video_path: str, output_dir: str) -> list[str]:
    """
    Cut landscape video into equal-length vertical YouTube Shorts (1080x1920).
    Chunk duration is computed from total duration so all chunks are equal length
    and each falls within 2:00-2:30 min.
    Returns list of output file paths.
    """
    os.makedirs(output_dir, exist_ok=True)

    total = _get_duration(video_path)
    if total <= 0:
        raise RuntimeError(f"Cannot read duration: {video_path}")

    n_chunks, chunk_dur = _calc_n_chunks(total)
    mins, secs = divmod(int(chunk_dur), 60)
    print(f"  Total: {total:.0f}s -> {n_chunks} chunks x {mins}:{secs:02d} each")

    base = os.path.splitext(os.path.basename(video_path))[0]
    outputs = []

    # Crop center 9:16 strip then scale to 1080x1920
    vf = (
        "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
        f"scale={SHORTS_WIDTH}:{SHORTS_HEIGHT}:flags=lanczos,"
        "setsar=1"
    )

    for i in range(n_chunks):
        start = i * chunk_dur
        out_path = os.path.join(output_dir, f"{base}_short_{i+1:02d}.mp4")

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
        if result.returncode != 0:
            print(f"  [short {i+1}] ffmpeg error: {result.stderr[-300:]}")
            continue

        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        s_mins, s_secs = divmod(int(start), 60)
        e_mins, e_secs = divmod(int(start + chunk_dur), 60)
        print(f"  [short {i+1}/{n_chunks}] {s_mins}:{s_secs:02d}-{e_mins}:{e_secs:02d} -> {out_path} ({size_mb:.1f} MB)")
        outputs.append(out_path)

    return outputs

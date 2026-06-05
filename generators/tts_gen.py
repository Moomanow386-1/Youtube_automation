import asyncio
import os
import re
import subprocess
import edge_tts
import config

_FFMPEG_DIR = r"C:\Users\fusen\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin"
_FFPROBE = os.path.join(_FFMPEG_DIR, "ffprobe.exe")
_FFMPEG = os.path.join(_FFMPEG_DIR, "ffmpeg.exe")

_CHUNK_WORDS = 400
_CHUNK_TIMEOUT = 120  # seconds per chunk — edge_tts stalls on very long text


async def _synthesize(text: str, audio_path: str, voice: str, rate: str):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await asyncio.wait_for(communicate.save(audio_path), timeout=_CHUNK_TIMEOUT)


def _split_chunks(text: str, max_words: int = _CHUNK_WORDS) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks, current, count = [], [], 0
    for sent in sentences:
        wc = len(sent.split())
        if count + wc > max_words and current:
            chunks.append(" ".join(current))
            current, count = [sent], wc
        else:
            current.append(sent)
            count += wc
    if current:
        chunks.append(" ".join(current))
    return chunks


def _concat_audio(parts: list[str], output: str):
    lst = output.replace(".mp3", "_concat.txt")
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p).replace(chr(92), '/')}'\n")
    subprocess.run(
        [_FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", output],
        capture_output=True, check=True
    )
    os.remove(lst)


def _generate_srt(script: str, duration_sec: float, srt_path: str):
    words = script.split()
    segment_size = 10
    segments = [" ".join(words[i:i+segment_size]) for i in range(0, len(words), segment_size)]
    sec_per_seg = duration_sec / len(segments)

    def fmt_time(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int((sec - int(sec)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            start = i * sec_per_seg
            end = start + sec_per_seg - 0.1
            f.write(f"{i+1}\n")
            f.write(f"{fmt_time(start)} --> {fmt_time(end)}\n")
            f.write(f"{seg}\n\n")


def _get_audio_duration(audio_path: str) -> float:
    result = subprocess.run(
        [_FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True, check=True, timeout=30
    )
    return float(result.stdout.strip())


def generate_audio(script: str, audio_path: str, voice: str = None) -> tuple[str, str]:
    """Generate MP3 + SRT. Returns (audio_path, srt_path)."""
    voice = voice or config.TTS_VOICE
    rate = config.TTS_RATE
    chunks = _split_chunks(script)
    print(f"  TTS: {len(chunks)} chunk(s)...")

    if len(chunks) == 1:
        asyncio.run(_synthesize(script, audio_path, voice, rate))
    else:
        base = audio_path.replace(".mp3", "")
        parts = []
        for i, chunk in enumerate(chunks):
            part = f"{base}_part{i}.mp3"
            print(f"    chunk {i+1}/{len(chunks)} ({len(chunk.split())} words)...")
            for attempt in range(3):
                try:
                    asyncio.run(_synthesize(chunk, part, voice, rate))
                    parts.append(part)
                    break
                except asyncio.TimeoutError:
                    if attempt == 2:
                        raise RuntimeError(f"TTS chunk {i+1} timed out after 3 attempts")
                    print(f"    timeout — retry {attempt+2}/3")
                except Exception as e:
                    if attempt == 2:
                        raise RuntimeError(f"TTS chunk {i+1} failed: {e}") from e
                    print(f"    error ({e}) — retry {attempt+2}/3")
        _concat_audio(parts, audio_path)
        for p in parts:
            if os.path.exists(p):
                os.remove(p)

    duration = _get_audio_duration(audio_path)
    srt_path = audio_path.replace(".mp3", ".srt")
    _generate_srt(script, duration, srt_path)
    return audio_path, srt_path


AVAILABLE_VOICES = {
    "male_storyteller": "en-US-GuyNeural",
    "female_storyteller": "en-US-AriaNeural",
    "british_male": "en-GB-RyanNeural",
    "british_female": "en-GB-SoniaNeural",
    "australian_male": "en-AU-WilliamNeural",
}

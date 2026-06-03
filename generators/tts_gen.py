import asyncio
import math
import edge_tts
import config

async def _synthesize(text: str, audio_path: str, voice: str, rate: str):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(audio_path)

def _generate_srt(script: str, duration_sec: float, srt_path: str):
    """Estimate subtitle timings by splitting script into segments."""
    words = script.split()
    # ~10 words per subtitle segment
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
    import subprocess
    _BIN = r"C:\Users\fusen\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffprobe.exe"
    result = subprocess.run(
        [_BIN, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())

def generate_audio(script: str, audio_path: str, voice: str = None) -> tuple[str, str]:
    """Generate MP3 + SRT. Returns (audio_path, srt_path)."""
    voice = voice or config.TTS_VOICE
    rate = config.TTS_RATE
    asyncio.run(_synthesize(script, audio_path, voice, rate))

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

import os
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30
TTS_VOICE = "en-US-AndrewMultilingualNeural"  # Most natural storytelling voice
TTS_RATE = "-8%"   # Slightly slower = more dramatic narrator feel
OUTPUT_DIR = "output"
TEMP_DIR = "temp"

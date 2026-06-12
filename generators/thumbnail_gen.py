import os
import io
import re
import random
import requests
import urllib.parse
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import config

THUMB_W, THUMB_H = 1280, 720
FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"
FONT_PATH_REGULAR = r"C:\Windows\Fonts\arial.ttf"

_CLICKBAIT_STRIPS = [
    "What REALLY Happened", "Nobody Talks About", "The Terrifying Secret",
    "SHOCKING Truth", "They Lied About", "The Hidden Story", "The Disturbing Reality",
    "What History Forgot", "The Untold Story", "Historians Got Wrong",
    "The Chilling Evidence", "What They Don't Want You To Know",
    "The DARK Truth", "DARK Truth", "Nobody Tells You", "The Secret",
    "What REALLY", "REALLY Happened", "Nobody Knows", "They Never Told You",
    "Hidden", "Disturbing", "Shocking", "About", "The Real",
]


def _extract_subject(title: str) -> str:
    subject = title
    for phrase in _CLICKBAIT_STRIPS:
        subject = re.sub(re.escape(phrase), "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"\s{2,}", " ", subject).strip(" ,-.'\"")
    return subject or title


def _build_ai_prompt(title: str, keywords: list[str]) -> str:
    subject = _extract_subject(title)
    visual = ", ".join(k for k in keywords[:4] if k)
    return (
        f"cinematic YouTube thumbnail clickbait style, {subject}, {visual}, "
        "dramatic dark atmospheric lighting, high contrast, epic composition, "
        "photorealistic, 4k ultra detailed, mysterious, intense, "
        "no text, no letters, no watermark"
    )


def _fetch_pollinations_image(prompt: str) -> Image.Image | None:
    encoded = urllib.parse.quote(prompt)
    seed = random.randint(1, 99999)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1280&height=720&nologo=true&model=flux&seed={seed}"
    )
    try:
        print(f"  Generating AI thumbnail (Pollinations)...")
        r = requests.get(url, timeout=90)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            return Image.open(io.BytesIO(r.content)).convert("RGB")
        print(f"  Pollinations returned status {r.status_code}")
    except Exception as e:
        print(f"  Pollinations failed: {e}")
    return None


def _fetch_pexels_image(keywords: list[str]) -> Image.Image | None:
    if not config.PEXELS_API_KEY:
        return None
    query = " ".join(keywords[:3])
    headers = {"Authorization": config.PEXELS_API_KEY}
    params = {"query": query, "per_page": 10, "orientation": "landscape"}
    try:
        resp = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=10)
        photos = resp.json().get("photos", [])
        if not photos:
            return None
        photo = random.choice(photos[:5])
        r = requests.get(photo["src"]["large2x"], timeout=30)
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"  Pexels fallback failed: {e}")
        return None


def _dark_gradient_bg() -> Image.Image:
    img = Image.new("RGB", (THUMB_W, THUMB_H), (10, 10, 20))
    draw = ImageDraw.Draw(img)
    for i in range(THUMB_H):
        alpha = int(40 * (1 - i / THUMB_H))
        draw.line([(0, i), (THUMB_W, i)], fill=(30, 10, 60 - alpha))
    return img


def _apply_dark_overlay(img: Image.Image) -> Image.Image:
    img = img.resize((THUMB_W, THUMB_H), Image.LANCZOS)
    overlay = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    # gradient only in bottom 35% — keeps image visible
    fade_start = int(THUMB_H * 0.65)
    for i in range(fade_start, THUMB_H):
        opacity = int(185 * ((i - fade_start) / (THUMB_H - fade_start)))
        draw_ov.line([(0, i), (THUMB_W, i)], fill=(0, 0, 0, opacity))
    # subtle vignette top
    for i in range(0, int(THUMB_H * 0.12)):
        opacity = int(50 * (1 - i / (THUMB_H * 0.12)))
        draw_ov.line([(0, i), (THUMB_W, i)], fill=(0, 0, 0, opacity))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _wrap_title(title: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = title.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if font.getbbox(test)[2] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _shorten_for_thumbnail(title: str) -> str:
    """Extract a punchy 4-6 word phrase from the title for the thumbnail."""
    # remove common filler endings
    title = re.sub(
        r"\s*(Nobody Talks About|You've Never Heard|Nobody Tells You|What They Don't Want You To Know"
        r"|and What It Means Today|The Full Story|Explained|Documentary)\s*",
        "", title, flags=re.IGNORECASE
    ).strip()
    words = title.split()
    if len(words) <= 5:
        return title
    # prefer keeping power words near the front
    power = ["SHOCKING", "DARK", "REAL", "TERRIFYING", "HIDDEN", "SECRET",
             "TRUTH", "REALLY", "CHILLING", "DISTURBING", "UNTOLD", "FORGOTTEN"]
    # try to find a natural break at 4-5 words that includes a power word
    for end in [5, 4, 6]:
        candidate = " ".join(words[:end])
        if any(p in candidate.upper() for p in power):
            return candidate
    return " ".join(words[:5])


def _draw_title(draw: ImageDraw.ImageDraw, title: str, font_title: ImageFont.FreeTypeFont,
                canvas_w: int, canvas_h: int):
    short_text = _shorten_for_thumbnail(title).upper()
    max_text_w = canvas_w - 100
    lines = _wrap_title(short_text, font_title, max_text_w)

    # hard cap at 2 lines
    if len(lines) > 2:
        lines = lines[:2]
        lines[-1] = lines[-1].rstrip() + "..."

    line_h = 78
    total_h = len(lines) * line_h
    # position: bottom 28% of image
    y = canvas_h - total_h - 52

    for line in lines:
        bbox = font_title.getbbox(line)
        lw = bbox[2] - bbox[0]
        x = (canvas_w - lw) // 2

        # stroke shadow
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if abs(dx) + abs(dy) <= 4:
                    draw.text((x + dx, y + dy), line, font=font_title, fill=(0, 0, 0))

        # yellow main text
        draw.text((x, y), line, font=font_title, fill=(255, 220, 0))
        y += line_h

    # red accent bar on left
    bar_top = canvas_h - total_h - 80
    bar_bot = canvas_h - 40
    draw.rectangle([(12, bar_top), (38, bar_bot)], fill=(220, 30, 30))


def generate_thumbnail(title: str, keywords: list[str], output_path: str) -> str:
    ai_prompt = _build_ai_prompt(title, keywords)

    bg = _fetch_pollinations_image(ai_prompt)

    if bg is None:
        print("  Falling back to Pexels...")
        # use title-derived subject for better Pexels match
        subject = _extract_subject(title)
        pexels_kw = [subject] + keywords[:2]
        bg = _fetch_pexels_image(pexels_kw)

    if bg is None:
        bg = _dark_gradient_bg()
    else:
        bg = _apply_dark_overlay(bg)

    draw = ImageDraw.Draw(bg)

    try:
        font_title = ImageFont.truetype(FONT_PATH, 65)
    except Exception:
        font_title = ImageFont.load_default()

    _draw_title(draw, title, font_title, THUMB_W, THUMB_H)

    bg.save(output_path, "JPEG", quality=95)
    print(f"  Thumbnail saved: {output_path}")
    return output_path

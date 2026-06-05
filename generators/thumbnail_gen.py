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
    for i in range(int(THUMB_H * 0.30), THUMB_H):
        opacity = int(210 * ((i - THUMB_H * 0.30) / (THUMB_H * 0.70)))
        draw_ov.line([(0, i), (THUMB_W, i)], fill=(0, 0, 0, opacity))
    # slight vignette on top
    for i in range(0, int(THUMB_H * 0.20)):
        opacity = int(80 * (1 - i / (THUMB_H * 0.20)))
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


def _draw_title(draw: ImageDraw.ImageDraw, title: str, font_title: ImageFont.FreeTypeFont,
                canvas_w: int, canvas_h: int):
    max_text_w = canvas_w - 80
    lines = _wrap_title(title.upper(), font_title, max_text_w)
    line_h = 95
    total_h = len(lines) * line_h
    y = canvas_h - total_h - 70

    for line in lines:
        bbox = font_title.getbbox(line)
        lw = bbox[2] - bbox[0]
        x = (canvas_w - lw) // 2

        # thick black shadow for depth
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                if abs(dx) + abs(dy) > 4:
                    continue
                draw.text((x + dx, y + dy), line, font=font_title, fill=(0, 0, 0))

        # yellow main text — high clickbait contrast
        draw.text((x, y), line, font=font_title, fill=(255, 220, 0))
        y += line_h

    # red accent bar on left
    bar_top = canvas_h - total_h - 100
    bar_bot = canvas_h - 55
    draw.rectangle([(12, bar_top), (40, bar_bot)], fill=(220, 30, 30))


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
        font_title = ImageFont.truetype(FONT_PATH, 80)
    except Exception:
        font_title = ImageFont.load_default()

    _draw_title(draw, title, font_title, THUMB_W, THUMB_H)

    bg.save(output_path, "JPEG", quality=95)
    print(f"  Thumbnail saved: {output_path}")
    return output_path

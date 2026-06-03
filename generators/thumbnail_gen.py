import os
import io
import requests
import textwrap
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import config

THUMB_W, THUMB_H = 1280, 720
FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"
FONT_PATH_REGULAR = r"C:\Windows\Fonts\arial.ttf"


def _fetch_pexels_image(keywords: list[str]) -> Image.Image | None:
    if not config.PEXELS_API_KEY:
        return None
    query = " ".join(keywords[:2])
    headers = {"Authorization": config.PEXELS_API_KEY}
    params = {"query": query, "per_page": 10, "orientation": "landscape"}
    try:
        resp = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=10)
        photos = resp.json().get("photos", [])
        if not photos:
            return None
        photo = random.choice(photos[:5])
        img_url = photo["src"]["large2x"]
        r = requests.get(img_url, timeout=30)
        return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"  Pexels image failed: {e}")
        return None


def _dark_gradient_bg() -> Image.Image:
    img = Image.new("RGB", (THUMB_W, THUMB_H), (10, 10, 20))
    draw = ImageDraw.Draw(img)
    for i in range(THUMB_H):
        alpha = int(40 * (1 - i / THUMB_H))
        draw.line([(0, i), (THUMB_W, i)], fill=(30, 10, 60 - alpha))
    return img


def _wrap_title(title: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = title.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = font.getbbox(test)
        if bbox[2] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def generate_thumbnail(title: str, keywords: list[str], output_path: str) -> str:
    print("  Fetching background image...")
    bg = _fetch_pexels_image(keywords)

    if bg:
        bg = bg.resize((THUMB_W, THUMB_H), Image.LANCZOS)
        # Darken bottom 60% for text readability
        overlay = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        for i in range(int(THUMB_H * 0.35), THUMB_H):
            opacity = int(200 * ((i - THUMB_H * 0.35) / (THUMB_H * 0.65)))
            draw_ov.line([(0, i), (THUMB_W, i)], fill=(0, 0, 0, opacity))
        bg = bg.convert("RGBA")
        bg = Image.alpha_composite(bg, overlay).convert("RGB")
    else:
        bg = _dark_gradient_bg()

    draw = ImageDraw.Draw(bg)

    # Load fonts
    try:
        font_title = ImageFont.truetype(FONT_PATH, 80)
        font_sub = ImageFont.truetype(FONT_PATH_REGULAR, 36)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = font_title

    # Wrap and draw title
    max_text_w = THUMB_W - 100
    lines = _wrap_title(title.upper(), font_title, max_text_w)
    total_h = len(lines) * 95
    y = THUMB_H - total_h - 80

    for line in lines:
        bbox = font_title.getbbox(line)
        x = (THUMB_W - bbox[2]) // 2
        # Shadow
        draw.text((x + 3, y + 3), line, font=font_title, fill=(0, 0, 0, 200))
        # Main text
        draw.text((x, y), line, font=font_title, fill=(255, 255, 255))
        y += 95

    # Red accent bar on left
    draw.rectangle([(12, THUMB_H - total_h - 110), (40, THUMB_H - 60)], fill=(220, 30, 30))

    bg.save(output_path, "JPEG", quality=95)
    return output_path

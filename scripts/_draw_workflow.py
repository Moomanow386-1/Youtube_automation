"""Generate workflow diagram as a single PNG image."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(14, 22))
ax.set_xlim(0, 14)
ax.set_ylim(0, 22)
ax.axis("off")
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#0d1117")

# ── Color palette ──────────────────────────────────────────────────────────────
C_TRIGGER  = "#1f4068"   # dark blue  — trigger/scheduler
C_PICK     = "#1b4332"   # dark green — topic picker
C_SCRIPT   = "#3d2b1f"   # dark brown — script gen
C_TTS      = "#2d1b4e"   # dark purple — TTS
C_THUMB    = "#1a3a4a"   # dark teal  — thumbnail
C_VIDEO    = "#3b1f1f"   # dark red   — video gen
C_UPLOAD   = "#1f3a1f"   # green      — upload
C_OUTPUT   = "#2a2a0a"   # gold-ish   — output
C_TEXT     = "#e6edf3"
C_ACCENT   = "#58a6ff"
C_ARROW    = "#6e7681"
C_BORDER   = "#30363d"


def box(ax, x, y, w, h, label, sublabel=None, color="#1c2128", border="#58a6ff",
        fontsize=11, subfontsize=8.5):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0.1",
                          linewidth=1.5,
                          edgecolor=border,
                          facecolor=color)
    ax.add_patch(rect)
    cy = y + h / 2 + (0.12 if sublabel else 0)
    ax.text(x + w / 2, cy, label, ha="center", va="center",
            fontsize=fontsize, fontweight="bold", color=C_TEXT,
            fontfamily="DejaVu Sans")
    if sublabel:
        ax.text(x + w / 2, y + h / 2 - 0.22, sublabel, ha="center", va="center",
                fontsize=subfontsize, color="#8b949e",
                fontfamily="DejaVu Sans")


def arrow(ax, x, y_top, y_bot, color=C_ARROW):
    ax.annotate("", xy=(x, y_bot), xytext=(x, y_top),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=1.8, mutation_scale=16))


def small_box(ax, x, y, w, h, label, color, border):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0.07",
                          linewidth=1.2,
                          edgecolor=border,
                          facecolor=color)
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=7.5, color=C_TEXT, fontfamily="DejaVu Sans")


# ── Title ──────────────────────────────────────────────────────────────────────
ax.text(7, 21.5, "YouTube Automation — Full Pipeline Workflow",
        ha="center", va="center", fontsize=15, fontweight="bold",
        color=C_ACCENT, fontfamily="DejaVu Sans")

# ── BLOCK 1: Trigger ──────────────────────────────────────────────────────────
box(ax, 3.5, 20.2, 7, 0.85,
    "[ Windows Task Scheduler ]",
    "Runs auto_daily.py every day",
    color=C_TRIGGER, border="#58a6ff", fontsize=11)

arrow(ax, 7, 20.2, 19.5)

# ── BLOCK 2: Topic picker ─────────────────────────────────────────────────────
box(ax, 2.5, 18.0, 9, 1.35,
    "auto_daily.py  —  Pick Topic",
    "30 preset SEED_TOPICS  →  if all used, ask Ollama to generate new one",
    color=C_PICK, border="#3fb950", fontsize=11)

arrow(ax, 7, 18.0, 17.25)

# ── STEP 1 ────────────────────────────────────────────────────────────────────
ax.text(0.4, 17.1, "STEP 1", fontsize=8, color=C_ACCENT,
        fontweight="bold", fontfamily="DejaVu Sans")
box(ax, 1.0, 15.6, 12, 1.5,
    "script_gen.py  —  Generate Script  (Ollama LLM)",
    "4-part narration script  •  ~2,400 words  •  ~14-16 min\n"
    "+ SEO metadata: title / description / tags / video_keywords",
    color=C_SCRIPT, border="#f0883e", fontsize=11)

arrow(ax, 7, 15.6, 14.85)

# ── STEP 2 ────────────────────────────────────────────────────────────────────
ax.text(0.4, 14.7, "STEP 2", fontsize=8, color=C_ACCENT,
        fontweight="bold", fontfamily="DejaVu Sans")
box(ax, 1.0, 13.2, 12, 1.5,
    "tts_gen.py  —  Text-to-Speech  (edge_tts Azure Neural)",
    "Split script into 400-word chunks  →  synthesize each to MP3\n"
    "ffmpeg concat chunks  →  final audio.mp3  +  subtitle .srt",
    color=C_TTS, border="#bc8cff", fontsize=11)

arrow(ax, 7, 13.2, 12.45)

# ── STEP 3 ────────────────────────────────────────────────────────────────────
ax.text(0.4, 12.3, "STEP 3", fontsize=8, color=C_ACCENT,
        fontweight="bold", fontfamily="DejaVu Sans")
box(ax, 1.0, 10.8, 12, 1.5,
    "thumbnail_gen.py  —  Generate Thumbnail",
    "Pollinations AI (flux)  →  1280×720 background image\n"
    "Fallback: Pexels photo  |  Draw bold title overlay  →  save JPG",
    color=C_THUMB, border="#39d353", fontsize=11)

arrow(ax, 7, 10.8, 10.05)

# ── STEP 4 ────────────────────────────────────────────────────────────────────
ax.text(0.4, 9.9, "STEP 4", fontsize=8, color=C_ACCENT,
        fontweight="bold", fontfamily="DejaVu Sans")

# Main Step 4 box
box(ax, 1.0, 6.9, 12, 2.95,
    "video_gen.py  —  Assemble Video",
    "",
    color=C_VIDEO, border="#f85149", fontsize=11)

# Phase boxes inside Step 4
phases = [
    ("Phase 1\nPexels Videos",    "#1f4068", "#58a6ff"),
    ("Phase 2\nPixabay Videos",   "#1f3a1f", "#3fb950"),
    ("Phase 3\nPexels Photos",    "#3d2b1f", "#f0883e"),
    ("Phase 4\nPixabay Photos",   "#2d1b4e", "#bc8cff"),
    ("Phase 5\nWikimedia Photos", "#1a3a4a", "#39d353"),
    ("Phase 6\nAI Images (fill)", "#3b1f1f", "#f85149"),
]
pw = 1.85
for i, (label, col, bdr) in enumerate(phases):
    small_box(ax, 1.15 + i * pw, 8.85, pw - 0.12, 0.85, label, col, bdr)

# ffmpeg steps
ax.text(7, 8.55, "▼  ffmpeg: normalize all clips → 1920×1080 @ 30fps → concat background.mp4",
        ha="center", va="center", fontsize=8, color="#8b949e",
        fontfamily="DejaVu Sans")
ax.text(7, 8.1, "▼  ffmpeg: merge background + audio → final .mp4  (1920×1080, AAC 192k)",
        ha="center", va="center", fontsize=8, color="#8b949e",
        fontfamily="DejaVu Sans")
ax.text(7, 7.55, "Media dedup tracked in used_media.json  (no repeated clips across videos)",
        ha="center", va="center", fontsize=7.5, color="#6e7681",
        fontfamily="DejaVu Sans", style="italic")

arrow(ax, 7, 6.9, 6.15)

# ── Output files ──────────────────────────────────────────────────────────────
box(ax, 2.0, 4.95, 10, 1.0,
    "output/  —  Generated Files",
    "{title}.mp4   •   {title}_thumbnail.jpg   •   {title}_script.txt",
    color=C_OUTPUT, border="#d4a017", fontsize=10)

arrow(ax, 7, 4.95, 4.2)

# ── UPLOAD ────────────────────────────────────────────────────────────────────
box(ax, 1.5, 2.85, 11, 1.15,
    "youtube_upload.py  —  YouTube Data API v3",
    "Upload MP4  •  Set custom thumbnail  •  title / description / tags  •  privacy: public",
    color=C_UPLOAD, border="#3fb950", fontsize=11)

arrow(ax, 7, 2.85, 2.1)

# ── Result ────────────────────────────────────────────────────────────────────
box(ax, 3.0, 0.85, 8, 1.05,
    ">>> Video Live on YouTube <<<",
    "URL logged to daily_log.json  •  topic saved to topic_history.json",
    color="#0d2818", border="#3fb950", fontsize=11)

# ── Legend ────────────────────────────────────────────────────────────────────
ax.text(0.3, 0.55, "APIs used:", fontsize=7.5, color="#6e7681",
        fontfamily="DejaVu Sans")
legend_items = [
    ("Ollama (local LLM)", "#f0883e"),
    ("edge_tts (free)", "#bc8cff"),
    ("Pexels API", "#58a6ff"),
    ("Pixabay API", "#3fb950"),
    ("Wikimedia (free)", "#39d353"),
    ("Pollinations AI (free)", "#f85149"),
    ("YouTube Data API v3", "#3fb950"),
]
xp = 1.8
for label, col in legend_items:
    ax.add_patch(plt.Rectangle((xp, 0.32), 0.18, 0.14, color=col))
    ax.text(xp + 0.24, 0.39, label, fontsize=7, color="#8b949e",
            va="center", fontfamily="DejaVu Sans")
    xp += 1.75

plt.tight_layout(pad=0.5)
plt.savefig("workflow_diagram.png", dpi=150, bbox_inches="tight",
            facecolor="#0d1117", edgecolor="none")
print("Saved: workflow_diagram.png")

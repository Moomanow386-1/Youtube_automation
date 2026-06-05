import requests
import json
import re
import config

def _ollama(prompt: str, max_tokens: int = 2048) -> str:
    resp = requests.post(
        f"{config.OLLAMA_HOST}/api/generate",
        json={
            "model": config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.8,
                "num_predict": max_tokens,
                "num_ctx": 8192,
            }
        },
        timeout=300
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()

def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    raise ValueError(f"Cannot parse JSON from:\n{text[:400]}")

_PART_PROMPTS = [
    ("hook + historical background. Hook with a shocking fact, set the scene, introduce key figures. End mid-story, do NOT conclude.", "1/4"),
    ("rising action. Escalate events, reveal new information, build tension. End on a cliffhanger.", "2/4"),
    ("peak drama. The most intense turning point, shocking revelations, key consequences unfold.", "3/4"),
    ("dramatic conclusion. Final outcome, historical impact, what it means today. End with a powerful closing and a question for viewers.", "4/4"),
]

def generate_script(topic: str) -> dict:
    """Returns dict with: title, description, tags, video_keywords, script — ~14-16 min target."""

    parts = []
    for focus, label in _PART_PROMPTS:
        prompt = f"""You are a world-class YouTube storyteller for a faceless history and mystery channel.

Write part {label} of a narration script about: "{topic}"

This part should cover: {focus}

Requirements:
- Write 600-700 words of pure engaging narration
- Documentary-style voice, vivid and specific historical details
- Flowing paragraphs only, no bullet points, no headers
- No stage directions, no [MUSIC], no [CUT TO], no part labels

Write ONLY the narration text:"""

        print(f"  Generating script part {label}...")
        text = _ollama(prompt, max_tokens=1200)
        parts.append(text.strip())

    script_text = "\n\n".join(parts)
    word_count = len(script_text.split())
    print(f"  Total script: {word_count} words (~{word_count/130:.1f} min)")

    meta_prompt = f"""Based on this YouTube narration script, create metadata optimized for YouTube SEO and clickbait.

Script topic: {topic}
Script preview: {script_text[:500]}

Return ONLY a valid JSON object (no extra text, no markdown):
{{
  "title": "Clickbait YouTube title under 70 chars. Pick ONE power phrase — vary them, never repeat the same phrase across videos: 'What REALLY Happened', 'Nobody Talks About', 'The Terrifying Secret', 'SHOCKING Truth', 'They Lied About', 'The Hidden Story', 'The Disturbing Reality', 'What History Forgot', 'The Untold Story', 'Historians Got Wrong', 'The Chilling Evidence', 'What They Don\\'t Want You To Know'. Avoid overusing \\'The DARK Truth\\'. Example: 'What REALLY Happened to Tutankhamun Nobody Tells You'",
  "description": "YouTube description 150-200 words. Start with a shocking hook sentence. Include main keywords naturally. End with call to action. Add 5 relevant hashtags at the bottom like #History #Mystery #TrueCrime",
  "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10","tag11","tag12","tag13","tag14","tag15"],
  "video_keywords": [
    "specific place or landmark from script",
    "specific ship aircraft or vehicle from script",
    "specific historical figure or era",
    "specific event location ocean mountain desert ruins",
    "dark atmospheric: storm night fog lightning",
    "vintage newspaper archive old photograph",
    "specific country or city landscape",
    "dramatic sky clouds dark cinematic",
    "relevant artifact relic object from the story",
    "underwater wreck or jungle or cave exploration"
  ]
}}

For video_keywords: 10 VERY SPECIFIC visual search terms from the script. Include: real places, objects, events, AND atmospheric/dark/vintage terms. No generic words like mystery or documentary."""

    print("  Generating metadata...")
    meta_raw = _ollama(meta_prompt, max_tokens=600)
    meta = _extract_json(meta_raw)
    meta["script"] = script_text

    return meta

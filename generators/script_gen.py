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
    (
        "historical background and setup. Set the scene with vivid, specific details. Introduce key figures and the central mystery or conflict. End mid-story — do NOT conclude or resolve anything.",
        "1/4"
    ),
    (
        "rising action. Escalate events, reveal new information, build tension. "
        "Halfway through this section, insert a RETENTION HOOK: one sentence formatted as '--- RETENTION HOOK ---' on its own line, "
        "then write a teaser like 'But what happened next changed everything — and what we found will shock you.' "
        "Then continue the rising action. End on a cliffhanger.",
        "2/4"
    ),
    (
        "peak drama. The most intense turning point of the story. Shocking revelations, key consequences, the moment everything changes.",
        "3/4"
    ),
    (
        "dramatic conclusion. Final outcome, historical impact, what this means today. "
        "End with a powerful closing thought, then a natural call-to-action: ask viewers one compelling question related to the topic to spark comments.",
        "4/4"
    ),
]

def _generate_opening_hook(topic: str) -> str:
    prompt = f"""You are a world-class YouTube hook writer for a faceless history and mystery channel.

Write ONE single opening sentence for a video about: "{topic}"

Rules:
- Maximum 20 words
- Must create immediate shock, curiosity, or disbelief
- Start with the most disturbing or surprising fact — no buildup
- Do NOT start with "In", "Have you", "What if", "Today", "Welcome"
- Examples of great hooks:
  "They found the body with no heartbeat — yet the autopsy revealed something impossible."
  "For 40 years, this man's death was classified by three governments."
  "The last thing the crew radioed before vanishing was a single word: impossible."

Write ONLY the one hook sentence, nothing else:"""

    return _ollama(prompt, max_tokens=60).strip().strip('"').strip("'")

def generate_script(topic: str) -> dict:
    """Returns dict with: title, description, tags, video_keywords, script, pinned_comment, cta_script — ~14-16 min target."""

    print("  Generating opening hook...")
    opening_hook = _generate_opening_hook(topic)
    print(f"  Hook: {opening_hook}")

    parts = [opening_hook]
    for focus, label in _PART_PROMPTS:
        prompt = f"""You are a world-class YouTube storyteller for a faceless history and mystery channel.

Write part {label} of a narration script about: "{topic}"

This part should cover: {focus}

Requirements:
- Write 600-700 words of pure engaging narration
- Documentary-style voice, vivid and specific historical details
- Flowing paragraphs only, no bullet points, no headers
- No stage directions, no [MUSIC], no [CUT TO], no part labels
- For the retention hook line (if instructed): write it exactly as specified

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
  ],
  "pinned_comment": "One engaging question (under 20 words) to pin as first comment. Make viewers want to answer. Example: 'What do YOU think really happened? Drop your theory below.'",
  "cta_script": "End-screen spoken CTA, ~10 seconds when read aloud. Friendly conversational English. Tell them to subscribe + what the next video will cover. No more than 3 sentences."
}}

For video_keywords: 10 VERY SPECIFIC visual search terms from the script. Include: real places, objects, events, AND atmospheric/dark/vintage terms. No generic words like mystery or documentary."""

    print("  Generating metadata...")
    meta_raw = _ollama(meta_prompt, max_tokens=700)
    meta = _extract_json(meta_raw)
    meta["script"] = script_text

    return meta

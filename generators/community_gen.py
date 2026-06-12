import requests
import json
import re
import os
import config

def _ollama(prompt: str, max_tokens: int = 2000) -> str:
    resp = requests.post(
        f"{config.OLLAMA_HOST}/api/generate",
        json={
            "model": config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.85, "num_predict": max_tokens, "num_ctx": 6144},
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()

def _extract_json(text: str):
    # find all top-level [...] blocks and collect items from each
    results = []
    i = 0
    while i < len(text):
        start = text.find('[', i)
        if start == -1:
            break
        depth = 0
        for j in range(start, len(text)):
            if text[j] == '[':
                depth += 1
            elif text[j] == ']':
                depth -= 1
                if depth == 0:
                    chunk = text[start:j+1]
                    try:
                        parsed = json.loads(chunk)
                        if isinstance(parsed, list):
                            results.extend(parsed)
                    except Exception:
                        pass
                    i = j + 1
                    break
        else:
            break
    if results:
        return results
    raise ValueError(f"Cannot parse JSON from:\n{text[:400]}")

_POST_PLAN = (
    ["poll"] * 6 +
    ["behind_the_scenes"] * 5 +
    ["discussion_question"] * 6 +
    ["hot_take"] * 4 +
    ["teaser"] * 4 +
    ["inspiration"] * 5
)

_POST_INSTRUCTIONS = {
    "poll": "A 1-sentence poll question about history/mystery. poll_options: 2 short choices.",
    "behind_the_scenes": "1-2 sentences teasing research process or upcoming video. poll_options: null.",
    "discussion_question": "1 open-ended question with no obvious answer. poll_options: null.",
    "hot_take": "1 bold controversial opinion about a historical event or mystery. poll_options: null.",
    "teaser": "1-2 sentences creating FOMO for next video without revealing topic. poll_options: null.",
    "inspiration": "A chilling quote or mind-blowing fact from history. Under 30 words. poll_options: null.",
}

def _generate_one(post_type: str, idx: int, total: int) -> dict:
    instruction = _POST_INSTRUCTIONS[post_type]
    prompt = f"""Write 1 YouTube Community tab post for a history/mystery channel.
Type: {post_type}
Task: {instruction}
Tone: conversational, human, not corporate.

Return ONLY this JSON object on one line (no extra text):
{{"type":"{post_type}","post":"text here","poll_options":null,"goal":"engagement"}}"""

    raw = _ollama(prompt, max_tokens=200)

    # attempt 1: parse whole raw as-is (must be a dict)
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
    except Exception:
        pass

    # attempt 2: find first {...} block and parse
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        chunk = raw[start:end+1]
        try:
            return json.loads(chunk)
        except Exception:
            # attempt 3: model wrapped JSON in outer quotes → unescape
            try:
                return json.loads(chunk.replace('\\"', '"').replace('\\\\', '\\'))
            except Exception:
                pass

    # attempt 4: regex-extract just the post text and build item manually
    post_match = re.search(r'"post"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
    post_text = post_match.group(1).replace('\\"', '"') if post_match else raw.strip()[:150]
    opts_match = re.search(r'"poll_options"\s*:\s*(\[.*?\])', raw)
    poll_options = None
    if opts_match:
        try:
            poll_options = json.loads(opts_match.group(1))
        except Exception:
            pass
    return {"type": post_type, "post": post_text, "poll_options": poll_options, "goal": "engagement"}

def generate_community_posts(channel_niche: str = "history mysteries and unsolved cases") -> list[dict]:
    """Returns 30 community tab posts via 30 single-item calls."""
    posts = []
    total = len(_POST_PLAN)
    for i, post_type in enumerate(_POST_PLAN, 1):
        print(f"  Post {i}/{total}: {post_type}")
        post = _generate_one(post_type, i, total)
        posts.append(post)
    return posts

def save_community_posts(output_path: str = None) -> str:
    """Generate and save community posts to a text file. Returns file path."""
    posts = generate_community_posts()

    if output_path is None:
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(config.OUTPUT_DIR, "community_posts.txt")

    type_order = ["poll", "behind_the_scenes", "discussion_question", "hot_take", "teaser", "inspiration"]
    grouped = {t: [] for t in type_order}
    for p in posts:
        t = p.get("type", "other")
        grouped.setdefault(t, []).append(p)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("YOUTUBE COMMUNITY TAB POSTS\n")
        f.write("=" * 60 + "\n")
        f.write("Copy-paste ready. Schedule 1 post every 2-3 days.\n")
        f.write("=" * 60 + "\n\n")

        count = 1
        for ptype in type_order:
            items = grouped.get(ptype, [])
            if not items:
                continue
            label = ptype.replace("_", " ").upper()
            f.write(f"\n{'─'*40}\n{label} ({len(items)} posts)\n{'─'*40}\n\n")
            for item in items:
                f.write(f"[Post #{count}] Goal: {item.get('goal','?')}\n")
                f.write(item.get("post", "") + "\n")
                opts = item.get("poll_options")
                if opts:
                    for opt in opts:
                        f.write(f"  • {opt}\n")
                f.write("\n")
                count += 1

    print(f"  Saved: {output_path} ({count-1} posts)")
    return output_path

if __name__ == "__main__":
    path = save_community_posts()
    print(f"\nDone! Open: {path}")

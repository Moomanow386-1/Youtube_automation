import requests
import json
import re
import config

def _ollama(prompt: str, max_tokens: int = 200) -> str:
    resp = requests.post(
        f"{config.OLLAMA_HOST}/api/generate",
        json={
            "model": config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.9, "num_predict": max_tokens, "num_ctx": 4096},
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()

def _parse_topic(raw: str) -> dict:
    # attempt 1: whole raw is a dict
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
    except Exception:
        pass
    # attempt 2: find first {...} block
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        chunk = raw[start:end+1]
        try:
            return json.loads(chunk)
        except Exception:
            try:
                return json.loads(chunk.replace('\\"', '"'))
            except Exception:
                pass
    # attempt 3: regex-extract fields
    topic_m = re.search(r'"topic"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
    demand_m = re.search(r'"search_demand"\s*:\s*"([^"]+)"', raw)
    why_m = re.search(r'"why_it_works"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
    return {
        "topic": topic_m.group(1) if topic_m else raw.strip()[:120],
        "search_demand": demand_m.group(1) if demand_m else "medium",
        "why_it_works": why_m.group(1) if why_m else "",
    }

def _generate_one_topic(idx: int, avoid: list[str]) -> dict:
    avoid_str = ", ".join(f'"{t}"' for t in avoid[-5:]) if avoid else "none"
    prompt = f"""YouTube content strategist for a faceless English history/mystery channel.

Generate 1 specific video topic. Requirements:
- Unsolved mystery, dark history, cover-up, or forgotten shocking event
- HIGH global search demand on YouTube
- Specific angle, not generic (bad: "Ancient Egypt", good: "The Pharaoh Who Erased Himself From History")
- NOT about: Titanic main story, Bermuda Triangle main story
- Different from recently used: {avoid_str}

Return ONLY this JSON on one line:
{{"topic":"specific title here","search_demand":"high|medium","why_it_works":"one sentence"}}"""

    raw = _ollama(prompt, max_tokens=150)
    return _parse_topic(raw)

def generate_topics(n: int = 10) -> list[dict]:
    """Returns n topic dicts via n single-item calls."""
    topics = []
    used = []
    for i in range(n):
        print(f"  Topic {i+1}/{n}...")
        t = _generate_one_topic(i, used)
        topics.append(t)
        used.append(t.get("topic", ""))
    # sort: high demand first
    topics.sort(key=lambda x: 0 if x.get("search_demand") == "high" else 1)
    return topics

def pick_best_topic() -> str:
    """Generate 10 topics, return the single best topic string."""
    topics = generate_topics(10)
    best = topics[0]
    print(f"\n  Best topic: {best['topic']}")
    print(f"  Search demand: {best['search_demand']}")
    print(f"  Why: {best['why_it_works']}\n")
    return best["topic"]

if __name__ == "__main__":
    topics = generate_topics(10)
    print("\nGenerated Topics:")
    for i, t in enumerate(topics, 1):
        print(f"\n{i}. [{t.get('search_demand','?').upper()}] {t['topic']}")
        print(f"   -> {t['why_it_works']}")

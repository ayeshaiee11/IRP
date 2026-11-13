"""Optional AI suggestions for possible real-world factors (Groq). Never raises."""
import json
import os
import re
import urllib.request

_CACHE = {}
API_URL = "https://api.groq.com/openai/v1/chat/completions"


def _parse(text):
    """Pull a JSON list of short strings out of the model's reply."""
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
    except ValueError:
        return []
    return [str(i).strip()[:80] for i in items if str(i).strip()][:5]


def suggest_factors(title, unit, first_label, last_label, direction, change_pct):
    """Return a list of possible factors, or [] when no key is set or anything fails."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return []
    ck = (title, unit, str(first_label), str(last_label), direction)
    if ck in _CACHE:
        return _CACHE[ck]
    prompt = (
        f'A dataset named "{title}" (measured in "{unit}") covers {first_label} to {last_label}. '
        f"Its trend is {direction.lower()}"
        + (f" ({change_pct:+.0f}% overall)" if change_pct is not None else "")
        + ". List 4 short, plausible real-world factors that could explain this kind of trend. "
        "They are hypotheses only. Reply with a JSON array of strings and nothing else."
    )
    body = json.dumps({
        "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3, "max_tokens": 200,
    }).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.load(r)
        result = _parse(data["choices"][0]["message"]["content"])
        if result:
            _CACHE[ck] = result
        return result
    except Exception:
        return []
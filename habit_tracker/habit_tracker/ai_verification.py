"""AI pre-verification for habit checks ("AI verifies first, then friends").

Pluggable + env-gated, OFF by default so social-only flow keeps working:

    AI_VERIFY_PROVIDER=off | ollama | openai
    AI_VERIFY_URL=http://127.0.0.1:11434          # ollama default
    AI_VERIFY_MODEL=qwen2.5vl:7b                  # any vision model you pulled
    AI_VERIFY_TIMEOUT=25
    AI_VERIFY_MIN_CONFIDENCE=0.6
    OPENAI_API_KEY=...                            # for provider=openai

Providers
---------
ollama  — local VLM on this PC's RTX 3090 (free, private, ~1-3s/image).
          Setup:  winget install Ollama.Ollama && ollama pull qwen2.5vl:7b
openai  — any OpenAI-compatible vision endpoint (gpt-4o-mini etc.); set
          AI_VERIFY_URL=https://api.openai.com and OPENAI_API_KEY.

Fail-open: if the provider is unreachable/errors, we return ok=True with
verdict 'skipped' — a down GPU box must never block users from sending checks.
"""
import base64
import json
import logging
import os

import requests

logger = logging.getLogger('habit_tracker')

PROMPT = (
    'You verify photo check-ins for a habit tracker. Claimed habit: "{habit}".\n'
    'Decide: is the photo plausibly RELATED to this habit? Related means: the '
    'activity itself, OR just its object/equipment, OR the place, OR the result. '
    'The user does NOT need to be visible doing it — the object alone is enough. '
    'Examples: a dumbbell alone MATCHES "workout"; a book alone MATCHES '
    '"reading"; any bottle/cup/glass MATCHES "drink water"; a dumbbell does NOT '
    'match "reading books". If you are unsure, set match=true (give the user the '
    'benefit of the doubt). Only clearly unrelated photos get match=false.\n'
    'Reply ONLY with JSON exactly like {{"match": true, "confidence": 0.9, '
    '"reason": "..."}} — match=false when the photo does not fit the habit, '
    'and confidence is how sure you are of YOUR match decision.'
)


class AIVerdict:
    def __init__(self, ok, verdict, confidence=0.0, reason=''):
        self.ok = ok                  # False only when AI confidently rejects
        self.verdict = verdict        # 'approved' | 'rejected' | 'skipped'
        self.confidence = confidence
        self.reason = reason

    def as_dict(self):
        return {'verdict': self.verdict, 'confidence': self.confidence, 'reason': self.reason}


def _downscale(raw_bytes, max_side=None):
    """Shrink the photo before sending it to the model. Fewer vision tokens =
    much faster + cheaper inference, and 512px is plenty for 'is this a gym?'.
    Falls back to the original bytes if Pillow chokes."""
    max_side = max_side or int(os.getenv('AI_VERIFY_IMAGE_SIZE', '512'))
    try:
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(raw_bytes))
        img.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        img.convert('RGB').save(buf, 'JPEG', quality=80)
        return buf.getvalue()
    except Exception:
        return raw_bytes


def _parse_model_json(text):
    """Models sometimes wrap JSON in prose/fences — extract the first object."""
    start, end = text.find('{'), text.rfind('}')
    if start == -1 or end <= start:
        raise ValueError(f'no JSON in: {text[:120]}')
    return json.loads(text[start:end + 1])


def _verify_ollama(image_b64, habit_name, url, model, timeout):
    resp = requests.post(
        f"{url.rstrip('/')}/api/chat",
        json={
            'model': model,
            'stream': False,
            'format': 'json',
            'messages': [{
                'role': 'user',
                'content': PROMPT.format(habit=habit_name),
                'images': [image_b64],
            }],
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return _parse_model_json(resp.json()['message']['content'])


def _verify_openai(image_b64, habit_name, url, model, timeout):
    resp = requests.post(
        f"{url.rstrip('/')}/v1/chat/completions",
        headers={'Authorization': f"Bearer {os.getenv('OPENAI_API_KEY', '')}"},
        json={
            'model': model or 'gpt-4o-mini',
            'messages': [{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': PROMPT.format(habit=habit_name)},
                    {'type': 'image_url',
                     'image_url': {'url': f'data:image/jpeg;base64,{image_b64}'}},
                ],
            }],
            'max_tokens': 150,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return _parse_model_json(resp.json()['choices'][0]['message']['content'])


def verify_check(image_file, habit_name) -> AIVerdict:
    """Run the configured AI check. `image_file` is a Django UploadedFile."""
    provider = os.getenv('AI_VERIFY_PROVIDER', 'off').lower()
    if provider in ('off', '', 'none'):
        return AIVerdict(True, 'skipped', reason='ai disabled')

    url = os.getenv('AI_VERIFY_URL', 'http://127.0.0.1:11434')
    model = os.getenv('AI_VERIFY_MODEL', 'qwen2.5vl:7b')
    timeout = int(os.getenv('AI_VERIFY_TIMEOUT', '25'))
    min_conf = float(os.getenv('AI_VERIFY_MIN_CONFIDENCE', '0.6'))

    try:
        image_file.seek(0)
        raw = image_file.read()
        image_file.seek(0)  # leave the file usable for the actual save
        image_b64 = base64.b64encode(_downscale(raw)).decode()

        if provider == 'ollama':
            data = _verify_ollama(image_b64, habit_name, url, model, timeout)
        elif provider == 'openai':
            data = _verify_openai(image_b64, habit_name, url, model, timeout)
        else:
            return AIVerdict(True, 'skipped', reason=f'unknown provider {provider}')

        match = bool(data.get('match'))
        conf = float(data.get('confidence', 0))
        reason = str(data.get('reason', ''))[:300]
        # Only reject when the model is confident it does NOT match.
        if not match and conf >= min_conf:
            return AIVerdict(False, 'rejected', conf, reason)
        return AIVerdict(True, 'approved', conf, reason)
    except Exception as exc:
        # Fail-open by design: AI being down must not block social checks.
        logger.warning('AI verification skipped (%s): %s', provider, exc)
        return AIVerdict(True, 'skipped', reason=f'provider error: {exc.__class__.__name__}')

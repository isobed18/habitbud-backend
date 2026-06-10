# AI Check Verification — Options & Implementation

Goal: **"AI verifies first, then it goes to friends."** When a user submits a
check photo, an AI decides whether the photo plausibly shows the claimed habit;
only passing photos reach friends for the social check. Social verification
stays the core — AI is a quality gate, not a replacement.

## Alternatives compared

| | A) Local VLM on the RTX 3090 (Ollama) | B) Cloud vision API | C) Client-side (on-device) | D) Hybrid (C → A/B) |
|---|---|---|---|---|
| How | Backend calls `http://127.0.0.1:11434` (this PC). Models: **qwen2.5vl:7b** (best mix), llama3.2-vision:11b, minicpm-v | OpenAI `gpt-4o-mini` / Anthropic Claude vision via API | CLIP-style zero-shot in the app (MobileCLIP / TFLite): image embedding vs habit-text embedding | Phone CLIP pre-filter; borderline photos go to server VLM |
| Cost | **Free** (your GPU, ~200W under load) | ~$0.001–0.01 per image | Free | Mostly free |
| Latency | ~1–3 s/image on a 3090 (7B Q4: ~6 GB VRAM) | ~1–4 s + network | <100 ms | <100 ms typical |
| Accuracy | High — real reasoning ("is this a gym?") | Highest | Moderate — similarity only, fooled by context | High where it matters |
| Privacy | Photos never leave your server | Photos go to a third party | Never leave the phone | Mixed |
| Ops | Ollama must run on this PC (it already hosts the backend) | None | +30–80 MB app size, native ML module work in RN/Expo | Both |
| Scale | One 3090 ≈ ~1 photo/sec sustained — fine for thousands of users | Infinite | Infinite | Very good |

**Recommendation: A (Ollama on the 3090) as the primary**, with B available by
flipping env vars (the code supports both). C is worth revisiting later as a
UX nicety (instant pre-feedback while the photo uploads), but on-device ML in
Expo means custom native modules — poor effort/benefit today. D becomes
attractive only at a scale where the 3090 saturates.

## What's implemented

`habit_tracker/ai_verification.py` — pluggable, **env-gated, OFF by default**,
**fail-open** (if the model/server errors, the check goes through socially —
a down GPU must never block users).

Flow in `ProofSubmissionView` (chat/views.py): photo → AI verdict →
- **rejected** (model says no-match with confidence ≥ threshold): HTTP **422**
  with a Turkish message + `{ai: {verdict, confidence, reason}}`; nothing is
  sent to friends — user retakes the photo.
- **approved / skipped**: message is created and sent to friends as before;
  the response includes the `ai` block so the UI can show "🤖 AI onayladı".

## Enabling on this PC (3090)

```powershell
winget install Ollama.Ollama
ollama pull qwen2.5vl:7b        # ~6 GB; first pull only
```
Then in `habit_tracker\.env`:
```
AI_VERIFY_PROVIDER=ollama
AI_VERIFY_URL=http://127.0.0.1:11434
AI_VERIFY_MODEL=qwen2.5vl:7b
AI_VERIFY_MIN_CONFIDENCE=0.6
```
Restart the server. Disable any time with `AI_VERIFY_PROVIDER=off`.

Cloud fallback instead: `AI_VERIFY_PROVIDER=openai`,
`AI_VERIFY_URL=https://api.openai.com`, `AI_VERIFY_MODEL=gpt-4o-mini`,
`OPENAI_API_KEY=...`.

## Tuning

- `AI_VERIFY_MIN_CONFIDENCE` (default 0.6): the model must be at least this
  confident in a NO before we reject — keeps false rejections rare.
- Prompt lives in `ai_verification.py::PROMPT`; verdicts are strict JSON.
- Test a model quickly:
  `ollama run qwen2.5vl:7b "describe this image" --image photo.jpg`

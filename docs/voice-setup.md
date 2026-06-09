# Voice Provider Setup

Use Vapi as the telephony/realtime layer. This repository provides the FastAPI backend tool endpoints; Vapi owns the public phone number, audio streaming, transcription, interruption handling, and TTS.

## Recommended Vapi Configuration

Assistant behavior:

- Introduce itself as Kuldeep's AI representative.
- Answer only from retrieved resume and GitHub evidence.
- If evidence is missing, say so plainly.
- Keep answers concise in voice mode.
- Ask for name, email, and preferred time before booking.

Server URL:

- `POST https://YOUR_DOMAIN/api/voice/respond`

Tools:

- `GET https://YOUR_DOMAIN/api/availability?from={{from}}&to={{to}}`
- `POST https://YOUR_DOMAIN/api/book`

Headers:

- `x-voice-secret: ${VOICE_WEBHOOK_SECRET}`

Model:

- Provider: Groq
- Suggested model: `llama-3.1-8b-instant`
- Temperature: `0.2`

Latency settings:

- Use a realtime-optimized transcription model.
- Use Groq for fast first-token latency.
- Keep retrieval top-k at 4 for voice.
- Prefer a fast TTS voice over the most expressive voice.

## Booking Flow

1. Caller asks to schedule an interview.
2. Assistant collects name, email, and preferred time.
3. Provider calls `/api/availability`.
4. Provider calls `/api/book`.
5. FastAPI calls Cal.com.
6. Assistant confirms only if Cal.com returns a successful booking.

## Test Script

Run at least 10 test calls:

- 3 direct booking calls.
- 3 background and repo Q&A calls.
- 2 interruption/barge-in calls.
- 2 adversarial or unsupported-claim calls.

Record first-response latency, transcription word error rate on a known script, and booking completion.

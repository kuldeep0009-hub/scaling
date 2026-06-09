# Deployment Checklist

## Required Accounts

- Groq API key for low-latency chat completions wired into `app/llm.py`.
- Cal.com event type or Google Calendar adapter.
- Vapi phone number for live calling.
- Public Python hosting. Recommended: Render web service using `render.yaml`.

## Environment Variables

Set every variable from `.env.example` in the host. Do not commit secrets.

Minimum production values:

- `PUBLIC_BASE_URL`
- `PERSONA_NAME`
- `PERSONA_EMAIL`
- `GROQ_API_KEY`
- `OPENAI_EMBEDDING_API_KEY` for hybrid RAG, optional but recommended
- `CALENDAR_PROVIDER`
- `CALCOM_API_KEY`
- `CALCOM_EVENT_TYPE_ID`
- `VOICE_WEBHOOK_SECRET`

## Before Submission

- Replace `data/resume.md` with the real resume.
- Set GitHub owner/repositories and run `python scripts/ingest.py`.
- Ask at least 20 golden questions and update `evals/golden.json`.
- Run `python scripts/eval.py`.
- Run `python scripts/make_report_pdf.py` and edit the generated report text with final measured numbers.
- Confirm `/api/book` creates a real calendar invitation.
- Confirm the voice provider phone number reaches the deployed backend.

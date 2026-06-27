# FirstFrame AI

**From vague ideas to structured story development.**

FirstFrame AI is a hackathon MVP that turns a rough creative idea into a structured short-film story plan through a **Creative Reasoning Harness**.

It is not a chatbot. Every generation follows an explicit workflow:

```text
Idea -> Reasoning -> Planning -> Evaluation -> Structured Story Plan
```

## Why It Exists

Beginners often have a promising story idea but do not know how to shape it:

- What is the emotional core?
- Who is the protagonist?
- Where is the conflict?
- Does the ending work?
- Is the story practical for a short film?

Direct prompting often jumps straight to prose. FirstFrame AI slows the process down and makes story development inspectable, structured, and repeatable.

## Current MVP

- FastAPI backend with `POST /api/generate`
- Next.js demo frontend
- Creative Reasoning Harness orchestration
- OpenAI provider adapter
- Prompt, Knowledge, Rubric, and Example loaders
- Short-film domain intelligence pack
- Pydantic structured output validation
- AI Thinking Timeline and Story Flow visualization
- English/Vietnamese loading UX and localized model-output guidance

## Architecture At A Glance

```text
Next.js Frontend
  |
  v
FastAPI API
  |
  v
StoryGenerationService
  |
  v
Creative Reasoning Harness
  |-- Reasoning Layer
  |-- Planning Layer
  |-- Evaluation Layer
  |
  v
Domain Assets
  |-- prompts
  |-- knowledge
  |-- rubrics
  |-- examples
  |
  v
OpenAI Provider Adapter
  |
  v
Validated Structured JSON
```

The engineering focus is **Track 2: Engineering Depth**: clean boundaries, provider isolation, domain plugin assets, loader components, immutable artifacts, and structured output contracts.

## Repository Structure

```text
backend/              FastAPI API, Harness runtime, core contracts, OpenAI adapter
frontend/             Next.js App Router demo UI
domains/short-film/   Short-film prompts, knowledge, rubric, examples, output schema
docs/                 Architecture, workflow, kernel, decisions, roadmap
```

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Create `backend/.env` from `backend/.env.example` and set `OPENAI_API_KEY`.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Default URLs:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

## Current Limitations

- One active domain: Short Film Story Development.
- No auth, persistence, save/resume, deployment, or streaming.
- Domain registration is currently static in the application service.
- OpenAI is the only implemented provider adapter.

## Future Domains

The Harness is designed so future domains can add their own assets without rewriting the core workflow:

- YouTube storytelling
- Marketing campaigns
- Game narrative design
- Book writing
- Educational storytelling


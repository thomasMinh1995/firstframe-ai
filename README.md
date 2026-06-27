# FirstFrame AI

> **From a vague idea to a production-ready story plan through AI-guided creative reasoning.**

FirstFrame AI is an AI-powered creative assistant designed to help beginners transform an early idea into a structured short-film story plan.

Instead of immediately generating a screenplay, FirstFrame AI guides creators through a reasoning workflow inspired by how experienced mentors develop stories.

The project is built on a reusable **Creative Reasoning Harness**, allowing different creative domains to share the same reasoning pipeline while using domain-specific knowledge, prompts, and evaluation rubrics.

---

# Why FirstFrame AI?

Many creators have interesting ideas but struggle to answer questions like:

* Is this idea emotionally strong enough?
* Where is the real conflict?
* Is the story complete?
* Is it practical to produce as a short film?

Traditional AI tools often jump directly to content generation.

FirstFrame AI slows down that process and focuses on structured creative thinking before generation.

---

# Features

Current MVP includes:

* AI-guided story reasoning
* Story planning workflow
* Story quality evaluation
* Creative Thinking Timeline
* Structured JSON output
* Short-film knowledge base
* Domain plugin architecture
* Creative Reasoning Harness

---

# Demo Workflow

```text
User Idea
      │
      ▼
Creative Reasoning Harness
      │
      ├── Reasoning Layer
      │        Understand the idea
      │
      ├── Planning Layer
      │        Build the story plan
      │
      ├── Evaluation Layer
      │        Review story quality
      │
      ▼
Structured Story Plan
```

Unlike a traditional chatbot, every request follows the same reasoning workflow before producing the final result.

---

# Architecture

The project follows Clean Architecture principles.

```text
Frontend (Next.js)

        │

        ▼

FastAPI API

        │

        ▼

Creative Reasoning Harness

        ├── Reasoning Layer

        ├── Planning Layer

        ├── Evaluation Layer

        ▼

Prompt Loader

Knowledge Loader

Rubric Loader

Example Loader

        ▼

OpenAI Provider

        ▼

Structured Output
```

The Harness is provider-independent.

The OpenAI integration is isolated behind infrastructure adapters.

Domain knowledge lives outside the runtime engine.

---

# Repository Structure

```text
firstframe-ai/

backend/
    FastAPI backend

frontend/
    Next.js frontend

domains/
    Domain plugins

docs/
    Architecture
    Workflow
    Design decisions
    Roadmap
```

---

# Tech Stack

Backend

* FastAPI
* Pydantic v2
* OpenAI Responses API

Frontend

* Next.js
* React
* TypeScript

Architecture

* Clean Architecture
* SOLID
* Provider Adapter Pattern
* Domain Plugin Pattern

---

# Local Development

Backend

```bash
cd backend

python -m venv .venv

source .venv/bin/activate

pip install -r requirements-dev.txt

uvicorn app.main:app --reload
```

Frontend

```bash
cd frontend

npm install

npm run dev
```

Backend:

http://localhost:8000

Frontend:

http://localhost:3000

---

# Current Domain

The first supported domain is:

🎬 Short Film Story Development

The architecture is designed to support future domains such as:

* YouTube content planning
* Marketing campaigns
* Book writing
* Game narrative design
* Educational storytelling

without changing the Creative Reasoning Harness.

---

# Roadmap

* ✅ Foundation
* ✅ Creative Reasoning Harness
* ✅ OpenAI Integration
* ✅ Prompt & Knowledge Loader
* ✅ Story Planning
* ✅ Story Evaluation
* ✅ Interactive Demo UI
* 🚧 Deployment
* 🚧 Multi-domain support

---

# Why it is different

FirstFrame AI is **not a chatbot**.

It is a **Creative Reasoning Harness**.

Instead of generating text immediately, it follows an explicit workflow:

Understand

↓

Reason

↓

Plan

↓

Evaluate

↓

Generate

This makes the system more structured, extensible, and reusable across different creative domains.

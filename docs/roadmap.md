# Roadmap

## Completed

### Foundation

- Repository structure
- FastAPI backend
- Next.js App Router frontend
- Documentation baseline
- Dependency files

### Creative Reasoning Harness

- Immutable artifacts
- Domain plugin protocol
- Domain registry
- Reasoning, Planning, and Evaluation interfaces
- API transport models separated from internal artifacts

### End-To-End Workflow

- `POST /api/generate`
- Reasoning -> Planning -> Evaluation orchestration
- API-safe error handling
- Integration tests around the workflow

### OpenAI Integration

- `OpenAIProvider`
- Environment-based configuration
- Strict JSON instructions
- Pydantic structured output validation
- Provider-independent errors for missing config, timeout, request failure, and malformed responses

### Short-Film Intelligence Pack

- Story planner prompt
- Script critic prompt
- Film glossary
- Film rules
- Story patterns
- Story rubric
- Five example stories
- Domain-level output schema documentation

### Loader System

- Prompt Loader
- Knowledge Loader
- Rubric loading through Knowledge Loader
- Example Loader
- Unit tests for loader behavior and caching

### Demo Experience

- Idea textarea and Generate flow
- Thinking Timeline UX
- English/Vietnamese loading label heuristic
- Story Flow visualization
- Presentation-ready Analysis, Story Plan, and Evaluation cards
- Rubric score indicators

## Near-Term Next Work

- Deploy backend and frontend for public judging.
- Add a loaded reasoning prompt instead of inline reasoning instructions.
- Improve frontend empty/error states.
- Add smoke tests for the frontend UI.
- Add a demo seed mode or fixture path for low-risk live presentations.

## Future Product Work

- Save/resume story plans.
- Export story plans to Markdown or PDF.
- Add iteration loops after mentor questions.
- Add user-selectable tone, budget, length, and production constraints.
- Add streaming or progress events if provider/runtime support is introduced.

## Future Engineering Work

- Dynamic domain discovery.
- Additional provider adapters.
- More explicit application service boundaries.
- More complete structured contracts for frontend rendering.
- Observability that remains lightweight and privacy-conscious.

## Future Domains

- YouTube storytelling
- Marketing campaigns
- Game narrative design
- Book writing
- Educational storytelling

## Not In Current MVP

- Authentication
- Database persistence
- RAG or vector search
- Multi-agent orchestration
- LangGraph
- Payment or account management


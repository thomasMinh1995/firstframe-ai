# Roadmap

## Product Direction

FirstFrame helps beginners complete their first short-film screenplay through guided story development and specific feedback, while keeping creative decisions with the author.

The first users are Vietnamese-speaking beginners with an idea or personal experience they want to turn into a screenplay. A crew and filming schedule are not prerequisites.

```text
Idea -> Story Development -> Scene Outline -> Write and Revise -> Complete Screenplay
```

The current MVP supports the project clarification and story-plan revision loop in Milestone 1. Later milestones extend that foundation toward a complete screenplay and remain planned work. Milestones describe delivery order rather than fixed dates.

## Completed MVP Foundation

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

### Story-Plan Generation Workflow

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

## Milestone 1: Continue and Revise a Story Project — Implemented, Awaiting User Validation

- Save and resume projects, including the creator's decisions and story-plan versions.
- Collect creative intent, desired length and tone, and practical constraints such as cast size and available locations.
- Ask focused follow-up questions and let the creator answer before developing the plan further.
- Let the creator edit the story plan and request feedback on the revised version.

Implemented with local SQLite persistence, explicit saves, up to three clarification questions, editable story-plan sections, version history and restoration, and feedback freshness checks. Stale saves are rejected to protect edits made in another window. AI actions save pending edits before running. JSON backup downloads are available; account sync and backup import are not implemented.

Automated tests cover the question gate, persistence across app instances, review of the exact edited draft, stale-save conflicts, provider failure, and preserving replaced drafts. Live model quality and beginner usability still need validation.

**User outcome:** A chosen story plan that reflects the creator's intent and resources, with a clear next step.

**Validation:** A beginner can return to a saved project, revise the plan after answering questions, and explain the choices they made.

## Milestone 1.1: Export a Selected Story Plan as PDF — Planned

- Export the current saved revision or a selected historical story-plan version.
- Preserve the selected draft's wording, section order, and incomplete content.
- Keep AI feedback, rubric scores, and analysis outside the exported document.
- Save pending edits before exporting the current draft; export history without restoring or changing the working draft.
- Distinguish save effects from the read-only export step; preserve unsaved buffers on save failures and historical exports, and pin the selected source across retries.
- Work without an AI provider and handle stale revisions without exporting a different draft.

**User outcome:** A readable development document to share for feedback, clearly labeled as a story plan rather than a completed screenplay.

**Status:** Planning only; no PDF export implementation is delivered yet. See [Feature #5](https://github.com/thomasMinh1995/firstframe-ai/issues/5) and the [implementation plan](plans/story-plan-pdf-export.md). Merging the planning PR does not complete the feature or close the issue.

**Validation:** Exporting historical version A while working on B produces A's content, excludes AI feedback from the document and PDF metadata, and preserves B's unsaved buffer. Late responses and retries cannot overwrite edits or silently select a newer revision. Vietnamese text and multi-page layout must be visually verified during implementation.

## Milestone 1.2: Visible Author Intent and Feedback-to-Edit Flow — P0, Planned

- Show the effective saved author context, including retained clarifications, without promoting AI analysis or proposals into author decisions.
- Distinguish saved context, unsaved edits, and the context of historical feedback.
- Pair each revision priority with evidence, its effect on the intended experience, and a next step; link to validated targets in the reviewed draft.
- Let the creator focus the relevant field and revise manually. Navigation never saves, rewrites, restores a draft, or calls AI.
- Keep stale feedback readable without applying its navigation to a different draft; preserve buffers on conflicts, failures, and late responses.

**User outcome:** The beginner can explain the intent being used, choose a useful revision, and complete a focused story-plan revision round while retaining creative control.

**Status:** Planning only; no implementation is delivered by the planning PR. See [P0 #7](https://github.com/thomasMinh1995/firstframe-ai/issues/7) and the [implementation plan](plans/p0-author-intent-revision-flow.md). This P0 can proceed independently of PDF export in Milestone 1.1; merging the plan does not close the feature issue.

**Validation:** Saved context must match AI input, links must target the correct reviewed content, and choosing an edit must preserve all unsaved text. Automated contract/UI tests and a real-model beginner pilot are required during implementation; transport tests alone do not establish feedback quality.

## Milestone 2: Build an Editable Scene Outline

- Develop the selected story plan into an ordered list of scenes.
- Clarify what happens in each scene, its purpose, and how it connects to the story.
- Let the creator add, remove, reorder, and revise scenes.
- Give specific feedback on missing connections, repetition, and whether events can be expressed on screen.

**User outcome:** A scene outline clear enough to begin writing the screenplay.

**Validation:** The creator can use the outline to write scenes and understand the effect of changing their order or purpose.

## Milestone 3: Complete and Revise the Screenplay

- Support writing and editing action and dialogue scene by scene.
- Anchor feedback to specific scenes or passages, explaining the issue and offering revision options.
- Let the creator choose which suggestions to apply and retain draft versions.
- Support at least one feedback-and-revision round and export a readable screenplay.
- Use the rubric as a discussion aid, adapted to creative intent; an AI score is not a completion gate.

**User outcome:** A complete short-film screenplay, from first scene to last, revised and ready to share for reading and further development.

**Completion means:** All scenes are written, action and dialogue communicate the intended story, at least one feedback-and-revision round has taken place, and the draft can be exported. Shooting or producing a film is not required.

**Validation:** Beginners can complete and revise drafts. Experienced readers review examples of feedback and before/after drafts to check whether suggestions are specific, useful, and respectful of the author's intent.

## Later Optional Extension: Rough Scene Illustrations

Consider this only after validating the core screenplay journey.

- Provide simple scene sketches showing characters, positions, and key actions based on the screenplay.
- Let the creator correct the sketches when they misrepresent a scene.
- Use the sketches to reveal unclear action or staging and inform further script revision.

**User outcome:** An optional visual aid for understanding the screenplay. Illustrations are not required to complete a project and do not extend the scope into animation, video generation, or production management.

## Product Validation

Recruit a small pilot of beginners working on their first screenplay. Track:

- How many starting projects reach a completed screenplay, and how long it takes.
- Whether creators can act on feedback and explain their revision decisions.
- Reasons projects stall or are abandoned.
- Experienced readers' assessment of feedback and draft improvement.
- How much manual mentor support each project needs.

Run a small pilot as soon as Milestone 1 is usable, using manual support to learn what later milestones need. Validate the full writing journey once Milestone 3 is available. Generation counts and AI rubric scores alone do not demonstrate success.

## Engineering Priorities

Keep the existing Harness and domain assets as the foundation. Add persistence, contracts, and checks as required by each milestone. Reliability work, including error handling and pilot access, should support the writing journey.

Dynamic domain discovery, additional providers, RAG, multi-agent orchestration, streaming, and architecture refactoring are not prerequisites; revisit them only when a demonstrated product need justifies the work.

## Outside This Roadmap

- Filming preparation, shooting schedules, and crew management.
- Shooting, video generation, editing, and screenings.
- Automatic expansion into feature films or television series, or producer matchmaking.
- Other creative domains such as marketing, games, books, or educational storytelling.
- Payment and account-management features beyond access needed for a pilot.

Feature-film potential may remain a long-term ambition. It is not a requirement for a successful first short-film screenplay.


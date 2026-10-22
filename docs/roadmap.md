# Roadmap

## Product Direction

FirstFrame helps people in Vietnam develop a moment from their own lives into their first short-film screenplay, understand their creative decisions, and revise the work for human collaborators.

The first pilot focuses on Vietnamese film enthusiasts, especially young people who have not completed a short-film screenplay and lack a development method or useful feedback. No prior film vocabulary, crew, or shooting schedule is required.

```text
Moment -> Story Plan -> Scene Outline -> Write and Revise Screenplay -> Export Screenplay
```

The current MVP delivers clarification and manual story-plan revision, not a complete screenplay. A story plan is a useful milestone for choosing the story; it is not a guarantee of screenplay quality or the final product ceiling. Review gives feedback without rewriting the author's draft.

The product handoff ends at screenplay export. Casting, staging, shooting, editing, and post-production are a separate process with real people and actors. AI video, synthetic actors, generated footage, and production management are outside the direction.

## Next Delivery Priority: Story-Plan Demo for Vietnamese Beginners — Planned

The [detailed plan](plans/vietnam-first-screenplay-mvp.md) records the agreed direction and acceptance criteria; [implementation issue #26](https://github.com/thomasMinh1995/firstframe-ai/issues/26) stays open after the documentation PR merges. These are proposed improvements, not features delivered by this documentation update. Existing milestone numbers are retained for references; the delivery order below takes precedence over their numbering.

| Order | Small change | Expected evidence |
| --- | --- | --- |
| P0.1 | Invite a small lived moment through plain Vietnamese copy and examples; keep existing project/save mechanics | A beginner knows what to enter with little assistance |
| P0.2 | Read title, logline, beginning, middle, and ending from the working draft; expand other details and retain the editor | The reader can picture the progression and a memorable detail; no extra AI narration call or loss of unsaved edits |
| P0.3 | Deliver the saved author-context card portion of #7, with shared backend provenance and saved/unsaved distinctions | The author can see what is being used; proposals are not promoted to decisions; old feedback keeps its own context |
| P0.4 | Guide one manual edit, save, and review using the existing controls | New feedback reads the exact revised draft; navigation does not rewrite, save, or call AI |
| P0.5 | Run three Vietnamese situations three times each as independent full workflows on the actual demo configuration; retain every result and timing | Live requires 9/9 passing runs and PO approval under plan section 4.1; otherwise use only an approved, clearly labeled recording |

P0.5 begins alongside preparation. Include everyday care, humor or awkwardness, and a quiet observational moment. Address observed model failures narrowly and recheck the relevant guidance on the actual configuration; valid JSON or AI rubric scores alone do not establish quality.

**Live/recorded acceptance:** Before running, freeze briefs, choices, manual edits, expected behavior, commit/prompt/model configuration, and per-AI-operation wait budgets. Follow the existing [model evaluation checklist](prompt-evaluation.md). Keep all nine independent analyze–plan–edit–save–review runs, including provider/validation failures, with inputs, outputs, seed when available, timings, and human verdicts; do not select only successful generations.

Live requires 9/9 completed runs within the declared wait budgets, no blockers, and a full presentation rehearsal of at most five minutes including real waiting, actions, and reading. Blockers include explicit-intent violations, invented author decisions/evidence, draft rewriting, wrong feedback source, data loss/overwrite, or errors/missing results that prevent completion. Feedback must be grounded and actionable; an empty issue list is valid when no supported issue exists. A taste difference alone is not a blocker.

The PO, together with an experienced reader, records **live / recorded only / not ready**, date, configuration, and evidence in #26. Missing evidence, any failed run, or a changed configuration prevents live approval until a new complete nine-run batch passes; retain earlier failures. Do not raise budgets retrospectively to pass a run. An approved recording must preserve the brief/plan/edit/review chain and label playback and editorial corrections; it does not establish live readiness or general model quality. During live failure, budget overrun, or a clear intent violation, disclose the problem and switch to the approved recording. Without an approved recording, defer that segment.

Demo outcome: **tell a moment -> clarify what matters -> read a story plan -> make one author-led edit -> review the exact revised draft**. Changing the source idea or constraints still requires the existing clarification round. A 3–5 minute presentation must label its output as a story plan.

The differences to validate are starting without a formed premise, handling Vietnamese relationships and speech in context, expressing emotion through performable action, learning through a small revision, and respecting intent and relevant resources. Do not require escalating conflict, transformation, reconciliation, or a resolved ending for every form.

After the demo pilot, complete the deeper feedback-to-edit flow (#7) and selected story-plan PDF (#5), then proceed to scene outlines, screenplay writing/revision, and screenplay export. PDF does not block the demo. Preserve the implemented onboarding tour (#22), finish its pending acceptance, and adjust its copy when the new flow settles. Technical experiments are prioritized when they address observed writing-flow failures.

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
- Bind every feedback item, including stale feedback on the main screen, to its immutable author-context/draft snapshot; never replace its source with the current intent.
- Pair each revision priority with evidence, its effect on the intended experience, and a next step; link to validated targets in the reviewed draft.
- Let the creator focus the relevant field and revise manually. Navigation never saves, rewrites, restores a draft, or calls AI.
- Keep stale feedback readable without applying its navigation to a different draft; preserve buffers on conflicts, failures, and late responses.

**User outcome:** The beginner can explain the intent being used, choose a useful revision, and complete a focused story-plan revision round while retaining creative control.

**Status:** Planning only; no implementation is delivered by the planning PR. See [P0 #7](https://github.com/thomasMinh1995/firstframe-ai/issues/7) and the [implementation plan](plans/p0-author-intent-revision-flow.md). This P0 can proceed independently of PDF export in Milestone 1.1; merging the plan does not close the feature issue.

**Validation:** Saved context must match AI input; feedback artifacts, snapshots and targets must remain paired. Validate quotations against each target field, not the whole draft. Navigation preserves all unsaved text, including project-name-only edits, and uncertain save results must not trigger a reload or retry that overwrites buffers. Automated contract/UI tests and a real-model beginner pilot are required during implementation; transport tests alone do not establish feedback quality.

## New-User Onboarding Tour — Implemented, Awaiting Review

- Guide beginners through six steps in three stages: starting a project, clarifying their choices, and editing/reviewing a story plan.
- Show each step only when its target exists; pause for real user actions and preserve all unsaved edits.
- Support dismissing, resuming, replaying, mobile layouts, keyboard navigation, and browser-local progress.
- Keep tour navigation independent of project writes and AI calls.

**User outcome:** A beginner knows what to do next and how to save, revise, and return to a story project.

**Status:** The frontend MVP is implemented for review, including browser-local progress, conditional steps, keyboard focus, and responsive spotlight/dialog layouts. See [Feature #22](https://github.com/thomasMinh1995/firstframe-ai/issues/22), the [implementation plan](plans/new-user-tour.md), and [test evidence](testing/new-user-tour.md). Beginner pilot validation is still pending.

**Validation:** Cover empty and existing projects, conditional questions/drafts, failures, reloads, and project switches. Verify focus and positioning in a browser, and confirm tour controls preserve the full buffer without making save or AI requests.

## Milestone 2: Build an Editable Scene Outline — Planned

- Develop the selected story plan into an ordered list of scenes.
- Clarify what happens in each scene, its purpose, and how it connects to the story.
- Let the creator add, remove, reorder, and revise scenes.
- Give specific feedback on missing connections, repetition, and whether events can be expressed on screen.

**User outcome:** A scene outline clear enough to begin writing the screenplay.

**Validation:** The creator can use the outline to write scenes and understand the effect of changing their order or purpose.

## Milestone 3: Complete and Revise the Screenplay — Planned

- Support writing and editing action and dialogue scene by scene.
- Anchor feedback to specific scenes or passages, explaining the issue and offering revision options.
- Let the creator choose which suggestions to apply and retain draft versions.
- Support at least one feedback-and-revision round; screenplay export is the handoff in Milestone 4.
- Use the rubric as a discussion aid, adapted to creative intent; an AI score is not a completion gate.

**User outcome:** A complete short-film screenplay, from first scene to last, revised and ready to share for reading and further development.

**Writing completion means:** All scenes are written, action and dialogue communicate the intended story, and at least one feedback-and-revision round has taken place. Full product completion also requires exporting the selected draft in Milestone 4. Shooting or producing a film is a separate process.

**Validation:** Beginners can complete and revise drafts. Experienced readers review examples of feedback and before/after drafts to check whether suggestions are specific, useful, and respectful of the author's intent.

## Milestone 4: Export the Selected Screenplay — Planned

- Export the current saved draft or a selected historical screenplay version without changing its wording.
- Deliver a readable screenplay with complete Vietnamese text, scene headings, action, and dialogue for human collaborators.
- Preserve draft/version identity, unsaved work, and revision protections; keep AI feedback separate from the script.
- Keep export independent of model availability. Select formats and verify layout during implementation.

**User outcome:** A complete, revised screenplay the author can share for reading and development with real actors and filmmakers. This is FirstFrame's product handoff and is distinct from story-plan PDF in Milestone 1.1.

**Validation:** The selected version exports faithfully, Vietnamese and multi-page layout remain readable, and writers and experienced readers can use the document. Neither export nor AI scoring certifies production readiness or artistic quality.

## Conditional Future Direction: Feature and Television Screenwriting

Explore only after beginners can complete the short-film journey and some demonstrate a need to continue. Assess whether the characters, relationships, and material support a longer story rather than simply adding scenes. Television would require separate validation of episodic development.

Keep original material, author choices, and version history. No feature/season infrastructure is required for the demo. The future scope would still end at screenplay export; no automatic expansion, synthetic casting, or production tooling is promised.

Automatic scene illustrations are no longer an active milestone under this writing-only direction.

## Product Validation

Start with a discovery pilot of 5–8 Vietnamese beginners using their own experiences; this is not a representative market study. Record:

- Where people need help starting, reading, saving, or revising.
- Which meaningful details are retained, lost, or invented against intent, including forms of address and relationships.
- Whether authors can complete and explain one useful edit, and want to keep, share, or develop the plan further.
- Experienced readers' assessment of performable action, progression, and ambiguity relative to intent.
- Reasons projects stall and how much manual mentor support they need.

Compare selected tasks with a familiar chatbot and a direct story-development tool such as Cinequill or Screenwriting.ai, using the same material and constraints and reasonable context/revision opportunities. Do not infer competitor quality or a local advantage from feature marketing alone. Use private material only with the author's agreement and keep it out of public demo assets unless explicitly approved.

**Pilot/Milestone 2 acceptance:** Apply [plan section 6.1](plans/vietnam-first-screenplay-mvp.md#61-điều-kiện-pilot-đạt-và-chuyển-sang-m2). Before starting, the PO fixes N=5–8, the application/model version, and the task sheet: enter a moment, clarify/generate, explain the progression, edit, save, review, reopen the saved revision, and explain the edit. Log each person's completion, obstacles, errors, dropout reasons, and help per step. H0 uses only the common instructions and in-product tour/docs; H1 receives step/navigation prompts from the observer; H2 receives creative suggestions or someone acts for them. Only full H0 completion is independent; starters who drop out stay in N and do not pass.

At least 80% of N must complete independently, rounded up (N=5/6/7/8 requires 4/5/6/7 people). At least two independent completers must want to continue their own story and identify a next step; capture the obstacles. No unresolved blocker may remain: lost/overwritten work, inability to save/reopen, feedback on the wrong draft/context, explicit-intent violations, or operation errors preventing completion. Record evidence and verify each fixed failure on the candidate version.

The PO records **pass / fail / more evidence needed** in #26 with the participant table and experienced-reader observations. Milestone 2 is prioritized only when all thresholds and the no-blocker condition hold and the PO records pass. Otherwise improve Milestone 1; an approved demo recording cannot substitute for a passing pilot. Do not lower thresholds retrospectively. A changed task/threshold requires a new batch; keep the old report. Separate different application/model versions rather than pooling results to pass; a new batch still needs N=5–8. These are operating thresholds for a small discovery pilot, not market-wide evidence.

Measure completed screenplay drafts and export only when Milestones 3 and 4 are available. Generation counts and AI scores do not demonstrate success.

## Engineering Priorities

Keep the existing Harness and domain assets as the foundation. Add persistence, contracts, and checks as required by each milestone. Reliability work, including error handling and pilot access, should support the writing journey.

Dynamic domain discovery, additional providers, RAG, multi-agent orchestration, streaming, and architecture refactoring are not prerequisites; revisit them only when a demonstrated product need justifies the work.

## Outside This Roadmap

- Filming preparation, shooting schedules, and crew management.
- Shooting, AI video, synthetic actors, generated footage, editing, post-production, and screenings.
- Automatic expansion into feature films or television series, or producer matchmaking.
- Other creative domains such as marketing, games, books, or educational storytelling.
- Payment and account-management features beyond access needed for a pilot.

Feature and television screenwriting are conditional future research within the export boundary, not current delivery commitments. A successful short film does not need to become a longer work.


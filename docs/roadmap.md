# Roadmap

**Implementation update — 2 November 2026:** [AI-first workflow phases 1–6](plans/ai-first-workflow.md) now have local technical verification, including automatic short-script drafting, controlled scene/block revision and selected-screenplay PDF export ([phase 5 evidence](testing/phase5-screenplay-pdf-2026-10-29.md)). [PR #89](https://github.com/thomasMinh1995/firstframe-ai/pull/89) merged the workflow, scene editing and progress continuity fixes into `dev`. The delivery sequence below records the implementation order and acceptance scope; its pilot/PO acceptance requirements are still pending. Story-plan PDF issue #5 is a separate export contract and is not closed by screenplay export. Phase 6 UI/tour work is implemented locally; [QA-01 evidence](testing/phase6-workflow-acceptance-2026-10-29.md) records technical passes and remaining release gates. It does not replace the pilot/PO decision.

## Product Direction

FirstFrame helps people in Vietnam develop a moment from their own lives into their first short-film screenplay, understand their creative decisions, and revise the work for human collaborators.

The first pilot focuses on Vietnamese film enthusiasts, especially young people who have not completed a short-film screenplay and lack a development method or useful feedback. No prior film vocabulary, crew, or shooting schedule is required.

```text
Moment -> Story Plan -> Scene Outline -> Write and Revise Screenplay -> Export Screenplay
```

The current technical delivery covers clarification, story plans, scene outlines, screenplay drafting/revision and selected-screenplay PDF export. User validation remains pending. A story plan is a useful milestone for choosing the story; it is not a guarantee of screenplay quality or the final product ceiling. Review gives feedback without rewriting the author's draft.

Keep the current story-plan level of detail as the basis for validating the next writing step. The product goal is a good screenplay supported by editable scenes; do not keep expanding the plan or polishing its critic indefinitely. Under the approved M2 prototype, “dàn cảnh” includes scene order and proposed action, performance, space and visual treatment, with the author choosing what to retain. Physical staging on set and production management remain outside this roadmap. Existing intent, data and acceptance requirements still apply.

The product handoff ends at screenplay export. Casting, on-set staging, shooting, editing, and post-production are a separate process with real people and actors. AI video, synthetic actors, generated footage, and production management are outside the direction. Optional author-requested reference sketches in M2 illustrate a scene; they are not generated film footage or a prerequisite for writing.

## Delivery Order and Pending Deployment/User Validation

The [product plan](plans/vietnam-first-screenplay-mvp.md) and [issue #26](https://github.com/thomasMinh1995/firstframe-ai/issues/26) retain the existing product and acceptance criteria. PRs #30–#33 delivered the four MVP foundations; PR #36 delivered the approved workspace. PR #38 delivered the remaining technical #7 pairing/target/navigation work and affected tour instructions. Reuse these deliveries. Technical merge does not close #7 or establish model quality or pilot acceptance.

The owner changed the development order on **26 October 2026** to **M2 scene outline → M3 screenplay writing/revision → M4 export the selected screenplay → technical deployment → user experience trials**. Build and test the complete writing journey before inviting users. This supersedes the requirement to pass the M1 pilot before starting M2 implementation; it does not waive any acceptance threshold, close #7/#22/#26, or certify the critic. No general-purpose critic, additional prompt/model loop, embedding or judge is a prerequisite.

| Priority | Smallest scope | Evidence and stopping point |
| --- | --- | --- |
| 1 — M2 scene outline and staging choices | Editable scenes, initial scene-list suggestions, author-controlled staging feedback and optional on-demand reference sketches | Stable source/scene identity, add/remove/reorder/save/reopen; no automatic acceptance; text remains usable without AI or images. |
| 2 — M3 screenplay | Action and dialogue per scene; manual writing, revision and versions | Preserve author decisions, unsaved work and exact feedback sources; no automatic rewrite |
| 3 — M4 export | Export the explicitly selected saved screenplay version | Faithful text/order, readable Vietnamese and layout, independent of AI availability |
| 4 — Deploy, then user trials | Verify the complete journey technically and deploy a test environment before inviting users | Collect reader/user evidence, retain #7/N1/N2 and all existing acceptance thresholds; deployment is not acceptance |

The technical audit and real-model trials already exist. The author reviewed four saved cases and chose to preserve open endings and sequential beats, use natural dialogue, and replace passport hiding with an apology letter that leaves the daughter free to decide. These are case-specific editorial decisions, not implemented fixes or independent-reader/pilot acceptance. An earlier frozen 16-call Qwen 2.5 7B trial passed the source/JSON contract in both arms, but both had 3/4 false alarms on valid cases and 0/4 fully valid repairs on violation cases. The candidate was not selected; do not schedule another trial merely to pass these reused development cases or relabel the original closed-ending case using the author's later clarification.

**Harness stopping point:** stop an unsuccessful candidate now; finish the delivery phase only when #7 has its required technical, real-model, reader and user evidence, its data protections hold, and no acceptance blocker remains. A perfect critic and agreement with every editorial preference are not additional requirements. M2–M4 implementation now proceeds before user validation. Record **not passed / more evidence needed** for outstanding #7/critic acceptance, with each blocker and verification step; neither implementation progress nor deployment converts that status into acceptance. Once handed over, maintain harness only for concrete failures in the writing journey, rather than a standing optimization backlog.

Keep the current story-plan scope and rejected prompt results. Reuse the delivered writing features; fix concrete data-loss, source or journey failures as encountered. Prepared reader/session sheets remain available for the later user phase, not a new prerequisite for beginning M2.

Source/chunk IDs, minimal-repair guidance and new cases are tools for a confirmed feedback failure, not separate projects that must all be completed. Reuse #7's existing contracts and anchors. Only profile/optimize operations whose measured waiting time blocks the writing flow. Do not automatically add a judge, change models repeatedly or expand the benchmark after an inconclusive result. Record the result and stop that candidate; another iteration needs a specific unresolved writing-flow question, not a larger framework. Stopping an experiment never waives an unresolved acceptance blocker.

Keep the existing UI and six-step tour. Adjust only affected instructions if a confirmed fix changes the flow, after technical stabilization and before #7 pilot/acceptance. Preserve stored progress and dismissal/replay. #22's real-device, screen-reader, full Safari, 3–5-user pilot and acceptance-summary work remain pending where evidence is missing. Its full closure is not a new prerequisite for narrow #7 fixes or subsequent justified improvements. See the [#7 plan](plans/p0-author-intent-revision-flow.md), [tour plan](plans/new-user-tour.md) and [reduced harness plan](plans/harness-improvement.md).

Full-flow validation on `f607732` completed nine journeys but seven plan-generation runs exceeded 120 seconds and unsupported or intent-violating feedback remained; this was not live acceptance. PR #40 / issue #39 delivered offline framing/publication-gate tools. The [60-call report](evaluations/issue-7-framing-v1-guardrail-2026-10-25.md) records no false block/hold but four missed publication violations out of 16 and 28 unnecessary warnings. This measures a simulated gate, not the runtime story-plan failure rate. Keep the evidence; do not turn the experiment into another MVP dependency.

Defer automatic ethics/publication blocking, additional framing/judge layers, model routing and open-ended model/prompt trials. Reader review can still flag ethical, language or cultural concerns in context; deferring automated blocking does not remove that review. Embedding, retrieval, vector databases, reranking, top-k context reduction, a new workflow engine and automatic rewriting remain deferred without a demonstrated writing-flow need.

Preserve snapshots, project/artifact/revision pairing, all unsaved buffers including project-name edits, history, recovery and legacy feedback. IDs belong to the exact source snapshot/field/span; do not relocate invalid references by fuzzy matching, title or ordinal position. Old feedback keeps its own context; missing source means no unverified navigation. Navigation never saves, rewrites or calls AI. Keep both initial-plan and regeneration recovery paths; do not silently retry, overwrite a draft, or use raw evaluation data as the recovery store. Full draft and effective author context remain available; examples and AI proposals do not become author decisions.

The technical wait budgets remain clarification ≤45 seconds, plan with critic ≤120 seconds, review ≤60 seconds and a complete demo ≤5 minutes; they do not replace PO approval or permit retrospective budget increases. The acceptance criteria below and milestone numbers stay unchanged.

**Live/recorded acceptance:** Before running, freeze briefs, choices, manual edits, expected behavior, commit/prompt/model configuration, and per-AI-operation wait budgets. Follow the existing [model evaluation checklist](prompt-evaluation.md). Keep all nine independent analyze–plan–edit–save–review runs, including provider/validation failures, with inputs, outputs, seed when available, timings, and human verdicts; do not select only successful generations.

Live requires 9/9 completed runs within the declared wait budgets, no blockers, and a full presentation rehearsal of at most five minutes including real waiting, actions, and reading. Blockers include explicit-intent violations, invented author decisions/evidence, draft rewriting, wrong feedback source, data loss/overwrite, or errors/missing results that prevent completion. Feedback must be grounded and actionable; an empty issue list is valid when no supported issue exists. A taste difference alone is not a blocker.

The PO, together with an experienced reader, records **live / recorded only / not ready**, date, configuration, and evidence in #26. Missing evidence, any failed run, or a changed configuration prevents live approval until a new complete nine-run batch passes; retain earlier failures. Do not raise budgets retrospectively to pass a run. An approved recording must preserve the brief/plan/edit/review chain and label playback and editorial corrections; it does not establish live readiness or general model quality. During live failure, budget overrun, or a clear intent violation, disclose the problem and switch to the approved recording. Without an approved recording, defer that segment.

Demo outcome: **tell a moment -> clarify what matters -> read a story plan -> make one author-led edit -> review the exact revised draft**. Changing the source idea or constraints still requires the existing clarification round. A 3–5 minute presentation must label its output as a story plan.

The differences to validate are starting without a formed premise, handling Vietnamese relationships and speech in context, expressing emotion through performable action, learning through a small revision, and respecting intent and relevant resources. Do not require escalating conflict, transformation, reconciliation, or a resolved ending for every form.

Keep #7 revision protections while implementing M2–M4. Update only affected tour guidance once the full flow is stable, before user trials; #7 content/acceptance work remains open. Selected story-plan PDF (#5) stays after the demo and does not block it. Scene outlines, screenplay writing/revision and screenplay export have technical delivery as recorded above; user acceptance remains separate. Keep pending #22 acceptance separate from its technical update. Technical experiments should address observed writing-flow failures.

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

Implemented with local SQLite persistence, explicit saves, the existing clarification/confirmation flow, editable story-plan sections, version history and restoration, and feedback freshness checks. Stale saves are rejected to protect edits made in another window. AI actions save pending edits before running. JSON backup downloads are available; account sync and backup import are not implemented.

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

## Milestone 1.2: Visible Author Intent and Feedback-to-Edit Flow — Technical Delivery Merged, Acceptance Pending

- Show the effective saved author context, including retained clarifications, without promoting AI analysis or proposals into author decisions.
- Distinguish saved context, unsaved edits, and the context of historical feedback.
- Bind every feedback item, including stale feedback on the main screen, to its immutable author-context/draft snapshot; never replace its source with the current intent.
- Pair each revision priority with evidence, its effect on the intended experience, and a next step; link to validated targets in the reviewed draft.
- Let the creator focus the relevant field and revise manually. Navigation never saves, rewrites, restores a draft, or calls AI.
- Keep stale feedback readable without applying its navigation to a different draft; preserve buffers on conflicts, failures, and late responses.

**User outcome:** The beginner can explain the intent being used, choose a useful revision, and complete a focused story-plan revision round while retaining creative control.

**Status:** The foundations and workspace were delivered through PRs #30–#36; PR #38 completed the technical pairing/target/navigation work and updated the affected tour instructions. [P0 #7](https://github.com/thomasMinh1995/firstframe-ai/issues/7) remains the first priority: audit each acceptance criterion against actual evidence, fix only confirmed remaining failures and validate the combined flow. Do not infer user/model acceptance from merged code or repeat the delivered UI. See the [implementation plan](plans/p0-author-intent-revision-flow.md). PDF remains independent; #7 stays open until its own acceptance evidence is sufficient.

**Validation:** Saved context must match AI input; feedback artifacts, snapshots and targets must remain paired. Validate quotations against each target field, not the whole draft. Navigation preserves all unsaved text, including project-name-only edits, and uncertain save results must not trigger a reload or retry that overwrites buffers. Automated contract/UI tests and a real-model beginner pilot are required during implementation; transport tests alone do not establish feedback quality.

## New-User Onboarding Tour — Implemented, Technical Review Passed, Acceptance Pending

- Guide beginners through six steps in three stages: starting a project, clarifying their choices, and editing/reviewing a story plan.
- Show each step only when its target exists; pause for real user actions and preserve all unsaved edits.
- Support dismissing, resuming, replaying, mobile layouts, keyboard navigation, and browser-local progress.
- Keep tour navigation independent of project writes and AI calls.

**User outcome:** A beginner knows what to do next and how to save, revise, and return to a story project.

**Status:** The tour was updated for PR #36 and the #7 flow in PR #38. The technical browser/state checks do not replace real-device or user acceptance. Reuse the tour; adjust affected instructions only if a confirmed #7 fix changes the stable flow, before its pilot/acceptance. Preserve six steps and existing progress; do not force users to replay. [Feature #22](https://github.com/thomasMinh1995/firstframe-ai/issues/22) remains open for its 3–5-user pilot, acceptance summary, real screen reader, mobile/IME/virtual keyboard and full real-Safari evidence. See the [plan](plans/new-user-tour.md), [tour evidence](testing/new-user-tour.md) and [workspace QA](testing/approved-story-workspace.md).

**Validation:** Cover empty and existing projects, conditional questions/drafts, failures, reloads, and project switches. Verify focus and positioning in a browser, and confirm tour controls preserve the full buffer without making save or AI requests.

## Milestone 2: Build an Editable Scene Outline — Technical Delivery, User Validation Pending

This scope has technical delivery in the workflow linked above. The M1 pilot and PO acceptance are deferred until after M2–M4 and technical deployment; their acceptance criteria remain pending, not passed. Do not require embedding, more judges, another model comparison or full closure of #22 as additional prerequisites. Validate whether the selected story plan helps the creator write scenes; do not expand it just to improve an isolated critic score.

- Develop the selected story plan into an ordered list of scenes.
- Clarify what happens in each scene, its purpose, and how it connects to the story.
- Let the creator add, remove, reorder, and revise scenes.
- Give specific feedback on missing connections, repetition, and whether events can be expressed on screen.
- Keep scene choices editable and suggestions optional. Reuse the current compact step cards and scene-level progress; do not restore an older prototype layout.
- Suggest a whole list only before an outline exists; preview/edit/remove before applying. Later suggestions add or develop individual scenes without replacing the outline.
- Add one reference sketch per scene on explicit request, preview before retaining, and keep prior images marked stale when their source changes. Image-provider feasibility, data and cost checks are part of the image delivery; a placeholder does not complete that feature.

**User outcome:** A scene outline clear enough to begin writing the screenplay.

**Validation:** The creator can use the outline to write scenes and understand the effect of changing their order or purpose.

Deliver manual editing and persistence first, then text suggestions, staging feedback and reference sketches. Reuse source/revision/recovery protections. If image-provider work is unresolved, the text path may proceed to M3 while image delivery and full M2 completion remain open; neither an unavailable image nor AI feedback blocks saving or writing. Existing M1/#7/#22 acceptance criteria remain unchanged.

## Milestone 3: Complete and Revise the Screenplay — Technical Delivery, User Validation Pending

- Support writing and editing action and dialogue scene by scene.
- Anchor feedback to specific scenes or passages, explaining the issue and offering revision options.
- Let the creator choose which suggestions to apply and retain draft versions.
- Support at least one feedback-and-revision round; screenplay export is the handoff in Milestone 4.
- Use the rubric as a discussion aid, adapted to creative intent; an AI score is not a completion gate.

**User outcome:** A complete short-film screenplay, from first scene to last, revised and ready to share for reading and further development.

**Writing completion means:** All scenes are written, action and dialogue communicate the intended story, and at least one feedback-and-revision round has taken place. Full product completion also requires exporting the selected draft in Milestone 4. Shooting or producing a film is a separate process.

**Validation:** Beginners can complete and revise drafts. Experienced readers review examples of feedback and before/after drafts to check whether suggestions are specific, useful, and respectful of the author's intent.

## Milestone 4: Export the Selected Screenplay — Technical Delivery, User Validation Pending

- Export the current saved draft or a selected historical screenplay version without changing its wording.
- Deliver a readable screenplay with complete Vietnamese text, scene headings, action, and dialogue for human collaborators.
- Preserve draft/version identity, unsaved work, and revision protections; keep AI feedback separate from the script.
- Keep export independent of model availability. The delivered format is PDF; retain its layout and fidelity checks.

**User outcome:** A complete, revised screenplay the author can share for reading and development with real actors and filmmakers. This is FirstFrame's product handoff and is distinct from story-plan PDF in Milestone 1.1.

**Validation:** The selected version exports faithfully, Vietnamese and multi-page layout remain readable, and writers and experienced readers can use the document. Neither export nor AI scoring certifies production readiness or artistic quality.

## Delivery Sequence for the Complete Writing Journey

| Step | Smallest implementation | Technical check before moving on |
| --- | --- | --- |
| M2 | Use an author-selected saved story plan to create an editable ordered scene outline; add/remove/reorder/save scenes | Stable scene/source identity, preserved intent and draft, reopen the same outline; upstream edits never silently replace scenes |
| M3 | Write and revise action/dialogue per scene, with saved versions and author-controlled feedback | Reorder/delete handling, unsaved buffers, exact feedback source, no automatic rewrite; failed AI feedback must not prevent manual writing/saving |
| M4 | Export the saved screenplay version explicitly selected by the author in one readable format | Vietnamese, scene order/headings/action/dialogue and multi-page layout faithful to that version; no AI required for export, no loss of unsaved work |
| Technical release | Verify the complete journey locally, then deploy a controlled test environment | Persistence/restore, configured model connectivity and error handling work in that environment; no public launch or paid provider is authorized by this sequence alone |
| User phase | Invite participants only when the deployment and session are ready; observe the complete journey and critic value | Keep M1/#7/#22 criteria separate from new M2–M4 observations. Record actual assistance and failures; do not infer usability or screenplay quality from technical completion |

M2–M4 start with the existing harness, provider and storage protections. Keep the first delivery focused on one continuous writing journey. Do not add automatic two-way story-plan/script synchronization, multi-model judging, embeddings, production tooling or multiple export formats. Story-plan PDF #5 is independent and does not block screenplay export.

The existing #26 pilot task and thresholds still measure M1. A later full-journey task sheet must be fixed before participants start, with M2–M4 observations recorded separately; do not silently extend the M1 pass calculation or reinterpret old results. Completion of all features means **ready for technical deployment/observation**, not accepted by users.

## Conditional Future Direction: Feature and Television Screenwriting

Explore only after beginners can complete the short-film journey and some demonstrate a need to continue. Assess whether the characters, relationships, and material support a longer story rather than simply adding scenes. Television would require separate validation of episodic development.

Keep original material, author choices, and version history. No feature/season infrastructure is required for the demo. The future scope would still end at screenplay export; no automatic expansion, synthetic casting, or production tooling is promised.

The approved M2 prototype adds author-requested reference sketches to the active scope. Automatic images for the whole outline, multi-frame storyboard generation and generated film footage remain outside this delivery. Image delivery requires a working provider and source/cost checks; unavailable images must not block writing.

## Product Validation

Start with a discovery pilot of 5–8 Vietnamese beginners using their own experiences; this is not a representative market study. Record:

- Where people need help starting, reading, saving, or revising.
- Which meaningful details are retained, lost, or invented against intent, including forms of address and relationships.
- Whether authors can complete and explain one useful edit, and want to keep, share, or develop the plan further.
- Experienced readers' assessment of performable action, progression, and ambiguity relative to intent.
- Reasons projects stall and how much manual mentor support they need.

Compare selected tasks with a familiar chatbot and a direct story-development tool such as Cinequill or Screenwriting.ai, using the same material and constraints and reasonable context/revision opportunities. Do not infer competitor quality or a local advantage from feature marketing alone. Use private material only with the author's agreement and keep it out of public demo assets unless explicitly approved.

**M1 pilot acceptance after deployment:** Apply [plan section 6.1](plans/vietnam-first-screenplay-mvp.md#61-điều-kiện-pilot-đạt-và-chuyển-sang-m2). Before starting, the PO fixes N=5–8, the application/model version, and the task sheet: enter a moment, clarify/generate, explain the progression, edit, save, review, reopen the saved revision, and explain the edit. Log each person's completion, obstacles, errors, dropout reasons, and help per step. H0 uses only the common instructions and in-product tour/docs; H1 receives step/navigation prompts from the observer; H2 receives creative suggestions or someone acts for them. Only full H0 completion is independent; starters who drop out stay in N and do not pass.

At least 80% of N must complete independently, rounded up (N=5/6/7/8 requires 4/5/6/7 people). At least two independent completers must want to continue their own story and identify a next step; capture the obstacles. No unresolved blocker may remain: lost/overwritten work, inability to save/reopen, feedback on the wrong draft/context, explicit-intent violations, or operation errors preventing completion. Record evidence and verify each fixed failure on the candidate version.

The PO records **pass / fail / more evidence needed** in #26 with the participant table and experienced-reader observations. These thresholds govern M1 acceptance; they no longer block beginning M2–M4 implementation. Outstanding blockers prevent a passing pilot/acceptance decision. An approved demo recording cannot substitute for a passing pilot. Do not lower thresholds retrospectively. A changed task/threshold requires a new batch; keep the old report. Separate different application/model versions rather than pooling results to pass; a new batch still needs N=5–8. These are operating thresholds for a small discovery pilot, not market-wide evidence.

Measure completed screenplay drafts and export only when Milestones 3 and 4 are available. Generation counts and AI scores do not demonstrate success.

## Engineering Priorities

Keep the existing Harness and domain assets as the foundation. Add persistence, contracts, and checks as required by each milestone. Reliability work, including error handling and pilot access, should support the writing journey.

The [reduced harness plan](plans/harness-improvement.md) closes the remaining #7 work, validates the existing journey and defines the handoff to scene-outline and screenplay features. Keep rejected prompt trials as evidence; do not keep optimizing story-plan critique as a separate product. Integrate only a useful narrow fix for a confirmed failure. Source IDs, repair checks, new cases and timing measurements are tools for that failure, not an eight-project delivery sequence. Respect the stopping point and unchanged acceptance conditions above.

Keep snapshots, revision checks, unsaved buffers, history, both recovery paths and legacy compatibility. Invalid references cannot become verified edit links or acquire current context. All demo/pilot thresholds remain unchanged. Plan–screenplay revision in both directions remains a later author-approved direction. This roadmap update aligns the documented order with the delivered workflow; it does not authorize deployment or record a user acceptance decision.

The [first paired Qwen 3B experiment](evaluations/harness-reference-contract-2026-10-21.md) completed 108 model calls. The snapshot-key prototype remains confined to the evaluation runner: quote-validation acceptance fell, so it has not been promoted to the application workflow.

The [controlled Qwen 3B–7B comparison](evaluations/harness-qwen3b-vs7b-2026-10-22.md) repeated all 108 calls with the 3B request profile and frozen source. On identical fixed drafts, the key-based variant passed reference/quote validation in 28/36 reviews with 7B versus 7/36 with 3B. These are technical acceptance counts; semantic errors persisted and latency increased. The runtime changed its critic contract during the experiment; these results describe the historical contract and do not validate the current runtime.

Dynamic domain discovery, additional providers, RAG, multi-agent orchestration, streaming, and architecture refactoring are not prerequisites; revisit them only when a demonstrated product need justifies the work.

## Outside This Roadmap

- Filming preparation, shooting schedules, and crew management.
- Shooting, AI video, synthetic actors, generated footage, editing, post-production, and screenings.
- Automatic expansion into feature films or television series, or producer matchmaking.
- Other creative domains such as marketing, games, books, or educational storytelling.
- Payment and account-management features beyond access needed for a pilot.

Feature and television screenwriting are conditional future research within the export boundary, not current delivery commitments. A successful short film does not need to become a longer work.


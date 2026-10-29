# Phase 6 local-model smoke — 29 October 2026

One synthetic brief, Ollama `qwen2.5:7b`, temperature 0.3, num_ctx 16384, local SQLite/dataset only. No OpenAI calls, no private author material, no model-output retry or prompt repair loop. The run was paused for clarification and resumed from its checkpoint; no received output was generated again.

`profile.json` records the intended stage thresholds and maximum 10 calls / 600 seconds for starting new work. `calls.json` retains actual per-call timeout, elapsed time, input and output, including the initial reasoning call's 90-second timeout (the expected clarification threshold is 45 seconds, and observed time was 12.862 seconds). This smoke measures observed latency; it is not proof that every timeout boundary is enforced at its target threshold. The overall guard stops starting calls after the budget; an in-flight call can finish later.

Five calls: reasoning 12.862s, planning 39.175s, plan evaluation 15.007s, outline 13.352s, screenplay generation 17.221s. Model time sums to 97.617s; active pipeline execution was 98.025s, excluding the deliberate human pause before continuing. Do not interpret this as a universal full-pipeline latency guarantee.

The provider returned one scene within the author's “at most two” constraint. The letter remained unopened, with no dialogue forced into the silent scene. The mentor still asked whether the letter would be opened, despite the brief specifying it; this is retained as an unnecessary clarification. Awkward wording (“mưa phù phù”) also remains for reader review. Structured output does not establish creative quality.

The run reached `ready` with `review_error`: the existing context budget rejected screenplay review before a model request. Plan and scene text stayed durable. Adoption, selection and PDF each returned 200. `result.json` retains this error and candidate; `screenplay.pdf` was rendered and visually checked. This is **not** a passed full AI-review round. Independent-reader/pilot acceptance and the context limitation remain open.

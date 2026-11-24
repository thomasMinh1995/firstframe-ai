# QA-01 — context guard and target-model review

29 October 2026. Branch feat/qa01-review-context, from dev df9fe53 (PR #75).

## Change and scope

The exact phase-6 synthetic candidate previously required **12,430 UTF-8 bytes** (instructions + strict JSON schema + source payload), exceeding the unchanged **11,776-byte conservative bound** at num_ctx=16384. num_ctx is measured in tokens, while this application intentionally uses a stricter byte upper bound without a model tokenizer. This is not a measured token count and cannot establish whether the old prompt would have fit Ollama.

The final request uses **11,450 bytes**. JSON separators remove whitespace; the prompt removes repeated role/source/evidence explanations. The original three-step constraint-first priority, optional suggestions and consistency instructions remain. All 25 source texts, labels, categories and target/kind metadata remain, with exact quotes checked as before. No source truncation, summary, tokenizer dependency, guard bypass or automatic retry was added. Larger requests still fail safely before sending AI.

Prompt version is screenplay-review-v6-compact in both manual and automatic review; draft_workflow now imports the shared version. Ollama screenplay review/generation explicitly set num_predict=4096 to enforce the output room already reserved by the guard. Existing length-output rejection remains. Other Ollama stages retain their existing settings.

## Frozen local-model evaluation

qwen2.5:7b, temperature 0.3, num_ctx 16384, num_predict 4096, timeout 60s/call. Separate temporary SQLite and datasets; no live author material, OpenAI calls or model retries. Exactly eight calls: original saved candidate, a letter-opening contradiction, then the six frozen M3 compliant/violating fixtures. See calls.json for complete system instructions, inputs, raw responses, actual token counts and timings; results.json retains saved reviews, errors and unchanged-screenplay checks.

| Case | Request bytes | Prompt tokens | Output tokens | Seconds | API status |
| --- | ---: | ---: | ---: | ---: | ---: |
| original | 11450 | 2657 | 224 | 14.858 | 502 |
| contradiction | 11348 | 2635 | 185 | 10.899 | 502 |
| open-ending-compliant | 8253 | 1888 | 211 | 10.462 | 502 |
| open-ending-violating | 8314 | 1898 | 205 | 11.56 | 502 |
| free-choice-compliant | 8177 | 1860 | 203 | 14.367 | 502 |
| free-choice-violating | 8180 | 1856 | 226 | 21.28 | 502 |
| broken-flashlight-compliant | 8375 | 1892 | 204 | 28.721 | 200 |
| broken-flashlight-violating | 8362 | 1891 | 164 | 21.903 | 200 |

**Context transport: 8/8 sent, no context rejection, no output cut; all 8 screenplay snapshots unchanged.** Total observed model-call time 134.05s; every call finished within 60s. This measures review only, not a fresh full-pipeline latency guarantee.

**Review reliability: FAIL release acceptance.** Six responses failed exact-source evidence validation and correctly returned HTTP 502. Two passed structural validation: broken-flashlight-violating identified the explicit impossible light source, but broken-flashlight-compliant incorrectly classified use of permitted street light as an intent conflict. Exact quotes do not certify a true contradiction. Some failed outputs also switched to English despite response_language=Vietnamese. No validator was relaxed, quote remapped or output rewritten to conceal these failures. Only the context-blocked portion is resolved for this corpus; QA-01 remains open for model reliability and independent human/device checks.

The earlier two-call compact-prompt experiment is retained with both failures at ../qa01-review-context-qwen7b-2026-10-29/. It rewrote more guidance; the final prompt restores the existing priority/consistency wording. These are development iterations, not retries inside the product; all ten received outputs are retained.

## Reproduce

From repository root with backend dependencies and local Ollama qwen2.5:7b installed:

    PYTHONPATH=backend python backend/scripts/check_review_context.py --output /tmp/qa01-context-new-run

Choose a new output directory (existing directories are never overwritten). The script permits at most eight calls, timeout 60s each, isolated storage and no retries. It exits nonzero if an API review fails. Exit zero still requires semantic human reading; structural success is not release approval.

Automated regression: from backend/, run python -m pytest -q. **559 passed, 1 skipped.** The retained candidate fits without mutating/dropping source data; small-context and long ASCII/Vietnamese requests still reject before AI. Provider tests assert the output cap only applies to guarded screenplay stages; existing malformed/length response, provenance, history, review and draft checkpoint tests pass. Frontend code is unchanged; its prior phase-6 checks are recorded in ../../testing/phase6-workflow-acceptance-2026-10-29.md.

Ollama documents token-based num_ctx, num_predict and prompt_eval_count at https://github.com/ollama/ollama/blob/main/docs/api.md and https://github.com/ollama/ollama/blob/main/docs/openapi.yaml .

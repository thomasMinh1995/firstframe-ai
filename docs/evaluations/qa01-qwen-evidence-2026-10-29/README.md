> Cập nhật review cuối: xem [bản sửa v8 và hai lượt 10 ca](../qa01-qwen-review-v8-2026-10-29/README.md). Báo cáo v7 dưới đây giữ nguyên kết quả lịch sử.

# QA-01 — grounded evidence and Qwen review accuracy

29 October 2026. Branch `feat/qa01-qwen-review-evidence`, from `dev` at `d9698f1` (PR #76).

**Partial implementation; release acceptance FAIL.** Evidence transport is fixed and the frozen-corpus result improves, but one semantic false accusation remains. This is a draft for review, not a completed QA-01 or a release recommendation.

## Implementation

- The model selects supplied excerpt IDs instead of reproducing quotes. Backend extracts exact text and canonical IDs from the saved snapshot; it never searches for a different source, repairs an invented quote, or changes the author’s text. Excerpts are at most 1,000 characters; all target/author text is retained within the scoped request, including long-block tails.
- A dynamic schema requires a check for **every target text excerpt**. Heading, speaker, neighboring-scene and author IDs cannot occupy a target check. Unknown/missing checks, unknown author IDs, quote-shaped legacy model output, blank conflict explanations and conflicts without author evidence fail validation. Valid references still do not establish that an interpretation is true.
- Only literal screenplay/neighboring text and confirmed author choices are sent for this comparison. Unconfirmed plan/AI background is excluded from the model request; the full source snapshot remains saved and readable. Idea, constraints, answers and confirmed M2 decisions remain eligible author evidence. This is intentional context scoping, not deletion or conversion of AI proposals into author intent.
- Conflicts take priority over secondary craft notes. The public six-note limit remains; complete model checks stay in the recorded output. Public review fields and prior reviews remain compatible; a v6 review reopens without a model call or rewriting.
- Ollama review uses temperature **0.0**; generation retains the configured temperature (0.3 in these runs). Metadata records the review override. The existing context bound and `num_predict=4096` remain. Target text repeated in schema descriptions counts against the unchanged conservative budget; sufficiently long requests still reject safely before AI. A request deadline now caps review at 60 seconds, bounds the provider timeout and rejects a late result; no automatic retry or additional verification call ships.

`screenplay-review-v7-evidence-selection` is shared by manual and automatic review through the existing prompt-version import. The prompt’s output language is also supplied directly in system instructions. [Ollama recommends temperature 0 for more deterministic structured output](https://ollama.com/blog/structured-outputs); this does not guarantee semantic accuracy.

## Frozen evaluation

The same eight synthetic cases retained from phase 6 and M3: original, letter-opening contradiction, and compliant/violating pairs for open ending, freedom to leave and broken flashlight. These are **development fixtures, not a held-out benchmark**. Separate SQLite/dataset storage, local `qwen2.5:7b` only, no OpenAI calls. Exact model digest, quantization, template, Ollama version and settings are in `model-info.json`.

| Check | Prior v6 eight-case run | Final run 1 | Final run 2 |
| --- | ---: | ---: | ---: |
| API review ready | 2/8 | 8/8 | 8/8 |
| No context rejection or output cut | 8/8 sent | 8/8 | 8/8 |
| Scene-level conflict yes/no matches annotation | Insufficient: six API failures | 8/8 | 8/8 |
| Usable case: API + exact relevant evidence pair + no public CJK prose | **1/8** | **7/8** | **7/8** |
| Spurious extra conflict on allowed streetlight passage | Present in compliant case | Present in violating case | Present in violating case |
| Author screenplay unchanged | 8/8 | 8/8 | 8/8 |

Final run 1: eight calls, 80.914 seconds total, maximum call 14.636 seconds. Final run 2: eight calls, 77.061 seconds total, maximum call 13.190 seconds. Each review uses one call. These are observed review latencies, not a whole-pipeline performance guarantee. The final evaluator exits **1**, correctly retaining the failing flashlight case.

`run-1/` and `run-2/` retain system instructions, schema, scoped inputs, options, raw model responses, token counts, saved reviews and summaries. Run 1 was captured before the evaluator required evidence-pair matching; it is re-scored with the same final annotations, preserving original gate fields. One annotation was corrected to accept both the explicit non-coercion rule and the daughter’s agency as valid grounds for the passport violation; both are author requirements. No production validation rule was weakened. `expectations.json` documents accepted exact target/author quotes.

## Remaining failures — do not close QA-01

The violating flashlight scene contains both an allowed streetlight action and an impossible working broken flashlight. The model correctly finds the latter, but also accuses the allowed action. A scene-level “conflict found” metric hid this error; the new evaluator rejects **any** conflict note that points to the wrong target/rule pair, even if another note identifies the real violation.

Public prose also remains unreliable: the open-ending compliant scene receives praise/compliance as a craft concern, and some impacts name the wrong numbered constraint or a different constraint. Correct IDs and exact quotes do not certify observation/impact/suggestion. No text was rewritten to conceal these outputs. Absence of CJK characters is only a narrow corpus check, not complete Vietnamese-language or creative-quality validation.

Release still needs these semantic/prose errors fixed on an independent corpus, plus independent-reader/pilot, real IME, screen reader and device/Safari evidence from the phase-6 acceptance plan.

## Development evidence and rejected approaches

`development-attempts.json` retains **77 calls** from discarded or earlier variants, including failed source selection, per-author checks that missed target passages, and JSON mode. The two temperature-0.3 target-block runs showed why a scene-level yes/no metric was insufficient. A separate verifier experiment added calls but did not remove the spurious streetlight accusation and introduced mixed-language prose; it is not shipped. One JSON-mode experiment began while the preceding experiment was finishing; its timings are not used as latency evidence. The two final runs were sequential.

Together with the 16 final calls, **all 93 development/final received outputs are retained**. These were explicit development experiments; there is no in-product prompt-repair loop, model retry or automatic edit.

## Regression and reproduction

**598 backend passed, 1 skipped**, with the existing TestClient/httpx deprecation warning. Tests cover forged/wrong-role IDs, missing checks, no evidence relocation, exact long-block excerpts, immutable snapshots, v6 reopening, bounded notes, deadline rejection, provider timeout caps and replay of all 16 final raw outputs. Replay tests protect transport/source behavior; they do not certify those retained model interpretations. The separate evaluator tests catch the real wrong-passage case and unknown references. Frontend code is unchanged; browser/device acceptance remains in the phase-6 report. Repository has no configured GitHub Actions CI.

From repository root, using the backend Python environment with local Ollama available:

    PYTHONPATH=backend python backend/scripts/check_review_context.py --output /tmp/qa01-qwen-new-run

Use a new output directory; existing evidence is never overwritten. Maximum eight calls, no retries, isolated storage. The command exits nonzero on API failure, source mutation, wrong conflict classification, wrong evidence pair or unexpected CJK in this Vietnamese corpus. Exit zero still requires independent semantic reading; it is not release approval.

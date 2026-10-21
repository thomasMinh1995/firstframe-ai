# Recorded local demo

`datasets/kitchen-waiting.jsonl` is an unchanged JSONL export of three real local
operations: analysis, planning/evaluation, and review of an edited ending.

- Source: the synthetic Vietnamese kitchen-waiting test used while verifying
  automatic dataset export.
- Provider/model: `ollama / qwen2.5:3b`.
- It contains no real user's private project or API credentials.
- Quality status remains `unreviewed`. Model outputs, including mistakes and
  mixed-language feedback, are preserved rather than presented as curated answers.

The demo catalog reads this file alongside the user's exported recordings when
`DEMO_DATASET_DIR` is empty. No model or dataset import is needed. Use the `/demo`
page to step through the recording. The demo never writes to this file or to the
normal project/dataset stores.

To demo another export collection exclusively, set `DEMO_DATASET_DIR` to its
absolute directory. JSON files, `runs/*.json`, and JSONL exports are supported.
See `docs/datasets.md` for record format, matching, and quality labels.

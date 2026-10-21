"""Replay recorded synthetic inputs with paired seeds; never writes project/review stores."""

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import httpx

from app.application.ai_provider import StructuredRequest, strict_json_instructions
from app.application.dataset_corrections import OUTPUT_MODELS
from app.application.workflow import compact_qwen_planning_input

PROMPTS = Path(__file__).resolve().parents[2] / "domains/short-film/prompts/ollama-qwen2.5-3b"
NAMES = {"reasoning": "story_mentor", "planning": "story_planner", "evaluation": "script_critic"}


def text_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from text_values(item)


def indicators(output):
    # These are screening signals, not an artistic-quality score or a language detector.
    strings = [re.sub(r"\[[^\]]+\]", "", text).lower() for text in text_values(output)]
    grams = [
        tuple(words[index : index + 4])
        for text in strings
        for words in [re.findall(r"\w+", text)]
        for index in range(len(words) - 3)
    ]
    english = re.findall(
        r"\b(?:the|and|would|should|character|story|scene|clear|emotional)\b", " ".join(strings)
    )
    return {
        "repeated_4gram_fraction": round(1 - len(set(grams)) / len(grams), 4) if grams else 0,
        "english_marker_hits": len(english),
        "text_words": sum(len(re.findall(r"\w+", text)) for text in strings),
    }


def compare(
    dataset: Path,
    destination: Path,
    seeds: list[int],
    base_url: str,
    stages=None,
    variants_to_run=None,
):
    if destination.exists():
        raise ValueError("Output already exists; choose a new path to preserve previous results.")
    if dataset.suffix == ".jsonl":
        records = [
            json.loads(line)
            for line in dataset.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        records = [json.loads(dataset.read_text(encoding="utf-8"))]
    report = {
        "model": "qwen2.5:3b",
        "provider": "ollama",
        "temperature": 0.3,
        "num_ctx": 16384,
        "seeds": seeds,
        "source_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "scope": "Paired step replay: same recorded author context/draft/schema/seeds; after planning omits long domain references. Critic stays unchanged. Not an end-to-end quality score.",
        "runs": [],
    }
    for record in records:
        if record["status"] != "completed":
            continue
        for index, step in enumerate(record["steps"]):
            stage = step["stage"]
            if stages and stage not in stages:
                continue
            model = OUTPUT_MODELS[stage]
            request = step["request"]
            if request["response_schema"] != model.model_json_schema():
                raise ValueError(
                    "Recorded schema differs from current schema; do not compare silently."
                )
            prompt_path = PROMPTS / f"{NAMES[stage]}_prompt.md"
            if stage == "evaluation":
                prompt_path = PROMPTS.parent / f"{NAMES[stage]}_prompt.md"
            candidate = StructuredRequest(
                instructions=prompt_path.read_text(encoding="utf-8").strip(),
                input_text=compact_qwen_planning_input(request["input_text"])
                if stage == "planning"
                else request["input_text"],
                response_model=model,
                stage=stage,
            )
            for seed_index, seed in enumerate(seeds):
                variants = [
                    ("before", request["effective_instructions"]),
                    ("after", strict_json_instructions(candidate)),
                ]
                # Alternate order to reduce first-call warm-up bias.
                for variant, instructions in variants[:: 1 if seed_index % 2 == 0 else -1]:
                    if variants_to_run and variant not in variants_to_run:
                        continue
                    input_text = (
                        candidate.input_text if variant == "after" else request["input_text"]
                    )
                    row = {
                        "run_id": record["run_id"],
                        "operation": record["operation"],
                        "step_index": index,
                        "stage": stage,
                        "seed": seed,
                        "variant": variant,
                        "changed": instructions != request["effective_instructions"]
                        or input_text != request["input_text"],
                        "instructions": instructions,
                        "input_text": input_text,
                        "input_sha256": hashlib.sha256(input_text.encode()).hexdigest(),
                        "prompt_sha256": hashlib.sha256(instructions.encode()).hexdigest(),
                        "response_schema": request["response_schema"],
                        "original_dataset_output": step["output"],
                    }
                    started = time.monotonic()
                    try:
                        response = httpx.post(
                            base_url.rstrip("/") + "/api/chat",
                            json={
                                "model": report["model"],
                                "stream": False,
                                "messages": [
                                    {"role": "system", "content": instructions},
                                    {"role": "user", "content": input_text},
                                ],
                                "format": request["response_schema"],
                                "options": {"temperature": 0.3, "num_ctx": 16384, "seed": seed},
                            },
                            timeout=180,
                            trust_env=False,
                        )
                        response.raise_for_status()
                        payload = response.json()
                        if not isinstance(payload, dict):
                            raise TypeError("Invalid response envelope")
                        row["actual_model"] = payload.get("model")
                        message = payload.get("message")
                        row["raw_output"] = (
                            message.get("content") if isinstance(message, dict) else None
                        )
                        if (
                            not payload.get("done")
                            or payload.get("error")
                            or payload.get("done_reason") == "length"
                        ):
                            raise ValueError("Incomplete response")
                        output = model.model_validate_json(row["raw_output"]).model_dump(
                            mode="json"
                        )
                        row.update(status="completed", output=output, indicators=indicators(output))
                    except (httpx.HTTPError, ValueError, TypeError, KeyError) as error:
                        row.update(status="failed", error_type=type(error).__name__)
                    row["duration_seconds"] = round(time.monotonic() - started, 2)
                    report["runs"].append(row)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    temporary = destination.with_suffix(".tmp")
                    temporary.write_text(
                        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                    )
                    temporary.replace(destination)
                    print(
                        f"{record['operation']}/{stage} seed={seed} {variant}: "
                        f"{row['status']} {row['duration_seconds']}s {row.get('indicators', {})}",
                        flush=True,
                    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 73])
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--stages", nargs="+", choices=list(NAMES))
    parser.add_argument("--variants", nargs="+", choices=["before", "after"])
    args = parser.parse_args()
    compare(args.dataset, args.output, args.seeds, args.base_url, args.stages, args.variants)

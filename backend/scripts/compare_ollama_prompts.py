"""Replay recorded synthetic inputs with paired seeds; never writes project/review stores."""

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

import httpx

from app.application.ai_provider import (
    MalformedProviderResponseError,
    StructuredRequest,
    strict_json_instructions,
)
from app.application.dataset_corrections import OUTPUT_MODELS
from app.application.workflow import (
    _EvaluationOutput,
    _feedback_language_header,
    _is_vietnamese_language,
    compact_qwen_planning_input,
)

PROMPTS = Path(__file__).resolve().parents[2] / "domains/short-film/prompts/ollama-qwen2.5-3b"
CRITIC_CANDIDATE = (
    Path(__file__).resolve().parents[2]
    / "demo/evaluations/prompts/qwen-critic-candidate-2026-10-21.md"
)
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


def compact_qwen_evaluation_input(input_text: str) -> str:
    # Decode whole JSON values so headers inside author text cannot cut the draft/context.
    header, separator, remainder = input_text.partition("\n\nCreator intent and decisions:\n")
    if not separator:
        return input_text
    try:
        creator, end = json.JSONDecoder().raw_decode(remainder)
        remainder = remainder[end:]
        marker = "\n\nCurrent draft (JSON data):\n"
        if not remainder.startswith(marker):
            return input_text
        draft, end = json.JSONDecoder().raw_decode(remainder[len(marker) :])
        if not remainder[len(marker) + end :].startswith("\n\nShort-film story rubric:\n"):
            return input_text
    except ValueError:
        return input_text
    rubric = {
        "story_clarity": "Hiểu tình huống và sự tiếp nối của các chi tiết.",
        "character": "Nhân vật thể hiện qua hành vi, kể cả im lặng.",
        "conflict": "Sức căng phù hợp hình thức; chờ đợi cũng có thể đủ.",
        "emotional_impact": "Chi tiết tạo cảm xúc tác giả muốn.",
        "ending": "Hiệu quả kết tác giả chọn, kể cả kết mở.",
        "production_feasibility": "Tôn trọng giới hạn quay đã nêu; chưa biết thì không đoán.",
    }
    return (
        f"{header}\n\nCurrent draft (JSON data):\n"
        f"{json.dumps(draft, ensure_ascii=False)}\n\n"
        "Rubric: số nguyên 1–5; 1 chưa hoạt động, 3 dùng được, 5 rất rõ và phù hợp.\n"
        f"{json.dumps(rubric, ensure_ascii=False)}\n\n"
        f"Creator intent and decisions:\n{json.dumps(creator, ensure_ascii=False)}\n\n"
        "Chỉ báo vấn đề có bằng chứng trái lựa chọn trên, tự mâu thuẫn hoặc vượt giới hạn. "
        "Nếu không có, weaknesses=[] và suggestions=[], passed=true. "
        "Không đòi biến cố, lời thoại hoặc lời giải khi tác giả đã chọn không có. "
        "Mọi góp ý dùng Target response language ở đầu."
    )


def validate_qwen_feedback_pairs(output: _EvaluationOutput, section_titles: set[str]) -> None:
    def anchor(text: str) -> str | None:
        if not text.startswith("[") or "]" not in text:
            return None
        title, _, body = text[1:].partition("]")
        return title if body.strip(" :;-") else None

    pairs = zip(output.weaknesses, output.suggestions)
    if len(output.weaknesses) != len(output.suggestions) or any(
        anchor(weakness) not in section_titles or anchor(weakness) != anchor(suggestion)
        for weakness, suggestion in pairs
    ):
        raise MalformedProviderResponseError(
            "Qwen critic returned unmatched feedback pairs.", raw_output=output.model_dump_json()
        )


def compare(
    dataset: Path,
    destination: Path,
    seeds: list[int],
    base_url: str,
    stages=None,
    variants_to_run=None,
    experimental_critic=False,
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
        "experimental_critic": experimental_critic,
        "source_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "scope": "Paired step replay: same author context/draft/schema/seeds; after planning omits long domain references; after evaluation updates the language contract and selects the full target-language critic prompt. Experimental critic changes prompt and uses a compact rubric only when explicitly enabled. Not an end-to-end quality score.",
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
                language_header = request["input_text"].split("\n", 1)[0]
                prefix = "Target response language: "
                language = language_header.removeprefix(prefix).strip()
                if not language_header.startswith(prefix) or not language:
                    raise ValueError("Evaluation input is missing its target response language.")
                critic_name = (
                    "script_critic_vi"
                    if _is_vietnamese_language(language)
                    else "script_critic"
                )
                prompt_path = (
                    CRITIC_CANDIDATE
                    if experimental_critic
                    else PROMPTS.parent / f"{critic_name}_prompt.md"
                )
            candidate_input = request["input_text"]
            if stage == "evaluation" and not experimental_critic:
                _, separator, body = candidate_input.partition("\n\nCreator intent and decisions:\n")
                if not separator:
                    raise ValueError("Evaluation input is missing its creator-context boundary.")
                candidate_input = (
                    _feedback_language_header(language) + "Creator intent and decisions:\n" + body
                )
            if stage == "evaluation" and not experimental_critic:
                raise ValueError(
                    "The live critic uses a grounded contract. Use check_author_roles.py; "
                    "legacy critic comparisons require --experimental-critic."
                )
            candidate = StructuredRequest(
                instructions=prompt_path.read_text(encoding="utf-8").strip(),
                input_text=compact_qwen_planning_input(request["input_text"])
                if stage == "planning"
                else compact_qwen_evaluation_input(request["input_text"])
                if stage == "evaluation" and experimental_critic
                else candidate_input,
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
                        if stage == "evaluation":
                            try:
                                draft, _ = json.JSONDecoder().raw_decode(
                                    request["input_text"].split("Current draft (JSON data):\n", 1)[
                                        1
                                    ]
                                )
                                validate_qwen_feedback_pairs(
                                    _EvaluationOutput.model_validate(output),
                                    {section["title"] for section in draft["sections"]},
                                )
                                row["feedback_pairs_valid"] = True
                            except (
                                ValueError,
                                KeyError,
                                IndexError,
                                MalformedProviderResponseError,
                            ):
                                row["feedback_pairs_valid"] = False
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
    parser.add_argument(
        "--experimental-critic",
        action="store_true",
        help="Evaluate the rejected critic candidate; never changes application behavior.",
    )
    args = parser.parse_args()
    compare(
        args.dataset,
        args.output,
        args.seeds,
        args.base_url,
        args.stages,
        args.variants,
        args.experimental_critic,
    )

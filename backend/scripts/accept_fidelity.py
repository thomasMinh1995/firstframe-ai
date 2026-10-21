"""Run a frozen, labeled fidelity suite without opening project data or training stores."""
import argparse
import hashlib
import json
import time
from pathlib import Path

from app.application.fidelity import (
    EvidenceIssue,
    audit_suggestions,
    cited_check,
    scan_fidelity,
)
from app.application.language import resolve_response_language
from app.infrastructure.ollama_provider import OllamaProvider, OllamaProviderConfig

ROOT = Path(__file__).resolve().parents[2]


class RecordedProvider:
    def __init__(self, provider):
        self.provider = provider
        self.steps = []

    @property
    def metadata(self):
        return self.provider.metadata

    def request_structured(self, request):
        step = {"stage": request.stage, "input": json.loads(request.input_text),
                "instructions": request.instructions,
                "schema": request.response_model.model_json_schema()}
        self.steps.append(step)
        start = time.monotonic()
        try:
            result = self.provider.request_structured(request)
            step.update(output=result.output.model_dump(), model=result.model)
            return result
        except Exception as error:
            step.update(error=type(error).__name__, raw_output=getattr(error, "raw_output", None))
            raise
        finally:
            step["duration_ms"] = round((time.monotonic() - start) * 1000)


def score_case(case, scan, report, steps):
    expected = case["expected"]
    detected = scan.status == expected["scan"]
    if expected["scan"] == "issues":
        detected = detected and any(
            i.draft_quote == case["candidate"]["draft_quote"]
            and i.author_quote == case["candidate"]["author_quote"] for i in scan.issues
        )
    audit = next(s["output"] for s in steps if s["stage"] == "fidelity_audit")
    approved = any(c.suggestion_status == "supported" for c in report.checks)
    dimensions = {k: audit[k] == expected[k] for k in ("relation", "concern", "revision")}
    return {"scan_correct": detected, "audit_dimensions": dimensions,
            "approval_correct": approved == expected["allow_revision"],
            "unsafe_approval": approved and not expected["allow_revision"],
            "all_labels_match": detected and all(dimensions.values())
            and approved == expected["allow_revision"]}


def summarize_run(cases, rows):
    """Label metrics are provisional; they cannot certify explanations or language."""
    by_id = {r["case_id"]: r for r in rows}
    counts = {}
    for split in ("all", "development", "holdout"):
        selected = [c for c in cases if split == "all" or c["split"] == split]
        positive = [c for c in selected if c["expected"]["scan"] == "issues"]
        compatible = [c for c in selected if c["expected"]["scan"] == "clear"]
        usable = [c for c in selected if c["expected"]["allow_revision"]]

        def matched(case, metric):
            return by_id.get(case["id"], {}).get("scores", {}).get(metric, False)

        counts[split] = {
            "cases": len(selected),
            "errors_or_missing": sum("scores" not in by_id.get(c["id"], {}) for c in selected),
            "scan_label_and_anchor_matches": sum(matched(c, "scan_correct") for c in selected),
            "conflict_matches": sum(matched(c, "scan_correct") for c in positive),
            "conflict_cases": len(positive),
            "compatible_matches": sum(matched(c, "scan_correct") for c in compatible),
            "compatible_cases": len(compatible),
            "false_conflicts": sum(by_id.get(c["id"], {}).get("scan", {}).get("status") == "issues"
                                   for c in compatible),
            "valid_repairs_approved": sum(matched(c, "approval_correct") for c in usable),
            "valid_repair_cases": len(usable),
            "unsafe_approvals": sum(matched(c, "unsafe_approval") for c in selected),
            "all_label_matches": sum(matched(c, "all_labels_match") for c in selected),
            "audit_dimensions": {k: sum(by_id.get(c["id"], {}).get("scores", {})
                                        .get("audit_dimensions", {}).get(k, False)
                                        for c in selected)
                                 for k in ("relation", "concern", "revision")},
        }
    total = counts["all"]
    coverage = (len(rows) == len(by_id) == len(cases)
                and set(by_id) == {c["id"] for c in cases} and not total["errors_or_missing"])
    gates = {
        "complete_without_errors": coverage,
        "conflict_label_recall_90pct": bool(total["conflict_cases"]) and
            total["conflict_matches"] / total["conflict_cases"] >= .9,
        "compatible_label_accuracy_90pct": bool(total["compatible_cases"]) and
            total["compatible_matches"] / total["compatible_cases"] >= .9,
        "valid_repair_acceptance_90pct": bool(total["valid_repair_cases"]) and
            total["valid_repairs_approved"] / total["valid_repair_cases"] >= .9,
        "no_unsafe_approval": coverage and total["unsafe_approvals"] == 0,
    }
    return {"counts": counts, "provisional_gates": gates,
            "acceptance": "pending_PO_semantic_and_language_review" if all(gates.values())
            else "failed_provisional_gates",
            "note": "Classification and source matching only; reasons can still be wrong."}


def run_suite(source, destination, provider, split="all", case_id=None):
    suite_bytes = source.read_bytes()
    suite = json.loads(suite_bytes)
    prompts = ROOT / "domains/short-film/prompts"
    scan_prompt = (prompts / "fidelity_prompt.md").read_text()
    audit_prompt = (prompts / "fidelity_audit_prompt.md").read_text()
    # Exclusive creation prevents a later run from replacing unfavorable evidence.
    with destination.open("x", encoding="utf-8") as output:
        for case in suite["cases"]:
            if (split != "all" and case["split"] != split) or (case_id and case["id"] != case_id):
                continue
            recorder = RecordedProvider(provider)
            row = {"case_id": case["id"], "split": case["split"],
                   "suite_sha256": hashlib.sha256(suite_bytes).hexdigest(),
                   "label_status": suite["label_status"], "expected": case["expected"],
                   "steps": recorder.steps, "model_config": provider.metadata.parameters,
                   "language_review": "pending_human", "semantic_reason_review": "pending_human"}
            try:
                language = resolve_response_language(case["author"].get("idea", ""), case["language"])
                scan, checks = scan_fidelity(recorder, scan_prompt, case["draft"],
                                             case["author"], language)
                row["scan"] = scan.model_dump()
                row["scan_checks"] = [c.model_dump() for c in checks]
                # Fixed candidates test the audit even when the scanner misses the problem.
                original = (cited_check(EvidenceIssue(**case["candidate"]),
                                        case["draft"], case["author"])
                            if case["candidate"]["author_quote"].strip() else None)
                report = audit_suggestions(recorder, audit_prompt, case["draft"],
                                           case["author"], language,
                                           [case["candidate"]], [original] if original else [])
                row["report"] = report.model_dump()
                row["scores"] = score_case(case, scan, report, recorder.steps)
            except Exception as error:  # noqa: BLE001 - record each failed case and continue the suite
                row["error"] = type(error).__name__
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
            output.flush()
            print(case["id"], row.get("scores", row.get("error")), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path,
                        default=ROOT / "demo/evaluations/fidelity-suite/cases.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=["all", "development", "holdout"], default="all")
    parser.add_argument("--case-id", help="Replay a harness failure into a new file; keep prior evidence")
    args = parser.parse_args()
    run_suite(args.cases, args.output, OllamaProvider(OllamaProviderConfig("qwen2.5:3b")), args.split,
              args.case_id)

    cases = json.loads(args.cases.read_text())["cases"]
    selected = [c for c in cases if (args.split == "all" or c["split"] == args.split)
                and (not args.case_id or c["id"] == args.case_id)]
    rows = [json.loads(line) for line in args.output.read_text().splitlines()]
    print(json.dumps(summarize_run(selected, rows), ensure_ascii=False, indent=2))

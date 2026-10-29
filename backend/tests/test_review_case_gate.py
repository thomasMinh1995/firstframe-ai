import json
from pathlib import Path

from scripts.check_review_context import evaluate_review

ROOT = Path(__file__).resolve().parents[2] / "docs/evaluations/qa01-qwen-evidence-2026-10-29"


def test_scene_level_conflict_detection_does_not_hide_wrong_target_pair():
    old = json.loads((ROOT / "development-attempts.json").read_text())
    # This real response found a conflict in the violating scene, but blamed
    # the permitted streetlight passage instead of the broken flashlight.
    run = next(r for r in old if r["label"] == "repeat-temperature-0.3")
    row = run["results"][-1]
    sources = json.loads(
        (ROOT.parent / "qa01-review-context-qwen7b-final-2026-10-29/results.json").read_text()
    )[-1]["review"]["sources"]
    target = next(
        s["scene_id"] for s in sources if s["field"] == "text" and s["text"].startswith("Bình bật")
    )
    review = {"notes": row["notes"], "sources": sources, "target_scene_id": target, "question": ""}
    expected = json.loads((ROOT / "expectations.json").read_text())["broken-flashlight-violating"]
    verdict = evaluate_review(review, expected)
    assert verdict["matches_expected_conflict"]
    assert not verdict["matches_expected_evidence"]


def test_unknown_source_is_an_evaluation_failure_not_a_crash():
    review = {
        "notes": [
            {
                "kind": "intent_mismatch",
                "evidence": [{"source_id": "forged", "quote": "x"}],
                "observation": "x",
                "impact": "x",
                "suggestion": "",
            }
        ],
        "sources": [],
        "question": "",
        "target_scene_id": "target",
    }
    verdict = evaluate_review(
        review, {"expected_conflict": True, "target_quote": "x", "author_quotes": ["y"]}
    )
    assert not verdict["matches_expected_evidence"]


def test_foreign_script_in_public_prose_is_flagged_for_this_vietnamese_corpus():
    review = {"notes": [], "sources": [], "question": "符合要求", "target_scene_id": "target"}
    verdict = evaluate_review(
        review, {"expected_conflict": False, "target_quote": None, "author_quotes": []}
    )
    assert verdict["unexpected_cjk"]

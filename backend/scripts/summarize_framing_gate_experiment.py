"""Grade every frozen attempt; never retry, repair model output or change labels."""

import argparse
import json
import statistics
from pathlib import Path

from scripts.run_framing_gate_experiment import decide, verify_freeze, write


def summarize(directory):
    verify_freeze(directory)
    frozen = json.loads((directory / "cases.json").read_text())
    cases = {case["id"]: case for case in frozen["cases"]}
    calls = json.loads((directory / "calls.json").read_text())
    scores = []
    for call in calls:
        case = cases[call["case_id"]]
        gate = call.get("gate", {"action": "incomplete", "can_publish": False})
        # Inspect invalid raw JSON for diagnostics only; never send it back to the gate.
        raw = call.get("output")
        json_valid = raw is not None
        if raw is None:
            try:
                raw = json.loads(call.get("raw_output") or "")
                json_valid = True
            except (ValueError, TypeError):
                raw = None
        predicted = {}
        if isinstance(raw, dict) and isinstance(raw.get("themes"), list):
            for item in raw["themes"]:
                if isinstance(item, dict) and isinstance(item.get("topic_id"), str):
                    predicted.setdefault(item.get("topic_id"), []).append(item.get("stance"))
        correct = {topic: predicted.get(topic) == [stance]
                   for topic, stance in case["expected_stances"].items()}
        scores.append({
            "label": call["label"], "case_id": call["case_id"], "split": case["split"],
            "expected": case["expected_action"], "actual": gate["action"],
            "positive": case["expected_action"] == "block",
            "can_publish": gate["can_publish"], "schema_valid": "output" in call,
            "json_valid": json_valid, "stance_correct": correct,
            "stance_expected": case["expected_stances"], "stance_predicted": predicted,
            "saved_and_edited": call.get("saved_and_edited", False),
            "stale_rejected": call.get("gate_after_edit", {}).get("reason") == "stale_snapshot",
            "warning_present": bool(call.get("warning")),
        })
    summaries = {}
    for split in ["regression", "new", "combined"]:
        rows = [row for row in scores if split == "combined" or row["split"] == split]
        matrix = {key: {action: 0 for action in ["block", "release", "review_required", "incomplete"]}
                  for key in ["should_block", "should_not_block"]}
        for row in rows:
            column = row["actual"] if row["actual"] in {"block", "review_required", "incomplete"} else "release"
            matrix["should_block" if row["positive"] else "should_not_block"][column] += 1
        positives = sum(row["positive"] for row in rows)
        negatives = len(rows) - positives
        fp = sum(not row["positive"] and row["actual"] == "block" for row in rows)
        held = sum(not row["positive"] and not row["can_publish"] for row in rows)
        misses = sum(row["positive"] and row["can_publish"] for row in rows)
        active = {}
        for row in rows:
            for topic, stance in row["stance_expected"].items():
                group = active.setdefault(stance, {"total": 0, "correct": 0})
                group["total"] += 1
                group["correct"] += row["stance_correct"][topic]
        timings = [call["seconds"] for call in calls if "seconds" in call
                   and (split == "combined" or call["split"] == split)]
        summaries[split] = {
            "attempts": len(rows), "positive": positives, "negative": negatives,
            "matrix": matrix, "false_blocks": fp, "false_block_rate": fp / negatives if negatives else None,
            "operational_false_holds": held, "operational_false_hold_rate": held / negatives if negatives else None,
            "missed_releases": misses, "missed_release_rate": misses / positives if positives else None,
            "exact_action_correct": sum(row["expected"] == row["actual"] for row in rows),
            "schema_valid": sum(row["schema_valid"] for row in rows),
            "json_valid": sum(row["json_valid"] for row in rows),
            "save_edit_passed": sum(row["saved_and_edited"] for row in rows),
            "stale_rejected": sum(row["stale_rejected"] for row in rows),
            "active_stance": active,
            "latency": {"min": min(timings), "median": statistics.median(timings), "max": max(timings)} if timings else None,
        }
    by_label = {call["label"]: call for call in calls}
    transitions = []
    for source, target in [("case-02", "case-15"), ("case-11", "case-16"),
                           ("case-05", "case-17"), ("case-11", "case-18")]:
        for repeat in [1, 2]:
            before = by_label.get(f"{source}-{repeat}")
            after = by_label.get(f"{target}-{repeat}")
            if before is None or after is None or "gate" not in after:
                continue
            stale = decide(before.get("output"), before["snapshot"], after["input"])
            transitions.append({"source": source, "target": target, "repeat": repeat,
                                "stale": stale, "fresh": after["gate"],
                                "expected": cases[target]["expected_action"]})
    result = {"splits": summaries, "scores": scores, "transitions": transitions}
    write(directory / "summary.json", result)
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    print(json.dumps(summarize(parser.parse_args().directory), ensure_ascii=False, indent=2))

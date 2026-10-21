"""Compare effective structured outputs without rewriting source recordings."""

from typing import Any

from app.application.dataset_review import OutputVersion


def json_diff(before: Any, after: Any, prefix: str = ""):
    """Compare JSON values, including absent fields and ordered array items."""
    changes = []
    missing = object()

    def compare(left: Any, right: Any, path: str) -> None:
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(left.keys() | right.keys()):
                compare(left.get(key, missing), right.get(key, missing), f"{path}.{key}")
        elif isinstance(left, list) and isinstance(right, list):
            for index in range(max(len(left), len(right))):
                compare(
                    left[index] if index < len(left) else missing,
                    right[index] if index < len(right) else missing,
                    f"{path}[{index}]",
                )
        elif type(left) is not type(right) or left != right:
            changes.append(
                {
                    "path": path,
                    "before_exists": left is not missing,
                    "after_exists": right is not missing,
                    "before": left if left is not missing else None,
                    "after": right if right is not missing else None,
                }
            )

    compare(before, after, prefix)
    return changes


def output_diff(sample: dict[str, Any], before: OutputVersion, after: OutputVersion):
    changes = []
    for index, step in enumerate(sample["steps"]):
        key = str(index)
        changes.extend(
            json_diff(
                before.corrected_outputs.get(key, step.get("output")),
                after.corrected_outputs.get(key, step.get("output")),
                f"steps[{index}].output",
            )
        )
    return changes

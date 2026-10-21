"""Request-local progress notifications for streamed workflows."""

from collections.abc import Callable
from contextvars import ContextVar

progress_listener: ContextVar[Callable[[dict], None] | None] = ContextVar(
    "progress_listener", default=None
)


def report_progress(stage: str, status: str) -> None:
    listener = progress_listener.get()
    if listener is not None:
        listener({"type": "progress", "stage": stage, "status": status})

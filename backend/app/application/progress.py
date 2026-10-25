"""Request-local progress notifications for streamed workflows."""

from collections.abc import Callable
from contextvars import ContextVar
from contextlib import contextmanager

progress_listener: ContextVar[Callable[[dict], None] | None] = ContextVar(
    "progress_listener", default=None
)


def report_progress(stage: str, status: str) -> None:
    listener = progress_listener.get()
    if listener is not None:
        listener({"type": "progress", "stage": stage, "status": status})


@contextmanager
def progress_step(stage: str):
    report_progress(stage, "active")
    try:
        yield
    except Exception:
        report_progress(stage, "failed")
        raise
    else:
        report_progress(stage, "completed")

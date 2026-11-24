"""Bound text requests without silently dropping the author's source."""
from app.application.ai_provider import ProviderRequestError, StructuredProvider, StructuredRequest, strict_json_instructions


SCREENPLAY_OUTPUT_TOKENS = 4096


class ScreenplayContextTooLarge(ProviderRequestError):
    pass


def check_context_budget(request: StructuredRequest, provider: StructuredProvider) -> None:
    # Conservative byte limit, leaving room for a response and chat-template overhead.
    context_limit = provider.metadata.parameters.get("num_ctx", 16384)
    budget = min(12000, max(0, context_limit - SCREENPLAY_OUTPUT_TOKENS - 512)) if isinstance(context_limit, int) else 12000
    if len(request.input_text.encode("utf-8")) + len(strict_json_instructions(request).encode("utf-8")) > budget:
        raise ScreenplayContextTooLarge("Ngữ cảnh vượt giới hạn yêu cầu AI hiện hỗ trợ; chưa gửi AI. Bản tác giả vẫn giữ, bạn có thể tiếp tục tự viết và lưu.")

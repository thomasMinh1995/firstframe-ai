"""A short author-choice framework alongside the model's contextual questions."""

MAX_CHOICES = 20
CHOICE_QUESTIONS = {
    "Vietnamese": (
        "Điều gì bạn nhất định muốn giữ, và không muốn FirstFrame tự thêm vào câu chuyện?",
        "Bạn muốn dừng câu chuyện ở khoảnh khắc nào, hoặc để điều gì còn bỏ ngỏ?",
        "Bạn muốn kể chủ yếu bằng hành động, hình ảnh, lời thoại hay âm thanh?",
        "Bạn muốn người xem mang theo cảm giác gì sau câu chuyện?",
        "Có giới hạn nào về bối cảnh, nhân vật, thời lượng hoặc điều kiện quay cần giữ không?",
    ),
    "English": (
        "What must stay in your story, and what should FirstFrame avoid adding?",
        "At which moment should the story stop, or what should remain open?",
        "Would you tell it mainly through action, images, dialogue, or sound?",
        "What feeling would you like the audience to leave with?",
        "Are there location, cast, duration, or production limits to keep?",
    ),
}


def conversation_questions(proposed, existing, known, language):
    # Keep existing indices stable; only new questions are deduplicated and appended.
    questions = list(existing)
    seen = {" ".join(q.split()).casefold() for q in [*existing, *known]}
    batch_limit = min(MAX_CHOICES, len(existing) + 3) if existing else 6
    for question in [*proposed, *CHOICE_QUESTIONS[language]]:
        question = question.strip()
        key = " ".join(question.split()).casefold()
        if question and key not in seen and len(questions) < batch_limit:
            questions.append(question)
            seen.add(key)
    return questions

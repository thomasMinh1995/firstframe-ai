"""Keep question indices stable without adding a fixed questionnaire."""
MAX_CHOICES = 20


def conversation_questions(proposed, existing, known, language):
    questions = list(existing)
    seen = {" ".join(q.split()).casefold() for q in [*existing, *known]}
    for question in proposed:
        question = question.strip()
        key = " ".join(question.split()).casefold()
        if question and key not in seen and len(questions) < MAX_CHOICES:
            questions.append(question)
            seen.add(key)
    return questions

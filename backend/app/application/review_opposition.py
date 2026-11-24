"""Conservative extractive checks, not a general natural-language inference engine."""

import re
import unicodedata

NEGATION = re.compile(
    r"\b(không|chưa|chẳng|chả|cấm|not|never|cannot|can't|mustn't|won't|forbidden)\b"
)
MODIFIERS = {
    "thể",
    "được",
    "phép",
    "phải",
    "nói",
    "hoặc",
    "xác",
    "nhận",
    "đã",
    "còn",
    "sẽ",
    "đang",
    "nữa",
    "hề",
    "từng",
    "be",
    "been",
    "being",
    "allowed",
    "to",
    "ever",
    "yet",
    "have",
    "has",
    "had",
    "able",
    "may",
    "must",
    "can",
    "will",
    "would",
    "should",
    "say",
    "says",
    "said",
    "that",
    "confirm",
    "confirmed",
    "or",
}
SPEECH = {"nói", "xác", "nhận", "say", "says", "said", "confirm", "confirmed"}
STOP = re.compile(r"\b(và|nhưng|để|vì|mà|còn|hoặc|and|but|because|so|or)\b")


def normalized(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def contains(text, phrase):
    return (
        bool(phrase)
        and re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", normalized(text)) is not None
    )


def negative_claims(text):
    # A subjectless clause can inherit the immediately preceding subject clause.
    for sentence in re.split(r"[;.!?]", normalized(text)):
        previous = ""
        for clause in sentence.split(","):
            for match in NEGATION.finditer(clause):
                before = clause[: match.start()].strip()
                if NEGATION.search(before):
                    continue  # Double/ambiguous negation: abstain.
                rest = clause[match.end() :].strip()
                tokens = rest.split()
                modifiers = []
                while tokens and tokens[0] in MODIFIERS:
                    modifiers.append(tokens.pop(0))
                if not tokens or tokens[0] in {
                    "chỉ",
                    "những",
                    "cần",
                    "muốn",
                    "only",
                    "necessarily",
                    "need",
                    "want",
                }:
                    continue
                predicate = STOP.split(" ".join(tokens), maxsplit=1)[0].strip()
                if not predicate or NEGATION.search(predicate):
                    continue
                prefix = before if before else previous
                yield (
                    predicate,
                    prefix + " " + predicate,
                    bool(set(modifiers) & SPEECH),
                    match.group(),
                    modifiers,
                    prefix,
                )
            previous = clause.strip()


def has_referent(context, other, predicate, characters):
    words = re.findall(r"\w+", context)
    for n in range(min(6, len(words)), 1, -1):
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i : i + n])
            if contains(phrase, predicate) or contains(predicate, phrase):
                continue
            if contains(other, phrase):
                return True
    # Single-word names must also be grounded in the saved character list.
    return any(
        contains(characters, w) and contains(other, w) and not contains(predicate, w)
        for w in words
        if len(w) > 1
    )


def character_mentions(text, characters):
    words = re.findall(r"\w+", text)
    names = set()
    for n in range(min(6, len(words)), 0, -1):
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i : i + n])
            if any(w in {"và", "and"} for w in words[i : i + n]):
                continue
            if contains(characters, phrase):
                names.add(phrase)
    return {
        name
        for name in names
        if not any(name != other and contains(other, name) for other in names)
    }


def positive_scope(text, predicate, negative_context):
    clauses = re.split(r"[;,.!?]", text)
    matches = [i for i, c in enumerate(clauses) if contains(c, predicate)]
    if len(matches) != 1:
        return "", ""
    index = matches[0]
    clause = clauses[index]
    before = re.split(r"(?<!\w)" + re.escape(predicate) + r"(?!\w)", clause, maxsplit=1)[0]
    prefix_words = before.split()
    scope = clause
    # A bare repeated noun can inherit the immediately preceding explicit object.
    # A differently qualified noun (e.g. another compound name) cannot.
    if (
        index
        and 0 < len(prefix_words) <= 2
        and all(contains(negative_context, w) for w in prefix_words)
    ):
        scope = clauses[index - 1] + " " + clause
    return scope, before


def literal_opposition(author_text, target_text, block, characters):
    """Require a whole shared predicate/referent, never a keyword or pronoun guess.

    shortcut: aliases, nonliteral attribute opposition and ambiguous scope abstain;
    add separately validated relation types before widening this scope.
    """
    author = normalized(author_text)
    target = normalized(target_text)
    for predicate, context, speech, _, _, actor_prefix in negative_claims(author):
        if speech and block.kind != "dialogue":
            continue
        if not speech and block.kind == "dialogue":
            continue
        if not contains(target, predicate):
            continue
        if any(
            contains(p, predicate) or contains(predicate, p) for p, *_ in negative_claims(target)
        ):
            continue
        scope, positive_prefix = positive_scope(target, predicate, context)
        if not scope:
            continue
        actors = character_mentions(actor_prefix, characters)
        if actors:
            actual = character_mentions(
                normalized(block.speaker) if speech else positive_prefix, characters
            )
            if len(actors) != 1 or len(actual) != 1 or actors != actual:
                continue
        counterpart = normalized(block.speaker) if speech else scope
        if has_referent(context, counterpart, predicate, characters):
            return True
    # Not-yet doing an event does not contradict a broad plan. Only an explicit
    # denied capability can oppose a confirmed ability/agency choice here.
    if block.kind == "action" and re.search(
        r"\b(tự quyết|quyền|có thể|can|free to|allowed to|decide)\b", author
    ):
        for predicate, context, _, marker, modifiers, _ in negative_claims(target):
            if not (marker in {"cannot", "can't"} or marker == "không" and "thể" in modifiers):
                continue
            if contains(author, predicate) and not any(
                contains(p, predicate) or contains(predicate, p)
                for p, *_ in negative_claims(author)
            ):
                if has_referent(context, author, predicate, characters):
                    return True
    return False

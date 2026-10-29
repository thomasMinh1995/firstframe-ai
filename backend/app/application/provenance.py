"""Attribute changed fields from trusted write paths, never from client labels."""
from app.api.schemas.provenance import TextProvenance


def scene_fields(scenes, screenplay=False):
    fields = {}
    for scene in scenes:
        if screenplay:
            fields[f"script:{scene.id}:heading"] = scene.heading
            for block in scene.blocks:
                for key in ("text", "speaker"):
                    fields[f"block:{block.id}:{key}"] = getattr(block, key)
        else:
            for key, value in scene.model_dump(exclude={"id", "staging_choices"}).items():
                fields[f"m2:{scene.id}:{key}"] = value
            for key, value in scene.staging_choices.items():
                fields[f"m2:{scene.id}:staging:{key}"] = value
    return fields


def draft_fields(draft):
    if draft is None:
        return {}
    return {"title": draft.title, "logline": draft.logline,
            **{f"section:{i}:{key}": getattr(section, key)
               for i, section in enumerate(draft.sections) for key in ("title", "purpose", "content")}}


def attribute_edits(provenance, before, after, ai_fields=None, confirmed=()):
    result = {}
    for key, value in after.items():
        if key in before and before[key] == value:
            if key not in provenance and key not in confirmed:
                continue
            result[key] = provenance.get(key, TextProvenance())
        else:
            ai = ai_fields is not None and key in ai_fields and ai_fields[key] == value
            result[key] = TextProvenance(origin="ai_proposal" if ai else "author_input")
        if key in confirmed:
            result[key] = result[key].model_copy(update={"author_confirmed": True})
    return result


def ai_draft(draft):
    return {key: TextProvenance(origin="ai_proposal") for key in draft_fields(draft)}

"""Resolve explicit scope; never guess a structural change or promote unverified feedback."""
import re
import unicodedata
from fastapi import HTTPException
from app.application.screenplay_review import review_sources

def validate_note(review, note):
    canonical = {s.id:s for s in review_sources(review)}
    refs = []
    for e in note.evidence:
        source = next((s for s in review.sources if s.id == e.source_id), None)
        expected = canonical.get(e.source_id)
        if source is None or expected is None or source != expected or not e.quote.strip() or e.quote not in source.text:
            return False
        refs.append(source)
    return any(s.category == "screenplay" and s.scene_id == review.target_scene_id and s.field == "text" for s in refs) and (note.kind != "intent_mismatch" or any(s.category == "author_choice" for s in refs))



def resolve_target(project, instructions, selected_scene_id=None):
    text = ''.join(c for c in unicodedata.normalize('NFD', instructions.lower().replace('đ','d')) if unicodedata.category(c) != 'Mn')
    script = project.screenplay
    if script is None:
        return {"kind":"clarify", "message":"Hãy mở một bản kịch bản trước.", "scene_id":None, "affected_scene_ids":[]}
    structural = any(word in text for word in ('them canh','xoa canh','bo canh','doi thu tu','sap xep lai','doi ket','thay ket','tat ca canh','toan bo kich ban','add scene','remove scene','delete scene','reorder','change ending','change the ending','all scenes','entire screenplay'))
    if structural:
        return {"kind":"candidate", "message":"Yêu cầu có thể đổi cấu trúc hoặc kết thúc. Tạo candidate riêng để đọc phạm vi ảnh hưởng trước khi nhận.", "scene_id":None, "affected_scene_ids":[s.id for s in script.scenes]}
    ordinals = re.findall(r'(?:canh|scene)\s*(\d+)', text)
    if len(set(ordinals)) > 1 or re.search(r'(?:canh|scene)\s*\d+\s*(?:va|and|,|&|-)\s*\d+', text):
        return {"kind":"clarify", "message":"Hãy chọn một cảnh hoặc một nhóm khối trong cảnh; nhiều cảnh cần candidate riêng.", "scene_id":None, "affected_scene_ids":[]}
    target = selected_scene_id
    if ordinals:
        index = int(ordinals[0])-1
        if index < 0 or index >= len(script.scenes):
            return {"kind":"clarify", "message":"Số cảnh không có trong bản này. Hãy chọn lại.", "scene_id":None, "affected_scene_ids":[]}
        target = script.scenes[index].id
    if not any(s.id == target for s in script.scenes):
        return {"kind":"clarify", "message":"Bạn muốn sửa cảnh nào?", "scene_id":None, "affected_scene_ids":[]}
    return {"kind":"scene", "message":"Chỉ cảnh đã nêu bị thay; các cảnh khác được giữ nguyên.", "scene_id":target, "affected_scene_ids":[target]}


def validate_request(project, request):
    resolved = resolve_target(project, request.instructions, request.target_scene_id)
    if resolved['kind'] != 'scene' or resolved['scene_id'] != request.target_scene_id:
        raise HTTPException(422, resolved['message'] + ' Kiểm tra lại cảnh đích trước khi gửi.')
    target = next(s for s in project.screenplay.scenes if s.id == request.target_scene_id)
    if (request.scope == 'blocks' and (not request.block_ids or len(set(request.block_ids)) != len(request.block_ids)
        or not set(request.block_ids) <= {b.id for b in target.blocks})) or (request.scope == 'scene' and request.block_ids):
        raise HTTPException(422, 'Phạm vi khối không khớp cảnh đã chọn.')
    if bool(request.review_id) != bool(request.note_id):
        raise HTTPException(422, 'Cần cả ID lượt góp ý và ID nhận xét.')
    if request.review_id:
        review = next((r for r in project.screenplay_reviews if r.id == request.review_id), None)
        note = next((n for n in review.notes if n.id == request.note_id), None) if review else None
        if review is None or note is None or review.id not in project.current_screenplay_review_ids or review.target_scene_id != target.id or not validate_note(review,note):
            raise HTTPException(409, 'Góp ý không còn khớp nguồn hoặc chưa đủ bằng chứng để nối thành phương án sửa.')
        return request.instructions + '\nGợi ý để tác giả cân nhắc (không phải kết luận bắt buộc):\n' + note.observation + '\n' + note.suggestion
    return request.instructions

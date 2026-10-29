"use client";
import {useId,useState} from 'react';
import {provenanceLabel} from './provenance';
import type {Project} from './projectsApi';
import type {SceneWritingInput,ScriptScene} from './screenplayTypes';
import {reviewNoteSupported,reviewSourceMatches,sameReviewScript,type ReviewAssessment,type ReviewSource,type ScreenplayReview} from './screenplayReviewTypes';

export function ScreenplayFeedback({project,scene,canNavigate,onReview,onInspect,onDiscard,onAssess,onNavigate}: {
  project:Project;scene:ScriptScene;canNavigate:boolean;onReview:(input:SceneWritingInput)=>Promise<void>;onInspect:()=>Promise<boolean>;
  onDiscard:(id:string)=>void;onAssess:(reviewId:string,noteId:string,value:ReviewAssessment)=>void;onNavigate:(source:ReviewSource)=>void;
}) {
  const id=useId(),[instructions,setInstructions]=useState(''),[sent,setSent]=useState<string|null>(null);
  const all=project.screenplay_reviews??[],uncertain=sent!==null&&!all.some(r=>r.id===sent);
  return <section className="screenplay-feedback" aria-label="Góp ý kịch bản có nguồn">
    <h3>Góp ý cho cảnh đang chọn</h3>
    <p>AI có thể hiểu sai hoặc bỏ sót. Trích đúng nguồn không chứng minh nhận xét đúng; đây là gợi ý để bạn tự cân nhắc và sửa, không phải điểm chất lượng hay phán quyết về tác giả.</p>
    <label htmlFor={`${id}-request`}>Bạn muốn góp ý chú ý điều gì? · tùy chọn</label><textarea id={`${id}-request`} maxLength={2000} value={instructions} onChange={e=>setInstructions(e.target.value)}/>
    <button type="button" disabled={uncertain||all.length>=100||[...all,...(project.screenplay_proposals??[])].some(r=>r.status==='pending')||!scene.blocks.some(b=>b.text.trim())}
      onClick={()=>{const request_id=crypto.randomUUID();setSent(request_id);void onReview({request_id,target_scene_id:scene.id,instructions});}}>Nhận góp ý cảnh này</button>
    <button type="button" className="secondary" onClick={async()=>{if(await onInspect())setSent(null);}}>Kiểm tra góp ý đã lưu</button>
    {uncertain&&<p role="status">Chưa rõ kết quả. Kiểm tra góp ý đã lưu trước lượt mới; không tự retry.</p>}
    {all.length>=100&&<p>Đã đủ 100 lượt góp ý; bạn vẫn tự sửa và lưu được.</p>}
    {[...all].reverse().filter(r=>r.source_screenplay.id===project.screenplay?.id&&r.target_scene_id===scene.id).map(r=><SavedFeedback key={r.id} review={r}
      current={canNavigate&&!!project.screenplay&&sameReviewScript(r.source_screenplay,project.screenplay)&&(project.current_screenplay_review_ids??[]).includes(r.id)} onNavigate={onNavigate}
      onAssess={(noteId,value)=>onAssess(r.id,noteId,value)} onDiscard={()=>onDiscard(r.id)}/>)}
    <p className="storage-note">Tự sửa ở phần kịch bản rồi lưu; nếu cần, chủ động nhận góp ý mới. Chuyển cảnh hoặc lưu không gọi AI. Bạn có thể giữ nguyên bản của mình.</p>
  </section>;
}
// Older reviews keep their original evidence IDs and text; update only the system label.
const sourceLabel = (source: ReviewSource) => source.label.replace("Diễn tiến M2 đã chọn", "Diễn tiến dàn cảnh đã chọn");

function SavedFeedback({review:r,current,onNavigate,onAssess,onDiscard}: {
  review:ScreenplayReview;current:boolean;onNavigate:(source:ReviewSource)=>void;onAssess:(noteId:string,value:ReviewAssessment)=>void;onDiscard:()=>void;
}) {
  const [sourceId,setSourceId]=useState<string|null>(null);
  const source=r.sources.find(s=>s.id===sourceId);
  const labels={pending:'đang chờ',ready:'đã lưu góp ý',failed:'lỗi',discarded:'đã bỏ'};
  const choices:[ReviewAssessment,string][]=[['helpful','Hữu ích'],['misleading','Dẫn sai'],['uncertain','Chưa đủ căn cứ'],['dismissed','Bỏ qua']];
  return <details className="script-review" open={r.status==='ready'}><summary>Góp ý · {labels[r.status]} · nguồn kịch bản bản {r.source_screenplay.version}</summary>
    {r.status==='ready'&&!current&&<p role="status">Góp ý thuộc nguồn trước hoặc có sửa chưa lưu; không dùng liên kết vào bản hiện tại. Nguồn cũ vẫn giữ để đối chiếu.</p>}
    {r.status==='pending'&&<p>Lượt này chưa rõ kết quả. Bỏ lượt không nhất thiết dừng model; không tự gọi lại.</p>}
    {r.error&&<p role="status">Lượt góp ý lỗi ({r.error}); bản tác giả vẫn giữ. Có thể tự sửa và lưu mà không cần nhận góp ý.</p>}
    {r.status==='ready'&&!r.notes.length&&<p>AI không đưa thêm nhận xét trong lượt này. Điều đó không chứng minh cảnh đúng ý hoặc hay.</p>}
    {r.question&&<p className="preserve-lines">Điều cần làm rõ: {r.question}</p>}
    {r.notes.map(note=>{
      const supported=reviewNoteSupported(r,note);
      return <article className="script-review-note" key={note.id} data-review-note={note.id}>
        <h4>{note.kind==='intent_mismatch'?'AI nghi có lệch ý đồ':note.kind==='craft'?'Một lựa chọn để cân nhắc':'Chưa chắc về cách hiểu'}</h4>
        <p className="preserve-lines">{note.observation}</p><p className="preserve-lines">Tác động có thể có: {note.impact}</p>
        {note.suggestion&&<p className="preserve-lines">Bạn có thể cân nhắc: {note.suggestion}</p>}
        {!supported&&<p role="alert">Nguồn hoặc vai trò lựa chọn tác giả chưa đủ căn cứ; chỉ đọc tham khảo, không mở liên kết sửa.</p>}
        {note.evidence.map((e,i)=>{const s=r.sources.find(s=>s.id===e.source_id);return <div key={i}>
          <blockquote className="preserve-lines">{e.quote}</blockquote><p>{s?sourceLabel(s):'Nguồn không xác định'}{s&&<> · {provenanceLabel(s.provenance)}</>}</p>
          {supported&&s&&<><button type="button" className="secondary" onClick={()=>setSourceId(s.id)}>Đọc nguồn đã giữ</button>
            {current&&s.category==='screenplay'&&<button type="button" className="secondary" onClick={()=>onNavigate(s)}>Đến phần đang viết</button>}</>}
        </div>})}
        {r.status==='ready'&&<div role="group" aria-label="Ghi nhận của tác giả">{choices.map(([value,label])=><button key={value} type="button" className="secondary" aria-pressed={note.assessment===value} onClick={()=>onAssess(note.id,value)}>{label}</button>)}</div>}
        <p className="storage-note">Ghi nhận chỉ lưu đánh giá của bạn về góp ý, không nhận phương án hoặc sửa nội dung.</p>
      </article>;
    })}
    {source&&reviewSourceMatches(r.source_screenplay,source)&&<div className="script-review-source" role="region" aria-label="Nguồn góp ý đã giữ">
      <h4>{sourceLabel(source)}</h4><p>Nguồn tại lúc nhận góp ý, không phải buffer hiện tại.</p><p className="preserve-lines">{source.text}</p>
      <button type="button" className="secondary" onClick={()=>setSourceId(null)}>Đóng nguồn góp ý</button>
    </div>}
    <details><summary>Thông tin lượt và ngữ cảnh nguồn</summary><p>{r.created_at} · {r.model??'Chưa xác định model'} · {r.prompt_version}</p>
      <p className="preserve-lines">Yêu cầu: {r.instructions||'Không có yêu cầu thêm'}</p>
      {r.sources.map(s=><p key={s.id} className="preserve-lines"><strong>{sourceLabel(s)}: </strong>{s.text}</p>)}
    </details>
    {r.status==='pending'&&<button type="button" className="secondary" onClick={onDiscard}>Lưu sửa và bỏ lượt góp ý đang chờ</button>}
  </details>;
}

"use client";
import {useId,useState} from 'react';
import type {Project} from './projectsApi';
import type {ScriptScene,SceneWritingInput,ScreenplayProposal} from './screenplayTypes';
import {ScriptSceneFields} from './ScriptSceneFields';

export function ScreenplayProposals({project,scene,canUse,onWrite,onInspect,onPreview,onUse,onDiscard}: {
  project:Project;scene:ScriptScene;canUse:boolean;onWrite:(input:SceneWritingInput)=>Promise<void>;onInspect:()=>Promise<boolean>;
  onPreview:(id:string,scene:ScriptScene)=>void;onUse:(id:string,scene:ScriptScene)=>void;onDiscard:(id:string)=>void;
}) {
  const id=useId();const [instructions,setInstructions]=useState('');const [sent,setSent]=useState<string|null>(null);
  const all=project.screenplay_proposals??[];
  const uncertain=sent!==null&&!all.some(p=>p.id===sent);
  return <section className="screenplay-proposals" aria-label="FirstFrame viết thử một cảnh">
    <h3>FirstFrame viết thử cảnh đang chọn</h3>
    <p>AI chỉ đề xuất tiêu đề và nội dung cho một cảnh. Lưu mọi sửa đang chờ trước khi gửi; bạn đọc, chỉnh rồi tự quyết định dùng hay bỏ. Góp ý AI cho kịch bản chưa được hỗ trợ.</p>
    <label htmlFor={`${id}-request`}>Bạn muốn viết thử theo hướng nào? · tùy chọn</label><textarea id={`${id}-request`} maxLength={2000} value={instructions} onChange={e=>setInstructions(e.target.value)}/>
    <button type="button" disabled={uncertain||all.some(p=>p.status==='pending')||all.length>=100} onClick={()=>{
      const request_id=crypto.randomUUID();setSent(request_id);void onWrite({request_id,target_scene_id:scene.id,instructions});
    }}>Nhờ FirstFrame viết thử cảnh này</button>
    <button type="button" className="secondary" onClick={async()=>{if(await onInspect())setSent(null);}}>Kiểm tra phương án đã lưu</button>
    {uncertain&&<p role="status">Chưa rõ kết quả viết thử. Kiểm tra phương án đã lưu trước khi yêu cầu lượt mới; không tự chạy lại.</p>}
    {all.length>=100&&<p role="status">Đã đủ 100 lượt viết thử; bạn vẫn tự viết và lưu được.</p>}
    {[...all].reverse().filter(p=>p.source_screenplay.id===project.screenplay?.id&&p.target_scene_id===scene.id).map(p=><Proposal key={p.id} proposal={p}
      value={project.pending_screenplay_previews?.[p.id]??p.preview_scene??p.scene} current={scene}
      eligible={canUse&&(project.applicable_screenplay_proposal_ids??[]).includes(p.id)}
      selected={project.pending_screenplay_proposal_id===p.id} onPreview={s=>onPreview(p.id,s)} onUse={s=>onUse(p.id,s)} onDiscard={()=>onDiscard(p.id)}/>)}
    <p className="storage-note">Phương án mới không thay bản đang viết. Mở/đóng phần xem, chuyển cảnh và lưu không gọi lại AI. Không có điểm chứng nhận chất lượng.</p>
  </section>;
}
function Proposal({proposal:p,value,current,eligible,selected,onPreview,onUse,onDiscard}: {
  proposal:ScreenplayProposal;value:ScriptScene|null;current:ScriptScene;eligible:boolean;selected:boolean;
  onPreview:(scene:ScriptScene)=>void;onUse:(scene:ScriptScene)=>void;onDiscard:()=>void;
}) {
  const [editing,setEditing]=useState(false);const [replace,setReplace]=useState(false);
  const labels={pending:'đang chờ',ready:'chờ tác giả chọn',failed:'lỗi',applied:'đã dùng và lưu',discarded:'đã bỏ'};
  return <details className="screenplay-proposal" open={p.status==='ready'}><summary>Phương án · {labels[p.status]} · bản kịch bản {p.source_screenplay.version}</summary>
    {selected&&<p role="status">Đã đưa vào bản đang sửa, chưa lưu. Bạn có thể hoàn tác hoặc lưu để giữ.</p>}
    {p.error&&<p role="status">Lượt viết lỗi ({p.error}); bản tác giả vẫn giữ. Kiểm tra kết quả/nguyên nhân trước khi chủ động tạo lượt mới.</p>}
    {p.status==='pending'&&<p>Bỏ lượt chỉ ngừng chờ/nhận kết quả; model có thể vẫn chạy. Không tự retry.</p>}
    <details><summary>Nguồn và yêu cầu của lượt viết</summary>
      <p>Model: {p.model??'chưa xác định'} · prompt {p.prompt_version}. Đây là nguồn tại lúc yêu cầu.</p>
      <p className="preserve-lines">{p.source_screenplay.source_outline.source.context.idea}</p>
      {p.source_screenplay.source_outline.source.context.constraints.map((c,i)=><p key={i} className="preserve-lines">{c}</p>)}
      {p.source_screenplay.source_outline.scenes.map(s=><p key={s.id} className="preserve-lines">M2 · {s.title}: {s.action}</p>)}
      {p.source_screenplay.scenes.map(s=><div key={s.id}><h4>{s.heading}</h4>{s.blocks.map(b=><p key={b.id} className="preserve-lines">{b.speaker&&<strong>{b.speaker}: </strong>}{b.text}</p>)}</div>)}
      <p className="preserve-lines">Yêu cầu thêm: {p.instructions||'Không có'}</p>
    </details>
    {value&&<>
      {editing&&p.status==='ready'&&!selected?<fieldset className="screenplay-proposal-edit"><legend>Chỉnh phương án riêng, chưa đổi bản tác giả</legend><ScriptSceneFields scene={value} onChange={onPreview}/></fieldset>
        :<div className="screenplay-proposal-text"><h4>{value.heading}</h4>{value.blocks.map(b=><p key={b.id} className="preserve-lines">{b.speaker&&<strong>{b.speaker}: </strong>}{b.text}</p>)}</div>}
      {p.status==='ready'&&!selected&&<>
        <button type="button" className="secondary" onClick={()=>setEditing(!editing)}>{editing?'Xong phần chỉnh phương án':'Chỉnh phương án'}</button>
        {!!current.blocks.length&&<label><input type="checkbox" checked={replace} onChange={e=>setReplace(e.target.checked)}/>Tôi hiểu phương án sẽ thay tiêu đề và toàn bộ khối của cảnh này trong bản đang sửa; chưa lưu và có thể hoàn tác.</label>}
        <button type="button" disabled={!eligible||selected||(!!current.blocks.length&&!replace)} onClick={()=>onUse(value)}>Dùng phương án cho cảnh này</button>
        {!eligible&&!selected&&<p role="status">Nguồn/ngữ cảnh hoặc bản đang sửa đã đổi. Lưu và đối chiếu lại; không tự nhận phương án cũ.</p>}
      </>}
      <details><summary>Bản viết thử ban đầu</summary><p>{p.scene?.heading}</p>{p.scene?.blocks.map(b=><p key={b.id} className="preserve-lines">{b.speaker&&<strong>{b.speaker}: </strong>}{b.text}</p>)}</details>
    </>}
    {p.status!=='applied'&&p.status!=='discarded'&&!selected&&<button type="button" className="secondary" onClick={onDiscard}>Lưu sửa và bỏ phương án này</button>}
  </details>;
}

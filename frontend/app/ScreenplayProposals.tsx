"use client";
import {useId,useState} from 'react';
import {request,type Project} from './projectsApi';
import type {ScriptScene,SceneWritingInput,ScreenplayProposal} from './screenplayTypes';
import {ScriptSceneFields} from './ScriptSceneFields';

export function ScreenplayProposals({project,scene,canUse,onWrite,onInspect,onPreview,onUse,onDiscard,onUndo,onStructural,onChooseScene}: {
  project:Project;scene:ScriptScene;canUse:boolean;onWrite:(input:SceneWritingInput)=>Promise<void>;onInspect:()=>Promise<boolean>;
  onChooseScene?:(id:string)=>void;onUndo?:(id:string)=>void;onStructural?:(instructions:string)=>void;
  onPreview:(id:string,scene:ScriptScene)=>void;onUse:(id:string,scene:ScriptScene)=>void;onDiscard:(id:string)=>void;
}) {
  const id=useId();const [instructions,setInstructions]=useState('');const [sent,setSent]=useState<string|null>(null);
  const [blocks,setBlocks]=useState<string[]>([]),[scope,setScope]=useState<'scene'|'blocks'>('scene');
  const [resolved,setResolved]=useState<{kind:string;scene_id:string|null;message:string;affected_scene_ids:string[]}|null>(null),[error,setError]=useState('');
  const all=project.screenplay_proposals??[];
  const uncertain=sent!==null&&!all.some(p=>p.id===sent);
  return <section className="screenplay-proposals" aria-label="FirstFrame viết thử một cảnh">
    <h3>Phương án sửa cảnh</h3>
    <p>Chọn cả cảnh hoặc các khối cần sửa. AI giữ phương án riêng để bạn đọc, chỉnh và quyết định dùng hay bỏ.</p>
    <label htmlFor={`${id}-request`}>Bạn muốn sửa điều gì? · tùy chọn</label><textarea id={`${id}-request`} maxLength={2000} value={instructions} onChange={e=>{setInstructions(e.target.value);setResolved(null)}}/>
    <label>Phạm vi sửa<select value={scope} onChange={e=>{setScope(e.target.value as 'scene'|'blocks');setResolved(null)}}><option value="scene">Cảnh đang chọn</option><option value="blocks">Chỉ các khối được chọn</option></select></label>
    {scope==='blocks'&&<fieldset><legend>Chọn khối được phép thay đổi</legend>{scene.blocks.map((b,i)=><label key={b.id}><input type="checkbox" checked={blocks.includes(b.id)} onChange={e=>{setBlocks(ids=>e.target.checked?[...ids,b.id]:ids.filter(id=>id!==b.id));setResolved(null)}}/>Khối {i+1} · {b.text.slice(0,70)}</label>)}</fieldset>}
    <button type="button" className="secondary" onClick={()=>{setError('');void request(`/${project.id}/screenplay-revision-target`,'POST',{revision:project.revision,request_id:crypto.randomUUID(),target_scene_id:scene.id,instructions}).then(r=>setResolved(r as typeof resolved)).catch(e=>setError(String(e)))}}>Xem phạm vi sửa</button>
    {resolved&&<p role="status">{resolved.message} {resolved.kind==='scene'?`Cảnh ${project.screenplay!.scenes.findIndex(s=>s.id===resolved.scene_id)+1} · ${scope==='blocks'?blocks.length+' khối':'toàn cảnh'}`:resolved.kind==='candidate'?`${resolved.affected_scene_ids.length} cảnh có thể bị ảnh hưởng.`:''}</p>}
    {resolved?.kind==='scene'&&resolved.scene_id!==scene.id&&<p>Chọn cảnh được nêu ở danh sách phía trên rồi kiểm tra lại phạm vi.</p>}
    {resolved?.kind==='scene'&&resolved.scene_id!==scene.id&&scope==='scene'&&onChooseScene&&<button type="button" disabled={uncertain||all.length>=100||[...all,...(project.screenplay_reviews??[])].some(p=>p.status==='pending')} onClick={()=>{
      const target=resolved.scene_id!;const request_id=crypto.randomUUID();setSent(request_id);
      void onWrite({request_id,target_scene_id:target,instructions,scope:'scene',block_ids:[]}).then(()=>onChooseScene(target));
    }}>Tạo phương án cho cảnh đã nêu</button>}
    {resolved?.kind==='candidate' &&onStructural&&<button type="button" onClick={()=>onStructural(instructions)}>Tạo candidate thay đổi cấu trúc</button>}
    <button type="button" disabled={!resolved||resolved.kind!=='scene'||resolved.scene_id!==scene.id||(scope==='blocks'&&!blocks.length)||uncertain||[...all,...(project.screenplay_reviews??[])].some(p=>p.status==='pending')||all.length>=100} onClick={()=>{
      const request_id=crypto.randomUUID();setSent(request_id);void onWrite({request_id,target_scene_id:scene.id,instructions,scope,block_ids:scope==='blocks'?blocks:[]});
    }}>Tạo phương án sửa trong phạm vi này</button>
    {error&&<p role="alert">{error}</p>}
    <button type="button" className="secondary" onClick={async()=>{if(await onInspect())setSent(null);}}>Kiểm tra phương án đã lưu</button>
    {uncertain&&<p role="status">Chưa rõ kết quả viết thử. Kiểm tra phương án đã lưu trước khi yêu cầu lượt mới; không tự chạy lại.</p>}
    {all.length>=100&&<p role="status">Đã đủ 100 lượt viết thử; bạn vẫn tự viết và lưu được.</p>}
    {[...all].reverse().filter(p=>p.source_screenplay.id===project.screenplay?.id&&p.target_scene_id===scene.id).map(p=><Proposal key={p.id} proposal={p}
      value={project.pending_screenplay_previews?.[p.id]??p.preview_scene??p.scene} current={scene}
      eligible={canUse&&(project.applicable_screenplay_proposal_ids??[]).includes(p.id)}
      selected={project.pending_screenplay_proposal_id===p.id} onPreview={s=>onPreview(p.id,s)} onUse={s=>onUse(p.id,s)} onDiscard={()=>onDiscard(p.id)} onUndo={onUndo?()=>onUndo(p.id):undefined}/>)}
    <p className="storage-note">Phương án mới không thay bản đang viết. Mở/đóng phần xem, chuyển cảnh và lưu không gọi lại AI. Không có điểm chứng nhận chất lượng.</p>
  </section>;
}
function Proposal({proposal:p,value,current,eligible,selected,onPreview,onUse,onDiscard,onUndo}: {
  proposal:ScreenplayProposal;value:ScriptScene|null;current:ScriptScene;eligible:boolean;selected:boolean;
  onUndo?:()=>void;onPreview:(scene:ScriptScene)=>void;onUse:(scene:ScriptScene)=>void;onDiscard:()=>void;
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
      {p.source_screenplay.source_outline.scenes.map(s=><p key={s.id} className="preserve-lines">Dàn cảnh · {s.title}: {s.action}</p>)}
      {p.source_screenplay.scenes.map(s=><div key={s.id}><h4>{s.heading}</h4>{s.blocks.map(b=><p key={b.id} className="preserve-lines">{b.speaker&&<strong>{b.speaker}: </strong>}{b.text}</p>)}</div>)}
      <p className="preserve-lines">Yêu cầu thêm: {p.instructions||'Không có'}</p>
    </details>
    <p>Phạm vi: {p.scope==='blocks'?`${p.block_ids?.length??0} khối; giữ tiêu đề và các khối khác`:'toàn bộ cảnh đã chọn'}. Các cảnh khác giữ nguyên.</p>
    {p.status==='applied'&&p.applied_scene&&p.undone_revision==null&&onUndo&&<button type="button" className="secondary" onClick={onUndo}>Hoàn tác lần nhận này</button>}
    {p.undone_revision!=null&&<p>Đã hoàn tác và giữ lịch sử.</p>}
    {value&&<>
      <details open className="revision-before"><summary>Trước khi sửa · nguồn đã giữ</summary>{p.source_screenplay.scenes.filter(s=>s.id===p.target_scene_id).map(s=><div key={s.id}><h4>{s.heading}</h4>{s.blocks.map(b=><p key={b.id} className="preserve-lines">{b.speaker} {b.text}</p>)}</div>)}</details>
      <h4>Sau khi sửa · phương án riêng</h4>
      {editing&&p.status==='ready'&&!selected?<fieldset className="screenplay-proposal-edit"><legend>Chỉnh phương án riêng, chưa đổi bản tác giả</legend>{p.scope==='blocks'?value.blocks.filter(b=>p.block_ids?.includes(b.id)).map(b=><label key={b.id}>Khối được chọn<textarea maxLength={10000} value={b.text} onChange={e=>onPreview({...value,blocks:value.blocks.map(x=>x.id===b.id?{...x,text:e.target.value}:x)})}/></label>):<ScriptSceneFields scene={value} onChange={onPreview}/>}</fieldset>
        :<div className="screenplay-proposal-text"><h4>{value.heading}</h4>{value.blocks.map(b=><p key={b.id} className="preserve-lines">{b.speaker&&<strong>{b.speaker}: </strong>}{b.text}</p>)}</div>}
      {p.status==='ready'&&!selected&&<>
        <button type="button" className="secondary" onClick={()=>setEditing(!editing)}>{editing?'Xong phần chỉnh phương án':'Chỉnh phương án'}</button>
        {p.scope!=='blocks'&&!!current.blocks.length&&<label><input type="checkbox" checked={replace} onChange={e=>setReplace(e.target.checked)}/>Tôi hiểu phương án sẽ thay tiêu đề và toàn bộ khối của cảnh này sau khi bấm Dùng; bản trước được giữ trong lịch sử và có thể hoàn tác nếu chưa sửa tiếp.</label>}
        <button type="button" disabled={!eligible||selected||(p.scope!=='blocks'&&!!current.blocks.length&&!replace)} onClick={()=>onUse(value)}>Dùng phương án và lưu</button>
        {!eligible&&!selected&&<p role="status">Nguồn/ngữ cảnh hoặc bản đang sửa đã đổi. Lưu và đối chiếu lại; không tự nhận phương án cũ.</p>}
      </>}
      <details><summary>Bản viết thử ban đầu</summary><p>{p.scene?.heading}</p>{p.scene?.blocks.map(b=><p key={b.id} className="preserve-lines">{b.speaker&&<strong>{b.speaker}: </strong>}{b.text}</p>)}</details>
    </>}
    {p.status!=='applied'&&p.status!=='discarded'&&!selected&&<button type="button" className="secondary" onClick={onDiscard}>Bỏ qua phương án</button>}
  </details>;
}

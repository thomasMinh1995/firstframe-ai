"use client";
import {useId,useState} from 'react';
import type {Project} from './projectsApi';
import {unfinishedScriptScenes,type Screenplay,type ScreenplaySelectionInput} from './screenplayTypes';
import {stagingLabels,type StagingKey} from './sceneTypes';

export function ScreenplayReading({saved,dirty,onSelect,onInspect,onEdit}: {
  saved:Project;dirty:boolean;onSelect:(input:ScreenplaySelectionInput)=>Promise<void>;onInspect:()=>Promise<boolean>;onEdit:(sceneId:string)=>void;
}) {
  const id=useId(),[version,setVersion]=useState('current'),[sent,setSent]=useState<string|null>(null);
  const versions=[...(saved.screenplay?[{id:'current',label:`Bản đang lưu · phiên bản ${saved.screenplay.version}`,screenplay:saved.screenplay}]:[]),
    ...[...(saved.screenplay_versions??[])].reverse().map(v=>({id:v.id,label:`Lịch sử · phiên bản ${v.screenplay.version} · ${v.created_at}`,screenplay:v.screenplay}))];
  const selected=versions.find(v=>v.id===version)??versions[0];
  if(!selected)return null;
  const script=selected.screenplay,incomplete=unfinishedScriptScenes(script),handoff=saved.screenplay_handoff;
  const uncertain=sent!==null&&!(saved.screenplay_selections??[]).some(s=>s.id===sent);
  const alreadySelected=handoff?.screenplay.id===script.id&&handoff.screenplay.version===script.version;
  return <section className="screenplay-reading" aria-label="Đọc bản đã lưu và chọn nguồn M4">
    <h3>Đọc toàn kịch bản đã lưu</h3>
    <p>Đọc đúng bản đã lưu, gồm cả cảnh/khối chưa viết. Chọn nguồn chỉ giữ một bản riêng cho M4, chưa xuất bản và không xác nhận chất lượng tác phẩm.</p>
    {dirty&&<p role="status">Có sửa chưa lưu. Phần đọc và chọn nguồn bên dưới vẫn dùng bản đã lưu; lưu kịch bản nếu muốn dùng các sửa mới.</p>}
    <label htmlFor={`${id}-version`}>Bản để đọc và đối chiếu</label><select id={`${id}-version`} value={selected.id} onChange={e=>setVersion(e.target.value)}>
      {versions.map(v=><option key={v.id} value={v.id}>{v.label}</option>)}
    </select>
    <p>Kịch bản phiên bản {script.version} · {script.scenes.length} cảnh · nguồn M2 phiên bản {script.source_outline.version}.</p>
    <SavedScript script={script}/>
    {incomplete.length>0&&<div role="status"><p>Chưa chọn được nguồn: cần tên cảnh, nội dung mỗi khối và người nói cho lời thoại. Bạn vẫn lưu nháp được.</p>
      <ul>{incomplete.map(s=><li key={s.id}>Cảnh {script.scenes.indexOf(s)+1}: {s.heading||'Chưa có tiêu đề'}
        {selected.id==='current'&&<button type="button" className="secondary" onClick={()=>onEdit(s.id)}>Quay lại sửa cảnh {script.scenes.indexOf(s)+1}</button>}</li>)}</ul>
      {selected.id!=='current'&&<p>Muốn sửa bản lịch sử, dùng thao tác khôi phục ở Lịch sử kịch bản; nguồn đã chọn trước vẫn giữ.</p>}
    </div>}
    <button type="button" disabled={!!incomplete.length||uncertain||alreadySelected||(saved.screenplay_selections?.length??0)>=100}
      onClick={()=>{const request_id=crypto.randomUUID();setSent(request_id);void onSelect({request_id,source_version_id:selected.id});}}>{alreadySelected?'Đã chọn nguồn này cho M4':'Chọn bản đã đọc cho M4'}</button>
    <button type="button" className="secondary" onClick={async()=>{if(await onInspect())setSent(null);}}>Kiểm tra nguồn M4 đã lưu</button>
    {uncertain&&<p role="status">Chưa rõ kết quả chọn nguồn. Kiểm tra nguồn M4 đã lưu trước lượt chọn mới; không tự gửi lại.</p>}
    {(saved.screenplay_selections?.length??0)>=100&&<p>Đã đủ 100 lần chọn nguồn; bạn vẫn tự viết/lưu và đọc nguồn đã chọn được.</p>}
    {handoff&&<details className="screenplay-handoff"><summary>Nguồn đã chọn cho M4 · kịch bản phiên bản {handoff.screenplay.version}</summary>
      <p>Đã chọn lúc {new Date(handoff.created_at).toLocaleString('vi-VN')}. Bản nguồn này không tự đổi khi sửa hoặc khôi phục kịch bản. M4 chưa triển khai, chưa có xuất bản.</p>
      <SavedScript script={handoff.screenplay}/>
    </details>}
    <p className="storage-note">Không cần ảnh, góp ý AI hoặc điểm số để chọn nguồn. Đọc, đổi bản và chọn không gọi AI hay tự lưu buffer.</p>
  </section>;
}
function SavedScript({script}:{script:Screenplay}) {
  const source=script.source_outline;
  return <div className="screenplay-full-text"><details><summary>Nguồn M2 và ý đồ đi cùng bản này</summary>
    <h4>{source.source.draft.title}</h4><p className="preserve-lines">{source.source.draft.logline}</p>
    <p className="preserve-lines">{source.source.context.idea}</p>
    {source.source.context.constraints.map((text,i)=><p key={i} className="preserve-lines">Giới hạn: {text}</p>)}
    {source.source.context.clarifications.map((a,i)=><p key={i} className="preserve-lines">{a.question} — {a.answer}</p>)}
    {source.source.context.pending_questions.map((q,i)=><p key={i} className="preserve-lines">Chưa quyết định: {q.question}</p>)}
    {source.scenes.map((s,i)=><div key={s.id}><h4>{i+1}. {s.title}</h4><p className="preserve-lines">{s.action}</p>
      {(['location','time','characters','goal','purpose','viewer_intent','keep_or_avoid'] as const).map((key,i)=>s[key]&&<p key={key} className="preserve-lines">{['Địa điểm','Thời điểm','Nhân vật','Mục tiêu','Đóng góp','Cảm nhận','Giữ/tránh'][i]}: {s[key]}</p>)}
      {Object.entries(s.staging_choices).map(([key,text])=><p key={key} className="preserve-lines">{stagingLabels[key as StagingKey]}: {text}</p>)}
    </div>)}
  </details>{script.scenes.map((s,i)=><article key={s.id} data-reading-scene={s.id}>
    <h4>{i+1}. {s.heading.trim()?s.heading:'Cảnh chưa có tiêu đề'}</h4>
    {!s.blocks.length&&<p>Cảnh chưa viết.</p>}
    {s.blocks.map(b=><div key={b.id} className={`reading-block reading-${b.kind}`}>
      {b.kind==='dialogue'&&<p className="preserve-lines"><strong>{b.speaker.trim()?b.speaker:'Chưa có người nói'}</strong></p>}
      <p className="preserve-lines">{b.text.trim()?b.text:'Khối chưa có nội dung.'}</p>
    </div>)}
  </article>)}</div>;
}

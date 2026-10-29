"use client";
import {useId,useState} from 'react';
import type {Project} from './projectsApi';
import {unfinishedScriptScenes,type Screenplay,type ScreenplaySelectionInput} from './screenplayTypes';
import {stagingLabels,type StagingKey} from './sceneTypes';

export function ScreenplayReading({saved,dirty,onSelect,onInspect,onEdit,onDownload}: {
  saved:Project;dirty:boolean;onSelect:(input:ScreenplaySelectionInput,read:Screenplay)=>Promise<void>;onDownload?:(selectionId:string)=>Promise<void>;onInspect:()=>Promise<boolean>;onEdit:(sceneId:string)=>void;
}) {
  const id=useId(),[version,setVersion]=useState('current'),[exportId,setExportId]=useState(''),[sent,setSent]=useState<string|null>(null);
  const versions=[...(saved.screenplay?[{id:'current',label:`Bản đang lưu · phiên bản ${saved.screenplay.version}`,screenplay:saved.screenplay}]:[]),
    ...[...(saved.screenplay_versions??[])].reverse().map(v=>({id:v.id,label:`Lịch sử · phiên bản ${v.screenplay.version} · ${v.created_at}`,screenplay:v.screenplay}))];
  const selected=versions.find(v=>v.id===version)??versions[0];
  if(!selected)return null;
  const script=selected.screenplay,incomplete=unfinishedScriptScenes(script),handoff=saved.screenplay_handoff;
  const uncertain=sent!==null&&!(saved.screenplay_selections??[]).some(s=>s.id===sent);
  const matching=(saved.screenplay_selections??[]).find(s=>JSON.stringify(s.screenplay)===JSON.stringify(script));
  const chosen=(saved.screenplay_selections??[]).find(s=>s.id===exportId)??handoff;
  const title=script.source_outline.source.draft.title;
  return <section className="screenplay-reading" tabIndex={-1} aria-label="Đọc bản đã lưu và chọn bản để xuất">
    <h3>Đọc toàn kịch bản đã lưu</h3>
    <p>Đọc đúng bản đã lưu, gồm cả cảnh/khối chưa viết. PDF lấy đúng bản đã đọc và chọn, chưa xuất bản và không xác nhận chất lượng tác phẩm.</p>
    {dirty&&<p role="status">Có sửa chưa lưu. Phần đọc và chọn nguồn bên dưới vẫn dùng bản đã lưu; lưu kịch bản nếu muốn dùng các sửa mới.</p>}
    <label htmlFor={`${id}-version`}>Bản để đọc và đối chiếu</label><select id={`${id}-version`} value={selected.id} onChange={e=>setVersion(e.target.value)}>
      {versions.map(v=><option key={v.id} value={v.id}>{v.label}</option>)}
    </select>
    <p>Kịch bản phiên bản {script.version} · {script.scenes.length} cảnh · nguồn dàn cảnh phiên bản {script.source_outline.version}.</p>
    <p>Tên phim đi cùng bản này: <strong>{title.trim()?title:"Chưa có tên phim trong nguồn; PDF dùng tên tệp trung tính."}</strong></p>
    <SavedScript script={script}/>
    {incomplete.length>0&&<div role="status"><p>Chưa chọn được nguồn: cần tên cảnh, nội dung mỗi khối và người nói cho lời thoại. Bạn vẫn lưu nháp được.</p>
      <ul>{incomplete.map(s=><li key={s.id}>Cảnh {script.scenes.indexOf(s)+1}: {s.heading||'Chưa có tiêu đề'}
        {selected.id==='current'&&<button type="button" className="secondary" onClick={()=>onEdit(s.id)}>Quay lại sửa cảnh {script.scenes.indexOf(s)+1}</button>}</li>)}</ul>
      {selected.id!=='current'&&<p>Muốn sửa bản lịch sử, dùng thao tác khôi phục ở trang Bản đã lưu; nguồn đã chọn trước vẫn giữ.</p>}
    </div>}
    <button type="button" disabled={dirty||!!incomplete.length||uncertain||(!matching&&(saved.screenplay_selections?.length??0)>=100)}
      onClick={()=>{if(matching&&onDownload){void onDownload(matching.id);return;}const request_id=crypto.randomUUID();setSent(request_id);void onSelect({request_id,source_version_id:selected.id},script);}}>Chọn bản đã đọc &amp; tải PDF</button>
    <button type="button" className="secondary" onClick={async()=>{if(await onInspect())setSent(null);}}>Kiểm tra nguồn xuất kịch bản đã lưu</button>
    {uncertain&&<p role="status">Chưa rõ kết quả chọn nguồn. Kiểm tra nguồn xuất kịch bản đã lưu trước lượt chọn mới; không tự gửi lại.</p>}
    {(saved.screenplay_selections?.length??0)>=100&&<p>Đã đủ 100 lần chọn nguồn; bạn vẫn tự viết/lưu và đọc nguồn đã chọn được.</p>}
    {handoff&&chosen&&<details className="screenplay-handoff"><summary>Kịch bản đã chọn để xuất · các bản PDF đã giữ</summary>
      <label htmlFor={`${id}-export`}>Bản đã chọn để tải lại</label><select id={`${id}-export`} value={chosen.id} onChange={e=>setExportId(e.target.value)}>
        {[...(saved.screenplay_selections??[])].reverse().map(s=><option key={s.id} value={s.id}>Kịch bản phiên bản {s.screenplay.version} · {new Date(s.created_at).toLocaleString('vi-VN')}</option>)}
      </select>
      <p>Bản chọn lúc {new Date(chosen.created_at).toLocaleString('vi-VN')} không tự đổi khi sửa hoặc khôi phục kịch bản. Tải lại vẫn dùng snapshot này, kể cả khi có chữ chưa lưu.</p>
      {!chosen.screenplay.source_outline.source.draft.title.trim()&&<p>Nguồn cũ chưa có tên phim; PDF dùng tên tệp trung tính.</p>}
      <button type="button" disabled={!onDownload} onClick={()=>void onDownload?.(chosen.id)}>Tải lại PDF bản đã chọn</button>
      <SavedScript script={chosen.screenplay}/>
    </details>}
    <p className="storage-note">Không cần ảnh, góp ý AI hoặc điểm số để chọn nguồn. Chờ trạng thái Đã lưu rồi đọc và chọn đúng bản; các thao tác này không gọi AI.</p>
  </section>;
}
export function SavedScript({script,activeSceneId}:{script:Screenplay;activeSceneId?:string}) {
  const source=script.source_outline;
  return <div className="screenplay-full-text"><details><summary>Nguồn dàn cảnh và ý đồ đi cùng bản này</summary>
    <h4>{source.source.draft.title}</h4><p className="preserve-lines">{source.source.draft.logline}</p>
    <p className="preserve-lines">{source.source.context.idea}</p>
    {source.source.context.constraints.map((text,i)=><p key={i} className="preserve-lines">Giới hạn: {text}</p>)}
    {source.source.context.clarifications.map((a,i)=><p key={i} className="preserve-lines">{a.question} — {a.answer}</p>)}
    {source.source.context.pending_questions.map((q,i)=><p key={i} className="preserve-lines">Chưa quyết định: {q.question}</p>)}
    {source.scenes.map((s,i)=><div key={s.id}><h4>{i+1}. {s.title}</h4><p className="preserve-lines">{s.action}</p>
      {(['location','time','characters','goal','purpose','viewer_intent','keep_or_avoid'] as const).map((key,i)=>s[key]&&<p key={key} className="preserve-lines">{['Địa điểm','Thời điểm','Nhân vật','Mục tiêu','Đóng góp','Cảm nhận','Giữ/tránh'][i]}: {s[key]}</p>)}
      {Object.entries(s.staging_choices).map(([key,text])=><p key={key} className="preserve-lines">{stagingLabels[key as StagingKey]}: {text}</p>)}
    </div>)}
  </details>{script.scenes.map((s,i)=><article key={s.id} data-reading-scene={s.id} data-selected={s.id===activeSceneId?'true':undefined}>
    <h4>{i+1}. {s.heading.trim()?s.heading:'Cảnh chưa có tiêu đề'}</h4>
    {!s.blocks.length&&<p>Cảnh chưa viết.</p>}
    {s.blocks.map(b=><div key={b.id} className={`reading-block reading-${b.kind}`}>
      {b.kind==='dialogue'&&<p className="preserve-lines"><strong>{b.speaker.trim()?b.speaker:'Chưa có người nói'}</strong></p>}
      <p className="preserve-lines">{b.text.trim()?b.text:'Khối chưa có nội dung.'}</p>
    </div>)}
  </article>)}</div>;
}

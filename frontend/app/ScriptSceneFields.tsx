"use client";
import {useId} from "react";
import type {ScriptScene,ScriptBlock} from "./screenplayTypes";

export function ScriptSceneFields({scene,onChange,onDelete}: {
  scene:ScriptScene;onChange:(scene:ScriptScene)=>void;onDelete?:(id:string)=>void;
}) {
  const prefix=useId();
  const edit=(id:string,change:Partial<ScriptBlock>)=>onChange({...scene,blocks:scene.blocks.map(b=>b.id===id?{...b,...change}:b)});
  const add=(kind:ScriptBlock['kind'])=>onChange({...scene,blocks:[...scene.blocks,{id:crypto.randomUUID(),kind,text:'',speaker:''}]});
  function move(i:number,by:number){const blocks=[...scene.blocks];[blocks[i],blocks[i+by]]=[blocks[i+by],blocks[i]];onChange({...scene,blocks});}
  return <div className="screenplay-scene">
    <label>Tiêu đề cảnh<input maxLength={500} value={scene.heading} onChange={e=>onChange({...scene,heading:e.target.value})}/></label>
    {!scene.blocks.length&&<p>Cảnh chưa viết. Thêm một hành động để bắt đầu; không cần viết lại toàn bộ ghi chú nguồn.</p>}
    {scene.blocks.map((b,i)=><fieldset key={b.id} className="script-block" data-script-block={b.id}>
      <legend>{i+1}. {b.kind==='action'?'Hành động':'Lời thoại'}</legend>
      {b.kind==='dialogue'&&<label>Người nói<input maxLength={200} value={b.speaker} onChange={e=>edit(b.id,{speaker:e.target.value})}/></label>}
      <label htmlFor={`${prefix}-${b.id}`}>{b.kind==='action'?'Nội dung hành động':'Nội dung lời thoại'}</label>
      <textarea id={`${prefix}-${b.id}`} rows={4} maxLength={10000} value={b.text} onChange={e=>edit(b.id,{text:e.target.value})}/>
      <button type="button" disabled={i===0} onClick={()=>move(i,-1)}>Đưa khối lên</button>
      <button type="button" disabled={i===scene.blocks.length-1} onClick={()=>move(i,1)}>Đưa khối xuống</button>
      <button type="button" onClick={()=>onDelete?onDelete(b.id):onChange({...scene,blocks:scene.blocks.filter(x=>x.id!==b.id)})}>Xóa khối</button>
    </fieldset>)}
    <button type="button" disabled={scene.blocks.length>=200} onClick={()=>add('action')}>Thêm hành động</button>
    <button type="button" disabled={scene.blocks.length>=200} onClick={()=>add('dialogue')}>Thêm lời thoại</button>
  </div>;
}

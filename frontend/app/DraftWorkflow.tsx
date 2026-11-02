'use client';
import {useEffect,useRef,useState,useId,useMemo,type ReactNode} from 'react';
import type {DraftRun,Candidate} from './draftRunsApi';
import {cardResult,parentWorkflowItems,currentWorkflowItem,workflowItemLabel,workflowStatusLabels,workflowItemDisplay,type WorkflowItem} from './draftWorkflowState';
import {revealSceneInViewport} from './sceneViewport';
import {runCapabilities} from './draftWorkflowActions';
import './draftWorkflow.css';
type Read=(target:string,trigger:HTMLButtonElement)=>void;
export function DraftWorkflow({run,candidate,onRead,reveals=[],actions,reading=false,following,onFollowingChange}:{run:DraftRun;candidate:Candidate|null;onRead:Read;reveals?:string[];actions?:(item:WorkflowItem)=>ReactNode;reading?:boolean;following:boolean;onFollowingChange:(enabled:boolean,manual?:boolean)=>void}){
 const list=useRef<HTMLOListElement>(null),[paths,setPaths]=useState<string[]>([]);
 const arrowId='workflow-arrow-'+useId().replace(/:/g,'');
 const items=useMemo(()=>parentWorkflowItems(run.workflow_items??[]),[run.workflow_items]);
 const current=currentWorkflowItem(items);
 const completed=run.status==='ready'&&run.adopted_revision===null;
 const ready=completed&&runCapabilities(run,candidate).canAdopt;
 function goCurrent(focus=true){
  const target=[...list.current?.querySelectorAll<HTMLElement>('[data-workflow-id]')??[]].find(el=>el.dataset.workflowId===current?.id);
  const details=target?.closest('details');if(details)details.open=true;
  if(target?.getClientRects().length){revealSceneInViewport(target,'center');if(focus)target.focus({preventScroll:true});}
 }
 useEffect(()=>{if(reading)onFollowingChange(false)},[reading]);
 useEffect(()=>{
  if(!following||reading||current?.status!=='running')return;
  let frame=0;
  const reveal=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>goCurrent(false))};
  const observer=new ResizeObserver(reveal);
  if(list.current){observer.observe(list.current);for(const card of list.current.children)observer.observe(card)}
  window.addEventListener('resize',reveal);reveal();
  return()=>{observer.disconnect();window.removeEventListener('resize',reveal);cancelAnimationFrame(frame)};
 },[following,reading,current?.id,current?.status,candidate?.revision]);
 useEffect(()=>{
  const pause=()=>onFollowingChange(false);
  const interact=(event:Event)=>{if(event.target instanceof Element&&event.target.closest('.draft-workflow-card')){
   const editing=!!event.target.closest('.draft-workflow-decisions');
   onFollowingChange(false,!editing);
  }};
  const key=(event:KeyboardEvent)=>{if(['ArrowUp','ArrowDown','PageUp','PageDown','Home','End',' '].includes(event.key)&&!(event.target as HTMLElement)?.closest('input,textarea,select,button,summary,[contenteditable="true"]'))pause()};
  window.addEventListener('wheel',pause,{passive:true});window.addEventListener('touchmove',pause,{passive:true});window.addEventListener('keydown',key);window.addEventListener('pointerdown',interact);window.addEventListener('click',interact);
  return()=>{window.removeEventListener('wheel',pause);window.removeEventListener('touchmove',pause);window.removeEventListener('keydown',key);window.removeEventListener('pointerdown',interact);window.removeEventListener('click',interact)};
 },[following]);
 const read:Read=(target,trigger)=>{onFollowingChange(false);onRead(target,trigger)};
 useEffect(()=>{
  const el=list.current;if(!el)return;let frame=0;
  const draw=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{const box=el.getBoundingClientRect();const cards=[...el.children].map(n=>n.getBoundingClientRect());setPaths(cards.slice(0,-1).map((a,i)=>{const b=cards[i+1];if(Math.abs(a.top-b.top)<5){const right=b.left>a.left,x=(right?a.right:a.left)-box.left,xx=(right?b.left:b.right)-box.left,y=a.top+a.height/2-box.top;return `M${x},${y} L${xx},${y}`;}const x=a.left+a.width/2-box.left,xx=b.left+b.width/2-box.left,y=a.bottom-box.top,yy=b.top-box.top;return `M${x},${y} C${x},${(y+yy)/2} ${xx},${(y+yy)/2} ${xx},${yy}`;}));});};
  const observer=new ResizeObserver(draw);observer.observe(el);for(const child of el.children)observer.observe(child);draw();return()=>{observer.disconnect();cancelAnimationFrame(frame)};
 },[items]);
 if(!items.length)return <p className="storage-note">Lượt này chưa có tiến độ chi tiết. Xem trạng thái và bản đã lưu bên dưới.</p>;
 return <section className="draft-workflow" aria-label="Tiến độ tạo nháp theo từng bước">
  <div className={`draft-workflow-current${current||completed?' is-active':''}`}><div><p role="status">{current?`${current.status==='needs_input'?'Cần bạn xem':'Đang xử lý'}: ${workflowItemLabel(current,candidate)}`:completed?(ready?`Đã hoàn tất ${run.completed_scenes} cảnh · Nháp đã lưu`:'Đã viết xong · Đang tải nháp đã lưu…'):'Tiến độ đã lưu'}</p>{current?.status==='running'&&<label className="draft-workflow-follow"><input type="checkbox" checked={following&&!reading} disabled={reading} onChange={e=>onFollowingChange(e.target.checked)}/>Theo dõi cảnh đang chạy</label>}{current&&!following&&<small role="status">Đã tạm dừng theo dõi để giữ vị trí đang xem.</small>}{ready&&run.review_error&&<small>Góp ý chưa hoàn tất; bạn vẫn có thể đọc bản nháp đã lưu.</small>}</div>{current&&<button type="button" className="secondary" onClick={()=>goCurrent()}>Đến bước đang chạy</button>}{ready&&<button type="button" onClick={e=>read('script',e.currentTarget)}>Đọc nháp</button>}</div>
  <p className="storage-note" role="status">{items.filter(i=>workflowItemDisplay(i,run).complete).length}/{items.length} bước đã có kết quả · {items.filter(i=>['warning','failed','interrupted','needs_input'].includes(i.status)).length} bước cần xem</p>
  <div className="draft-workflow-map"><svg aria-hidden="true" className="draft-workflow-route"><defs><marker id={arrowId} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="userSpaceOnUse"><path d="M1,1 L7,4 L1,7"/></marker></defs>{paths.map((d,i)=><path key={i} className={items[i+1]?.status==='running'?'is-current':undefined} d={d} markerEnd={`url(#${arrowId})`}/>)}</svg>
   <ol ref={list} role="list" className="draft-workflow-cards">{items.map((item,index)=><WorkflowCard key={item.id} item={item} run={run} index={index} candidate={candidate} onRead={read} reveal={reveals.indexOf(item.id)} actions={actions?.(item)}/>)}</ol>
  </div>
 </section>;
}
function WorkflowCard({item,run,index,candidate,onRead,reveal,actions}:{item:WorkflowItem;run:DraftRun;index:number;candidate:Candidate|null;onRead:Read;reveal:number;actions?:ReactNode}){
 const active=item.status==='running'||item.status==='needs_input';
 const [expanded,setExpanded]=useState(active),wasActive=useRef(active);
 useEffect(()=>{if(active&&!wasActive.current)setExpanded(true);wasActive.current=active},[active]);
 const result=cardResult(item,candidate),row=Math.floor(index/3),col=row%2?3-index%3:1+index%3;
 const display=workflowItemDisplay(item,run);
 const preview=result?.target&&item.kind==='draft'?(run.adopted_revision!=null?'Bản nháp đã nhận. Các sửa tiếp theo lưu trong workspace.':run.status==='running'?'Nội dung nháp đã lưu; bạn có thể đọc trong khi chờ góp ý.':result.text):result?.text;
 return <li data-workflow-id={item.id} tabIndex={-1} aria-current={item.status==='running'||item.status==='needs_input'?'step':undefined} className={`draft-workflow-card is-${item.status}`} style={{gridRow:row+1,gridColumn:col}}>
  <div className="draft-workflow-heading">
   <span className="draft-workflow-badge" aria-hidden="true"><span className="draft-workflow-number">{index+1}</span>{display.complete&&<span className="draft-workflow-check">✓</span>}</span>
   <h3>{workflowItemLabel(item,candidate)}</h3>
  </div>
  <p className={`draft-workflow-status${item.status==='running'?' draft-workflow-thinking':''}`}>{item.status==='running'&&<span className="process-spinner" aria-hidden="true"/>}{item.status==='running'?`Đang xử lý · ${workflowItemLabel(item,candidate)}`:display.label}</p>
  {!item.children.length&&(item.status==='running'&&!result?.target||result&&!result.target)&&<WorkflowSkeleton processing={item.status==='running'}/>}
  {preview&&<p className={`draft-workflow-preview${reveal>=0?' is-revealing':''}`} style={reveal>=0?{animationDelay:`${reveal*100}ms`}:undefined}>{preview.slice(0,180)}{preview.length>180?'…':''}</p>}
  {item.children.length>0&&<details className="draft-workflow-children" open={expanded} onToggle={e=>setExpanded(e.currentTarget.open)}>
   <summary>{item.children.filter(child=>child.status==='completed').length}/{item.children.length} cảnh {item.kind==='review'?'đã góp ý':'đã viết'} · Tiến trình con</summary>
   <ul>{item.children.map(child=>{const childResult=cardResult(child,candidate);const scene=candidate?.project.screenplay?.scenes.find(s=>s.id===child.scene_id);const sceneNumber=scene?candidate!.project.screenplay!.scenes.indexOf(scene)+1:0;const status=child.status==='completed'?(item.kind==='review'?'Đã góp ý':'Đã viết'):child.status==='running'?(item.kind==='review'?'Đang góp ý':'Đang viết'):workflowStatusLabels[child.status];return <li key={child.id} data-workflow-id={child.id} tabIndex={-1} aria-current={child.status==='running'?'step':undefined}>
    <div className="draft-workflow-child-copy"><strong>{scene?`Cảnh ${sceneNumber} · ${scene.heading}`:workflowItemLabel(child,candidate)}</strong><span className="draft-workflow-child-state">{child.status==='running'&&<span className="process-spinner" aria-hidden="true"/>}{child.status==='completed'&&<span aria-hidden="true">✓</span>}{status}</span></div>
    {childResult?.target&&<button type="button" className="secondary" aria-label={`Đọc ${scene?.heading??'nội dung cảnh'}`} data-read-target={childResult.target} onClick={e=>onRead(childResult.target,e.currentTarget)}>Đọc</button>}
   </li>})}</ul>
  </details>}
  {result?.target&&<button type="button" data-read-target={result.target} className="secondary" onClick={e=>onRead(result.target,e.currentTarget)}>Đọc nội dung</button>}
  {actions}
 </li>;
}
export function WorkflowSkeleton({processing=false}:{processing?:boolean}){
 return <div className={`draft-workflow-skeleton${processing?' is-processing':''}`} aria-hidden="true"><span/><span/><span/><span/></div>;
}

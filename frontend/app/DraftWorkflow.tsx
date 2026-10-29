'use client';
import {useEffect,useRef,useState} from 'react';
import type {DraftRun,Candidate} from './draftRunsApi';
import {cardResult,workflowLabels,workflowStatusLabels,type WorkflowItem} from './draftWorkflowState';
import './draftWorkflow.css';
export function DraftWorkflow({run,candidate,onRead}:{run:DraftRun;candidate:Candidate|null;onRead:(target:string)=>void}){
 const list=useRef<HTMLOListElement>(null),[paths,setPaths]=useState<string[]>([]);
 const items=run.workflow_items??[];
 useEffect(()=>{
  const el=list.current;if(!el)return;let frame=0;
  const draw=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{const box=el.getBoundingClientRect();const cards=[...el.children].map(n=>n.getBoundingClientRect());setPaths(cards.slice(0,-1).map((a,i)=>{const b=cards[i+1];if(Math.abs(a.top-b.top)<5){const right=b.left>a.left,x=(right?a.right:a.left)-box.left,xx=(right?b.left:b.right)-box.left,y=a.top+a.height/2-box.top;return `M${x},${y} L${xx},${y}`;}if(Math.abs(a.left-b.left)<5&&box.width>620){const right=Math.floor(i/3)%2===0,x=(right?a.right:a.left)-box.left,y=a.top+a.height/2-box.top,yy=b.top+b.height/2-box.top,turn=x+(right?15:-15);return `M${x},${y} C${turn},${y} ${turn},${y+20} ${turn},${y+28} L${turn},${yy-28} C${turn},${yy-20} ${turn},${yy} ${x},${yy}`;}const x=a.left+a.width/2-box.left,xx=b.left+b.width/2-box.left,y=a.bottom-box.top,yy=b.top-box.top;return `M${x},${y} C${x},${(y+yy)/2} ${xx},${(y+yy)/2} ${xx},${yy}`;}));});};
  const observer=new ResizeObserver(draw);observer.observe(el);for(const child of el.children)observer.observe(child);draw();return()=>{observer.disconnect();cancelAnimationFrame(frame)};
 },[items]);
 if(!items.length)return <p className="storage-note">Lượt này chưa có tiến độ chi tiết. Xem trạng thái và bản đã lưu bên dưới.</p>;
 return <section className="draft-workflow" aria-label="Tiến độ tạo nháp theo từng bước">
  <p className="storage-note">{items.filter(i=>i.status==='completed').length}/{items.length} mục có kết quả · {items.filter(i=>['warning','failed','interrupted','needs_input'].includes(i.status)).length} mục cần xem</p>
  <div className="draft-workflow-map"><svg aria-hidden="true" className="draft-workflow-route">{paths.map((d,i)=><path key={i} d={d}/>)}</svg>
   <ol ref={list} className="draft-workflow-cards">{items.map((item,index)=><WorkflowCard key={item.id} item={item} index={index} candidate={candidate} onRead={onRead}/>)}</ol>
  </div>
 </section>;
}
function WorkflowCard({item,index,candidate,onRead}:{item:WorkflowItem;index:number;candidate:Candidate|null;onRead:(target:string)=>void}){
 const sceneIndex=candidate?.project.screenplay?.scenes.findIndex(s=>s.id===item.scene_id)??-1;
 const result=cardResult(item,candidate),row=Math.floor(index/3),col=row%2?3-index%3:1+index%3;
 return <li className={`draft-workflow-card is-${item.status}`} style={{gridRow:row+1,gridColumn:col}}>
  <span className="draft-workflow-number" aria-hidden="true">{item.status==='completed'?'✓':index+1}</span>
  <h3>{workflowLabels[item.kind]}{item.kind==='write'&&sceneIndex>=0&&` ${sceneIndex+1}`}</h3>
  <p className="draft-workflow-status">{workflowStatusLabels[item.status]}</p>
  {result&&<p className="draft-workflow-preview">{result.text.slice(0,180)}{result.text.length>180?'…':''}</p>}
  {item.children.length>0&&<ul>{item.children.map((child,i)=><li key={child.id}>Cảnh {i+1} · {workflowStatusLabels[child.status]}</li>)}</ul>}
  {result?.target&&<button type="button" className="secondary" onClick={()=>onRead(result.target)}>Đọc nội dung</button>}
 </li>;
}

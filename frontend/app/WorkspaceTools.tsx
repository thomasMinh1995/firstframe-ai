"use client";
import {Fragment,useEffect,useState,useId} from 'react';
import type {Project} from './projectsApi';
import type {DraftRun} from './draftRunsApi';
import {draftRunActionLabel} from './draftRunsApi';
import type {TourStep} from './onboardingState';
import {progressCopy,progressLanguage,type OperationKind,type OperationStep} from './progressState';
import {revealWorkspaceTarget} from './WorkspaceStage';
import {workspaceGroup,workspaceToolSteps,toolOperations,type WorkspaceTool} from './workspaceToolState';
import './workspaceTools.css';

function useWorkspaceStage(projectId?:string) {
  const [stage,setStage]=useState('workspace-idea');
  useEffect(()=>{
    const workspace=document.querySelector<HTMLElement>('[data-desktop-stage]');
    setStage(workspace?.dataset.desktopStage??'workspace-idea');
    const change=(e:Event)=>setStage((e as CustomEvent<string>).detail);
    workspace?.addEventListener('workspace-stage-change',change);
    return()=>workspace?.removeEventListener('workspace-stage-change',change);
  },[projectId]);
  return stage;
}
function openTarget(id:string) {
  const target=document.getElementById(id);
  if(!target)return;
  revealWorkspaceTarget(target);
  if(target instanceof HTMLDetailsElement)target.open=true;
  target.scrollIntoView({block:'start'});target.focus({preventScroll:true});
}
export function WorkspaceNavigation({project,tourStep,draftRun}: {
  project:Project|null;draftRun?:DraftRun|null;tourStep?:TourStep;briefChanged:boolean;creatingPlan:boolean;analyzing:boolean;
}) {
  const stage=useWorkspaceStage(project?.id);
  useEffect(()=>{
    const workspace=document.querySelector<HTMLElement>('[data-desktop-stage]');
    const remember=(e:Event)=>{try{sessionStorage.setItem(`firstframe-stage:${project?.id}`,(e as CustomEvent<string>).detail)}catch{}};
    workspace?.addEventListener('workspace-stage-change',remember);
    let previous:string|null=null;
    try{previous=sessionStorage.getItem(`firstframe-stage:${project?.id}`)}catch{}
    revealWorkspaceTarget(document.getElementById(previous??'workspace-idea')??document.getElementById('workspace-idea'));
    return()=>workspace?.removeEventListener('workspace-stage-change',remember);
  },[project?.id]);
  const shown=tourStep==='draft-run'?'draft-run':tourStep&&['idea','script','export'].includes(tourStep)?`workspace-${tourStep}`:stage;
  const group=workspaceGroup(shown);
  const hasPrivateDraft=!!draftRun&&draftRun.project_id===project?.id&&draftRun.adopted_revision===null&&draftRun.completed_scenes>0;
  const finishHint=hasPrivateDraft?(project?.screenplay?'Bản đang lưu · Nháp mới chưa nhận':'Chưa nhận nháp vào workspace'):null;
  const items=[
    {group:'idea',id:'workspace-idea',label:'Ý tưởng',available:!!project},
    {group:'draft',id:project?.screenplay?'workspace-script':project?.draft?'workspace-draft':'draft-run',label:'Bản nháp & review',available:!!project},
    {group:'finish',id:'workspace-export',label:'Hoàn tất',available:!!project?.screenplay},
  ];
  return <aside className="workspace-rail"><p className="eyebrow">Câu chuyện của bạn</p><nav className="workspace-stage-nav" aria-label="Hành trình câu chuyện">
    {items.map((item,i)=><Fragment key={item.group}>{i>0&&<span className="workspace-journey-arrow" aria-hidden="true">↓</span>}<button type="button" disabled={!item.available} aria-controls={item.id} aria-current={item.available&&group===item.group?'step':undefined} onClick={()=>openTarget(item.id)}>
      <span className="workspace-stage-number" aria-hidden="true">{String(i+1).padStart(2,'0')}</span><span>{item.label}<small>{item.group==='finish'&&finishHint?finishHint:!item.available?(item.group==='finish'?'Chưa có kịch bản':'Chưa có nội dung'):group===item.group?'Đang làm việc':'Xem lại'}</small></span>
    </button></Fragment>)}
  </nav><button type="button" className="secondary workspace-run-link" disabled={!project} onClick={()=>openTarget('draft-run')}>Tạo hoặc mở lại bản nháp</button></aside>;
}

type Tool={id:WorkspaceTool;label:string;target:string;available:boolean};
type NavigationRun=DraftRun&{workflow_items?:{id:string;kind:string;status:string;children:{id:string;kind:string;status:string}[]}[]};
export function WorkspaceTools({project,saved,dirty,busy,run,steps,timing,onStartDraft}: {
  project:Project;saved:Project;dirty:boolean;busy:boolean;run:NavigationRun|null;steps:OperationStep[];
  timing:{kind:OperationKind;finishedAt:number|null}|null;onStartDraft:()=>void;
}) {
  const stage=useWorkspaceStage(project.id),group=workspaceGroup(stage),selectId=useId();
  const [selected,setSelected]=useState<{stage:string;tool:WorkspaceTool}|null>(null);
  const tools:Tool[]=group==='idea'?[
    {id:'moment',label:'Khoảnh khắc',target:'idea',available:true},
    {id:'clarify',label:'Làm rõ',target:project.analysis?'workspace-choices':'draft-run',available:!!project.analysis||!!run},
    {id:'limits',label:'Điều muốn giữ',target:'constraints',available:true},
  ]:group==='finish'?[
    {id:'reader',label:'Đọc toàn bộ',target:'workspace-export',available:!!saved.screenplay},
    {id:'selection',label:'Chọn bản xuất',target:'workspace-export-choice',available:!!saved.screenplay},
    {id:'pdf',label:'Bản PDF đã giữ',target:'workspace-export-pdf',available:!!saved.screenplay_handoff},
  ]:[
    {id:'plan',label:'Story plan',target:'workspace-draft',available:!!project.draft},
    {id:'outline',label:'Dàn cảnh',target:'workspace-outline',available:!!project.draft},
    {id:'write',label:'Viết & sửa',target:'workspace-script',available:!!project.draft||!!project.screenplay},
    {id:'review',label:'Góp ý AI',target:project.screenplay?'workspace-script':'workspace-draft',available:!!project.draft||!!project.screenplay},
    {id:'history',label:'Phiên bản',target:'workspace-history',available:true},
  ];
  const current=selected?.stage===stage&&tools.some(t=>t.id===selected.tool)?selected.tool
    :stage==='workspace-outline'?'outline':stage==='workspace-draft'?'plan':stage==='workspace-history'?'history':group==='draft'?'write':tools[0].id;
  const process=group==='draft'?workspaceToolSteps(current,saved,dirty):[];
  const live=timing&&toolOperations[current]?.includes(timing.kind)?steps:[];
  const runKinds:Partial<Record<WorkspaceTool,string[]>>={plan:['plan','plan_review'],outline:['outline'],write:['write'],review:['review','review_scene']};
  const runSteps=run?.workflow_items?.filter(item=>runKinds[current]?.includes(item.kind)).flatMap(item=>item.children.length?item.children:[item])??[];
  const runLabels:Record<string,string>={plan:'Tạo Story plan',plan_review:'Đối chiếu Story plan',outline:'Tạo dàn cảnh',write:'Viết nội dung cảnh',review:'Góp ý kịch bản',review_scene:'Góp ý cảnh'};
  const runStates:Record<string,string>={pending:'Chờ bước trước',running:'Đang xử lý',completed:'Đã có kết quả',needs_input:'Cần bạn xem',warning:'Cần kiểm tra',failed:'Chưa hoàn tất',interrupted:'Gián đoạn',cancelled:'Đã hủy',skipped:'Chưa thực hiện',unknown:'Chưa rõ trạng thái'};
  const copy=progressCopy[progressLanguage(project.response_language)];
  function choose(tool:Tool) {
    openTarget(tool.target);
    const target=document.getElementById(tool.target);
    const nextStage=target?.closest<HTMLElement>('[data-workspace-stage]')?.dataset.workspaceStage??stage;
    setSelected({stage:nextStage,tool:tool.id});
    document.dispatchEvent(new CustomEvent('workspace-tool-change',{detail:tool.id}));
  }
  const existing=!!project.screenplay||!!project.draft;
  return <section className="workspace-tools-at-hand" aria-label="Công cụ trong workspace">
    <div className="workspace-next"><div><span>Bước tiếp theo</span><p>{group==='idea'?'Giữ ý tưởng và tiếp tục bản nháp của bạn.':group==='draft'?'Chỉnh từng phần tại chỗ, rồi đọc đúng bản đã lưu.':'Đọc, chọn phiên bản và tải PDF từ bản đã chọn.'}</p></div>
      <button type="button" disabled={busy||(group==='idea'&&!run&&!existing&&!project.idea.trim())||(group!=='idea'&&!saved.screenplay&&group!=='draft')} onClick={()=>{
        if(group==='idea'){if(run)onStartDraft();else if(existing)openTarget(project.screenplay?'workspace-script':'workspace-draft');else onStartDraft();}
        else openTarget(saved.screenplay?(group==='finish'?'workspace-export-choice':'workspace-export'):'draft-run');
      }}>{group==='idea'?(draftRunActionLabel(run)??(existing?'Mở bản nháp':'Tạo bản nháp')):group==='draft'?(saved.screenplay?'Đọc & xuất PDF':'Mở tiến độ bản nháp'):'Chọn bản & tải PDF'} <span aria-hidden="true">→</span></button>
    </div>
    <div className="workspace-tool-picker">
      <label htmlFor={selectId}>{group==='finish'?'Phần cần xem':'Phần cần sửa'}</label>
      <select id={selectId} value={current} disabled={busy} onChange={event=>{const tool=tools.find(item=>item.id===event.target.value);if(tool?.available)choose(tool)}}>
        {tools.map(tool=><option key={tool.id} value={tool.id} disabled={!tool.available}>{tool.label}{!tool.available?' · Chưa có nội dung':''}</option>)}
      </select>
      <div className="workspace-tool-actions">
        <button type="button" disabled={busy||!tools.find(tool=>tool.id===current)?.available} onClick={()=>{const tool=tools.find(item=>item.id===current);if(tool)choose(tool)}}>Mở {tools.find(tool=>tool.id===current)?.label}</button>
        <button type="button" className="secondary" disabled={busy} onClick={()=>openTarget('draft-run')}>Mở tiến độ bản nháp</button>
      </div>
    </div>
    {process.length>0&&<details className="workspace-tool-process" key={`${project.id}:${current}`} open><summary>Tiến trình · {tools.find(t=>t.id===current)?.label}<span>{live.some(s=>s.status==='active')||runSteps.some(s=>s.status==='running')?'Đang xử lý':'Nội dung đã lưu'}</span></summary>
      <ol>{process.map(step=><li key={step.label} data-state={step.status}><span aria-hidden="true">{step.status==='available'?'✓':step.status==='unsaved'?'…':'○'}</span><div>{step.label}<small>{step.detail}</small></div><em>{step.status==='available'?'Đã có':step.status==='unsaved'?'Chờ lưu':'Chưa có'}</em></li>)}</ol>
      {live.length>0&&<details open={timing?.finishedAt===null}><summary>Các bước của lượt xử lý gần nhất</summary><ol>{live.map(s=><li key={`${s.stage}:${s.occurrence}`}><span aria-hidden="true">{s.status==='completed'?'✓':s.status==='failed'?'!':'…'}</span><div>{copy.stages[s.stage]??copy.other}</div><em>{copy[s.status]}</em></li>)}</ol></details>}
      {runSteps.length>0&&<details open><summary>Các bước của lượt tạo đang có</summary><ol>{runSteps.map((s,i)=><li key={s.id}><span aria-hidden="true">{s.status==='completed'?'✓':s.status==='running'?'…':'○'}</span><div>{runLabels[s.kind]??'Xử lý bản nháp'}{s.scene_id?` · ${project.screenplay?.scenes.find(scene=>scene.id===s.scene_id)?.heading||saved.screenplay?.scenes.find(scene=>scene.id===s.scene_id)?.heading||`Cảnh ${i+1}`}`:runSteps.length>1?` · ${i+1}`:''}</div><em>{runStates[s.status]??'Chưa rõ trạng thái'}</em></li>)}</ol></details>}
      {run&&<p className="storage-note">Lượt tạo hiện có: {run.completed_scenes}/{run.total_scenes||'…'} cảnh đã giữ. <button type="button" className="secondary" onClick={()=>openTarget('draft-run')}>Mở đúng tiến độ</button></p>}
    </details>}
  </section>;
}

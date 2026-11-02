"use client";
import {Fragment,useEffect,useState,useId} from 'react';
import type {Project} from './projectsApi';
import type {DraftRun} from './draftRunsApi';
import type {TourStep} from './onboardingState';
import {progressCopy,progressLanguage,type OperationKind,type OperationStep} from './progressState';
import {revealWorkspaceTarget} from './WorkspaceStage';
import {workspaceGroup,workspaceJourney,workspaceNextStep,workspaceToolSteps,toolOperations,type WorkspaceTool} from './workspaceToolState';
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
export function WorkspaceNavigation({project,tourStep,draftRun,briefChanged}: {
  project:Project|null;draftRun?:DraftRun|null;tourStep?:TourStep;briefChanged:boolean;
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
  const shown=tourStep==='draft-run'?(!briefChanged&&project?.draft?'workspace-draft':project?.analysis&&!briefChanged?'workspace-choices':'workspace-idea'):tourStep&&['idea','script','export'].includes(tourStep)?`workspace-${tourStep}`:stage;
  const hasPrivateDraft=!!draftRun&&draftRun.project_id===project?.id&&draftRun.adopted_revision===null&&draftRun.completed_scenes>0;
  const finishHint=hasPrivateDraft?(project?.screenplay?'Bản đang lưu · Nháp mới chưa nhận':'Chưa nhận nháp vào workspace'):null;
  const items=workspaceJourney(project,briefChanged);
  return <aside className="workspace-rail"><p className="eyebrow">Câu chuyện của bạn</p><nav className="workspace-stage-nav" aria-label="Hành trình câu chuyện">
    {items.map((item,i)=><Fragment key={item.id}>{i>0&&<span className="workspace-journey-arrow" aria-hidden="true">↓</span>}<button type="button" disabled={!item.available} aria-controls={item.id} aria-current={item.available&&shown===item.id?'step':undefined} onClick={()=>openTarget(item.id)}>
      <span className="workspace-stage-number" aria-hidden="true">{String(i+1).padStart(2,'0')}</span><span>{item.label}<small>{item.id==='workspace-export'&&finishHint?finishHint:!item.available?(item.id==='workspace-export'?'Chưa có kịch bản':'Chưa có nội dung'):shown===item.id?'Đang làm việc':'Xem lại'}</small></span>
    </button></Fragment>)}
  </nav><button type="button" className="secondary workspace-run-link" disabled={!project} onClick={()=>openTarget('draft-run')}>Tùy chọn: tạo nháp tự động</button><button type="button" className="secondary workspace-run-link" disabled={!project} onClick={()=>openTarget('workspace-history')}>Các phiên bản đã giữ</button></aside>;
}

type Tool={id:WorkspaceTool;label:string;target:string;available:boolean};
type NavigationRun=DraftRun&{workflow_items?:{id:string;kind:string;status:string;children:{id:string;kind:string;status:string}[]}[]};
export function WorkspaceTools({project,saved,dirty,busy,run,steps,timing,briefChanged,onAnalyze}: {
  project:Project;saved:Project;dirty:boolean;busy:boolean;run:NavigationRun|null;steps:OperationStep[];
  timing:{kind:OperationKind;finishedAt:number|null}|null;briefChanged:boolean;onAnalyze:()=>void;
}) {
  const stage=useWorkspaceStage(project.id),group=workspaceGroup(stage),selectId=useId();
  const [selected,setSelected]=useState<{stage:string;tool:WorkspaceTool}|null>(null);
  const tools:Tool[]=group==='idea'?[
    {id:'moment',label:'Khoảnh khắc',target:'idea',available:true},
    {id:'clarify',label:'Làm rõ',target:'workspace-choices',available:!!project.analysis&&!briefChanged},
    {id:'limits',label:'Điều muốn giữ',target:'constraints',available:true},
  ]:group==='finish'?[
    {id:'reader',label:'Đọc toàn bộ',target:'workspace-export',available:!!saved.screenplay},
    {id:'selection',label:'Chọn bản xuất',target:'workspace-export-choice',available:!!saved.screenplay},
    {id:'pdf',label:'Bản PDF đã giữ',target:'workspace-export-pdf',available:!!saved.screenplay_handoff},
  ]:[
    {id:'plan',label:'Story plan',target:'workspace-draft',available:!!project.draft},
    {id:'outline',label:'Dàn cảnh',target:'workspace-outline',available:!!project.draft||!!project.scene_outline},
    {id:'write',label:'Viết & sửa',target:'workspace-script',available:!!project.scene_outline||!!project.screenplay},
    {id:'review',label:'Góp ý AI',target:project.screenplay?'workspace-script':'workspace-draft',available:!!project.draft||!!project.screenplay},
    {id:'history',label:'Phiên bản',target:'workspace-history',available:true},
  ];
  const current=selected?.stage===stage&&tools.some(t=>t.id===selected.tool)?selected.tool
    :stage==='workspace-outline'?'outline':stage==='workspace-draft'?'plan':stage==='workspace-history'?'history':stage==='workspace-choices'?'clarify':group==='draft'?'write':tools[0].id;
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
  const next=workspaceNextStep(stage,project,briefChanged,!!run);
  const nextCopy=stage==='workspace-idea'?'Bắt đầu từ một quan sát, hành động hoặc chi tiết đời sống.':stage==='workspace-choices'?'Trả lời, để mở hoặc chỉnh lựa chọn trước khi yêu cầu AI tạo Story plan.':stage==='workspace-draft'?'Đọc và sửa Story plan; bạn quyết định khi nào chuyển sang dàn cảnh.':stage==='workspace-outline'?'Tự dựng cảnh hoặc yêu cầu gợi ý, rồi lưu bản nguồn bạn muốn viết tiếp.':stage==='workspace-script'?'Tự viết và sửa từng cảnh; yêu cầu AI hỗ trợ khi cần.':'Đọc đúng bản đã lưu, chọn phiên bản rồi xuất PDF.';
  return <section className="workspace-tools-at-hand" aria-label="Công cụ trong workspace">
    <div className="workspace-next"><div><span>Bước tiếp theo</span><p>{nextCopy}</p></div>
      <button type="button" disabled={busy||(next.target==='analyze'&&!project.idea.trim())} onClick={()=>{
        if(next.target==='analyze')onAnalyze();else openTarget(next.target);
      }}>{next.label} <span aria-hidden="true">→</span></button>
    </div>
    <div className="workspace-tool-picker">
      <label htmlFor={selectId}>{group==='finish'?'Phần cần xem':'Phần cần sửa'}</label>
      <select id={selectId} value={current} disabled={busy} onChange={event=>{const tool=tools.find(item=>item.id===event.target.value);if(tool?.available)choose(tool)}}>
        {tools.map(tool=><option key={tool.id} value={tool.id} disabled={!tool.available}>{tool.label}{!tool.available?' · Chưa có nội dung':''}</option>)}
      </select>
      <div className="workspace-tool-actions">
        <button type="button" disabled={busy||!tools.find(tool=>tool.id===current)?.available} onClick={()=>{const tool=tools.find(item=>item.id===current);if(tool)choose(tool)}}>Mở {tools.find(tool=>tool.id===current)?.label}</button>
        <button type="button" className="secondary" disabled={busy} onClick={()=>openTarget('draft-run')}>Mở lượt tự động</button>
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

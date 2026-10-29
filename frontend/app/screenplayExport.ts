import {projectRequest,type Project} from './projectsApi';
import type {Screenplay,ScreenplaySelectionInput} from './screenplayTypes';

export async function selectReadScreenplay(source:Project,input:ScreenplaySelectionInput,read:Screenplay):Promise<Project> {
  const target=input.source_version_id==='current'?source.screenplay:source.screenplay_versions?.find(v=>v.id===input.source_version_id)?.screenplay;
  if(!target||JSON.stringify(target)!==JSON.stringify(read))throw new Error('Bản để xuất đã đổi trong lúc lưu. Hãy đọc lại và chọn đúng bản trước khi tải PDF.');
  return projectRequest(`/${source.id}/screenplay-selections`,'POST',{revision:source.revision,...input});
}

export async function downloadScreenplayPdf(projectId:string,selectionId:string):Promise<void> {
  const base=process.env.NEXT_PUBLIC_API_BASE_URL??'http://localhost:8000';
  const response=await fetch(`${base}/api/projects/${encodeURIComponent(projectId)}/screenplay-selections/${encodeURIComponent(selectionId)}/pdf`,{cache:'no-store',signal:AbortSignal.timeout(45_000)});
  if(!response.ok){const error=await response.json().catch(()=>null);throw new Error(typeof error?.detail==='string'?error.detail:'Chưa tải được PDF. Bản đã chọn vẫn giữ, bạn có thể thử lại.');}
  const blob=await response.blob();
  if(!response.headers.get('content-type')?.startsWith('application/pdf')||await blob.slice(0,5).text()!=='%PDF-')throw new Error('Chưa nhận được tệp PDF hợp lệ. Bản đã chọn vẫn giữ.');
  const filename=response.headers.get('content-disposition')?.match(/filename="([a-zA-Z0-9.-]+)"/)?.[1]??`screenplay-${selectionId}.pdf`;
  const url=URL.createObjectURL(blob),link=document.createElement('a');
  try{link.href=url;link.download=filename;document.body.appendChild(link);link.click();}
  finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
}

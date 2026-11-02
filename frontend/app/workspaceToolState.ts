import type {Project} from './projectsApi';
import type {OperationKind} from './progressState';

export type WorkspaceTool = 'moment'|'clarify'|'limits'|'plan'|'outline'|'write'|'review'|'history'|'reader'|'selection'|'pdf';
export const toolOperations: Partial<Record<WorkspaceTool, OperationKind[]>> = {
  plan:['plan'], outline:['scene-suggestions','scene-sketches'],
  write:['screenplay-proposals'], review:['review','screenplay-reviews'],
};
export function workspaceGroup(stage:string) {
  return ['workspace-idea','workspace-choices'].includes(stage)?'idea':stage==='workspace-export'?'finish':'draft';
}
export function workspaceJourney(project:Project|null, briefChanged:boolean) {
  return [
    {id:'workspace-idea',label:'Chất liệu',available:!!project},
    {id:'workspace-choices',label:'Làm rõ',available:!!project?.analysis&&!briefChanged},
    {id:'workspace-draft',label:'Story plan',available:!!project?.draft},
    {id:'workspace-outline',label:'Dàn cảnh',available:!!project?.draft||!!project?.scene_outline},
    {id:'workspace-script',label:'Viết & sửa',available:!!project?.scene_outline||!!project?.screenplay},
    {id:'workspace-export',label:'Đọc & xuất',available:!!project?.screenplay},
  ];
}
export function workspaceNextStep(stage:string, project:Project, briefChanged:boolean, blockingRun:boolean) {
  if(stage==='workspace-idea') {
    if(blockingRun)return {label:'Mở lượt tự động đang có',target:'draft-run'};
    if(!project.analysis||briefChanged)return {label:'Cùng làm rõ chất liệu',target:'analyze'};
    return {label:'Xem các lựa chọn làm rõ',target:'workspace-choices'};
  }
  if(stage==='workspace-choices')return project.draft
    ?{label:'Đọc Story plan đang có',target:'workspace-draft'}
    :{label:'Xem lựa chọn trước khi tạo Story plan',target:'clarification-complete'};
  if(stage==='workspace-draft')return {label:'Sang dàn cảnh',target:'workspace-outline'};
  if(stage==='workspace-outline')return project.scene_outline||project.screenplay
    ?{label:'Sang viết & sửa',target:'workspace-script'}
    :{label:'Chọn nguồn để bắt đầu dàn cảnh',target:'workspace-outline'};
  if(stage==='workspace-script')return project.screenplay
    ?{label:'Đọc & xuất bản đã lưu',target:'workspace-export'}
    :{label:'Xem nguồn trước khi bắt đầu viết',target:'workspace-script-start'};
  if(stage==='workspace-export')return {label:'Chọn bản đã đọc để xuất',target:'workspace-export-choice'};
  return {label:'Về chất liệu câu chuyện',target:'workspace-idea'};
}
export function workspaceFallbackStage(stage:string, briefChanged:boolean) {
  return briefChanged && stage === 'workspace-choices' ? 'workspace-idea' : stage;
}
export function workspaceToolSteps(tool:WorkspaceTool, saved:Project, dirty:boolean) {
  const script=saved.screenplay;
  const written=script?.scenes.filter(s=>s.blocks.some(b=>b.text.trim())).length??0;
  const reviews=saved.screenplay_reviews?.length??0;
  const versions=(saved.screenplay_versions?.length??0)+(saved.scene_versions?.length??0)+saved.versions.length;
  const definitions:Partial<Record<WorkspaceTool,[string,boolean,string][]>>={
    plan:[['Ý tưởng và lựa chọn nguồn',!!saved.idea.trim(),'Nguồn đã lưu cùng dự án.'],['Story plan',!!saved.draft,'Mở bản hiện có để chỉnh; không tự tạo lại.']],
    outline:[['Nguồn Story plan',!!saved.draft,'Giữ nguyên nguồn câu chuyện.'],['Dàn cảnh',!!saved.scene_outline,`${saved.scene_outline?.scenes.length??0} cảnh đã lưu.`],['Nguồn để viết tiếp',!!saved.scene_handoff,'Chỉ đổi nguồn khi bạn chủ động chọn.']],
    write:[['Nguồn dàn cảnh',!!script,'Nguồn được giữ riêng cùng kịch bản.'],['Nội dung các cảnh',written>0,`${written}/${script?.scenes.length??0} cảnh có nội dung đã lưu; chưa đánh giá chất lượng.`]],
    review:[['Bản thảo để đọc',!!script||!!saved.draft,'Góp ý đọc đúng nguồn của từng lượt.'],['Góp ý đã giữ',reviews>0||!!saved.feedback,`${reviews} lượt góp ý cảnh đã lưu. Mở góp ý để đối chiếu nguồn trước khi dùng.`]],
    history:[['Bản đang làm việc',true,`Revision ${saved.revision} đã xác nhận lưu.`],['Các phiên bản trước',versions>0,`${versions} phiên bản được giữ để đọc và khôi phục.`]],
  };
  return [...(definitions[tool]??[]).map(([label,available,detail])=>({label,status:available?'available' as const:'missing' as const,detail})),
    {label:'Thay đổi trên màn hình',status:dirty?'unsaved' as const:'available' as const,detail:dirty?'Đang có sửa chưa xác nhận lưu; bản đã lưu vẫn được giữ.':'Đã đồng bộ với bản lưu hiện tại.'}];
}

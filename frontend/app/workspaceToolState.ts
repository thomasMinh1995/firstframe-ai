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

"use client";
import {useState} from "react";
import {sceneSketchUrl, type Project} from "./projectsApi";
import {SceneHint} from "./SceneHint";
import type {Scene} from "./sceneTypes";

export type SketchInput = {request_id: string; scene_id: string; instructions: string};
export function SketchImage({projectId, sketchId, alt}: {projectId: string; sketchId: string; alt: string}) {
  const [missing, setMissing] = useState(false);
  return missing ? <span role="status">Tệp ảnh thiếu hoặc lỗi. Nội dung cảnh vẫn được giữ; có thể viết tiếp không cần ảnh.</span>
    : <img className="scene-sketch-image" src={sceneSketchUrl(projectId, sketchId)} alt={alt} onError={() => setMissing(true)} />;
}

export function SceneSketchPanel({project, scene, dirty, onGenerate, onInspect, onDecide}: {
  project: Project; scene: Scene; dirty: boolean;
  onGenerate: (input: SketchInput) => Promise<void>; onInspect: () => Promise<boolean>;
  onDecide: (id: string, action: "keep" | "discard") => void;
}) {
  const [instructions, setInstructions] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const all = project.scene_sketches ?? [];
  const uncertain = sent !== null && !all.some(s => s.id === sent);
  const selected = project.selected_scene_sketches?.[scene.id];
  return <section className="scene-sketches" aria-label="Phác hình cảnh">
    <SceneHint title="Phác hình theo yêu cầu"><p>Ảnh phác tham khảo có thể sai nhân vật, hành động hoặc chi tiết. Xem trước rồi tự chọn giữ; ảnh không chứng minh cảnh đúng hoặc hay.</p>
    <p className="storage-note">Một cảnh/một ảnh local, 768×432; chờ tối đa 180 giây, không tự retry. Lưu mọi sửa đang chờ trước khi tạo.
      Không cần ảnh để lưu hoặc viết tiếp. Runtime/model cần được cài và bật riêng ở backend.</p>
      <p>Ảnh mới chưa chọn không thay ảnh đang giữ. Tải JSON chỉ sao lưu nội dung và tham chiếu ảnh, không chứa tệp ảnh.</p>
    </SceneHint>
    <label>Khoảnh khắc muốn phác · tùy chọn<textarea rows={2} maxLength={1000} value={instructions} onChange={e => setInstructions(e.target.value)} /></label>
    <div className="scene-order"><button type="button" disabled={uncertain || all.some(s=>s.status==='pending') || all.length>=20 || !scene.action.trim()}
      onClick={()=>{const request_id=crypto.randomUUID();setSent(request_id);void onGenerate({request_id,scene_id:scene.id,instructions});}}>Tạo một hình phác</button>
      <button type="button" className="secondary" onClick={async()=>{if(await onInspect())setSent(null);}}>Kiểm tra ảnh đã lưu</button></div>
    {all.length>=20 && <p role="status">Đã đủ 20 lượt phác của dự án; vẫn lưu và viết tiếp được.</p>}
    {uncertain && <p role="status">Chưa rõ kết quả. Kiểm tra ảnh đã lưu trước khi yêu cầu lượt mới.</p>}
    {[...all].reverse().filter(s=>s.scene_id===scene.id).map(s=><details key={s.id} open={s.status==='ready'}>
      <summary>Hình phác · nguồn dàn cảnh phiên bản {s.source_outline.version} · {selected===s.id?'đang giữ':s.status==='pending'?'đang chờ':s.status==='failed'?'lỗi':s.status==='discarded'?'đã bỏ':'xem trước'}</summary>
      <p className="storage-note">{s.duration_seconds!==null?`${s.duration_seconds.toFixed(1)} giây. `:''}Nguồn được giữ tại lúc yêu cầu; không gồm góp ý chưa dùng.</p>
      {s.error && <p role="status">Lượt này lỗi ({s.error}); text và ảnh đã giữ không đổi. Kiểm tra cấu hình hoặc nguyên nhân trước khi chủ động tạo lượt mới.</p>}
      {s.status==='pending' && <p role="status">Bỏ yêu cầu chỉ ngừng chờ/chọn kết quả; tiến trình có thể vẫn đang chạy. Không tự retry.</p>}
      {s.asset_id && <SketchImage key={s.asset_id} projectId={project.id} sketchId={s.id} alt={`Phác hình tham khảo của cảnh ${s.source_outline.scenes.find(c=>c.id===s.scene_id)?.title || 'đã chọn'}`} />}
      {s.status==='ready' && !(project.applicable_sketch_ids??[]).includes(s.id) && <p role="status">Nguồn đã đổi. Giữ ảnh cũ để đối chiếu, không chọn ảnh này cho nguồn hiện tại.</p>}
      <details><summary>Đối chiếu nguồn và yêu cầu phác</summary><p className="preserve-lines">{s.prompt}</p></details>
      <div className="scene-order">{s.status==='ready' && <button type="button" disabled={dirty || selected===s.id || !(project.applicable_sketch_ids??[]).includes(s.id)} onClick={()=>onDecide(s.id,'keep')}>Giữ hình phác này</button>}
        {s.status!=='discarded' && <button type="button" className="secondary" onClick={()=>onDecide(s.id,'discard')}>{selected===s.id?'Bỏ hình đang giữ':'Bỏ hình phác này'}</button>}</div>
      {dirty && s.status==='ready' && <p className="storage-note">Còn sửa chưa lưu. Lưu và đối chiếu nguồn trước khi chọn giữ; bỏ hình không tự lưu text.</p>}
    </details>)}
  </section>;
}

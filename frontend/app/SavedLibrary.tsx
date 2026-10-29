"use client";

import {useEffect, useRef, useState, type ReactNode} from "react";
import {createPortal} from "react-dom";
import type {Project} from "./projectsApi";
import {stagingLabels, type StagingKey, type Scene, type SceneSketch} from "./sceneTypes";
import type {Screenplay} from "./screenplayTypes";
import {SketchImage} from "./SceneSketchPanel";
import {screenplaySketches} from "./screenplaySketches";
import "./savedLibrary.css";

export function SavedLibrary({project, busy, outline, storyPlan, onRestoreScreenplay}: {
  project: Project; busy: boolean; outline: ReactNode; storyPlan: ReactNode;
  onRestoreScreenplay: (id: string) => Promise<void>;
}) {
  const [tab, setTab] = useState("script");
  const [versionId, setVersionId] = useState("current");
  const [sourceId, setSourceId] = useState<string | null>(project.screenplay?.scenes[0]?.id ?? null);
  const [preview, setPreview] = useState<{sketch: SceneSketch; heading: string; trigger: HTMLButtonElement} | null>(null);
  const sourceClose = useRef<HTMLButtonElement>(null);
  const mobileClose = useRef<HTMLButtonElement>(null);
  const sceneTriggers = useRef(new Map<string, HTMLButtonElement>());
  const versions = [
    ...(project.screenplay ? [{id:"current", screenplay:project.screenplay, created_at:project.updated_at}] : []),
    ...[...(project.screenplay_versions ?? [])].reverse(),
  ];
  const selected = versions.find(version => version.id === versionId) ?? versions[0];
  const script = selected?.screenplay;
  const selectedScene = script?.scenes.find(scene => scene.id === sourceId);
  const source = script?.source_outline.scenes.find(scene => scene.id === selectedScene?.source_scene_id);
  const images = script ? screenplaySketches(project, script.source_outline) : {};

  useEffect(() => {
    setVersionId("current");
    setSourceId(project.screenplay?.scenes[0]?.id ?? null);
    setPreview(null);
  }, [project.screenplay?.id, project.screenplay?.version]);

  function closeSource() {
    const id = sourceId;
    setSourceId(null);
    if (id) sceneTriggers.current.get(id)?.focus({preventScroll:true});
  }
  function openSource(id: string) {
    setSourceId(id);
    // Let the responsive detail panel mount before moving keyboard focus.
    requestAnimationFrame(() => {
      const close = sourceClose.current?.getClientRects().length ? sourceClose.current : mobileClose.current;
      close?.focus({preventScroll:true});
    });
  }
  return <fieldset className="workspace-library saved-library" disabled={busy} aria-label="Quản lý bản đã lưu">
    <header className="library-heading"><h2>Bản đã lưu</h2><p>{project.title}</p></header>
    <nav className="library-tabs" aria-label="Loại nội dung đã lưu">
      {([["script","Kịch bản"],["outline","Dàn cảnh"],["plan","Story plan"]] as const).map(([id,label]) =>
        <button key={id} type="button" aria-pressed={tab===id} onClick={() => {setTab(id); setPreview(null);}}>{label}</button>)}
    </nav>
    {tab === "script" && (selected && script ? <div className="library-layout">
      <aside className="library-versions" aria-label="Các phiên bản kịch bản"><p className="library-overline">Phiên bản kịch bản</p>
        {versions.map(version => <button type="button" key={version.id} aria-pressed={selected.id===version.id} onClick={() => {
          setVersionId(version.id);setSourceId(version.screenplay.scenes[0]?.id ?? null);setPreview(null);
        }}><strong>{version.id === "current" && <span className="library-saved-dot" />}Phiên bản {version.screenplay.version}</strong>
          <small>{version.id === "current" ? "Đang lưu" : new Date(version.created_at).toLocaleString("vi-VN")}</small>
          <small>{version.screenplay.scenes.length} cảnh</small></button>)}
      </aside>
      <section className="library-document" aria-label="Nội dung kịch bản đã lưu">
        <div className="library-document-heading"><div><h3>{script.source_outline.source.draft.title || project.title}</h3>
          <p>Phiên bản {script.version} · {script.scenes.length} cảnh · {selected.id === "current" ? "Đang lưu" : "Bản trước"}</p></div><span className="library-tag">Chỉ đọc</span></div>
        {!script.scenes.length && <p className="library-empty">Kịch bản này chưa có cảnh.</p>}
        <div className={`library-reading-layout${source ? " has-source" : ""}`}>
          <div className="library-scenes">{script.scenes.map((scene,index) => {
            const image = images[scene.source_scene_id];
            return <article className={`library-scene${sourceId === scene.id ? " is-selected" : ""}`} key={scene.id} data-library-scene={scene.id}>
              <button type="button" className="library-script-hit" ref={node => {if(node)sceneTriggers.current.set(scene.id,node);else sceneTriggers.current.delete(scene.id);}}
                aria-label={`Đọc Dàn cảnh nguồn của cảnh ${index+1}: ${scene.heading || "Chưa có tiêu đề"}`} aria-expanded={sourceId===scene.id}
                onClick={() => openSource(scene.id)}><span className="library-scene-kicker">CẢNH {String(index+1).padStart(2,"0")}<span aria-hidden="true">↶</span></span>
                <span className="library-scene-title">{scene.heading.trim() || "Cảnh chưa có tiêu đề"}</span>
                <span className="library-script-text">{!scene.blocks.length && <span className="library-script-paragraph">Cảnh chưa viết.</span>}
                  {scene.blocks.map(block => <span key={block.id} className={block.kind === "dialogue" ? "library-dialogue" : "library-script-paragraph"}>
                    {block.kind === "dialogue" && <span className="library-speaker">{block.speaker.trim() || "Chưa có người nói"}</span>}
                    {block.text.trim() ? block.text : "Khối chưa có nội dung."}</span>)}
                </span>
              </button>
              <figure className="library-attachment" aria-label={`Hình đính kèm cảnh ${index+1}`}>
                {image?.matches ? <button type="button" className="library-image-button" aria-label={`Xem hình phác cảnh ${index+1}`}
                  onClick={event => setPreview({sketch:image.sketch,heading:`Hình phác · Cảnh ${index+1}`,trigger:event.currentTarget})}>
                  <SketchImage key={image.sketch.asset_id} projectId={project.id} sketchId={image.sketch.id} alt={`Hình dàn cảnh đính kèm cảnh ${index+1}: ${scene.heading}`} />
                </button> : <div className="library-image-empty" aria-label={`Chưa có hình phù hợp cho cảnh ${index+1}`}><span aria-hidden="true">▧</span>Chưa có hình đính kèm</div>}
                <figcaption><span>Hình dàn cảnh đính kèm</span><span>{image?.matches ? `Dàn cảnh nguồn · phiên bản ${image.sketch.source_outline.version}`
                  : image ? "Ảnh đang chọn khác nguồn của kịch bản này." : "Chọn hình cho cảnh tại phần Dàn cảnh."}</span></figcaption>
              </figure>
              <div className="library-scene-footer"><span>Dàn cảnh nguồn · bản {script.source_outline.version}</span>
                <button type="button" className="library-link" onClick={() => openSource(scene.id)}>{sourceId === scene.id ? "Đang đối chiếu" : "Xem Dàn cảnh"}<span aria-hidden="true">↗</span></button>
              </div>
              {sourceId===scene.id && source && <div className="library-mobile-source" onKeyDown={event => {if(event.key === "Escape")closeSource();}}><SourceDetails source={source} script={script}
                index={index} onClose={closeSource} closeRef={mobileClose} /></div>}
            </article>;
          })}</div>
          {source && selectedScene && <aside className="library-source" aria-label="Dàn cảnh nguồn của cảnh đang chọn" onKeyDown={event => {if(event.key === "Escape")closeSource();}}>
            <SourceDetails source={source} script={script} index={script.scenes.indexOf(selectedScene)} onClose={closeSource} closeRef={sourceClose} />
          </aside>}
        </div>
        {selected.id !== "current" && <div className="library-restore"><p>Khôi phục giữ bản hiện tại trong lịch sử; Story plan và Dàn cảnh vẫn được giữ.</p>
          <button type="button" onClick={() => void onRestoreScreenplay(selected.id)}>Khôi phục kịch bản này</button></div>}
        <p className="library-history-note">Đang đọc bản đã lưu. Đối chiếu Dàn cảnh không thay đổi nội dung hoặc khôi phục phiên bản.</p>
      </section>
    </div> : <section className="library-empty"><h3>Chưa có kịch bản đã lưu</h3><p>Bắt đầu viết từ Dàn cảnh, rồi lưu kịch bản để đọc và đối chiếu tại đây.</p>
      <button type="button" className="library-link" onClick={() => setTab("outline")}>Xem các bản Dàn cảnh →</button></section>)}
    {tab === "outline" && <section className="library-other" aria-label="Các bản Dàn cảnh">{outline}</section>}
    {tab === "plan" && <section className="library-other" aria-label="Các bản Story plan">{storyPlan}</section>}
    {preview && <ImagePreview projectId={project.id} preview={preview} onClose={() => setPreview(null)} />}
  </fieldset>;
}

function SourceDetails({source,script,index,onClose,closeRef}: {
  source: Scene; script: Screenplay; index: number; onClose: () => void; closeRef?: React.Ref<HTMLButtonElement>;
}) {
  const fields: [string,string][] = [["Diễn tiến",source.action],["Không gian",[source.location,source.time].filter(Boolean).join(" · ")],
    ["Nhân vật",source.characters],["Mục tiêu",source.goal],["Vai trò của cảnh",source.purpose],["Cảm nhận người xem",source.viewer_intent],["Điều muốn giữ",source.keep_or_avoid],
    ...Object.entries(source.staging_choices).map(([key,value]):[string,string] => [stagingLabels[key as StagingKey],value])];
  return <><div className="library-source-top"><span className="library-tag">Dàn cảnh nguồn</span><button type="button" className="library-icon-button" aria-label="Đóng Dàn cảnh" ref={closeRef} onClick={onClose}>×</button></div>
    <p className="library-source-meta">Phiên bản {script.source_outline.version} · Cảnh {index+1}</p><h3>{source.title}</h3>
    <dl>{fields.filter(([,value]) => value.trim()).map(([label,value]) => <div className="library-field" key={label}><dt>{label}</dt><dd className="preserve-lines">{value}</dd></div>)}</dl>
    <p className="library-source-foot">Nguồn đi cùng bản kịch bản này.</p><button type="button" className="library-link" onClick={onClose}>← Quay lại kịch bản</button></>;
}

function ImagePreview({projectId,preview,onClose}: {projectId:string;preview:{sketch:SceneSketch;heading:string;trigger:HTMLButtonElement};onClose:()=>void}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element=dialog.current;element?.showModal();
    return () => {element?.close();if(preview.trigger.isConnected)preview.trigger.focus({preventScroll:true});};
  }, [preview]);
  return createPortal(<dialog ref={dialog} className="library-image-preview" aria-label={preview.heading} onCancel={event => {event.preventDefault();onClose();}}>
    <div className="library-source-top"><h2>{preview.heading}</h2><button type="button" className="library-icon-button" aria-label="Đóng hình phác" onClick={onClose}>×</button></div>
    <SketchImage projectId={projectId} sketchId={preview.sketch.id} alt={preview.heading} />
    <p>Dàn cảnh nguồn · phiên bản {preview.sketch.source_outline.version}</p>
  </dialog>, document.body);
}

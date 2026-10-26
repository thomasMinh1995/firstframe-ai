"use client";

import { useEffect, useId, useRef, useState, type CSSProperties, type KeyboardEvent, type ReactNode } from "react";
import type { StoryDraft } from "./projectsApi";
import { sectionLabels } from "./storyLabels";

export type DraftField = "title" | "logline" | number;
const narrativeTitles = new Set(["Beginning", "Middle", "Ending"]);
type Span = { start: number; end: number };

// Keep offsets into the shared section text; spaces and paragraph breaks remain untouched.
export function splitStorySection(content: string): Span[] {
  const spans: Span[] = [];
  function add(start: number, end: number) {
    while (start < end && /\s/u.test(content[start])) start++;
    while (end > start && /\s/u.test(content[end - 1])) end--;
    if (start === end) return;
    while (end - start > 200) {
      const gaps = [...content.slice(start, start + 200).matchAll(/\s+/gu)];
      const gap = gaps.at(-1);
      if (!gap || gap.index < 40) break;
      spans.push({ start, end: start + gap.index });
      start += gap.index + gap[0].length;
    }
    spans.push({ start, end });
  }
  let start = 0;
  for (const match of content.matchAll(/(?:[.!?…。！？]+[”"'’)\]]*(?=\s|$)|\r?\n+)/gu)) {
    const end = match.index + match[0].length;
    add(start, end); start = end;
  }
  add(start, content.length);
  return spans.length ? spans : [{ start: 0, end: content.length }];
}

export function replaceStoryBeat(content: string, spans: Span[], part: number, value: string) {
  const { start, end } = spans[part];
  const next = content.slice(0, start) + value + content.slice(end);
  if (next.length > 10000) return null;
  const delta = value.length - (end - start);
  return { content: next, spans: spans.map((span, i) => i < part ? span : i === part
    ? { start, end: start + value.length } : { start: span.start + delta, end: span.end + delta }) };
}

export function StoryPlanEditor({ draft, dirty, onChange, selectedCardId, onSelectCard, inspector }: {
  draft: StoryDraft;
  dirty: boolean;
  onChange: (field: DraftField, value: string) => void;
  selectedCardId?: string; onSelectCard?: (card: { id: string; label: string } | null) => void; inspector?: ReactNode;
}) {
  const [layout, setLayout] = useState(() => draft.sections.map(section => splitStorySection(section.content)));
  const [wideInspector, setWideInspector] = useState(false);
  useEffect(() => {
    const media = window.matchMedia("(min-width: 1200px)");
    const update = () => setWideInspector(media.matches);
    update(); media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  const path = useRef<HTMLOListElement>(null);
  const sections = draft.sections.map((section, index) => ({ section, index }));
  const narrative = sections.filter(({ section }) => narrativeTitles.has(section.title));
  const cards = (narrative.length ? narrative : sections).flatMap(({ section, index }) =>
    layout[index].map((span, part) => ({ section, index, part, span })));
  const context = narrative.length ? sections.filter(({ section }) => !narrativeTitles.has(section.title)) : [];

  function changePart(index: number, part: number, value: string) {
    const next = replaceStoryBeat(draft.sections[index].content, layout[index], part, value);
    if (!next) return "Phần này đã đủ 10.000 ký tự. Rút ngắn một card rồi thử lại.";
    setLayout(layout.map((spans, i) => i === index ? next.spans : spans));
    onChange(index, next.content);
  }

  return <div className="story-draft-editor" aria-label="Phác thảo đang viết">
    <div className="story-draft-intro">
      <p className="storage-note" role="status">{dirty ? "Bản đang viết · Có thay đổi chưa lưu" : "Bản đang viết · Đã lưu"}</p>
      <p className="storage-note">Sửa ngay tại từng card. Đóng ô sửa giữ chữ trong bản đang viết. Dùng Lưu thay đổi để ghi lên máy.
        Đây là story plan, chưa phải kịch bản theo cảnh.</p>
    </div>
    <div className="story-draft-overview">
      <Field id="draft-title" label="Tên phim tạm thời" value={draft.title} maxLength={200}
        onChange={value => onChange("title", value)} />
      <Field id="draft-logline" label="Tóm tắt câu chuyện trong một câu" value={draft.logline} maxLength={2000}
        onChange={value => onChange("logline", value)} />
    </div>
    <div className="story-draft-caption"><span>ĐƯỜNG KỂ CỦA BẠN</span><span>{cards.length} card · Đọc theo số thứ tự</span></div>
    <div className={`story-workbench${inspector && wideInspector ? " has-inspector" : ""}`}><div className="story-path-canvas">
    <StoryPath list={path} count={cards.length} />
    <ol ref={path} className="story-draft-path" aria-label="Các phần câu chuyện theo số thứ tự">
      {cards.map(({ section, index, part, span }, position) => {
        const wideRow = Math.floor(position / 3), row = Math.floor(position / 2);
        const id = `section-${index}${part ? `-part-${part}` : ""}`;
        const label = `${sectionLabels[section.title] ?? section.title}${layout[index].length > 1 ? ` · ${part + 1}` : ""}`;
        return <li data-card-id={id} className={selectedCardId === id ? "is-selected" : undefined} key={`${index}:${part}`} style={{ "--wide-row": wideRow + 1,
          "--wide-column": wideRow % 2 ? 3 - position % 3 : position % 3 + 1,
          "--row": row + 1, "--column": row % 2 ? 2 - position % 2 : position % 2 + 1 } as CSSProperties}>
          <span className="story-card-number" aria-hidden="true">{position + 1}</span>
          <Field id={`section-${index}${part ? `-part-${part}` : ""}`}
            label={label}
            value={section.content.slice(span.start, span.end)}
            maxLength={10000 - section.content.length + span.end - span.start}
            onChange={value => changePart(index, part, value)} />
          {onSelectCard && <button type="button" className="secondary card-feedback-trigger"
            aria-pressed={selectedCardId === id} aria-label={`Xem góp ý cho card ${position + 1}`}
            onClick={() => onSelectCard({ id, label: `Card ${position + 1} · ${label}` })}>Xem góp ý</button>}
          {!wideInspector && selectedCardId === id && inspector}
        </li>;
      })}
    </ol>
    </div>{wideInspector && inspector}</div>
    {!cards.length && <p className="storage-note">Chưa có nội dung phác thảo.</p>}
    {!!context.length && <details className="story-draft-context">
      <summary>Nhân vật, chủ đề và các chi tiết khác ({context.length})</summary>
      {context.map(({ section, index }) => <Field key={index} id={`section-${index}`}
        label={sectionLabels[section.title] ?? section.title} value={section.content}
        maxLength={10000} onChange={value => onChange(index, value)} />)}
    </details>}
  </div>;
}

export function StoryPath({ list, count, orderKey = "" }: {
  list: React.RefObject<HTMLOListElement | null>; count: number; orderKey?: string;
}) {
  const marker = useId();
  const [drawing, setDrawing] = useState({ width: 1, height: 1, paths: [] as string[] });
  useEffect(() => {
    const ol = list.current;
    const canvas = ol?.parentElement;
    if (!ol || !canvas) return;
    const cards = [...ol.children] as HTMLElement[];
    function measure() {
      const area = canvas!.getBoundingClientRect();
      const boxes = cards.map(card => {
        const box = card.getBoundingClientRect();
        return { x: box.left - area.left, y: box.top - area.top, w: box.width, h: box.height };
      });
      const single = getComputedStyle(ol!).gridTemplateColumns.split(" ").length === 1;
      const paths = boxes.slice(0, -1).map((a, i) => {
        const b = boxes[i + 1];
        if (single) return `M ${a.x + a.w / 2} ${a.y + a.h} L ${b.x + b.w / 2} ${b.y}`;
        if (Math.abs(a.y - b.y) < 1) return a.x < b.x
          ? `M ${a.x + a.w} ${a.y + a.h / 2} L ${b.x} ${b.y + b.h / 2}`
          : `M ${a.x} ${a.y + a.h / 2} L ${b.x + b.w} ${b.y + b.h / 2}`;
        const right = a.x + a.w / 2 > area.width / 2;
        const x = right ? a.x + a.w : a.x;
        const end = right ? b.x + b.w : b.x;
        const bend = right ? 36 : -36;
        return `M ${x} ${a.y + a.h / 2} C ${x + bend} ${a.y + a.h / 2} ${end + bend} ${b.y + b.h / 2} ${end} ${b.y + b.h / 2}`;
      });
      setDrawing(current => current.width === area.width && current.height === area.height
        && current.paths.join() === paths.join() ? current : { width: area.width, height: area.height, paths });
    }
    const observer = new ResizeObserver(measure);
    observer.observe(canvas); cards.forEach(card => observer.observe(card)); measure();
    return () => observer.disconnect();
  }, [list, count, orderKey]);
  return <svg className="story-path-lines" aria-hidden="true" viewBox={`0 0 ${drawing.width} ${drawing.height}`}>
    <defs><marker id={marker} markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
      <path d="M 1 1 L 5 3.5 L 1 6" fill="none" stroke="currentColor" strokeWidth="1.4" />
    </marker></defs>
    {drawing.paths.map((path, i) => <path key={i} d={path} markerEnd={`url(#${marker})`} />)}
  </svg>;
}

function Field({ id, label, value, maxLength, onChange }: {
  id: string; label: string; value: string; maxLength: number; onChange: (value: string) => void | string;
}) {
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const previous = useRef(value);
  const editButton = useRef<HTMLButtonElement>(null);
  function change(value: string) {
    const error = onChange(value);
    const message = typeof error === "string" ? error : "";
    setError(message); return !message;
  }
  function close(cancel = false) {
    if (cancel && !change(previous.current)) return;
    setEditing(false);
    requestAnimationFrame(() => editButton.current?.focus());
  }
  function keyDown(event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) {
    if (event.key === "Escape" && !event.nativeEvent.isComposing) {
      event.preventDefault(); event.stopPropagation(); close(true);
    }
  }
  return <div data-revision-target={id} className={`story-field${id === "draft-title" ? " story-field-title" : ""}`}>
    <div className="story-field-heading">
      <h3 id={`${id}-label`}>{label}</h3>
      {!editing && <button ref={editButton} type="button" className="story-edit-button"
        data-draft-open={id === "draft-logline" ? "logline" : undefined}
        aria-label={`Sửa ${label.toLocaleLowerCase("vi")}`} onClick={() => {
          previous.current = value; setError(""); setEditing(true);
        }}>Sửa <span aria-hidden="true">↗</span></button>}
    </div>
    {editing ? <>
      {id === "draft-title" ? <input id={id} autoFocus aria-labelledby={`${id}-label`}
        value={value} maxLength={maxLength} onChange={event => change(event.target.value)} onKeyDown={keyDown} />
        : <textarea id={id} autoFocus aria-labelledby={`${id}-label`} rows={id === "draft-logline" ? 3 : 6}
          value={value} maxLength={maxLength} onChange={event => change(event.target.value)} onKeyDown={keyDown} />}
      {error && <p className="error" role="alert">{error}</p>}
      <div className="story-field-actions"><button type="button" onClick={() => close()} title="Đóng ô sửa, chưa lưu lên máy">Xong</button>
        <button type="button" className="secondary" onClick={() => close(true)}>Hủy</button></div>
    </> : <p className="story-field-value preserve-lines">{value || "Chưa có nội dung."}</p>}
  </div>;
}

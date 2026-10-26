"use client";

import type { EvaluationFinding } from "./apiClient";
import type { Feedback, FeedbackSource } from "./projectsApi";
import { splitStorySection } from "./StoryPlanEditor";
import { readRevisionNotes, validatedTargets } from "./revisionNotes";
import { feedbackGuidance } from "./storyLabels";

// Interpret only the server's exact quoted anchors; legacy prose remains general feedback.
export function anchoredReview(finding: EvaluationFinding, source: FeedbackSource | null | undefined) {
  if (!source) return null;
  const narrative = source.draft.sections.some(s => ["Beginning", "Middle", "Ending"].includes(s.title));
  let position = 0;
  const cards = source.draft.sections.flatMap((section, index) => {
    const onPath = !narrative || ["Beginning", "Middle", "Ending"].includes(section.title);
    const spans = onPath ? splitStorySection(section.content) : [{ start: 0, end: section.content.length }];
    return spans.flatMap((span, part) => {
      const prefix = onPath ? `Card ${++position} · ` : "";
      const vi = ({ Beginning: "Mở đầu", Middle: "Phần giữa", Ending: "Kết thúc" } as Record<string, string>)[section.title] ?? section.title;
      return [...new Set([vi, section.title])].map(title => ({
        id: `section-${index}${part ? `-part-${part}` : ""}`,
        quote: `${prefix}${title}${spans.length > 1 ? ` · ${part + 1}` : ""}: “${section.content.slice(span.start, span.end)}”`,
      }));
    });
  });
  for (const key of ["title", "logline"] as const) cards.push({ id: `draft-${key}`, quote: `${key}: “${source.draft[key]}”` });
  const primary = cards.find(card => finding.message.startsWith(card.quote));
  if (!primary) return null;
  let remaining = finding.message.slice(primary.quote.length);
  const ids = [primary.id];
  if (remaining.startsWith(" ↔ ")) {
    const related = cards.find(card => remaining.startsWith(` ↔ ${card.quote}`));
    if (!related || related.id === primary.id) return null;
    ids.push(related.id); remaining = remaining.slice(3 + related.quote.length);
  }
  const decisions = [
    { label: "Ý tưởng", text: source.context.idea },
    ...source.context.constraints.map((text, i) => ({ label: `Giới hạn ${i + 1}`, text })),
    ...source.context.clarifications.map(item => ({ label: item.input_index === null ? "Lựa chọn đã lưu" : `Làm rõ ${item.input_index + 1}`, text: item.answer })),
  ];
  const allDecisions = decisions.flatMap(item => [item, { ...item, label: item.label.replace("Ý tưởng", "Idea")
    .replace("Giới hạn ", "Constraint ").replace("Làm rõ ", "Clarification ").replace("Lựa chọn đã lưu", "Saved decision") }]);
  const decision = allDecisions.find(item => remaining.startsWith(`\n${item.label}: “${item.text}”\n`));
  if (!decision) return null;
  return { cardIds: ids, decision, observation: remaining.slice(`\n${decision.label}: “${decision.text}”\n`.length), original: finding.message };
}

export function CardFeedback({ cardId, label, evaluation, source, current, selected, onClose, onReview }: {
  cardId: string; label: string; evaluation: Feedback | null; source: FeedbackSource | null | undefined;
  current: boolean; selected?: Pick<EvaluationFinding, "message"> | null; onClose: () => void; onReview: () => void;
}) {
  const notes = evaluation ? readRevisionNotes(evaluation) : null;
  const cardNotes = current ? notes?.filter(note => validatedTargets(note, source, evaluation?.artifact_id)
    ?.some(target => target.target_id === cardId)) ?? [] : [];
  const entries = current && notes === null ? (evaluation?.findings ?? []).flatMap(finding => {
    const review = anchoredReview(finding, source);
    return review?.cardIds.includes(cardId) ? [{ finding, review }] : [];
  }) : [];
  return <aside className="card-feedback" aria-label={`Góp ý cạnh ${label}`}>
    <header><div><span className="eyebrow">Góp ý AI · tham khảo</span><h4>{label}</h4></div>
      <button type="button" className="secondary" aria-label="Đóng góp ý cạnh card" onClick={onClose}>Đóng</button></header>
    <p>{feedbackGuidance.vi}</p>
    {!current && <p className="form-message" role="status">{evaluation ? "Nội dung đã thay đổi. Góp ý cũ thuộc bản trước." : "Chưa có góp ý cho bản này."}</p>}
    {cardNotes.map(note => <div key={note.note_id} className="card-feedback-item">
      <p className="preserve-lines">{note.observation}</p>
      <p className="preserve-lines"><strong>Bước tiếp theo: </strong>{note.suggestion}</p>
      <details><summary>Xem nguồn đối chiếu</summary><p>{note.decision_question}</p>
        <p className="preserve-lines">{note.decision_quote}</p>
        {note.targets.map(target => <blockquote key={target.target_id} className="preserve-lines">{target.quote}</blockquote>)}
      </details>
    </div>)}
    {entries.map(({ finding, review }) => {
      return <div key={finding.criterion_id} className="card-feedback-item">
        <p className="feedback-source-label">Dựa trên {review.decision.label}</p>
        <p className="preserve-lines">{review.observation}</p>
        <details><summary>Xem nguồn đối chiếu</summary><p className="preserve-lines">{review.decision.text}</p>
          <p className="preserve-lines">{review.original}</p></details>
      </div>;
    })}
    {current && !entries.length && !cardNotes.length && <p>Chưa có nhận xét riêng cho card này. Góp ý chung nằm trong phần “Toàn bộ góp ý”.</p>}
    {!current && selected && <details><summary>Góp ý trước đó đang tham khảo</summary><p className="preserve-lines">{selected.message}</p></details>}
    <button type="button" data-tour-review onClick={onReview}>Nhận phản hồi trên bản hiện tại</button>
    <p className="storage-note">Bạn quyết định sửa hay giữ. Thao tác này lưu nội dung hiện tại trước khi gửi AI.</p>
  </aside>;
}

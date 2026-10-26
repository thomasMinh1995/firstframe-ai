import type { RevisionNote } from "./apiClient";
import type { Feedback, FeedbackSource } from "./projectsApi";
import { splitStorySection } from "./StoryPlanEditor";
import { sectionLabels } from "./storyLabels";

const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);

// Treat malformed optional metadata as legacy prose. Never guess an actionable pair.
export function readRevisionNotes(feedback: Feedback): RevisionNote[] | null {
  const notes: unknown = feedback.revision_notes;
  if (!Array.isArray(notes) || notes.length > 3 || !notes.every(n => record(n)
    && ["note_id", "artifact_id", "observation", "suggestion", "decision_id", "decision_quote"].every(k => typeof n[k] === "string")
    && !!n.note_id && !!n.observation && ["mismatch", "uncertain"].includes(String(n.comparison))
    && (n.comparison !== "mismatch" || !!String(n.suggestion).trim())
    && (n.decision_question === null || typeof n.decision_question === "string")
    && Array.isArray(n.targets) && n.targets.length > 0 && n.targets.length <= 2
    && n.targets.every(t => record(t) && typeof t.target_id === "string" && typeof t.quote === "string"))) return null;
  return new Set(notes.map(n => n.note_id)).size === notes.length ? notes as RevisionNote[] : null;
}

export function validatedTargets(note: RevisionNote, source: FeedbackSource | null | undefined, artifactId?: string) {
  if (!source || !artifactId || source.artifact_id !== artifactId || note.artifact_id !== artifactId) return null;
  const narrative = source.draft.sections.some(s => ["Beginning", "Middle", "Ending"].includes(s.title));
  const labels = source.draft.sections.map(s => sectionLabels[s.title] ?? s.title);
  let position = 0;
  const cards = source.draft.sections.flatMap((section, index) => {
    const onPath = !narrative || ["Beginning", "Middle", "Ending"].includes(section.title);
    const spans = onPath
      ? splitStorySection(section.content) : [{ start: 0, end: section.content.length }];
    return spans.map((span, part) => {
      if (onPath) position++;
      const duplicate = labels.filter(label => label === labels[index]).length > 1;
      let label = labels[index] + (spans.length > 1 ? ` · ${part + 1}` : "");
      if (duplicate) label += onPath ? ` · Card ${position}` : ` · mục ${index + 1}`;
      return { target_id: `section-${index}${part ? `-part-${part}` : ""}`, quote: section.content.slice(span.start, span.end),
        label };
    });
  });
  cards.push({ target_id: "draft-title", quote: source.draft.title, label: "Tên phim" },
    { target_id: "draft-logline", quote: source.draft.logline, label: "Tóm tắt một câu" });
  const decisions = [{ id: "idea", text: source.context.idea, question: null },
    ...source.context.constraints.map((text, i) => ({ id: `constraint-${i}`, text, question: null })),
    ...source.context.clarifications.map((item, i) => ({ id: `answer-${i}`, text: item.answer, question: item.question }))];
  if (!decisions.some(d => d.id === note.decision_id && d.text === note.decision_quote && d.question === note.decision_question)
    || new Set(note.targets.map(t => t.target_id)).size !== note.targets.length) return null;
  const targets = note.targets.map(t => cards.find(c => c.target_id === t.target_id && c.quote === t.quote));
  // A partially valid multi-target note is entirely read-only.
  return targets.every(t => t !== undefined) ? targets as typeof cards : null;
}

"use client";

import { AnalysisNote, GenerateResponse, StoryPlanSection, type EvaluationFinding } from "./apiClient";
import type { UiLanguage } from "./language";
import { feedbackGuidance, rubricLabels } from "./storyLabels";
import type { ReactNode } from "react";
import type { Feedback, FeedbackSource } from "./projectsApi";
import type { RevisionNote } from "./apiClient";
import { readRevisionNotes, validatedTargets } from "./revisionNotes";

type StoryResultCardsProps = {
  result: GenerateResponse;
  uiLanguage: UiLanguage;
};

const storySectionKeys = [
  "workingTitle",
  "logline",
  "theme",
  "characters",
  "conflict",
  "beginning",
  "middle",
  "ending",
  "visualStyle",
  "tone",
  "productionNotes",
] as const;

const resultCopy = {
  en: {
    analysis: "Analysis",
    analysisTitle: "What FirstFrame noticed",
    coreIdea: "Core Idea",
    emotionalCore: "Emotional Core",
    missingInformation: "Missing Information",
    opportunities: "Opportunities",
    storyPlan: "Story Plan",
    storyPlanTitle: "First structured pass",
    workingTitle: "Working Title",
    evaluation: "AI feedback",
    evaluationTitle: "Points to consider",
    strengths: "Strengths",
    weaknesses: "Weaknesses",
    suggestions: "Suggestions",
    clarifications: "Not enough evidence — clarification needed",
    emptyMissing: "No major missing information returned.",
    emptyOpportunities: "No additional opportunities returned.",
    emptyStrengths: "No strengths returned yet.",
    emptyWeaknesses: "No weaknesses returned yet.",
    emptySuggestions: "No suggestions returned yet.",
    noLogline: "No logline returned yet.",
    untitled: "Untitled Short Film",
    notReturned: "Not returned yet.",
    sectionLabels: {
      workingTitle: "Working Title",
      logline: "Logline",
      theme: "Theme",
      characters: "Characters",
      conflict: "Conflict",
      beginning: "Beginning",
      middle: "Middle",
      ending: "Ending",
      visualStyle: "Visual Style",
      tone: "Tone",
      productionNotes: "Production Notes",
    },
  },
  vi: {
    analysis: "Phân tích",
    analysisTitle: "Những gì FirstFrame nhận ra",
    coreIdea: "Ý tưởng chính",
    emotionalCore: "Lõi cảm xúc",
    missingInformation: "Thông tin còn thiếu",
    opportunities: "Cơ hội phát triển",
    storyPlan: "Bản phát triển",
    storyPlanTitle: "Bản phát triển đầu tiên",
    workingTitle: "Tên tạm thời",
    evaluation: "Góp ý AI",
    evaluationTitle: "Những điều cần cân nhắc",
    strengths: "Điểm mạnh",
    weaknesses: "Điểm yếu",
    suggestions: "Gợi ý cải thiện",
    clarifications: "Chưa đủ căn cứ — cần làm rõ",
    emptyMissing: "Chưa có thông tin còn thiếu.",
    emptyOpportunities: "Chưa có cơ hội phát triển bổ sung.",
    emptyStrengths: "Chưa có điểm mạnh.",
    emptyWeaknesses: "Chưa có điểm yếu.",
    emptySuggestions: "Chưa có gợi ý cải thiện.",
    noLogline: "Chưa có tóm tắt câu chuyện.",
    untitled: "Phim ngắn chưa đặt tên",
    notReturned: "Chưa có nội dung.",
    sectionLabels: {
      workingTitle: "Tên tạm thời",
      logline: "Tóm tắt một câu",
      theme: "Chủ đề",
      characters: "Nhân vật",
      conflict: "Xung đột",
      beginning: "Mở đầu",
      middle: "Phần giữa",
      ending: "Kết thúc",
      visualStyle: "Phong cách hình ảnh",
      tone: "Tông cảm xúc",
      productionNotes: "Ghi chú sản xuất",
    },
  },
};

type ResultCopy = (typeof resultCopy)[UiLanguage];

export function StoryFeedback({ evaluation, uiLanguage, onChoose, onTarget, source, selectedCriterion, selectionDisabled = false }: {
  evaluation: Feedback;
  uiLanguage: UiLanguage;
  onChoose?: (finding: EvaluationFinding) => void;
  onTarget?: (note: RevisionNote, targetId: string) => void;
  source?: FeedbackSource | null;
  selectedCriterion?: string;
  selectionDisabled?: boolean;
}) {
  const copy = resultCopy[uiLanguage];
  const shaped = shapeEvaluation({ evaluation }, uiLanguage);
  const weaknesses = evaluation.findings.filter(item => item.criterion_id.startsWith("weakness-"));
  const suggestions = evaluation.findings.filter(item => item.criterion_id.startsWith("suggestion-"));
  const notes = readRevisionNotes(evaluation);
  const noteGroups = (["mismatch", "uncertain"] as const).map(comparison => ({
    comparison,
    title: comparison === "uncertain" ? copy.clarifications
      : uiLanguage === "vi" ? "Điều có thể trái lựa chọn của bạn" : "Possible conflicts with your choices",
    notes: notes?.filter(note => note.comparison === comparison) ?? [],
  }));
  return (
    <ReportCard eyebrow={copy.evaluation} title={uiLanguage === "vi" ? "Góp ý cho lần sửa tiếp theo" : copy.evaluationTitle}
      icon="✍️" delayClass="reveal-1">
      <p>{feedbackGuidance[uiLanguage]}</p>
      {onChoose && <p>Chọn một góp ý để xem cạnh bản thảo và tự quyết định phần muốn sửa.
        Đối chiếu với ý đồ của bạn: điều trái dữ kiện hoặc lựa chọn rõ, điều còn để mở và đề xuất sáng tạo cần được cân nhắc khác nhau.
        Bạn có thể bỏ qua góp ý không phù hợp; không cần sửa tất cả.</p>}
      <div className="feedback-grid">
        <SectionList title={copy.strengths} items={shaped.strengths} emptyText={copy.emptyStrengths} />
        {notes !== null ? <>
          {!notes.length && <p>Không có ưu tiên sửa được trả về. Bạn vẫn quyết định có giữ cách kể này hay không.</p>}
          {noteGroups.filter(group => group.notes.length).map(group => <section key={group.comparison} className="list-section">
          <h3>{group.title} ({group.notes.length})</h3>
          {group.comparison === "uncertain" && <p>{uiLanguage === "vi"
            ? "Chưa xác định đây là lỗi. Bạn có thể giữ nguyên hoặc làm rõ ý định."
            : "This has not been established as a problem. You can keep the draft or clarify your intent."}</p>}
          {group.notes.map(note => {
            const targets = validatedTargets(note, source, evaluation.artifact_id);
            return <article key={note.note_id} className="card-feedback-item">
              <p className="preserve-lines">{note.observation}</p>
              {note.suggestion.trim() && <p className="preserve-lines"><strong>{uiLanguage === "vi" ? "Gợi ý tùy chọn: " : "Optional suggestion: "}</strong>{note.suggestion}</p>}
              <details><summary>Xem nguồn đối chiếu</summary>
                {note.decision_question && <p>{note.decision_question}</p>}
                <p className="preserve-lines">{note.decision_quote}</p>
                {note.targets.map(target => <blockquote key={target.target_id} className="preserve-lines">{target.quote}</blockquote>)}
                <p>Trích dẫn đúng chữ chưa chứng minh nhận xét đúng nghĩa. Bạn có thể giữ bản hiện tại.</p>
              </details>
              {onTarget && targets && !selectionDisabled ? <div>
                {targets.length > 1 && <p>{note.comparison === "uncertain" ? "Chọn phần bạn muốn đối chiếu:" : "Chọn phần bạn muốn tự sửa:"}</p>}
                {targets.map(target => <button key={target.target_id} type="button" className="secondary"
                  onClick={() => onTarget(note, target.target_id)}>{note.comparison === "uncertain" ? "Xem phần này" : "Sửa phần này"}: {target.label}</button>)}
              </div> : <p className="storage-note">{!targets ? "Chưa xác minh được nguồn và mục tiêu; góp ý này chỉ để đọc."
                : "Góp ý thuộc bản trước hoặc đang chỉ đọc."}</p>}
            </article>;
          })}
        </section>)}
        </> : <>
        <SectionList title={copy.weaknesses} items={shaped.weaknesses} emptyText={copy.emptyWeaknesses}
          onChoose={onChoose && (index => onChoose(weaknesses[index]))}
          selectedIndex={weaknesses.findIndex(item => item.criterion_id === selectedCriterion)}
          selectionDisabled={selectionDisabled} />
        <SectionList title={copy.suggestions} items={shaped.suggestions} emptyText={copy.emptySuggestions}
          onChoose={onChoose && (index => onChoose(suggestions[index]))}
          selectedIndex={suggestions.findIndex(item => item.criterion_id === selectedCriterion)}
          selectionDisabled={selectionDisabled} />
        </>}
        {notes === null && shaped.clarifications.length > 0 && <SectionList title={copy.clarifications}
          items={shaped.clarifications} emptyText="" />}
      </div>
      {shaped.scores.length > 0 && <details className="rubric-details">
        <summary>{uiLanguage === "vi" ? "Xem điểm tham khảo" : "Reference scores"}</summary>
        <div className="scores">{shaped.scores.map((score) => <span key={score.label}>
          {score.label}: {score.value}/5
        </span>)}</div>
      </details>}
    </ReportCard>
  );
}

export function StoryResultCards({ result, uiLanguage }: StoryResultCardsProps) {
  const copy = resultCopy[uiLanguage];
  const analysis = shapeAnalysis(result);
  const storyPlan = shapeStoryPlan(result, copy);
  const evaluation = shapeEvaluation(result, uiLanguage);

  return (
    <div className="results report-stack">
      <ReportCard eyebrow={copy.analysis} title={copy.analysisTitle} icon="🧠" delayClass="reveal-1">
        <DetailGrid
          items={[
            { label: copy.coreIdea, content: analysis.coreIdea },
            { label: copy.emotionalCore, content: analysis.emotionalCore },
          ]}
        />

        <SectionList
          title={copy.missingInformation}
          items={result.analysis.missing_information}
          emptyText={copy.emptyMissing}
        />

        <SectionList
          title={copy.opportunities}
          items={analysis.opportunities}
          emptyText={copy.emptyOpportunities}
        />
      </ReportCard>

      <ReportCard eyebrow={copy.storyPlan} title={copy.storyPlanTitle} icon="🎬" delayClass="reveal-2">
        <div className="story-heading">
          <span className="story-kicker">{copy.workingTitle}</span>
          <h3>{result.story_plan.title ?? copy.untitled}</h3>
          {result.story_plan.logline ? <p>{result.story_plan.logline}</p> : null}
        </div>

        <DetailGrid items={storyPlan} />
      </ReportCard>

      <ReportCard eyebrow={copy.evaluation} title={copy.evaluationTitle} icon="⭐" delayClass="reveal-3">
        <p>{feedbackGuidance[uiLanguage]}</p>

        {evaluation.scores.length > 0 ? (
          <div className="score-grid" aria-label={uiLanguage === "vi" ? "Điểm tham khảo" : "AI reference scores"}>
            {evaluation.scores.map((score) => (
              <article key={score.label} className="score-card">
                <div className="score-row">
                  <span>{score.label}</span>
                  <strong>{score.value}/5</strong>
                </div>
                <div className="score-track" aria-hidden="true">
                  <span style={{ width: `${Math.min(score.value, 5) * 20}%` }} />
                </div>
              </article>
            ))}
          </div>
        ) : null}

        <div className="feedback-grid">
          {evaluation.clarifications.length > 0 && <SectionList title={copy.clarifications}
            items={evaluation.clarifications} emptyText="" />}
          <SectionList
            title={copy.strengths}
            items={evaluation.strengths}
            emptyText={copy.emptyStrengths}
          />
          <SectionList
            title={copy.weaknesses}
            items={evaluation.weaknesses}
            emptyText={copy.emptyWeaknesses}
          />
          <SectionList
            title={copy.suggestions}
            items={evaluation.suggestions}
            emptyText={copy.emptySuggestions}
          />
        </div>
      </ReportCard>
    </div>
  );
}

function ReportCard({
  eyebrow,
  title,
  icon,
  delayClass,
  children,
}: {
  eyebrow: string;
  title: string;
  icon: string;
  delayClass: string;
  children: ReactNode;
}) {
  return (
    <section className={`panel report-card ${delayClass}`}>
      <div className="report-card-header">
        <span className="report-icon">{icon}</span>
        <div>
          <p className="report-eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
      </div>
      {children}
    </section>
  );
}

function DetailGrid({ items }: { items: Array<{ label: string; content: string }> }) {
  return (
    <div className="detail-grid">
      {items.map((item) => (
        <article key={item.label} className="detail-card">
          <h3>{item.label}</h3>
          <p>{item.content}</p>
        </article>
      ))}
    </div>
  );
}

function SectionList({
  title,
  items,
  emptyText,
  onChoose,
  selectedIndex,
  selectionDisabled,
}: {
  title: string;
  items: string[];
  emptyText: string;
  onChoose?: (index: number) => void;
  selectedIndex?: number;
  selectionDisabled?: boolean;
}) {
  return (
    <section className="list-section">
      <h3>{title}</h3>
      {items.length > 0 ? (
        <ul>
          {items.map((item, index) => (
            <li key={index}><span className="preserve-lines">{item}</span>
              {onChoose && <button type="button" className="secondary feedback-choice"
                aria-label={`Chọn ${title.toLowerCase()} ${index + 1} để tự sửa`}
                aria-pressed={selectedIndex === index} disabled={selectionDisabled}
                onClick={() => onChoose(index)}>Xem cạnh bản thảo</button>}
            </li>
          ))}
        </ul>
      ) : (
        <p>{emptyText}</p>
      )}
    </section>
  );
}

function shapeAnalysis(result: GenerateResponse) {
  const originalIdea = findNote(result.analysis.notes, "Original idea");
  const emotionalNote = findNoteByKeyword(result.analysis.notes, "emotional");
  const opportunities = result.analysis.notes
    .filter((note) => !["original idea", "analysis summary"].includes(note.label.toLowerCase()))
    .map((note) => `${note.label}: ${note.content}`);

  return {
    coreIdea: originalIdea?.content ?? result.analysis.summary,
    emotionalCore: emotionalNote?.content ?? result.analysis.summary,
    opportunities,
  };
}

function shapeStoryPlan(result: GenerateResponse, copy: ResultCopy) {
  return storySectionKeys.map((key) => {
    const label = copy.sectionLabels[key];
    if (key === "workingTitle") {
      return {
        label,
        content: result.story_plan.title ?? copy.untitled,
      };
    }
    if (key === "logline") {
      return {
        label,
        content: result.story_plan.logline ?? copy.noLogline,
      };
    }

    const matchingSection = findStorySection(result.story_plan.sections, key);
    return {
      label,
      content: matchingSection?.content ?? copy.notReturned,
    };
  });
}

function shapeEvaluation(result: Pick<GenerateResponse, "evaluation">, uiLanguage: UiLanguage) {
  return {
    scores: Object.entries(result.evaluation.rubric_scores).map(([criterion, value]) => ({
      label: uiLanguage === "vi" ? rubricLabels[criterion] ?? criterion : formatLabel(criterion),
      value,
    })),
    strengths: result.evaluation.findings
      .filter((finding) => finding.criterion_id.startsWith("strength-"))
      .map((finding) => finding.message),
    weaknesses: result.evaluation.findings
      .filter((finding) => finding.criterion_id.startsWith("weakness-"))
      .map((finding) => finding.message),
    suggestions: result.evaluation.findings
      .filter((finding) => finding.criterion_id.startsWith("suggestion-"))
      .map((finding) => finding.message),
    clarifications: result.evaluation.findings
      .filter((finding) => finding.criterion_id.startsWith("clarification-"))
      .map((finding) => finding.message),
  };
}

function findNote(notes: AnalysisNote[], label: string) {
  return notes.find((note) => note.label.toLowerCase() === label.toLowerCase());
}

function findNoteByKeyword(notes: AnalysisNote[], keyword: string) {
  return notes.find(
    (note) =>
      note.label.toLowerCase().includes(keyword) ||
      note.content.toLowerCase().includes(keyword),
  );
}

function findStorySection(sections: StoryPlanSection[], key: (typeof storySectionKeys)[number]) {
  if (key === "characters") {
    return sections.find((section) => normalize(section.title).includes("maincharacter"));
  }
  if (key === "conflict") {
    return sections.find((section) => normalize(section.title).includes("mainconflict"));
  }
  if (key === "visualStyle") {
    return sections.find((section) => normalize(section.title).includes("visualstyle"));
  }
  if (key === "productionNotes") {
    return sections.find((section) => normalize(section.title).includes("productionnotes"));
  }
  const normalizedLabel = normalize(key);
  return sections.find((section) => normalize(section.title).includes(normalizedLabel));
}

function normalize(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function formatLabel(value: string) {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

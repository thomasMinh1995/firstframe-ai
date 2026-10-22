"use client";

import { AnalysisNote, GenerateResponse, StoryPlanSection, type EvaluationFinding } from "./apiClient";
import type { UiLanguage } from "./language";
import { rubricLabels } from "./storyLabels";
import type { ReactNode } from "react";

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
    evaluation: "Evaluation",
    evaluationTitle: "Creative quality check",
    ready: "Ready for demo pass",
    needsRevision: "Needs revision",
    strengths: "Strengths",
    weaknesses: "Weaknesses",
    suggestions: "Suggestions",
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
    evaluation: "Đánh giá",
    evaluationTitle: "Kiểm tra chất lượng sáng tạo",
    ready: "Sẵn sàng cho bản demo",
    needsRevision: "Cần chỉnh sửa",
    strengths: "Điểm mạnh",
    weaknesses: "Điểm yếu",
    suggestions: "Gợi ý cải thiện",
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

export function StoryFeedback({ evaluation, uiLanguage, onChoose, selectedCriterion, selectionDisabled = false }: {
  evaluation: GenerateResponse["evaluation"];
  uiLanguage: UiLanguage;
  onChoose?: (finding: EvaluationFinding) => void;
  selectedCriterion?: string;
  selectionDisabled?: boolean;
}) {
  const copy = resultCopy[uiLanguage];
  const shaped = shapeEvaluation({ evaluation }, uiLanguage);
  const weaknesses = evaluation.findings.filter(item => item.criterion_id.startsWith("weakness-"));
  const suggestions = evaluation.findings.filter(item => item.criterion_id.startsWith("suggestion-"));
  return (
    <ReportCard eyebrow={copy.evaluation} title={uiLanguage === "vi" ? "Góp ý cho lần sửa tiếp theo" : copy.evaluationTitle}
      icon="✍️" delayClass="reveal-1">
      <p>{uiLanguage === "vi" ? "Đây là gợi ý tham khảo. Bạn quyết định điều gì phù hợp với câu chuyện của mình."
        : "These are suggestions. You decide what fits your story."}</p>
      {onChoose && <p>Chọn một góp ý để xem cạnh bản thảo và tự quyết định phần muốn sửa.
        Đối chiếu với ý đồ của bạn: điều trái dữ kiện hoặc lựa chọn rõ, điều còn để mở và đề xuất sáng tạo cần được cân nhắc khác nhau.
        Bạn có thể bỏ qua góp ý không phù hợp; không cần sửa tất cả.</p>}
      <div className="feedback-grid">
        <SectionList title={copy.strengths} items={shaped.strengths} emptyText={copy.emptyStrengths} />
        <SectionList title={copy.weaknesses} items={shaped.weaknesses} emptyText={copy.emptyWeaknesses}
          onChoose={onChoose && (index => onChoose(weaknesses[index]))}
          selectedIndex={weaknesses.findIndex(item => item.criterion_id === selectedCriterion)}
          selectionDisabled={selectionDisabled} />
        <SectionList title={copy.suggestions} items={shaped.suggestions} emptyText={copy.emptySuggestions}
          onChoose={onChoose && (index => onChoose(suggestions[index]))}
          selectedIndex={suggestions.findIndex(item => item.criterion_id === selectedCriterion)}
          selectionDisabled={selectionDisabled} />
      </div>
      <details className="rubric-details">
        <summary>{uiLanguage === "vi" ? "Xem điểm tham khảo" : "Reference scores"}</summary>
        <div className="scores">{shaped.scores.map((score) => <span key={score.label}>
          {score.label}: {score.value}/5
        </span>)}</div>
      </details>
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
        <div className="evaluation-summary">
          <span className={result.evaluation.passed ? "result-pill is-pass" : "result-pill"}>
            {result.evaluation.passed ? copy.ready : copy.needsRevision}
          </span>
        </div>

        {evaluation.scores.length > 0 ? (
          <div className="score-grid" aria-label={uiLanguage === "vi" ? "Điểm tham khảo" : "Rubric scores"}>
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

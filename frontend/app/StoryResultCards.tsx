"use client";

import { AnalysisNote, GenerateResponse, StoryPlanSection } from "./apiClient";
import type { UiLanguage } from "./language";
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
    storyPlan: "Story Plan",
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
    noLogline: "Chưa có logline.",
    untitled: "Phim ngắn chưa đặt tên",
    notReturned: "Chưa có nội dung.",
    sectionLabels: {
      workingTitle: "Tên tạm thời",
      logline: "Logline",
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

export function StoryResultCards({ result, uiLanguage }: StoryResultCardsProps) {
  const copy = resultCopy[uiLanguage];
  const analysis = shapeAnalysis(result);
  const storyPlan = shapeStoryPlan(result, copy);
  const evaluation = shapeEvaluation(result);

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
          <div className="score-grid" aria-label="Rubric scores">
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
}: {
  title: string;
  items: string[];
  emptyText: string;
}) {
  return (
    <section className="list-section">
      <h3>{title}</h3>
      {items.length > 0 ? (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
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

function shapeEvaluation(result: GenerateResponse) {
  return {
    scores: Object.entries(result.evaluation.rubric_scores).map(([criterion, value]) => ({
      label: formatLabel(criterion),
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

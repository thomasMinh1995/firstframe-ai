"use client";

import { AnalysisNote, GenerateResponse, StoryPlanSection } from "./apiClient";
import type { ReactNode } from "react";

type StoryResultCardsProps = {
  result: GenerateResponse;
};

const storySectionOrder = [
  "Working Title",
  "Logline",
  "Theme",
  "Characters",
  "Conflict",
  "Beginning",
  "Middle",
  "Ending",
  "Visual Style",
  "Tone",
  "Production Notes",
];

export function StoryResultCards({ result }: StoryResultCardsProps) {
  const analysis = shapeAnalysis(result);
  const storyPlan = shapeStoryPlan(result);
  const evaluation = shapeEvaluation(result);

  return (
    <div className="results report-stack">
      <ReportCard eyebrow="Analysis" title="What FirstFrame noticed" icon="🧠" delayClass="reveal-1">
        <DetailGrid
          items={[
            { label: "Core Idea", content: analysis.coreIdea },
            { label: "Emotional Core", content: analysis.emotionalCore },
          ]}
        />

        <SectionList
          title="Missing Information"
          items={result.analysis.missing_information}
          emptyText="No major missing information returned."
        />

        <SectionList
          title="Opportunities"
          items={analysis.opportunities}
          emptyText="No additional opportunities returned."
        />
      </ReportCard>

      <ReportCard eyebrow="Story Plan" title="First structured pass" icon="🎬" delayClass="reveal-2">
        <div className="story-heading">
          <span className="story-kicker">Working Title</span>
          <h3>{result.story_plan.title ?? "Untitled Short Film"}</h3>
          {result.story_plan.logline ? <p>{result.story_plan.logline}</p> : null}
        </div>

        <DetailGrid items={storyPlan} />
      </ReportCard>

      <ReportCard eyebrow="Evaluation" title="Creative quality check" icon="⭐" delayClass="reveal-3">
        <div className="evaluation-summary">
          <span className={result.evaluation.passed ? "result-pill is-pass" : "result-pill"}>
            {result.evaluation.passed ? "Ready for demo pass" : "Needs revision"}
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
            title="Strengths"
            items={evaluation.strengths}
            emptyText="No strengths returned yet."
          />
          <SectionList
            title="Weaknesses"
            items={evaluation.weaknesses}
            emptyText="No weaknesses returned yet."
          />
          <SectionList
            title="Suggestions"
            items={evaluation.suggestions}
            emptyText="No suggestions returned yet."
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

function shapeStoryPlan(result: GenerateResponse) {
  return storySectionOrder.map((label) => {
    if (label === "Working Title") {
      return {
        label,
        content: result.story_plan.title ?? "Untitled Short Film",
      };
    }
    if (label === "Logline") {
      return {
        label,
        content: result.story_plan.logline ?? "No logline returned yet.",
      };
    }

    const matchingSection = findStorySection(result.story_plan.sections, label);
    return {
      label,
      content: matchingSection?.content ?? "Not returned yet.",
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

function findStorySection(sections: StoryPlanSection[], label: string) {
  const normalizedLabel = normalize(label);
  if (label === "Characters") {
    return sections.find((section) => normalize(section.title).includes("maincharacter"));
  }
  if (label === "Conflict") {
    return sections.find((section) => normalize(section.title).includes("mainconflict"));
  }
  if (label === "Working Title" || label === "Logline") {
    return null;
  }
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

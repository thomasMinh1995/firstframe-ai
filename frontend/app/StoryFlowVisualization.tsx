"use client";

import { AnalysisNote, GenerateResponse, StoryPlanSection } from "./apiClient";
import type { UiLanguage } from "./language";

type StoryFlowVisualizationProps = {
  result: GenerateResponse;
  uiLanguage: UiLanguage;
};

type FlowStep = {
  label: string;
  content: string;
};

const flowCopy = {
  en: {
    eyebrow: "Story Flow",
    title: "Arc at a glance",
    labels: {
      idea: "Idea",
      emotionalCore: "Emotional Core",
      conflict: "Conflict",
      turningPoint: "Turning Point",
      ending: "Ending",
    },
    fallback: {
      conflict: "The central obstacle is still being clarified.",
      turningPoint: "The middle turn is still being shaped.",
      ending: "The final image is still being refined.",
    },
  },
  vi: {
    eyebrow: "Luồng câu chuyện",
    title: "Tổng quan câu chuyện",
    labels: {
      idea: "Ý tưởng",
      emotionalCore: "Lõi cảm xúc",
      conflict: "Xung đột",
      turningPoint: "Bước ngoặt",
      ending: "Kết thúc",
    },
    fallback: {
      conflict: "Xung đột trung tâm vẫn đang được làm rõ.",
      turningPoint: "Bước ngoặt ở phần giữa vẫn đang được định hình.",
      ending: "Hình ảnh kết thúc vẫn đang được tinh chỉnh.",
    },
  },
};

export function StoryFlowVisualization({ result, uiLanguage }: StoryFlowVisualizationProps) {
  const copy = flowCopy[uiLanguage];
  const steps = buildFlowSteps(result, copy);

  return (
    <section className="panel story-flow-card" aria-labelledby="story-flow-heading">
      <div className="story-flow-header">
        <p className="report-eyebrow">{copy.eyebrow}</p>
        <h2 id="story-flow-heading">{copy.title}</h2>
      </div>

      <ol className="story-flow">
        {steps.map((step, index) => (
          <li key={step.label} className="story-flow-step">
            <span className="flow-index">{index + 1}</span>
            <span className="flow-label">{step.label}</span>
            <span className="flow-content">{step.content}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function buildFlowSteps(result: GenerateResponse, copy: (typeof flowCopy)[UiLanguage]): FlowStep[] {
  const originalIdea = findNote(result.analysis.notes, "Original idea")?.content;
  const emotionalCore = findNoteByKeyword(result.analysis.notes, "emotional")?.content;
  const conflict = findStorySection(result.story_plan.sections, ["Main conflict", "Conflict"])?.content;
  const turningPoint = findStorySection(result.story_plan.sections, ["Middle", "Turning point"])?.content;
  const ending = findStorySection(result.story_plan.sections, ["Ending", "Resolution"])?.content;

  return [
    {
      label: copy.labels.idea,
      content: originalIdea ?? result.story_plan.logline ?? result.analysis.summary,
    },
    {
      label: copy.labels.emotionalCore,
      content: emotionalCore ?? result.analysis.summary,
    },
    {
      label: copy.labels.conflict,
      content: conflict ?? copy.fallback.conflict,
    },
    {
      label: copy.labels.turningPoint,
      content: turningPoint ?? copy.fallback.turningPoint,
    },
    {
      label: copy.labels.ending,
      content: ending ?? copy.fallback.ending,
    },
  ].filter((step) => step.content.trim().length > 0);
}

function findNote(notes: AnalysisNote[], label: string) {
  return notes.find((note) => normalize(note.label) === normalize(label));
}

function findNoteByKeyword(notes: AnalysisNote[], keyword: string) {
  const normalizedKeyword = normalize(keyword);
  return notes.find(
    (note) =>
      normalize(note.label).includes(normalizedKeyword) ||
      normalize(note.content).includes(normalizedKeyword),
  );
}

function findStorySection(sections: StoryPlanSection[], labels: string[]) {
  const normalizedLabels = labels.map(normalize);
  return sections.find((section) => {
    const normalizedTitle = normalize(section.title);
    return normalizedLabels.some((label) => normalizedTitle.includes(label));
  });
}

function normalize(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}

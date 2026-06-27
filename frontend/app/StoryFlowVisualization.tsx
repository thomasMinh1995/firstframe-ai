"use client";

import { AnalysisNote, GenerateResponse, StoryPlanSection } from "./apiClient";

type StoryFlowVisualizationProps = {
  result: GenerateResponse;
};

type FlowStep = {
  label: string;
  content: string;
};

export function StoryFlowVisualization({ result }: StoryFlowVisualizationProps) {
  const steps = buildFlowSteps(result);

  return (
    <section className="panel story-flow-card" aria-labelledby="story-flow-heading">
      <div className="story-flow-header">
        <p className="report-eyebrow">Story Flow</p>
        <h2 id="story-flow-heading">Arc at a glance</h2>
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

function buildFlowSteps(result: GenerateResponse): FlowStep[] {
  const originalIdea = findNote(result.analysis.notes, "Original idea")?.content;
  const emotionalCore = findNoteByKeyword(result.analysis.notes, "emotional")?.content;
  const conflict = findStorySection(result.story_plan.sections, ["Main conflict", "Conflict"])?.content;
  const turningPoint = findStorySection(result.story_plan.sections, ["Middle", "Turning point"])?.content;
  const ending = findStorySection(result.story_plan.sections, ["Ending", "Resolution"])?.content;

  return [
    {
      label: "Idea",
      content: originalIdea ?? result.story_plan.logline ?? result.analysis.summary,
    },
    {
      label: "Emotional Core",
      content: emotionalCore ?? result.analysis.summary,
    },
    {
      label: "Conflict",
      content: conflict ?? "The central obstacle is still being clarified.",
    },
    {
      label: "Turning Point",
      content: turningPoint ?? "The middle turn is still being shaped.",
    },
    {
      label: "Ending",
      content: ending ?? "The final image is still being refined.",
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

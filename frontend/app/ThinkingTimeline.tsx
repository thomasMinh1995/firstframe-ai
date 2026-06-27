"use client";

import { useEffect, useState } from "react";

export type ThinkingTimelineStatus = "active" | "ready";

export type ThinkingTimelineProps = {
  steps?: string[];
  status: ThinkingTimelineStatus;
  onStepChange?: (stepIndex: number) => void;
};

const defaultSteps = [
  "Understanding your idea",
  "Identifying emotional core",
  "Planning the story",
  "Evaluating story quality",
  "Preparing Story Plan",
];

export function ThinkingTimeline({
  steps,
  status,
  onStepChange,
}: ThinkingTimelineProps) {
  const timelineSteps = steps ?? defaultSteps;
  const [activeStepIndex, setActiveStepIndex] = useState(0);

  useEffect(() => {
    if (status === "ready") {
      setActiveStepIndex(timelineSteps.length);
      onStepChange?.(timelineSteps.length);
      return;
    }

    setActiveStepIndex(0);
    onStepChange?.(0);
    const intervalId = window.setInterval(() => {
      setActiveStepIndex((current) => {
        const nextStep = Math.min(current + 1, timelineSteps.length - 1);
        onStepChange?.(nextStep);
        return nextStep;
      });
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [onStepChange, status, timelineSteps.length]);

  return (
    <section className="panel status-panel" aria-live="polite">
      <h2>{status === "ready" ? "Story Plan Ready" : "Creative Reasoning Harness"}</h2>
      <ol className="thinking-timeline">
        {timelineSteps.map((step, index) => {
          const isComplete = status === "ready" || index < activeStepIndex;
          const isActive = status === "active" && index === activeStepIndex;
          const stateLabel = isComplete ? "Completed" : isActive ? "In Progress" : "Waiting";

          return (
            <li
              key={step}
              className={`thinking-step${isComplete ? " is-complete" : ""}${
                isActive ? " is-active" : ""
              }`}
            >
              <span className="thinking-marker" aria-hidden="true">
                {isComplete ? "OK" : index + 1}
              </span>
              <span>
                <span className="thinking-label">{step}</span>
                <span className="thinking-state">{stateLabel}</span>
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

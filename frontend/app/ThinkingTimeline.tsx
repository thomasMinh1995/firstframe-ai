"use client";

import { useEffect, useState } from "react";

export type ThinkingTimelineStatus = "active" | "ready";

export type ThinkingTimelineProps = {
  steps?: string[];
  finalStepDetails?: string[];
  readyTitle?: string;
  status: ThinkingTimelineStatus;
  stateLabels?: {
    completed: string;
    inProgress: string;
    waiting: string;
  };
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
  finalStepDetails = [],
  readyTitle = "Story Plan Ready",
  status,
  stateLabels = {
    completed: "Completed",
    inProgress: "In Progress",
    waiting: "Waiting",
  },
  onStepChange,
}: ThinkingTimelineProps) {
  const timelineSteps = steps ?? defaultSteps;
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [detailIndex, setDetailIndex] = useState(0);

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

  useEffect(() => {
    const shouldShowDetails =
      status === "active" &&
      activeStepIndex === timelineSteps.length - 1 &&
      finalStepDetails.length > 0;

    if (!shouldShowDetails) {
      setDetailIndex(0);
      return;
    }

    const intervalId = window.setInterval(() => {
      setDetailIndex((current) => (current + 1) % finalStepDetails.length);
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [activeStepIndex, finalStepDetails.length, status, timelineSteps.length]);

  const shouldShowDetails =
    status === "active" &&
    activeStepIndex === timelineSteps.length - 1 &&
    finalStepDetails.length > 0;

  return (
    <section className="panel status-panel" aria-live="polite">
      <h2>{status === "ready" ? readyTitle : "Creative Reasoning Harness"}</h2>
      <ol className="thinking-timeline">
        {timelineSteps.map((step, index) => {
          const isComplete = status === "ready" || index < activeStepIndex;
          const isActive = status === "active" && index === activeStepIndex;
          const stateLabel = isComplete
            ? stateLabels.completed
            : isActive
              ? stateLabels.inProgress
              : stateLabels.waiting;

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
      {shouldShowDetails ? (
        <p className="thinking-detail">{finalStepDetails[detailIndex]}</p>
      ) : null}
    </section>
  );
}

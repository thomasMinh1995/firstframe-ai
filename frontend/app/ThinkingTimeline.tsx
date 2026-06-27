"use client";

import { useEffect, useState } from "react";

export type ThinkingTimelineStatus = "active" | "complete";

export type ThinkingTimelineProps = {
  steps?: string[];
  status: ThinkingTimelineStatus;
};

const defaultSteps = [
  "Understanding your idea",
  "Identifying emotional core",
  "Planning the story",
  "Evaluating story quality",
  "Preparing Story Plan",
];

export function ThinkingTimeline({ steps = defaultSteps, status }: ThinkingTimelineProps) {
  const [completedCount, setCompletedCount] = useState(0);

  useEffect(() => {
    if (status === "complete") {
      setCompletedCount(steps.length);
      return;
    }

    setCompletedCount(0);
    const intervalId = window.setInterval(() => {
      setCompletedCount((current) => Math.min(current + 1, steps.length));
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [status, steps.length]);

  return (
    <section className="panel status-panel" aria-live="polite">
      <h2>Creative Reasoning Harness</h2>
      <ol className="thinking-timeline">
        {steps.map((step, index) => {
          const isComplete = index < completedCount;
          const isActive = status === "active" && index === completedCount;
          const stateLabel = isComplete ? "Complete" : isActive ? "In progress" : "Waiting";

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

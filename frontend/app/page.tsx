"use client";

import { FormEvent, useState } from "react";
import { generateStoryPlan, GenerateResponse } from "./apiClient";
import { StoryResultCards } from "./StoryResultCards";
import { ThinkingTimeline, ThinkingTimelineStatus } from "./ThinkingTimeline";

const defaultIdea =
  "A retired father wants to meet his daughter one last time before she leaves Vietnam.";

export default function Home() {
  const [idea, setIdea] = useState(defaultIdea);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [timelineStatus, setTimelineStatus] = useState<ThinkingTimelineStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (idea.trim().length === 0) {
      setValidationMessage("Enter a short idea before generating.");
      return;
    }

    setIsLoading(true);
    setTimelineStatus("active");
    setError(null);
    setValidationMessage(null);
    setResult(null);

    try {
      const generatedResult = await generateStoryPlan(idea.trim());
      setResult(generatedResult);
      setTimelineStatus("complete");
      await wait(250);
    } catch (caughtError) {
      setTimelineStatus(null);
      setError(caughtError instanceof Error ? caughtError.message : "Something went wrong.");
    } finally {
      setIsLoading(false);
      setTimelineStatus(null);
    }
  }

  return (
    <main className="page-shell">
      <section className="workspace">
        <header className="intro">
          <p className="eyebrow">Creative Reasoning Harness</p>
          <h1>FirstFrame AI</h1>
          <p className="tagline">From vague idea to your first structured story plan</p>
          <p className="summary">
            FirstFrame AI helps beginners turn vague creative ideas into structured story plans
            through reasoning, planning, and evaluation.
          </p>
        </header>

        <form className="generator" onSubmit={handleSubmit}>
          <label htmlFor="idea">Your story idea</label>
          <textarea
            id="idea"
            value={idea}
            onChange={(event) => {
              setIdea(event.target.value);
              setValidationMessage(null);
            }}
            placeholder="Describe a rough short-film idea..."
            rows={7}
          />
          {validationMessage ? <p className="form-message">{validationMessage}</p> : null}
          <button type="submit" disabled={isLoading}>
            {isLoading ? "Generating..." : "Generate Story Plan"}
          </button>
        </form>

        {error ? <p className="error">{error}</p> : null}

        {timelineStatus ? <ThinkingTimeline status={timelineStatus} /> : null}

        {result && !timelineStatus ? <StoryResultCards result={result} /> : null}
      </section>
    </main>
  );
}

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

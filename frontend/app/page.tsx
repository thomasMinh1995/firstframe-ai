"use client";

import { FormEvent, useCallback, useState } from "react";
import { generateStoryPlan, GenerateResponse } from "./apiClient";
import { StoryFlowVisualization } from "./StoryFlowVisualization";
import { StoryResultCards } from "./StoryResultCards";
import { ThinkingTimeline, ThinkingTimelineStatus } from "./ThinkingTimeline";
import { detectInputLanguage, UiLanguage } from "./language";

const defaultIdea =
  "A retired father wants to meet his daughter one last time before she leaves Vietnam.";

const uiCopy = {
  en: {
    timelineSteps: [
      "Understanding your idea",
      "Identifying emotional core",
      "Planning the story",
      "Evaluating story quality",
      "Preparing Story Plan",
    ],
    finalStepDetails: [
      "Selecting the strongest story direction...",
      "Checking the emotional arc...",
      "Making sure the plan stays production-friendly...",
      "Preparing a structured mentor-style response...",
    ],
    buttonPhaseLabels: ["Analyzing...", "Analyzing...", "Planning...", "Reviewing...", "Finalizing..."],
    readyTitle: "Story Plan Ready",
    stateLabels: {
      completed: "Completed",
      inProgress: "In Progress",
      waiting: "Waiting",
    },
  },
  vi: {
    timelineSteps: [
      "Đang hiểu ý tưởng của bạn",
      "Xác định lõi cảm xúc",
      "Xây dựng cấu trúc câu chuyện",
      "Đánh giá chất lượng câu chuyện",
      "Chuẩn bị Story Plan",
    ],
    finalStepDetails: [
      "Chọn hướng phát triển câu chuyện rõ nhất...",
      "Kiểm tra mạch cảm xúc...",
      "Đảm bảo kế hoạch vẫn phù hợp để sản xuất chi phí thấp...",
      "Chuẩn bị phản hồi theo phong cách mentor...",
    ],
    buttonPhaseLabels: [
      "Đang phân tích...",
      "Đang phân tích...",
      "Đang lập kế hoạch...",
      "Đang đánh giá...",
      "Đang hoàn thiện...",
    ],
    readyTitle: "Story Plan đã sẵn sàng",
    stateLabels: {
      completed: "Hoàn tất",
      inProgress: "Đang xử lý",
      waiting: "Đang chờ",
    },
  },
} satisfies Record<
  UiLanguage,
  {
    timelineSteps: string[];
    finalStepDetails: string[];
    buttonPhaseLabels: string[];
    readyTitle: string;
    stateLabels: {
      completed: string;
      inProgress: string;
      waiting: string;
    };
  }
>;

export default function Home() {
  const [idea, setIdea] = useState(defaultIdea);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [timelineStatus, setTimelineStatus] = useState<ThinkingTimelineStatus | null>(null);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [uiLanguage, setUiLanguage] = useState<UiLanguage>("en");
  const [error, setError] = useState<string | null>(null);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const copy = uiCopy[uiLanguage];

  const handleTimelineStepChange = useCallback((stepIndex: number) => {
    setActiveStepIndex(stepIndex);
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (idea.trim().length === 0) {
      setValidationMessage("Enter a short idea before generating.");
      return;
    }

    const detectedLanguage = detectInputLanguage(idea.trim());
    const detectedCopy = uiCopy[detectedLanguage];
    setUiLanguage(detectedLanguage);
    setIsLoading(true);
    setTimelineStatus("active");
    setActiveStepIndex(0);
    setError(null);
    setValidationMessage(null);
    setResult(null);

    try {
      const generatedResult = await generateStoryPlan(idea.trim());
      setResult(generatedResult);
      setTimelineStatus("ready");
      setActiveStepIndex(detectedCopy.buttonPhaseLabels.length - 1);
      await wait(650);
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
            {isLoading
              ? copy.buttonPhaseLabels[activeStepIndex] ??
                copy.buttonPhaseLabels[copy.buttonPhaseLabels.length - 1]
              : "Generate Story Plan"}
          </button>
        </form>

        {error ? <p className="error">{error}</p> : null}

        {timelineStatus ? (
          <ThinkingTimeline
            steps={copy.timelineSteps}
            finalStepDetails={copy.finalStepDetails}
            readyTitle={copy.readyTitle}
            status={timelineStatus}
            stateLabels={copy.stateLabels}
            onStepChange={handleTimelineStepChange}
          />
        ) : null}

        {result && !timelineStatus ? (
          <>
            <StoryFlowVisualization result={result} uiLanguage={uiLanguage} />
            <StoryResultCards result={result} uiLanguage={uiLanguage} />
          </>
        ) : null}
      </section>
    </main>
  );
}

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

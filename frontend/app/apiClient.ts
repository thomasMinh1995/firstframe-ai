export type AnalysisNote = {
  label: string;
  content: string;
};

export type StoryPlanSection = {
  title: string;
  purpose: string;
  content: string;
};

export type EvaluationFinding = {
  criterion_id: string;
  message: string;
  severity: string;
  score: number | null;
};

export type GenerateResponse = {
  analysis: {
    summary: string;
    notes: AnalysisNote[];
    missing_information: string[];
  };
  story_plan: {
    title: string | null;
    logline: string | null;
    sections: StoryPlanSection[];
  };
  evaluation: {
    passed: boolean | null;
    rubric_scores: Record<string, number>;
    findings: EvaluationFinding[];
  };
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function generateStoryPlan(idea: string): Promise<GenerateResponse> {
  let response: Response;

  try {
    response = await fetch(`${apiBaseUrl}/api/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ idea }),
    });
  } catch {
    throw new Error("Backend unavailable. Start the backend and try again.");
  }

  if (!response.ok) {
    throw new Error("The story plan request failed. Please try again.");
  }

  try {
    const data = await response.json();
    if (!isGenerateResponse(data)) {
      throw new Error("invalid-shape");
    }
    return data;
  } catch {
    throw new Error("The backend returned an invalid response.");
  }
}

function isGenerateResponse(value: unknown): value is GenerateResponse {
  if (!isRecord(value)) {
    return false;
  }

  const analysis = value.analysis;
  const storyPlan = value.story_plan;
  const evaluation = value.evaluation;

  return (
    isRecord(analysis) &&
    typeof analysis.summary === "string" &&
    Array.isArray(analysis.notes) &&
    Array.isArray(analysis.missing_information) &&
    isRecord(storyPlan) &&
    Array.isArray(storyPlan.sections) &&
    isRecord(evaluation) &&
    isRecord(evaluation.rubric_scores) &&
    Array.isArray(evaluation.findings)
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

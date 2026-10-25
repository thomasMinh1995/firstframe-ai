import type { ResponseLanguage } from "./language";

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

export type RevisionNote = {
  note_id: string; artifact_id: string; comparison: "mismatch" | "uncertain";
  observation: string; suggestion: string;
  decision_id: string; decision_quote: string; decision_question: string | null;
  targets: { target_id: string; quote: string }[];
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
    revision_notes?: RevisionNote[] | null;
  };
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function generateStoryPlan(
  idea: string, responseLanguage: ResponseLanguage = "auto",
): Promise<GenerateResponse> {
  let response: Response;

  try {
    response = await fetch(`${apiBaseUrl}/api/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ idea, response_language: responseLanguage }),
    });
  } catch {
    throw new Error("Không kết nối được backend. Hãy kiểm tra rồi thử lại.");
  }

  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null);
    throw new Error(isRecord(detail) && typeof detail.detail === "string" ? detail.detail
      : "Chưa tạo được bản phát triển. Hãy thử lại.");
  }

  try {
    const data = await response.json();
    if (!isGenerateResponse(data)) {
      throw new Error("invalid-shape");
    }
    return data;
  } catch {
    throw new Error("Backend trả về dữ liệu không hợp lệ.");
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

import type { FidelityReport } from "./FidelityPanel";
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
    fidelity?: FidelityReport | null;
    passed: boolean | null;
    rubric_scores: Record<string, number>;
    findings: EvaluationFinding[];
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
    Array.isArray(evaluation.findings) &&
    (evaluation.fidelity == null || isFidelityReport(evaluation.fidelity))
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isFidelityReport(value: unknown): value is FidelityReport {
  return isRecord(value) && ["clear", "issues", "unverified"].includes(String(value.status))
    && Number.isInteger(value.withheld_count) && Number(value.withheld_count) >= 0
    && Array.isArray(value.checks) && value.checks.every((check) => isRecord(check)
      && ["fidelity", "craft"].includes(String(check.kind))
      && Number.isInteger(check.section_index) && Number(check.section_index) >= -2
      && ["section_title", "section_text", "draft_quote", "author_quote", "explanation"]
        .every((key) => typeof check[key] === "string")
      && (check.suggestion === null || typeof check.suggestion === "string")
      && (check.assessment == null || (isRecord(check.assessment)
        && ["contradictory", "compatible", "uncertain"].includes(String(check.assessment.relation))
        && ["supported", "unsupported", "uncertain"].includes(String(check.assessment.concern))
        && ["aligned", "violates", "uncertain"].includes(String(check.assessment.revision))
        && ["relation_reason", "concern_reason", "revision_reason"]
          .every(key => typeof (check.assessment as Record<string, unknown>)[key] === "string")))
      && (check.verification_note == null || typeof check.verification_note === "string")
      && ["supported", "unverified"].includes(String(check.suggestion_status)));
}

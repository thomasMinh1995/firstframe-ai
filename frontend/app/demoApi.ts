import type { GenerateResponse } from "./apiClient";
import { isDraft, isFeedback, type StoryDraft } from "./projectsApi";

type ModelUse = { provider: string; model: string };
export type DemoStep = {
  kind: "brief" | "analysis" | "answers" | "plan" | "evaluation" | "edit" | "review";
  title: string; description: string; models_used: ModelUse[];
  idea: string | null; constraints: string[];
  analysis: GenerateResponse["analysis"] | null;
  answers: { question: string; answer: string }[];
  draft: StoryDraft | null; feedback: GenerateResponse["evaluation"] | null;
};
export type DemoSummary = {
  id: string; title: string; description: string; started_at: string;
  review_status: string; models_used: ModelUse[]; step_count: number;
};
export type DemoScenario = DemoSummary & { steps: DemoStep[] };
const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request(path: string): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/demo/scenarios${path}`, { cache: "no-store" });
  } catch {
    throw new Error("Không đọc được dữ liệu demo. Hãy kiểm tra backend local rồi tải lại.");
  }
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(isRecord(data) && typeof data.detail === "string" ? data.detail
      : "Không đọc được kịch bản demo. Hãy tải lại danh sách.");
  }
  return data;
}

export async function listDemoScenarios(curated = false): Promise<DemoSummary[]> {
  const data = await request(`?curated=${curated}`);
  if (!Array.isArray(data) || !data.every(isSummary)) throw new Error("Danh sách demo không hợp lệ.");
  return data;
}

export async function getDemoScenario(id: string, curated = false): Promise<DemoScenario> {
  const data = await request(`/${encodeURIComponent(id)}?curated=${curated}`);
  const steps = isRecord(data) ? data.steps : null;
  if (!isSummary(data) || !Array.isArray(steps)
      || steps.length !== data.step_count || !steps.every(isStep)) {
    throw new Error("Kịch bản demo không hợp lệ. Hãy chọn kịch bản khác hoặc tải lại.");
  }
  return { ...data, steps };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}
function models(value: unknown): value is ModelUse[] {
  return Array.isArray(value) && value.every((item) => isRecord(item)
    && typeof item.provider === "string" && typeof item.model === "string");
}
function isSummary(value: unknown): value is DemoSummary {
  return isRecord(value) && typeof value.id === "string" && typeof value.title === "string"
    && typeof value.description === "string" && typeof value.started_at === "string"
    && typeof value.review_status === "string" && models(value.models_used)
    && Number.isInteger(value.step_count) && Number(value.step_count) > 0;
}
function isStep(value: unknown): value is DemoStep {
  if (!isRecord(value) || typeof value.kind !== "string"
      || !["brief", "analysis", "answers", "plan", "evaluation", "edit", "review"].includes(value.kind)
      || typeof value.title !== "string" || typeof value.description !== "string"
      || !models(value.models_used) || !strings(value.constraints)
      || !(value.idea === null || typeof value.idea === "string")
      || !Array.isArray(value.answers) || !value.answers.every((answer) => isRecord(answer)
        && typeof answer.question === "string" && typeof answer.answer === "string")) return false;
  const analysis = value.analysis;
  return (analysis === null || (isRecord(analysis) && typeof analysis.summary === "string"
    && strings(analysis.missing_information) && Array.isArray(analysis.notes)
    && analysis.notes.every((note) => isRecord(note) && typeof note.label === "string"
      && typeof note.content === "string")))
    && (value.draft === null || isDraft(value.draft))
    && (value.feedback === null || isFeedback(value.feedback));
}

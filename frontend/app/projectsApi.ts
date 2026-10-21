import type { GenerateResponse, StoryPlanSection } from "./apiClient";
import { progressCopy } from "./progressState";
import type { UiLanguage } from "./language";
import type { ResponseLanguage } from "./language";

export type StoryDraft = { title: string; logline: string; sections: StoryPlanSection[] };
export type Feedback = GenerateResponse["evaluation"];
export type ClarificationVersion = {
  response_language: ResponseLanguage;
  id: string; created_at: string; idea: string; constraints: string[]; answers: string[];
  questions: string[];
};
export type DraftVersion = ClarificationVersion & {
  draft: StoryDraft; feedback: Feedback | null;
};
export type Project = {
  response_language: ResponseLanguage;
  id: string; revision: number; updated_at: string; title: string; idea: string;
  constraints: string[]; analysis: (GenerateResponse["analysis"] & { artifact_id: string }) | null; answers: string[];
  draft: StoryDraft | null; feedback: Feedback | null; feedback_is_current: boolean;
  versions: DraftVersion[];
  clarification_history: ClarificationVersion[];
};
export type ProjectSummary = Pick<Project, "id" | "title" | "updated_at">;
const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type ProgressEvent = {
  stage: string; status: "active" | "completed" | "failed";
};

export async function streamProjectOperation(
  project: Project, kind: "analyze" | "plan" | "review",
  onProgress: (event: ProgressEvent) => void, language: UiLanguage = "vi",
): Promise<Project> {
  const copy = progressCopy[language];
  const response = await fetch(`${baseUrl}/api/projects/${project.id}/${kind}/stream`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ revision: project.revision }),
  }).catch(() => { throw new Error(copy.connectionError); });
  if (!response.ok || !response.body) throw new Error(copy.startError);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  try {
    while (true) {
      const { value, done } = await reader.read().catch(() => { throw new Error(copy.connectionError); });
      pending += decoder.decode(value, { stream: !done });
      const lines = pending.split("\n");
      pending = lines.pop() ?? "";
      if (done && pending.trim()) lines.push(pending);
      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (event.type === "error") throw new Error(event.detail);
        if (event.type === "progress") {
          if (typeof event.stage !== "string" || !["active", "completed", "failed"].includes(event.status)) {
            throw new Error(copy.invalid);
          }
          onProgress(event);
        }
        if (event.type === "result") {
          if (!isProject(event.project) || event.project.id !== project.id) throw new Error(copy.invalid);
          return event.project;
        }
      }
      if (done) break;
    }
  } finally { reader.releaseLock(); }
  throw new Error(copy.connectionError);
}

async function request(path: string, method = "GET", body?: unknown): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/projects${path}`, {
      method, headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store",
    });
  } catch {
    throw new Error("Không kết nối được backend. Bản đang sửa vẫn được giữ trên màn hình.");
  }
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(isRecord(data) && typeof data.detail === "string" ? data.detail
      : response.status === 422 ? "Kiểm tra nội dung: tên và các phần không được trống hoặc vượt giới hạn."
        : "Không hoàn tất được thao tác. Bản đang sửa vẫn được giữ; hãy thử lại.");
  }
  return data;
}

export async function listProjects(): Promise<ProjectSummary[]> {
  const data = await request("");
  if (!Array.isArray(data) || !data.every(isSummary)) throw new Error("Danh sách dự án không hợp lệ.");
  return data;
}
export async function projectRequest(path: string, method = "GET", body?: unknown): Promise<Project> {
  const data = await request(path, method, body);
  if (!isProject(data)) throw new Error("Dự án trả về không hợp lệ. Nội dung đang sửa được giữ nguyên.");
  return data;
}
export function editableProject(project: Project) {
  return { revision: project.revision, response_language: project.response_language,
    title: project.title, idea: project.idea,
    constraints: project.constraints, answers: project.answers, draft: project.draft };
}
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}
function isSummary(value: unknown): value is ProjectSummary & Record<string, unknown> {
  return isRecord(value) && typeof value.id === "string" && typeof value.title === "string"
    && typeof value.updated_at === "string";
}
export function isDraft(value: unknown): value is StoryDraft {
  return isRecord(value) && typeof value.title === "string" && typeof value.logline === "string"
    && Array.isArray(value.sections) && value.sections.every((section) => isRecord(section)
      && typeof section.title === "string" && typeof section.purpose === "string"
      && typeof section.content === "string");
}
export function isFeedback(value: unknown): value is Feedback {
  return isRecord(value) && (value.passed === null || typeof value.passed === "boolean")
    && isRecord(value.rubric_scores)
    && Object.values(value.rubric_scores).every((score) => typeof score === "number")
    && Array.isArray(value.findings) && value.findings.every((finding) => isRecord(finding)
      && typeof finding.criterion_id === "string" && typeof finding.message === "string"
      && typeof finding.severity === "string");
}
function isProject(value: unknown): value is Project {
  if (!isSummary(value) || !isRecord(value)) return false;
  const analysis = value.analysis;
  return ["auto", "vi", "en"].includes(String(value.response_language))
    && Number.isInteger(value.revision) && typeof value.idea === "string"
    && strings(value.constraints) && strings(value.answers)
    && (analysis === null || (isRecord(analysis) && typeof analysis.artifact_id === "string" && typeof analysis.summary === "string"
      && strings(analysis.missing_information) && Array.isArray(analysis.notes)))
    && (value.draft === null || isDraft(value.draft))
    && (value.feedback === null || isFeedback(value.feedback))
    && typeof value.feedback_is_current === "boolean" && Array.isArray(value.versions)
    && value.versions.every((version) => isClarificationVersion(version) && isRecord(version)
      && isDraft(version.draft) && (version.feedback === null || isFeedback(version.feedback)))
    && Array.isArray(value.clarification_history)
    && value.clarification_history.every(isClarificationVersion);
}
function isClarificationVersion(value: unknown): value is ClarificationVersion & Record<string, unknown> {
  return isRecord(value) && typeof value.id === "string" && typeof value.created_at === "string"
    && typeof value.idea === "string" && strings(value.constraints) && strings(value.questions)
    && strings(value.answers);
}

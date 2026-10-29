import type { GenerateResponse, StoryPlanSection } from "./apiClient";
import { progressCopy } from "./progressState";
import {isProvenanceMap} from './provenance';
import type { UiLanguage } from "./language";
import type { ResponseLanguage } from "./language";
import { stagingLabels, type Scene, type SceneOutline, type SceneVersion, type SceneHandoff, type SceneProposal, type SceneSuggestionInput, type StagingIdea, type StagingUse, type SceneSketch } from "./sceneTypes";

import {unfinishedScriptScenes,type Screenplay, type ScreenplayVersion, type ScreenplayProposal, type ScriptScene, type SceneWritingInput, type ScreenplaySelection} from "./screenplayTypes";

import {reviewNoteSupported,reviewSourceMatches,type ScreenplayReview,type ReviewSource,type ReviewNote} from "./screenplayReviewTypes";

export type StoryDraft = { title: string; logline: string; sections: StoryPlanSection[] };
export type Feedback = GenerateResponse["evaluation"] & { artifact_id?: string };
export type AuthorContext = {
  idea: string; constraints: string[];
  clarifications: { question: string; answer: string; input_index: number | null }[];
  pending_questions: { question: string; input_index: number }[];
};
export type FeedbackSource = {
  project_id: string; artifact_id: string; revision: number; content_key: string;
  context: AuthorContext; draft: StoryDraft;
};
export type ClarificationVersion = {
  response_language: ResponseLanguage;
  id: string; created_at: string; idea: string; constraints: string[]; answers: string[];
  questions: string[];
};
export type DraftVersion = ClarificationVersion & {
  draft: StoryDraft; feedback: Feedback | null; feedback_source?: FeedbackSource | null;
};
export type PlanGeneration = {
  id: string; created_at: string; source_revision: number; source_content: string;
  context: AuthorContext; draft: StoryDraft; critic_status: "pending" | "failed" | "reviewed";
  applied_revision: number | null; feedback: Feedback | null; feedback_source: FeedbackSource | null;
};
export type Project = {
  last_save_id?: string | null;
  last_save_revision?: number | null;
  response_language: ResponseLanguage;
  id: string; revision: number; updated_at: string; title: string; idea: string;
  constraints: string[]; analysis: (GenerateResponse["analysis"] & { artifact_id: string }) | null; answers: string[];
  draft: StoryDraft | null; feedback: Feedback | null; feedback_is_current: boolean;
  author_context?: AuthorContext; feedback_source?: FeedbackSource | null;
  versions: DraftVersion[];
  clarification_history: ClarificationVersion[];
  plan_generations?: PlanGeneration[]; applicable_plan_ids?: string[];
  screenplay_reviews?:ScreenplayReview[];current_screenplay_review_ids?:string[];
  screenplay_proposals?:ScreenplayProposal[];applicable_screenplay_proposal_ids?:string[];
  pending_screenplay_proposal_id?:string;pending_screenplay_previews?:Record<string,ScriptScene>;
  screenplay?: Screenplay | null; screenplay_versions?: ScreenplayVersion[]; screenplay_source_is_current?: boolean;
  screenplay_selections?:ScreenplaySelection[];screenplay_handoff?:ScreenplaySelection|null;
  scene_outline?: SceneOutline | null; scene_versions?: SceneVersion[];
  staging_proposals?: SceneProposal[];
  scene_sketches?: SceneSketch[]; selected_scene_sketches?: Record<string, string>; applicable_sketch_ids?: string[];
  scene_proposals?: SceneProposal[]; applicable_scene_proposal_ids?: string[];
  pending_staging_use?: StagingUse; pending_staging_edits?: Record<string, string>;
  pending_scene_proposal_id?: string; pending_scene_previews?: Record<string, Scene[]>;
  scene_source_is_current?: boolean; scene_handoff?: SceneHandoff | null;
};
export type ProjectSummary = Pick<Project, "id" | "title" | "updated_at">;
const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type ProgressEvent = {
  stage: string; status: "active" | "completed" | "failed";
};

export async function streamProjectOperation(
  project: Project, kind: "analyze" | "plan" | "review" | "scene-suggestions" | "scene-sketches" | "screenplay-proposals" | "screenplay-reviews",
  onProgress: (event: ProgressEvent) => void, language: UiLanguage = "vi", input?: SceneWritingInput | SceneSuggestionInput | {request_id: string; scene_id: string; instructions: string},
): Promise<Project> {
  const copy = progressCopy[language];
  // Backend heartbeats arrive every 15s. A silent connection must not lock the editor forever.
  const controller = new AbortController();
  let timer = setTimeout(() => controller.abort(), 45_000);
  try {
    const response = await fetch(`${baseUrl}/api/projects/${project.id}/${kind === "analyze" ? "clarify" : kind}/stream`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ revision: project.revision, ...input }), signal: controller.signal,
    }).catch(() => { throw new Error(copy.connectionError); });
    if (!response.ok || !response.body) throw new Error(copy.startError);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let pending = "";
    try {
      while (true) {
        const { value, done } = await reader.read().catch(() => { throw new Error(copy.connectionError); });
        clearTimeout(timer);
        timer = setTimeout(() => controller.abort(), 45_000);
        pending += decoder.decode(value, { stream: !done });
        const lines = pending.split("\n");
        pending = lines.pop() ?? "";
        if (done && pending.trim()) lines.push(pending);
        for (const line of lines) {
          if (!line.trim()) continue;
          let event: unknown;
          try { event = JSON.parse(line); } catch { throw new Error(copy.invalid); }
          if (!isRecord(event) || !["progress", "result", "error"].includes(String(event.type))) throw new Error(copy.invalid);
          if (event.type === "error") throw new Error(typeof event.detail === "string" ? event.detail : copy.invalid);
          if (event.type === "progress") {
            if (typeof event.stage !== "string" || !event.stage || typeof event.status !== "string"
              || !["active", "completed", "failed"].includes(event.status)) {
              throw new Error(copy.invalid);
            }
            onProgress({ stage: event.stage, status: event.status as ProgressEvent["status"] });
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
  } finally {
    clearTimeout(timer);
    controller.abort();
  }
}

export class ProjectRequestError extends Error {
  constructor(message: string, public status: number) {super(message);}
}

async function request(path: string, method = "GET", body?: unknown): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/projects${path}`, {
      method, signal: AbortSignal.timeout(45_000), headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body), cache: "no-store",
    });
  } catch {
    throw new Error("Không kết nối được backend. Bản đang sửa vẫn được giữ trên màn hình.");
  }
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ProjectRequestError(isRecord(data) && typeof data.detail === "string" ? data.detail
      : response.status === 422 ? "Kiểm tra nội dung: tên và các phần không được trống hoặc vượt giới hạn."
        : "Không hoàn tất được thao tác. Bản đang sửa vẫn được giữ; hãy thử lại.", response.status);
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
export function sceneSketchUrl(projectId: string, sketchId: string): string {
  return `${baseUrl}/api/projects/${encodeURIComponent(projectId)}/scene-sketches/${encodeURIComponent(sketchId)}/image`;
}
export function editableProject(project: Project) {
  return { revision: project.revision, response_language: project.response_language,
    title: project.title, idea: project.idea,
    ...(project.pending_scene_proposal_id ? { scene_proposal_id: project.pending_scene_proposal_id } : {}),
    ...(project.pending_scene_previews && Object.keys(project.pending_scene_previews).length ? { scene_proposal_previews: project.pending_scene_previews } : {}),
    ...(project.pending_staging_use ? { staging_use: project.pending_staging_use } : {}),
    ...(project.pending_staging_edits && Object.keys(project.pending_staging_edits).length ? { staging_idea_edits: project.pending_staging_edits } : {}),
    ...(project.screenplay == null ? {} : {screenplay: {id:project.screenplay.id, version:project.screenplay.version, scenes:project.screenplay.scenes}}),
    ...(project.pending_screenplay_proposal_id?{screenplay_proposal_id:project.pending_screenplay_proposal_id}:{}),
    ...(project.pending_screenplay_previews&&Object.keys(project.pending_screenplay_previews).length?{screenplay_proposal_previews:project.pending_screenplay_previews}:{}),
    constraints: project.constraints, answers: project.answers, draft: project.draft,
    ...(project.scene_outline == null ? {} : { scene_outline: {
      id: project.scene_outline.id, version: project.scene_outline.version, scenes: project.scene_outline.scenes,
    } }) };
}

export function sameEditableContent(a: Project, b: Project): boolean {
  const { revision: _a, ...left } = editableProject(a);
  const { revision: _b, ...right } = editableProject(b);
  const previews = (project: Project) => (project.scene_proposals ?? [])
    .filter(p => p.preview_scenes != null).map(p => [p.id, p.preview_scenes]);
  const ideaEdits = (project: Project) => (project.staging_proposals ?? []).flatMap(p => (p.staging_ideas ?? [])
    .filter(i => i.preview_text !== null).map(i => [i.id, i.preview_text]));
  const ideaDecisions = (project: Project) => (project.staging_proposals ?? []).flatMap(p => (p.staging_ideas ?? [])
    .filter(i => i.status !== "available").map(i => [i.id, i.status, i.applied_text]));
  const imageDecisions = (p: Project) => [p.selected_scene_sketches ?? {},
    (p.scene_sketches ?? []).filter(s => s.status === "discarded").map(s => s.id)];
  const scriptDecisions=(p:Project)=>(p.screenplay_proposals??[]).filter(x=>x.preview_scene!==null||['applied','discarded'].includes(x.status))
    .map(x=>[x.id,x.status==='applied'||x.status==='discarded'?x.status:null,x.preview_scene]);
  const reviewDecisions=(p:Project)=>(p.screenplay_reviews??[]).filter(r=>r.status==='discarded'||r.notes.some(n=>n.assessment!==null)).map(r=>[r.id,r.status==='discarded',r.notes.map(n=>[n.id,n.assessment])]);
  const selections=(p:Project)=>(p.screenplay_selections??[]).map(s=>s.id);
  const questions=(p:Project)=>p.analysis?.missing_information??[];
  return JSON.stringify([questions(a),selections(a),reviewDecisions(a),scriptDecisions(a),left, previews(a), ideaEdits(a), ideaDecisions(a), imageDecisions(a)])
    === JSON.stringify([questions(b),selections(b),reviewDecisions(b),scriptDecisions(b),right, previews(b), ideaEdits(b), ideaDecisions(b), imageDecisions(b)]);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}
function isAuthorContext(value: unknown): value is AuthorContext {
  const index = (v: unknown) => typeof v === "number" && Number.isInteger(v) && v >= 0;
  return isRecord(value) && typeof value.idea === "string" && strings(value.constraints)
    && Array.isArray(value.clarifications) && value.clarifications.every(item => isRecord(item)
      && typeof item.question === "string" && typeof item.answer === "string"
      && (item.input_index === null || index(item.input_index)))
    && Array.isArray(value.pending_questions) && value.pending_questions.every(item => isRecord(item)
      && typeof item.question === "string" && index(item.input_index));
}
function isFeedbackSource(value: unknown): value is FeedbackSource | null | undefined {
  return value == null || (isRecord(value) && typeof value.project_id === "string"
    && typeof value.artifact_id === "string" && typeof value.content_key === "string"
    && typeof value.revision === "number" && Number.isInteger(value.revision) && value.revision >= 0
    && isAuthorContext(value.context) && isDraft(value.draft));
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
    && (value.artifact_id === undefined || typeof value.artifact_id === "string")
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
    && (value.author_context === undefined || isAuthorContext(value.author_context))
    && isFeedbackSource(value.feedback_source)
    && (value.plan_generations === undefined || (Array.isArray(value.plan_generations)
      && value.plan_generations.every(isPlanGeneration)))
    && (value.applicable_plan_ids === undefined || strings(value.applicable_plan_ids))
    && (value.scene_proposals === undefined || (Array.isArray(value.scene_proposals) && value.scene_proposals.every(isSceneProposal)))
    && (value.staging_proposals === undefined || (Array.isArray(value.staging_proposals) && value.staging_proposals.every(p => isSceneProposal(p) && p.mode === "staging")))
    && (value.scene_sketches === undefined || (Array.isArray(value.scene_sketches) && value.scene_sketches.length <= 20 && value.scene_sketches.every(isSketch)))
    && (value.selected_scene_sketches === undefined || (isRecord(value.selected_scene_sketches)
      && Object.entries(value.selected_scene_sketches).every(([k,v]) => uuid(k) && uuid(v))))
    && (value.applicable_sketch_ids === undefined || (Array.isArray(value.applicable_sketch_ids) && value.applicable_sketch_ids.every(uuid)))
    && (value.applicable_scene_proposal_ids === undefined || strings(value.applicable_scene_proposal_ids))
    && (value.screenplay_reviews===undefined||(Array.isArray(value.screenplay_reviews)&&value.screenplay_reviews.length<=100&&value.screenplay_reviews.every(isScreenplayReview)))
    && (value.current_screenplay_review_ids===undefined||(Array.isArray(value.current_screenplay_review_ids)&&value.current_screenplay_review_ids.every(uuid)))
    && (value.screenplay_proposals===undefined||(Array.isArray(value.screenplay_proposals)&&value.screenplay_proposals.length<=100&&value.screenplay_proposals.every(isScreenplayProposal)))
    && (value.applicable_screenplay_proposal_ids===undefined||(Array.isArray(value.applicable_screenplay_proposal_ids)&&value.applicable_screenplay_proposal_ids.every(uuid)))
    && (value.screenplay == null || isScreenplay(value.screenplay))
    && (value.screenplay_versions === undefined || (Array.isArray(value.screenplay_versions) && value.screenplay_versions.every(v=>isRecord(v)&&uuid(v.id)&&typeof v.created_at==="string"&&isScreenplay(v.screenplay))))
    && (value.screenplay_source_is_current === undefined || typeof value.screenplay_source_is_current === "boolean")
    && (value.screenplay_selections===undefined||(Array.isArray(value.screenplay_selections)&&value.screenplay_selections.length<=100
      &&value.screenplay_selections.every(isScreenplaySelection)&&new Set(value.screenplay_selections.map(s=>s.id)).size===value.screenplay_selections.length))
    && (value.screenplay_handoff===undefined||((value.screenplay_handoff===null||isScreenplaySelection(value.screenplay_handoff))
      &&JSON.stringify(value.screenplay_handoff)===JSON.stringify(Array.isArray(value.screenplay_selections)?value.screenplay_selections.at(-1)??null:null)))
    && (value.scene_outline == null || isSceneOutline(value.scene_outline))
    && (value.scene_versions === undefined || (Array.isArray(value.scene_versions)
      && value.scene_versions.every(v => isRecord(v) && typeof v.id === "string"
        && typeof v.created_at === "string" && isSceneOutline(v.outline))))
    && (value.scene_source_is_current === undefined || typeof value.scene_source_is_current === "boolean")
    && (value.scene_handoff == null || isSceneHandoff(value.scene_handoff))
    && typeof value.feedback_is_current === "boolean" && Array.isArray(value.versions)
    && value.versions.every((version) => isClarificationVersion(version) && isRecord(version)
      && isDraft(version.draft) && (version.feedback === null || isFeedback(version.feedback))
      && isFeedbackSource(version.feedback_source))
    && Array.isArray(value.clarification_history)
    && value.clarification_history.every(isClarificationVersion);
}
const uuid = (v: unknown): v is string => typeof v === "string"
  && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v);
const positive = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v) && v >= 1;
function isScene(v: unknown): v is Scene {
  return isRecord(v) && uuid(v.id)
    && ["title", "action", "location", "time", "characters", "goal", "purpose", "viewer_intent", "keep_or_avoid"]
      .every(k => typeof v[k] === "string") && isRecord(v.staging_choices)
    && Object.entries(v.staging_choices).every(([key, text]) => Object.hasOwn(stagingLabels, key) && typeof text === "string");
}
function isScenes(v: unknown): v is Scene[] {
  return Array.isArray(v) && v.length <= 60 && v.every(isScene) && new Set(v.map(s => s.id)).size === v.length;
}
function isSceneOutline(v: unknown): v is SceneOutline {
  return isRecord(v) && uuid(v.id) && positive(v.version) && isScenes(v.scenes) && isRecord(v.source)
    && isProvenanceMap(v.provenance) && isProvenanceMap(v.source.draft_provenance)
    && uuid(v.source.id) && Number.isInteger(v.source.project_revision) && Number(v.source.project_revision) >= 0
    && typeof v.source.version_id === "string" && isDraft(v.source.draft) && isAuthorContext(v.source.context)
    && ["auto", "vi", "en"].includes(String(v.source.response_language));
}
function isSceneProposal(v: unknown): v is SceneProposal {
  return isRecord(v) && uuid(v.id) && typeof v.created_at === "string"
    && Number.isInteger(v.source_revision) && Number(v.source_revision) >= 0 && typeof v.source_content === "string"
    && isSceneOutline(v.source_outline) && ["list", "append", "develop", "staging"].includes(String(v.mode))
    && (v.target_scene_id === null || uuid(v.target_scene_id)) && typeof v.instructions === "string"
    && ["pending", "ready", "failed", "applied", "discarded"].includes(String(v.status)) && isScenes(v.scenes)
    && (v.staging_ideas === undefined || (Array.isArray(v.staging_ideas) && v.staging_ideas.length <= 6 && v.staging_ideas.every(isStagingIdea)))
    && (v.staging_sources === undefined || (Array.isArray(v.staging_sources) && v.staging_sources.every(s => isRecord(s)
      && typeof s.id === "string" && typeof s.label === "string" && typeof s.text === "string")))
    && (v.staging_question === undefined || typeof v.staging_question === "string")
    && (v.preview_scenes == null || isScenes(v.preview_scenes))
    && isRecord(v.transitions) && Object.values(v.transitions).every(t => typeof t === "string")
    && (v.provider === null || typeof v.provider === "string") && (v.model === null || typeof v.model === "string")
    && isRecord(v.parameters) && typeof v.prompt_version === "string" && (v.error === null || typeof v.error === "string")
    && (v.applied_revision === null || positive(v.applied_revision));
}
function isStagingIdea(v: unknown): v is StagingIdea {
  return isRecord(v) && uuid(v.id) && typeof v.field === "string" && Object.hasOwn(stagingLabels, v.field)
    && Array.isArray(v.evidence) && v.evidence.length >= 1 && v.evidence.length <= 3
    && v.evidence.every(e => isRecord(e) && typeof e.source_id === "string" && typeof e.quote === "string" && !!e.quote.trim())
    && ["reason", "suggestion", "purpose"].every(k => typeof v[k] === "string" && !!v[k].trim())
    && ["available", "applied", "discarded"].includes(String(v.status))
    && (v.preview_text === null || typeof v.preview_text === "string")
    && (v.applied_text === null || typeof v.applied_text === "string")
    && (v.applied_revision === null || positive(v.applied_revision));
}
function isSceneHandoff(v: unknown): v is SceneHandoff {
  return isRecord(v) && uuid(v.outline_id) && uuid(v.source_id) && positive(v.version)
    && Number.isInteger(v.project_revision) && Number(v.project_revision) >= 0 && isScenes(v.scenes);
}
function isSketch(v: unknown): v is SceneSketch {
  return isRecord(v) && uuid(v.id) && uuid(v.scene_id) && typeof v.created_at === "string"
    && Number.isInteger(v.source_revision) && Number(v.source_revision) >= 0 && typeof v.source_content === "string"
    && isSceneOutline(v.source_outline) && ["instructions", "prompt", "prompt_version", "provider", "model"].every(k => typeof v[k] === "string")
    && isRecord(v.parameters) && ["pending", "ready", "failed", "discarded"].includes(String(v.status))
    && (v.asset_id === null || uuid(v.asset_id)) && (v.error === null || typeof v.error === "string")
    && (v.duration_seconds === null || (typeof v.duration_seconds === "number" && Number.isFinite(v.duration_seconds) && v.duration_seconds >= 0));
}
function isPlanGeneration(value: unknown): value is PlanGeneration {
  return isRecord(value) && typeof value.id === "string" && typeof value.created_at === "string"
    && typeof value.source_revision === "number" && Number.isInteger(value.source_revision) && value.source_revision >= 0
    && typeof value.source_content === "string" && isAuthorContext(value.context) && isDraft(value.draft)
    && ["pending", "failed", "reviewed"].includes(String(value.critic_status))
    && (value.applied_revision === null || (typeof value.applied_revision === "number"
      && Number.isInteger(value.applied_revision) && value.applied_revision >= 0))
    && (value.feedback === null || isFeedback(value.feedback)) && isFeedbackSource(value.feedback_source);
}
function isClarificationVersion(value: unknown): value is ClarificationVersion & Record<string, unknown> {
  return isRecord(value) && typeof value.id === "string" && typeof value.created_at === "string"
    && typeof value.idea === "string" && strings(value.constraints) && strings(value.questions)
    && strings(value.answers);
}

function isScriptScene(v:unknown):v is ScriptScene {
  if(!isRecord(v)||!uuid(v.id)||!uuid(v.source_scene_id)||typeof v.heading!=="string"||Array.from(v.heading).length>500
    ||!Array.isArray(v.blocks)||v.blocks.length>200)return false;
  return v.blocks.every(b=>isRecord(b)&&uuid(b.id)&&['action','dialogue'].includes(String(b.kind))
    &&typeof b.text==='string'&&Array.from(b.text).length<=10000&&typeof b.speaker==='string'&&Array.from(b.speaker).length<=200)
    &&new Set([v.id,...v.blocks.map(b=>b.id)]).size===v.blocks.length+1
    &&Array.from(v.heading).length+v.blocks.reduce((n,b)=>n+Array.from(b.text).length+Array.from(b.speaker).length,0)<=200000;
}
function isScreenplay(v: unknown): v is Screenplay {
  if(!isRecord(v)||!isProvenanceMap(v.provenance)||!uuid(v.id)||!positive(v.version)||!Number.isInteger(v.source_revision)||Number(v.source_revision)<0
    ||!isSceneOutline(v.source_outline)||!Array.isArray(v.scenes)||!v.scenes.length||v.scenes.length>60||!v.scenes.every(isScriptScene))return false;
  const scenes=v.scenes,outline=v.source_outline;
  const ids=scenes.flatMap(s=>[s.id,...s.blocks.map(b=>b.id)]);
  return scenes.length===outline.scenes.length&&scenes.every((s,i)=>s.source_scene_id===outline.scenes[i].id)
    &&new Set(ids).size===ids.length&&scenes.reduce((n,s)=>n+s.blocks.length,0)<=1000
    &&scenes.reduce((n,s)=>n+Array.from(s.heading).length+s.blocks.reduce((n,b)=>n+Array.from(b.text).length+Array.from(b.speaker).length,0),0)<=200000;
}
function isScreenplayProposal(v:unknown):v is ScreenplayProposal {
  if(!isRecord(v)||!uuid(v.id)||typeof v.created_at!=='string'||!Number.isInteger(v.source_revision)||Number(v.source_revision)<0
    ||typeof v.source_content!=='string'||!isScreenplay(v.source_screenplay)||(v.source_outline!==null&&!isSceneOutline(v.source_outline))
    ||!uuid(v.target_scene_id)||typeof v.instructions!=='string'||!['pending','ready','failed','applied','discarded'].includes(String(v.status))
    ||typeof v.prompt_version!=='string'||!isRecord(v.parameters)||(v.provider!==null&&typeof v.provider!=='string')
    ||(v.model!==null&&typeof v.model!=='string')||(v.error!==null&&typeof v.error!=='string')
    ||(v.applied_revision!==null&&(!Number.isInteger(v.applied_revision)||Number(v.applied_revision)<0)))return false;
  const target=v.source_screenplay.scenes.find(s=>s.id===v.target_scene_id);
  return !!target&&[v.scene,v.preview_scene].every(s=>s===null||(isScriptScene(s)&&s.id===target.id&&s.source_scene_id===target.source_scene_id))
    &&(!['ready','applied'].includes(String(v.status))||v.scene!==null);
}

function isScreenplaySelection(v:unknown):v is ScreenplaySelection {
  return isRecord(v)&&uuid(v.id)&&typeof v.created_at==='string'&&Number.isInteger(v.source_revision)&&Number(v.source_revision)>=0
    &&(v.source_version_id==='current'||uuid(v.source_version_id))&&isScreenplay(v.screenplay)&&!unfinishedScriptScenes(v.screenplay).length;
}

function isScreenplayReview(v:unknown):v is ScreenplayReview {
  if(!isRecord(v)||!uuid(v.id)||typeof v.created_at!=='string'||!Number.isInteger(v.source_revision)||Number(v.source_revision)<0
    ||typeof v.source_content!=='string'||!isScreenplay(v.source_screenplay)||(v.source_outline!==null&&!isSceneOutline(v.source_outline))
    ||!uuid(v.target_scene_id)||!v.source_screenplay.scenes.some(s=>s.id===v.target_scene_id)||typeof v.instructions!=='string'
    ||!['pending','ready','failed','discarded'].includes(String(v.status))||typeof v.question!=='string'||typeof v.prompt_version!=='string'
    ||!isRecord(v.parameters)||(v.provider!==null&&typeof v.provider!=='string')||(v.model!==null&&typeof v.model!=='string')
    ||(v.error!==null&&typeof v.error!=='string')||!Array.isArray(v.sources)||v.sources.length>1500||!Array.isArray(v.notes)||v.notes.length>6)return false;
  const script=v.source_screenplay;
  const legacy = v.prompt_version !== 'screenplay-review-v5-provenance'
    && v.sources.every(s=>isRecord(s)&&s.provenance==null);
  if(!v.sources.every(s=>isRecord(s)&&typeof s.id==='string'&&typeof s.label==='string'&&typeof s.text==='string'
    &&['screenplay','author_choice','context'].includes(String(s.category))&&['text','speaker','heading','choice','context'].includes(String(s.field))
    &&(s.scene_id===null||uuid(s.scene_id))&&(s.block_id===null||uuid(s.block_id))&&reviewSourceMatches(script,s as ReviewSource,legacy))
    ||new Set(v.sources.map(s=>s.id)).size!==v.sources.length)return false;
  return v.notes.every(n=>isRecord(n)&&uuid(n.id)&&['intent_mismatch','craft','uncertain'].includes(String(n.kind))
    &&typeof n.observation==='string'&&!!n.observation.trim()&&Array.from(n.observation).length<=2000
    &&typeof n.impact==='string'&&!!n.impact.trim()&&Array.from(n.impact).length<=2000
    &&typeof n.suggestion==='string'&&Array.from(n.suggestion).length<=2000
    &&(n.assessment===null||['helpful','misleading','uncertain','dismissed'].includes(String(n.assessment)))
    &&Array.isArray(n.evidence)&&n.evidence.length>=1&&n.evidence.length<=4&&n.evidence.every(e=>isRecord(e)&&typeof e.source_id==='string'
      &&typeof e.quote==='string'&&!!e.quote.trim()&&Array.from(e.quote).length<=1000)
    &&reviewNoteSupported(v as ScreenplayReview,n as ReviewNote,legacy))&&new Set(v.notes.map(n=>n.id)).size===v.notes.length;
}

import type { AuthorContext, StoryDraft } from "./projectsApi";

export const stagingLabels = {
  blocking: "Vị trí & chuyển động", performance: "Cử chỉ & diễn xuất",
  setting: "Bối cảnh & đạo cụ", lighting: "Ánh sáng", color: "Màu sắc", costume: "Trang phục",
  moment: "Khoảnh khắc", shot: "Cỡ cảnh", angle: "Góc máy", composition: "Bố cục",
} as const;
export type StagingKey = keyof typeof stagingLabels;
export type Scene = {
  id: string; title: string; action: string; location: string; time: string;
  characters: string; goal: string; purpose: string; viewer_intent: string; keep_or_avoid: string;
  staging_choices: Partial<Record<StagingKey, string>>;
};
export type SceneOutline = {
  id: string; version: number; scenes: Scene[];
  source: { id: string; project_revision: number; version_id: string; draft: StoryDraft;
    context: AuthorContext; response_language: "auto" | "vi" | "en" };
};
export type SceneVersion = { id: string; created_at: string; outline: SceneOutline };
export type SceneHandoff = { outline_id: string; version: number; project_revision: number;
  source_id: string; scenes: Scene[] };
export function emptyScene(): Scene {
  return { id: crypto.randomUUID(), title: "Cảnh mới", action: "", location: "", time: "",
    characters: "", goal: "", purpose: "", viewer_intent: "", keep_or_avoid: "", staging_choices: {} };
}

export type SceneSuggestionInput = { request_id: string; mode: "list" | "append" | "develop" | "staging";
  target_scene_id: string | null; instructions: string };
export type SceneProposal = {
  id: string; created_at: string; source_revision: number; source_content: string; source_outline: SceneOutline;
  mode: SceneSuggestionInput["mode"]; target_scene_id: string | null; instructions: string;
  status: "pending" | "ready" | "failed" | "applied" | "discarded";
  staging_ideas?: StagingIdea[]; staging_sources?: { id: string; label: string; text: string }[]; staging_question?: string;
  scenes: Scene[]; preview_scenes?: Scene[] | null; transitions: Record<string, string>; provider: string | null; model: string | null;
  parameters: Record<string, unknown>; prompt_version: string; error: string | null; applied_revision: number | null;
};

export const stagingGroups: { title: string; keys: StagingKey[] }[] = [
  { title: "Hành động & diễn xuất", keys: ["blocking", "performance"] },
  { title: "Không gian & chi tiết", keys: ["setting", "lighting", "color", "costume"] },
  { title: "Cách nhìn qua máy quay", keys: ["composition", "shot", "angle", "moment"] },
];
export type StagingIdea = {
  id: string; field: StagingKey; evidence: { source_id: string; quote: string }[];
  reason: string; suggestion: string; purpose: string;
  status: "available" | "applied" | "discarded"; preview_text: string | null;
  applied_revision: number | null; applied_text: string | null;
};
export type StagingUse = { proposal_id: string; idea_id: string; value: string };

export type SceneSketch = {
  id: string; scene_id: string; created_at: string; source_revision: number; source_content: string;
  source_outline: SceneOutline; instructions: string; prompt: string; prompt_version: string;
  provider: string; model: string; parameters: Record<string, unknown>;
  status: "pending" | "ready" | "failed" | "discarded"; asset_id: string | null;
  error: string | null; duration_seconds: number | null;
};

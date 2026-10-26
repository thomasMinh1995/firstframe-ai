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

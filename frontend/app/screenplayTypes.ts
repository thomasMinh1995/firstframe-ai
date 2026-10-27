import type {SceneOutline} from "./sceneTypes";
export type ScriptBlock = {id: string; kind: "action" | "dialogue"; text: string; speaker: string};
export type ScriptScene = {id: string; source_scene_id: string; heading: string; blocks: ScriptBlock[]};
export type Screenplay = {id: string; version: number; scenes: ScriptScene[]; source_revision: number; source_outline: SceneOutline};
export type ScreenplayVersion = {id: string; created_at: string; screenplay: Screenplay};

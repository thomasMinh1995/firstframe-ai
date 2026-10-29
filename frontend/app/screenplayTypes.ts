import type {SceneOutline} from "./sceneTypes";
export type ScriptBlock = {id: string; kind: "action" | "dialogue"; text: string; speaker: string};
export type ScriptScene = {id: string; source_scene_id: string; heading: string; blocks: ScriptBlock[]};
export type Screenplay = {id: string; version: number; scenes: ScriptScene[]; source_revision: number; source_outline: SceneOutline; provenance?: Record<string, import('./provenance').TextProvenance>};
export type ScreenplayVersion = {id: string; created_at: string; screenplay: Screenplay};
export type ScreenplaySelection = {id:string;created_at:string;source_revision:number;source_version_id:string;screenplay:Screenplay};
export type ScreenplaySelectionInput = {request_id:string;source_version_id:string};
export function unfinishedScriptScenes(script:Screenplay):ScriptScene[] {
  return script.scenes.filter(s=>!s.heading.trim()||!s.blocks.length||s.blocks.some(b=>!b.text.trim()||(b.kind==='dialogue'&&!b.speaker.trim())));
}
export type SceneWritingInput = {request_id:string;target_scene_id:string;instructions:string};
export type ScreenplayProposal = {
  id:string;created_at:string;source_revision:number;source_content:string;source_screenplay:Screenplay;source_outline:SceneOutline|null;
  target_scene_id:string;instructions:string;status:'pending'|'ready'|'failed'|'applied'|'discarded';
  scene:ScriptScene|null;preview_scene:ScriptScene|null;provider:string|null;model:string|null;parameters:Record<string,unknown>;
  prompt_version:string;error:string|null;applied_revision:number|null;
};

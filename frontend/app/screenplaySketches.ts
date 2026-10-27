import type {Project} from "./projectsApi";
import type {SceneOutline, SceneSketch} from "./sceneTypes";

// Ignore the outline save counter only. Keep source IDs, intent and all scene content.
// Sorting object keys avoids treating staging field insertion order as a content change.
function sourceKey({version: _version, ...source}: SceneOutline): string {
  return JSON.stringify(source, (_key, value) => value && typeof value === "object" && !Array.isArray(value)
    ? Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b))) : value);
}
export function screenplaySketches(saved: Project, outline: SceneOutline): Record<string, {sketch: SceneSketch; matches: boolean}> {
  const result: Record<string, {sketch: SceneSketch; matches: boolean}> = {};
  const key = sourceKey(outline);
  for (const scene of outline.scenes) {
    const selected = saved.selected_scene_sketches?.[scene.id];
    const sketch = saved.scene_sketches?.find(s => s.id === selected && s.scene_id === scene.id);
    if (sketch?.status !== "ready" || !sketch.asset_id || !sketch.source_outline.scenes.some(s => s.id === scene.id)) continue;
    result[scene.id] = {sketch, matches: sourceKey(sketch.source_outline) === key};
  }
  return result;
}

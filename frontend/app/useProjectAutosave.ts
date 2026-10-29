"use client";
import {useEffect, useState, useSyncExternalStore} from "react";
import {ProjectAutosave} from "./projectAutosave";
import {projectRequest} from "./projectsApi";

export function useProjectAutosave(enabled: boolean) {
  const [autosave] = useState(() => new ProjectAutosave(
    (project, body) => projectRequest(`/${project.id}`, "PUT", body),
    id => projectRequest(`/${id}`)));
  const state = useSyncExternalStore(autosave.subscribe, autosave.getSnapshot, autosave.getSnapshot);
  useEffect(() => {autosave.setEnabled(enabled); return () => autosave.setEnabled(false);}, [enabled, autosave]);
  return {...state, autosave};
}

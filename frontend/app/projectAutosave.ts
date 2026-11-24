import {editableProject, sameEditableContent, type Project} from "./projectsApi";

type SaveBody = ReturnType<typeof editableProject> & {
  save_mode: "autosave" | "checkpoint"; edit_session_id: string; save_id: string;
};
type Snapshot = {project: Project | null; saved: Project | null; saving: boolean; error: string | null};
const content = (p: Project) => {
  const {revision: _, ...value} = editableProject(p);
  return JSON.stringify(value);
};
const equal = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);
const confirmedSave = (project: Project | null, id: string) => project?.last_save_id === id
  && project.revision === project.last_save_revision;

/** Acknowledgements update server metadata without replacing newer local input. */
export function acknowledgeSave(current: Project, sent: Project, next: Project): Project {
  const result = {...next};
  for (const key of ["title", "idea", "constraints", "answers", "draft", "response_language"] as const) {
    if (!equal(current[key], sent[key])) Object.assign(result, {[key]: current[key]});
  }
  for (const key of ["scene_outline", "screenplay"] as const) {
    if (!equal(current[key], sent[key]) && current[key] && next[key]?.id === current[key]?.id) {
      Object.assign(result, {[key]: {...next[key], scenes: current[key]!.scenes}});
    }
  }
  for (const key of ["pending_scene_proposal_id", "pending_scene_previews", "pending_staging_use",
    "pending_staging_edits", "pending_screenplay_proposal_id", "pending_screenplay_previews"] as const) {
    if (!equal(current[key], sent[key])) Object.assign(result, {[key]: current[key]});
  }
  if (current.pending_staging_use?.proposal_id === sent.pending_staging_use?.proposal_id
      && current.pending_staging_use?.idea_id === sent.pending_staging_use?.idea_id) delete result.pending_staging_use;
  for (const [idKey, previewsKey] of [
    ["pending_scene_proposal_id", "pending_scene_previews"],
    ["pending_screenplay_proposal_id", "pending_screenplay_previews"],
  ] as const) {
    if (sent[idKey] && current[idKey] === sent[idKey]) delete result[idKey];
    if (sent[idKey] && result[previewsKey]) {
      const previews = {...result[previewsKey]}; delete previews[sent[idKey]!];
      Object.assign(result, {[previewsKey]: Object.keys(previews).length ? previews : undefined});
    }
  }
  return result;
}

export class ProjectAutosave {
  private state: Snapshot = {project: null, saved: null, saving: false, error: null};
  private listeners = new Set<() => void>();
  private enabled = false;
  private composing = false;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private flight: Promise<Project | null> | null = null;
  private session = "";
  private uncertain: {sent: Project; body: SaveBody} | null = null;

  constructor(private write: (project: Project, body: SaveBody) => Promise<Project>,
    private read: (id: string) => Promise<Project>, private delay = 1000,
    private uuid = () => crypto.randomUUID()) {}

  getSnapshot = () => this.state;
  subscribe = (listener: () => void) => {this.listeners.add(listener); return () => {this.listeners.delete(listener);};};
  private update(patch: Partial<Snapshot>) {
    this.state = {...this.state, ...patch};
    this.listeners.forEach(listener => listener());
  }
  get dirty() {return !!this.state.project && !!this.state.saved && content(this.state.project) !== content(this.state.saved);}
  accept = (project: Project | null) => {
    this.cancelTimer();
    this.session = this.uuid();
    this.uncertain = null;
    this.update({project, saved: project, error: null});
  };
  setProject = (value: Project | null | ((current: Project | null) => Project | null)) => {
    this.update({project: typeof value === "function" ? value(this.state.project) : value});
    this.schedule();
  };
  setSaved = (saved: Project | null) => this.update({saved});
  setEnabled = (enabled: boolean) => {this.enabled = enabled; this.schedule();};
  setComposing = (composing: boolean) => {this.composing = composing; this.schedule();};
  private cancelTimer() {clearTimeout(this.timer); this.timer = undefined;}
  private schedule() {
    this.cancelTimer();
    if (this.enabled && !this.composing && !this.flight && !this.state.error && this.dirty) {
      if (this.state.project?.pending_scene_proposal_id || this.state.project?.pending_screenplay_proposal_id
          || this.state.project?.pending_staging_use) {
        void this.flush().catch(() => {});
        return;
      }
      this.timer = setTimeout(() => {void this.flush().catch(() => {});}, this.delay);
    }
  }
  idle = async () => {if (this.flight) await this.flight;};

  /** Inspect after queued saves settle, preserving edits against the latest baseline. */
  inspect = async (refreshSelections = false) => {
    await this.idle();
    const baseline = this.state.saved;
    if (!baseline) return null;
    const next = await this.read(baseline.id);
    const current = this.state.project;
    if (next.id !== baseline.id || current?.id !== baseline.id || this.state.saved !== baseline) {
      throw new Error("Bản đang xem đã đổi trong lúc kiểm tra. Hãy kiểm tra lại.");
    }
    const compared = refreshSelections ? {...baseline, screenplay_selections: next.screenplay_selections} : baseline;
    if (this.dirty && !sameEditableContent(compared, next)) {
      throw new Error("Nội dung đã đổi ở cửa sổ khác. Bản đang sửa vẫn giữ; hãy tải bản sao trước khi mở lại.");
    }
    this.update({project: acknowledgeSave(current, baseline, next), saved: next});
    return this.state.project;
  };

  private async send(sent: Project, body: SaveBody): Promise<Project> {
    let next: Project;
    try {next = await this.write(sent, body);}
    catch (error) {
      if (error instanceof Error && "status" in error && error.status === 422) {
        this.uncertain = null;
        throw error;
      }
      const remote = await this.read(sent.id).catch(() => null);
      if (!confirmedSave(remote, body.save_id)) throw error;
      next = remote!;
    }
    // An idempotent replay can return a newer project; it is not our acknowledgement.
    if (!confirmedSave(next, body.save_id)) {
      throw new Error("Bản lưu đã thay đổi sau lần gửi. Bản đang sửa vẫn được giữ; hãy tải bản sao trước khi mở lại.");
    }
    return next;
  }

  private acknowledge(sent: Project, next: Project) {
    if (this.state.project?.id !== sent.id || next.id !== sent.id) throw new Error("Dự án trả về không khớp lần lưu.");
    this.uncertain = null;
    this.update({project: acknowledgeSave(this.state.project, sent, next), saved: next, error: null});
  }

  /** Retry is explicit. A read can confirm a lost acknowledgement without writing. */
  flush = async (mode: "autosave" | "checkpoint" = "autosave", retry = false): Promise<Project | null> => {
    this.cancelTimer();
    if (this.flight) {
      await this.flight;
      return this.flush(mode, retry);
    }
    if (this.composing) throw new Error("Hãy hoàn tất ký tự đang nhập trước khi tiếp tục.");
    if (this.state.error && !retry) throw new Error(this.state.error);
    const work = async () => {
      if (retry && this.uncertain) {
        const {sent, body} = this.uncertain;
        const remote = await this.read(sent.id);
        if (confirmedSave(remote, body.save_id)) this.acknowledge(sent, remote);
        else if (remote.revision !== sent.revision) throw new Error("Bản lưu đã đổi ở cửa sổ khác. Hãy tải bản sao trước khi mở lại.");
        else {
          try {this.acknowledge(sent, await this.send(sent, body));}
          catch (error) {
            if (!(error instanceof Error && "status" in error && error.status === 422
                && this.state.project && content(this.state.project) !== content(sent))) throw error;
            // The old write was rejected. This explicit retry may now save the corrected input.
          }
        }
      }
      this.update({error: null});
      while (this.dirty && !this.composing) {
        const sent = this.state.project!;
        const body: SaveBody = {...editableProject(sent), save_mode: mode,
          edit_session_id: this.session, save_id: this.uuid()};
        this.uncertain = {sent, body};
        this.acknowledge(sent, await this.send(sent, body));
      }
      return this.state.project;
    };
    this.update({saving: true});
    this.flight = work();
    try {return await this.flight;}
    catch (error) {
      const detail = error instanceof Error ? error.message : "Chưa xác nhận được kết quả lưu.";
      this.update({error: detail});
      throw error;
    } finally {
      this.flight = null;
      this.update({saving: false});
      this.schedule();
    }
  };
}

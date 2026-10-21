export type Review = {
  revision: number; status: "unreviewed" | "approved" | "needs_revision";
  feedback: string; use_for_demo: boolean; use_for_training: boolean; updated_at: string | null;
};
export type Sample = {
  run_id: string; project_id: string | null; fingerprint: string; operation: string; status: string; title: string;
  idea: string; started_at: string; models_used: {provider: string; model: string}[];
  eligible: boolean; has_corrections: boolean; review: Review;
};
export type SampleDetail = Sample & {corrected_outputs: Record<string, Record<string, unknown>>; recording: {
  input: Record<string, unknown>; output: Record<string, unknown> | null;
  steps: {stage: string; provider: string; model: string | null; status: string;
    output: unknown; request?: unknown; error_type?: string}[];
}};
export const datasetBase = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/datasets`;
async function request(path: string, init?: RequestInit) {
  const response = await fetch(datasetBase + path, {cache: "no-store", ...init}).catch(() => {
    throw new Error("Không kết nối được backend local.");
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Dữ liệu đánh giá không hợp lệ.");
  return data;
}
export async function listSamples(): Promise<Sample[]> { return request("/samples"); }
export async function getSample(id: string): Promise<SampleDetail> { return request(`/samples/${encodeURIComponent(id)}`); }
export async function saveReview(sample: Sample, review: Review): Promise<Review> {
  return request(`/samples/${encodeURIComponent(sample.run_id)}/review`, {
    method: "PUT", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({...review, fingerprint: sample.fingerprint}),
  });
}

export async function saveOutputs(sample: SampleDetail, corrected_outputs: Record<string, Record<string, unknown>>): Promise<SampleDetail> {
  return request(`/samples/${encodeURIComponent(sample.run_id)}/output`, {
    method: "PUT", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({revision: sample.review.revision, fingerprint: sample.fingerprint, corrected_outputs}),
  });
}

export type OutputVersion = {
  version: number; created_at: string | null;
  action: "original" | "edit" | "restore" | "imported"; restored_from: number | null;
};
export type OutputHistory = {fingerprint: string; current_version: number; versions: OutputVersion[]};
export type OutputDiff = {fingerprint: string; from_version: number; to_version: number; changes: {
  path: string; before_exists: boolean; after_exists: boolean; before: unknown; after: unknown;
}[]};
export async function getOutputHistory(id: string): Promise<OutputHistory> {
  return request(`/samples/${encodeURIComponent(id)}/history`);
}
export async function diffOutputs(id: string, from: number, to: number): Promise<OutputDiff> {
  return request(`/samples/${encodeURIComponent(id)}/diff?from_version=${from}&to_version=${to}`);
}
export async function restoreOutputs(sample: SampleDetail, version: number): Promise<SampleDetail> {
  return request(`/samples/${encodeURIComponent(sample.run_id)}/restore`, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({revision: sample.review.revision, fingerprint: sample.fingerprint, version}),
  });
}

export type BundleReport = {
  sha256: string; sample_count: number; new_count: number; unchanged_count: number;
  correction_count: number; history_count: number; demo_count: number;
  branch_add_count: number; kept_local_count?: number; used_incoming_count?: number;
  conflicts: {run_id: string; reason: string; local_token: string; originals_differ: boolean; incoming_allowed: boolean}[];
};
export async function previewBundle(content: string): Promise<BundleReport> {
  return request("/bundle/preview", {method: "POST", headers: {"Content-Type": "application/json"}, body: content});
}
export type ConflictChoices = Record<string, {choice: "local" | "incoming"; local_token: string}>;
export type JsonChange = OutputDiff["changes"][number];
export type StateComparison = {local_token: string; changes: JsonChange[]};
export async function compareBundle(content: string, id: string): Promise<StateComparison> {
  return request(`/bundle/compare?run_id=${encodeURIComponent(id)}`, {method: "POST", headers: {"Content-Type": "application/json"}, body: content});
}
export async function importBundle(content: string, resolutions: ConflictChoices = {}): Promise<BundleReport> {
  // Keep original JSON number tokens intact when wrapping the package.
  const body = '{"bundle":' + content + ',"resolutions":' + JSON.stringify(resolutions) + '}';
  return request("/bundle/import", {method: "POST", headers: {"Content-Type": "application/json"}, body});
}
export async function downloadBundle(): Promise<void> {
  const response = await fetch(`${datasetBase}/bundle`, {cache: "no-store"}).catch(() => {
    throw new Error("Không kết nối được backend local.");
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(typeof data?.detail === "string" ? data.detail : "Không xuất được gói dataset.");
  }
  // Preserve source JSON bytes; parsing/stringifying can alter numeric fingerprints.
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url; link.download = "firstframe-reviewed-dataset.json";
  link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export type SavedBranches = {local_token: string; branches: {
  branch_id: string; source: "local" | "incoming" | "restore"; created_at: string;
  fingerprint: string; history_count: number; status: string; feedback: string; is_current: boolean;
}[]};
export async function listBranches(id: string): Promise<SavedBranches> {
  return request(`/samples/${encodeURIComponent(id)}/branches`);
}
export async function compareBranch(id: string, branch: string): Promise<StateComparison> {
  return request(`/samples/${encodeURIComponent(id)}/branches/${encodeURIComponent(branch)}`);
}
export async function restoreSavedBranch(id: string, branch: string, token: string): Promise<SampleDetail> {
  return request(`/samples/${encodeURIComponent(id)}/branches/${encodeURIComponent(branch)}/restore`, {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({local_token: token}),
  });
}

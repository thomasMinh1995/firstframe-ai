export const tourSteps = ["new-project", "idea", "language", "choices", "draft", "save"] as const;
export type TourStep = typeof tourSteps[number];
export type TourStatus = "active" | "waiting" | "paused" | "dismissed" | "completed";
export type TourRecord = { version: 1; status: TourStatus; stepId: TourStep; projectId: string | null };
export type TourContext = { projectId: string | null; hasAnalysis: boolean; hasDraft: boolean; briefChanged: boolean };
export type TourOperation = "create" | "analyze" | "plan";
export type TourRequest = { session: number; serial: number; kind: TourOperation; projectId: string | null };
export type TourState = {
  initialized: boolean; offerAllowed: boolean; record: TourRecord | null;
  session: number; serial: number; request: TourRequest | null; waitingReady: boolean; hint: string | null;
};
export const tourStorageKey = "firstframe:onboarding";
export const initialTour: TourState = {
  initialized: false, offerAllowed: false, record: null, session: 0, serial: 0,
  request: null, waitingReady: false, hint: null,
};

export function parseTour(raw: string | null | undefined): TourRecord | null {
  try {
    const value: unknown = raw ? JSON.parse(raw) : null;
    if (!value || typeof value !== "object") return null;
    const r = value as Record<string, unknown>;
    if (r.version !== 1 || typeof r.status !== "string" || !["active", "waiting", "paused", "dismissed", "completed"].includes(r.status)
      || !tourSteps.includes(r.stepId as TourStep)
      || !(r.projectId === null || (typeof r.projectId === "string" && r.projectId.length > 0))) return null;
    return { version: 1, status: r.status as TourStatus, stepId: r.stepId as TourStep, projectId: r.projectId as string | null };
  } catch { return null; }
}

export function validAnalysis(c: TourContext) { return c.hasAnalysis && !c.briefChanged; }
export function entryStep(c: TourContext): TourStep {
  return !c.projectId ? "new-project" : !validAnalysis(c) ? "idea" : !c.hasDraft ? "choices" : "draft";
}
export function available(step: TourStep, c: TourContext): boolean {
  if (step === "new-project") return true;
  if (!c.projectId) return false;
  if (step === "choices") return validAnalysis(c);
  return step === "draft" || step === "save" ? c.hasDraft : true;
}
function safeStep(step: TourStep, c: TourContext): TourStep {
  if (tourSteps.indexOf(step) >= 3 && !validAnalysis(c)) return entryStep(c);
  return available(step, c) ? step : entryStep(c);
}
export function nextStep(step: TourStep, c: TourContext): TourStep | null {
  if (tourSteps.indexOf(step) >= 3 && !validAnalysis(c)) return entryStep(c);
  const next = tourSteps[tourSteps.indexOf(step) + 1];
  return next && available(next, c) ? next : null;
}
export function previousStep(step: TourStep, c: TourContext): TourStep | null {
  return [...tourSteps.slice(0, tourSteps.indexOf(step))].reverse().find(s => available(s, c)) ?? null;
}
export function continuation(s: TourState, c: TourContext): TourStep | null {
  const r = s.record;
  if (!r || r.projectId !== c.projectId) return entryStep(c);
  if (tourSteps.indexOf(r.stepId) >= 3 && !validAnalysis(c)) return entryStep(c);
  if (r.status === "waiting") return s.waitingReady ? nextStep(r.stepId, c) : null;
  return safeStep(r.stepId, c);
}

type Action =
  | { type: "load" | "external"; raw: string | null | undefined }
  | { type: "open"; resume: boolean; context: TourContext }
  | { type: "navigate"; step: TourStep; context: TourContext }
  | { type: "practice" | "dismiss" | "complete"; context: TourContext }
  | { type: "pause"; hint?: string }
  | { type: "begin"; kind: TourOperation; context: TourContext }
  | { type: "success"; ticket: TourRequest | null; resultId: string }
  | { type: "failed"; ticket: TourRequest | null };

function paused(s: TourState, hint: string | null = null): TourState {
  if (!s.record || ["dismissed", "completed"].includes(s.record.status)) return s;
  return { ...s, session: s.session + 1, request: null, waitingReady: false, hint,
    record: { ...s.record, status: "paused" } };
}
function matches(s: TourState, ticket: TourRequest | null) {
  return !!ticket && !!s.request && ticket.session === s.session
    && ticket.serial === s.request.serial && ticket.kind === s.request.kind
    && ticket.projectId === s.request.projectId && s.record?.status === "waiting";
}

export function reduceTour(s: TourState, a: Action): TourState {
  switch (a.type) {
    case "load": {
      if (s.initialized) return s;
      const r = parseTour(a.raw);
      return { ...s, initialized: true, offerAllowed: a.raw === null,
        record: r && ["active", "waiting"].includes(r.status) ? { ...r, status: "paused" } : r };
    }
    case "external": {
      const r = parseTour(a.raw);
      if (r && ["dismissed", "completed"].includes(r.status)) {
        return { ...s, offerAllowed: false, record: r, session: s.session + 1,
          request: null, waitingReady: false, hint: null };
      }
      return r ? s : { ...paused(s), offerAllowed: false };
    }
    case "open": {
      const step = a.resume ? continuation(s, a.context) : entryStep(a.context);
      if (!step) return s;
      return { ...s, offerAllowed: false, session: s.session + 1, request: null, waitingReady: false, hint: null,
        record: { version: 1, status: "active", stepId: step, projectId: a.context.projectId } };
    }
    case "navigate":
      if (s.record?.status !== "active") return s;
      return { ...s, hint: null, record: { ...s.record, stepId: safeStep(a.step, a.context) } };
    case "practice":
      if (s.record?.status !== "active" || s.record.stepId === "save") return s;
      return { ...s, request: null, waitingReady: nextStep(s.record.stepId, a.context) !== null,
        record: { ...s.record, status: "waiting" } };
    case "pause": return paused(s, a.hint ?? null);
    case "dismiss":
      return { ...s, offerAllowed: false, session: s.session + 1, request: null, waitingReady: false, hint: null,
        record: { version: 1, status: "dismissed", stepId: s.record?.stepId ?? "new-project", projectId: a.context.projectId } };
    case "complete":
      if (s.record?.status !== "active" || s.record.stepId !== "save") return s;
      if (!validAnalysis(a.context) || !a.context.hasDraft) return reduceTour(s, { type: "navigate", step: "save", context: a.context });
      return { ...s, session: s.session + 1, request: null, waitingReady: false,
        record: { ...s.record, status: "completed" } };
    case "begin": {
      const step = { create: "new-project", analyze: "language", plan: "choices" }[a.kind];
      if (s.record?.status !== "waiting" || s.record.stepId !== step || s.record.projectId !== a.context.projectId) {
        return a.kind === "create" ? paused(s) : s;
      }
      const serial = s.serial + 1;
      return { ...s, serial, waitingReady: false,
        request: { serial, session: s.session, kind: a.kind, projectId: a.context.projectId } };
    }
    case "success":
      if (!matches(s, a.ticket) || !a.resultId || (a.ticket!.kind !== "create" && a.resultId !== a.ticket!.projectId)) return s;
      return { ...s, request: null, waitingReady: true, record: { ...s.record!, projectId: a.resultId } };
    case "failed": return matches(s, a.ticket) ? paused(s) : s;
  }
}

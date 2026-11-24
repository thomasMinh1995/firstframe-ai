export type TextProvenance = {origin: "author_input" | "ai_proposal" | "legacy_unknown"; author_confirmed: boolean};
export const unknownProvenance: TextProvenance = {origin:"legacy_unknown",author_confirmed:false};
export function isTextProvenance(value: unknown): value is TextProvenance {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
  const source = value as Record<string, unknown>;
  return typeof source.origin === 'string' && ['author_input','ai_proposal','legacy_unknown'].includes(source.origin)
    && typeof source.author_confirmed === 'boolean';
}
export function isProvenanceMap(value: unknown): boolean {
  return value === undefined || (typeof value === 'object' && value !== null && !Array.isArray(value)
    && Object.values(value).every(isTextProvenance));
}
export const provenanceLabel = (source?: TextProvenance | null) => source?.author_confirmed
  ? "Lựa chọn bạn đã xác nhận" : source?.origin === "author_input" ? "Bạn nhập hoặc tự chỉnh"
    : source?.origin === "ai_proposal" ? "AI đề xuất" : "Nguồn cũ chưa xác định";

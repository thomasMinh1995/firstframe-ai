import { sectionLabels } from "./storyLabels";
import type { UiLanguage } from "./language";

export type FidelityAssessment = {
  relation: "contradictory" | "compatible" | "uncertain";
  relation_reason: string;
  concern: "supported" | "unsupported" | "uncertain";
  concern_reason: string;
  revision: "aligned" | "violates" | "uncertain";
  revision_reason: string;
};

export type FidelityReport = {
  status: "clear" | "issues" | "unverified";
  withheld_count: number;
  checks: Array<{
    kind: "fidelity" | "craft";
    section_index: number;
    section_title: string;
    section_text: string;
    draft_quote: string;
    author_quote: string;
    explanation: string;
    suggestion: string | null;
    verification_note?: string | null;
    assessment?: FidelityAssessment | null;
    suggestion_status: "supported" | "unverified";
  }>;
};

export function HighlightedQuote({ text, quote }: { text: string; quote: string }) {
  const start = text.indexOf(quote);
  if (!quote.trim() || start < 0 || text.indexOf(quote, start + 1) >= 0) return <>{text}</>;
  return <>{text.slice(0, start)}<mark>{quote}</mark>{text.slice(start + quote.length)}</>;
}

export function FidelityPanel({ report, uiLanguage }: {
  report?: FidelityReport | null; uiLanguage: UiLanguage;
}) {
  if (!report) return null;
  const vi = uiLanguage === "vi";
  return <section className="fidelity-panel" aria-label={vi ? "Đối chiếu ý đồ tác giả" : "Author intent check"}>
    <h3>{vi ? "Đối chiếu ý đồ tác giả" : "Author intent check"}</h3>
    <p role="status">{report.status === "unverified"
      ? (vi ? "Chưa xác minh đầy đủ. Gợi ý chưa được xác minh đã được giữ lại, không hiển thị như hướng sửa." : "Verification incomplete. Unverified revision suggestions have been withheld.")
      : report.status === "issues"
        ? (vi ? "AI phát hiện điểm có thể trái ý đồ. Hãy đối chiếu các trích dẫn bên dưới." : "AI found possible conflicts with your intent. Compare the quotations below.")
        : (vi ? "AI chưa tìm thấy mâu thuẫn với ý đồ. Đây không phải bảo đảm rằng bản thảo không có lỗi." : "AI found no conflict with your intent. This does not guarantee an error-free draft.")}</p>
    <p>{vi ? "Trích dẫn thuộc bản chụp tại lần kiểm tra; không tự cập nhật theo nội dung bạn đang sửa. Bạn quyết định có áp dụng gợi ý hay không." : "Quotations belong to the reviewed snapshot, not your unsaved edits. You decide whether to apply a suggestion."}</p>
    {report.checks.map((check, index) => <article className="fidelity-check" key={index}>
      <h4>{vi ? (sectionLabels[check.section_title] ?? ({Title: "Tên phim", Logline: "Tóm tắt"} as Record<string, string>)[check.section_title] ?? check.section_title) : check.section_title} · {check.kind === "craft"
        ? (vi ? "Góp ý phát triển" : "Development feedback")
        : (vi ? "Đối chiếu tính trung thành" : "Fidelity check")}</h4>
      <p><strong>{vi ? "Điều tác giả đã nói" : "Author's words"}</strong></p>
      <blockquote><mark>{check.author_quote}</mark></blockquote>
      <p><strong>{vi ? "Đoạn trong bản đã kiểm tra" : "Passage in the reviewed draft"}</strong></p>
      <details open>
        <summary>{vi ? "Xem đoạn được tô sáng trong ngữ cảnh" : "Highlighted passage in context"}</summary>
        <blockquote><HighlightedQuote text={check.section_text} quote={check.draft_quote} /></blockquote>
      </details>
      <p><strong>{vi ? (check.suggestion_status === "supported" ? "Điểm cần đối chiếu: " : "Nhận xét chưa xác minh: ") : (check.suggestion_status === "supported" ? "Compare: " : "Unverified observation: ")}</strong>{check.explanation}</p>
      {check.assessment && <dl>
        <dt>{vi ? "Hai trích dẫn có mâu thuẫn?" : "Do the quotations conflict?"}</dt>
        <dd>{({contradictory: vi ? "Có mâu thuẫn" : "Contradictory", compatible: vi ? "Tương thích" : "Compatible", uncertain: vi ? "Chưa đủ căn cứ" : "Uncertain"})[check.assessment.relation]} — {check.assessment.relation_reason}</dd>
        <dt>{vi ? "Nhận xét có căn cứ?" : "Is the concern supported?"}</dt>
        <dd>{({supported: vi ? "Có căn cứ" : "Supported", unsupported: vi ? "Không có căn cứ" : "Unsupported", uncertain: vi ? "Chưa đủ căn cứ" : "Uncertain"})[check.assessment.concern]} — {check.assessment.concern_reason}</dd>
        <dt>{vi ? "Gợi ý có giữ ý đồ?" : "Does the revision preserve intent?"}</dt>
        <dd>{({aligned: vi ? "Giữ ý đồ" : "Aligned", violates: vi ? "Trái ý đồ" : "Violates intent", uncertain: vi ? "Chưa đủ căn cứ" : "Uncertain"})[check.assessment.revision]} — {check.assessment.revision_reason}</dd>
      </dl>}
      {check.suggestion_status === "supported" && check.suggestion
        ? <><p><strong>{vi ? "AI đánh giá gợi ý phù hợp — cần tác giả đối chiếu" : "AI considers this suggestion aligned — author review needed"}</strong></p><p>{check.suggestion}</p><p>{check.verification_note}</p></>
        : <><p>{vi ? "Chưa có gợi ý sửa được xác minh cho đoạn này." : "No verified revision suggestion for this passage."}</p>{check.verification_note && <p>{check.verification_note}</p>}</>}
    </article>)}
  </section>;
}

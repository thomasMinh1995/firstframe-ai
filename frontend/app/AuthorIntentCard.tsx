import { revealWorkspaceTarget } from "./WorkspaceStage";
import type { AuthorContext, FeedbackSource } from "./projectsApi";

function focusInput(id: string) {
  const input = document.getElementById(id);
  revealWorkspaceTarget(input ?? document.querySelector(`[data-answer-open="${id}"]`));
  if (!input && id.startsWith("answer-")) {
    document.querySelector<HTMLButtonElement>(`[data-answer-open="${id}"]`)?.click();
    return;
  }
  if (input?.matches(":disabled")) return;
  input?.scrollIntoView({ block: "center" });
  input?.focus({ preventScroll: true });
}

export function IntentDetails({ context, editAnswers = false }: { context: AuthorContext; editAnswers?: boolean }) {
  return <dl className="intent-details">
    <div><dt>Khoảnh khắc của bạn</dt><dd className="preserve-lines">{context.idea || "Chưa ghi lại khoảnh khắc."}</dd></div>
    <div><dt>Điều muốn giữ / giới hạn</dt><dd>{context.constraints.length
      ? <ul>{context.constraints.map((value, i) => <li className="preserve-lines" key={i}>{value}</li>)}</ul>
      : "Chưa nêu giới hạn."}</dd></div>
    <div><dt>Những lựa chọn đã trả lời hoặc để mở</dt><dd>
      {!context.clarifications.length && <p>Chưa có câu trả lời được lưu.</p>}
      {context.clarifications.map((item, i) => <div className="intent-answer" key={i}>
        <p className="preserve-lines"><strong>{item.question}</strong></p>
        <p className="preserve-lines">{item.answer}</p>
        {item.input_index === null && <p className="storage-note">Giữ từ lượt làm rõ trước của cùng khoảnh khắc · chỉ đọc ở đây.</p>}
        {editAnswers && item.input_index !== null && <button type="button" className="secondary"
          onClick={() => focusInput(`answer-${item.input_index}`)}>Chỉnh câu trả lời {i + 1}</button>}
      </div>)}
    </dd></div>
    {!!context.pending_questions.length && <div><dt>Câu hỏi chưa trả lời</dt><dd>
      <p className="storage-note">Đây là câu hỏi đang chờ, chưa phải lựa chọn gửi cho AI.</p>
      {context.pending_questions.map(item => <div className="intent-answer" key={item.input_index}>
        <p className="preserve-lines">{item.question}</p>
        {editAnswers && <button type="button" className="secondary"
          onClick={() => focusInput(`answer-${item.input_index}`)}>Trả lời câu hỏi {item.input_index + 1}</button>}
      </div>)}
    </dd></div>}
  </dl>;
}

export function AuthorIntentCard({ context, revision, dirty, canEditAnswers }: {
  context: AuthorContext | undefined; revision: number; dirty: boolean; canEditAnswers: boolean;
}) {
  return <section className="panel form-stack author-intent" aria-labelledby="author-intent-title">
    <h2 id="author-intent-title">Ý đồ đã lưu hiện tại</h2>
    <p className="storage-note">Bản đã xác nhận lưu · revision {revision}. Thẻ cập nhật sau khi lưu thành công.</p>
    {dirty && <p className="form-message" role="status">Có thay đổi chưa lưu; thẻ này chưa bao gồm các sửa đó.
      Nếu chưa xác nhận được kết quả lưu, đây vẫn là bản cuối đã xác nhận, có thể khác bản trên server.</p>}
    {context ? <>
      <IntentDetails context={context} editAnswers={canEditAnswers} />
      <div className="intent-actions">
        <button type="button" className="secondary" onClick={() => focusInput("idea")}>Chỉnh khoảnh khắc</button>
        <button type="button" className="secondary" onClick={() => focusInput("constraints")}>Chỉnh điều muốn giữ</button>
      </div>
      <p className="storage-note">Đổi khoảnh khắc hoặc giới hạn rồi lưu sẽ yêu cầu làm rõ lại;
        các lựa chọn trước đó được giữ trong lịch sử. Lựa chọn giữ từ lượt cũ chưa có ô sửa riêng.</p>
    </> : <p>Chưa có đủ thông tin nguồn từ backend. Không suy ý đồ từ bản tóm tắt của AI.</p>}
  </section>;
}

export function FeedbackIntent({ source, projectId, artifactId }: {
  source: FeedbackSource | null | undefined; projectId: string; artifactId: string | undefined;
}) {
  const checked = source?.project_id === projectId && source.artifact_id === artifactId ? source : null;
  return <details className="feedback-context">
    <summary>Ý đồ đã dùng cho góp ý này</summary>
    {checked ? <>
      <p className="storage-note preserve-lines">Góp ý {checked.artifact_id} · đọc từ revision {checked.revision}.
        Nguồn được lưu cùng góp ý; có thể khác ý đồ hiện tại.</p>
      <IntentDetails context={checked.context} />
    </> : <p>Chưa có đủ thông tin nguồn đã kiểm tra cho góp ý này.
      Không dùng ý đồ hiện tại để điền thay.</p>}
  </details>;
}

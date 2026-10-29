"use client";

export function ClarificationConversation({ summary, questions, answers, onChange, onAskMore, onConfirm, onEditBrief, idea, constraints = [], retained = [], aiSuggestions = [], hasDraft = false, thinking = false, creatingScreenplay = false, idPrefix = "" }: {
  idPrefix?:string;creatingScreenplay?: boolean; thinking?: boolean; summary: string; questions: string[]; answers: string[]; onChange: (index: number, value: string) => void;
  onAskMore?: () => void; onConfirm?: () => void; onEditBrief?: () => void; confirmationKey?: string;
  idea?: string; constraints?: string[]; retained?: { question: string; answer: string }[]; aiSuggestions?: string[]; hasDraft?: boolean;
}) {
  const pending = questions.filter((_, i) => !answers[i]?.trim()).length;
  return <div className="clarification-conversation" aria-busy={thinking}>
    <fieldset className="conversation-content" disabled={thinking}>
      <section className="clarification-summary" aria-labelledby={`${idPrefix}understanding-title`}>
        <h3 id={`${idPrefix}understanding-title`}>Điều FirstFrame đã hiểu</h3>
        <p className="preserve-lines">{summary}</p>
        <p className="storage-note">Đây là cách AI hiểu ý tưởng, bạn có thể sửa nguồn bên dưới nếu chưa đúng.</p>
        {onEditBrief && <button type="button" className="secondary" onClick={onEditBrief}>Chỉnh ý tưởng và điều muốn giữ</button>}
      </section>
      <details><summary>Thông tin bạn đã nêu</summary>
        <p className="preserve-lines">{idea}</p>
        {!!constraints.filter(Boolean).length && <ul>{constraints.filter(Boolean).map((c,i)=><li key={i}>{c}</li>)}</ul>}
        {retained.map((c,i)=><p key={i}><strong>{c.question}</strong><br />{c.answer}</p>)}
      </details>
      {!!aiSuggestions.length && <aside className="revision-note" aria-label="Gợi ý AI chưa xác nhận">
        <h3>AI có thể đề xuất</h3>
        <ul>{aiSuggestions.map((s,i)=><li key={i}>{s}</li>)}</ul>
        <p>Đây chưa phải lựa chọn của bạn. Chỉ nhập vào câu trả lời nếu bạn muốn chọn hướng đó.</p>
      </aside>}
      {!questions.length ? <p role="status">Đã đủ thông tin để tạo story plan. Bạn không cần trả lời thêm.</p> : <>
        <h3>Phần còn để mở</h3>
        <p>Trả lời phần bạn muốn quyết định. Bỏ trống để AI đưa phương án cho bạn review.</p>
        <ol className="clarification-thread" aria-label="Các câu hỏi làm rõ">
          {questions.map((question,i)=><li key={i} className="clarification-current">
            <label htmlFor={`${idPrefix}answer-${i}`}>{question}</label>
            <textarea className="short-textarea" id={`${idPrefix}answer-${i}`} rows={3} maxLength={2000} value={answers[i] ?? ""}
              onChange={e=>onChange(i,e.target.value)} placeholder="Có thể để mở…" />
          </li>)}
        </ol>
      </>}
      {thinking && <p role="status">FirstFrame đang đọc ý tưởng…</p>}
      <div id={`${idPrefix}clarification-complete`} tabIndex={-1} className="clarification-complete">
        <p>{creatingScreenplay ? "Tiếp tục tạo dàn cảnh và nội dung kịch bản. Các phần chưa quyết định vẫn là phương án AI để bạn review." : hasDraft ? "Bản đề xuất mới được giữ riêng để bạn đọc và chọn nhận." : "Bước này tạo story plan để bạn đọc và sửa."}</p>
        <div className="clarification-actions">
          {onConfirm && <button type="button" data-tour-action="plan" onClick={onConfirm}>
            {creatingScreenplay ? "Tiếp tục tạo bản nháp" : pending ? "Tạo story plan với phần còn để mở" : hasDraft ? "Tạo đề xuất story plan mới" : "Tạo story plan"}
          </button>}
          {onAskMore && questions.length < 20 && <button type="button" className="secondary" onClick={onAskMore}>Làm rõ thêm nếu cần</button>}
        </div>
      </div>
    </fieldset>
  </div>;
}

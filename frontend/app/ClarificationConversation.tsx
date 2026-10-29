"use client";

import { useEffect, useRef, useState } from "react";

export function ClarificationConversation({ summary, questions, answers, onChange, onAskMore, onConfirm, confirmationKey, idea, constraints = [], retained = [], hasDraft = false, thinking = false }: {
  thinking?: boolean; summary: string; questions: string[]; answers: string[]; onChange: (index: number, value: string) => void;
  onAskMore?: () => void; onConfirm?: () => void; confirmationKey?: string;
  idea?: string; constraints?: string[]; retained?: { question: string; answer: string }[]; hasDraft?: boolean;
}) {
  const [advancing, setAdvancing] = useState(false);
  const nextTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (nextTimer.current) clearTimeout(nextTimer.current); }, []);
  const thinkingBubble = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (thinking || advancing) thinkingBubble.current?.scrollIntoView({block: "nearest"});
  }, [thinking, advancing]);
  const firstEmpty = questions.findIndex((_, i) => !answers[i]?.trim());
  const [active, setActive] = useState(firstEmpty < 0 ? questions.length : firstEmpty);
  const answered = questions.filter((_, i) => answers[i]?.trim()).length;
  const [reviewedKey, setReviewedKey] = useState<string | null>(null);
  const beforeEdit = useRef("");
  function choose(index: number) {
    setReviewedKey(null);
    beforeEdit.current = answers[index] ?? "";
    setActive(index);
    requestAnimationFrame(() => document.getElementById(index < questions.length ? `answer-${index}` : "clarification-complete")?.focus());
  }
  function next() {
    const following = questions.findIndex((_, i) => i > active && !answers[i]?.trim());
    const missing = questions.findIndex((_, i) => i !== active && !answers[i]?.trim());
    setAdvancing(true);
    nextTimer.current = setTimeout(() => {
      choose(following >= 0 ? following : missing >= 0 ? missing : questions.length);
      setAdvancing(false);
    }, 450);
  }
  return <div className="clarification-conversation" aria-busy={thinking || advancing}>
    <fieldset className="conversation-content" disabled={thinking || advancing}>
    <details className="clarification-summary"><summary>Điều FirstFrame đã hiểu</summary>
      <p className="preserve-lines">{summary}</p>
    </details>
    {!questions.length ? <p>Bạn có thể làm rõ thêm, hoặc xem lại các lựa chọn trước khi đồng ý tạo bản phát triển.</p> : <>
      <div className="clarification-progress">
        <p role="status">Đã trả lời {answered}/{questions.length}</p>
        <nav aria-label="Các câu hỏi làm rõ">{questions.map((_, i) =>
          <button key={i} type="button" data-answer-open={`answer-${i}`} aria-current={i === active ? "step" : undefined}
            aria-label={`Câu hỏi ${i + 1}${answers[i]?.trim() ? " · Đã trả lời" : ""}`} onClick={() => choose(i)}>
            {i + 1}<span aria-hidden="true">{answers[i]?.trim() ? " ✓" : ""}</span>
          </button>)}</nav>
      </div>
      <ol className="clarification-thread" aria-label="Cuộc trò chuyện làm rõ">
        {questions.map((question, i) => i === active ? <li key={i} className="clarification-current">
          <div className="clarification-question"><span>FirstFrame · Câu {active + 1}/{questions.length}</span>
            <label htmlFor={`answer-${active}`}>{questions[active]}</label></div>
          <div className="clarification-composer">
            <label className="clarification-you" htmlFor={`answer-${active}`}>Câu trả lời của bạn</label>
            <textarea key={active} id={`answer-${active}`} rows={3} maxLength={2000} value={answers[active] ?? ""}
              onChange={event => onChange(active, event.target.value)} placeholder="Điều bạn muốn giữ trong câu chuyện…" />
            <div className="clarification-actions">
              <button type="button" disabled={!answers[active]?.trim()} onClick={next}>{beforeEdit.current ? "Xong" : "Tiếp tục"}</button>
              {beforeEdit.current && <button type="button" className="secondary" onClick={() => {
                onChange(active, beforeEdit.current);
                const pending = questions.findIndex((_, i) => i !== active && !answers[i]?.trim());
                choose(pending < 0 ? questions.length : pending);
              }}>Hủy</button>}
              <button type="button" className="secondary" onClick={() => {
                onChange(active, "Chưa quyết định. Nếu đề xuất một lựa chọn, hãy ghi rõ đó là gợi ý của AI.");
                next();
              }}>Để quyết định sau</button>
            </div>
          </div>
        </li> : answers[i]?.trim() ? <li key={i}>
          <div className="clarification-question"><span>FirstFrame · {i + 1}</span><p>{question}</p></div>
          <div className="clarification-answer"><span>Bạn</span><p id={`answer-${i}-value`} className="preserve-lines">{answers[i]}</p>
            <button className="secondary" type="button" onClick={() => choose(i)}>Sửa câu trả lời {i + 1}</button>
          </div>
        </li> : null)}
      </ol>


    </>}
    {(thinking || advancing) && <div ref={thinkingBubble} className="firstframe-thinking" role="status">
      <span className="thinking-dots" aria-hidden="true"><i /><i /><i /></span>
      <span>{thinking ? "FirstFrame đang suy nghĩ…" : "FirstFrame đang chuẩn bị câu tiếp theo…"}</span>
    </div>}
    {active === questions.length && answered === questions.length && <div id="clarification-complete" tabIndex={-1} className="clarification-complete">
      <div className="clarification-question"><span>FirstFrame · Tiếp tục cùng bạn</span>
        <p>Đã có {answered + retained.length} lựa chọn. Bạn muốn làm rõ thêm hay xem lại trước khi tạo bản phát triển?</p></div>
      <div className="clarification-actions">
        {onAskMore && questions.length < 20 && <button type="button" className="secondary" onClick={() => {
          setReviewedKey(null); onAskMore();
        }}>Hỏi thêm từ câu trả lời của tôi</button>}
        {onConfirm && <button type="button" data-choice-review onClick={() => {
          setReviewedKey(confirmationKey ?? "");
          requestAnimationFrame(() => document.getElementById("clarification-consent-title")?.focus());
        }}>Xem lại các lựa chọn</button>}
      </div>
      {reviewedKey !== null && reviewedKey === (confirmationKey ?? "") && <section className="clarification-consent" aria-labelledby="clarification-consent-title">
        <h3 id="clarification-consent-title" tabIndex={-1}>FirstFrame · Bạn đồng ý để tôi tạo bản phát triển?</h3>
        <p className="preserve-lines">{idea}</p>
        {!!constraints.filter(Boolean).length && <p>Điều muốn giữ: {constraints.filter(Boolean).join(" · ")}</p>}
        <div className="consent-choices">{[...retained, ...questions.map((question, index) => ({ question, answer: answers[index] }))].map((choice, index) =>
          <details key={index}><summary><strong>{choice.question}</strong><span>{choice.answer}</span></summary>
            <p className="preserve-lines">{choice.answer}</p></details>)}</div>
        <p>{hasDraft ? "Tôi sẽ tạo đề xuất riêng từ các lựa chọn này; bản đang viết chỉ thay khi bạn chọn nhận."
          : "Tôi sẽ dùng các lựa chọn trên để tạo story plan. Những điều bạn chưa quyết định vẫn được để mở."}</p>
        <div className="clarification-actions">
          <button type="button" data-tour-action="plan" onClick={onConfirm}>{hasDraft ? "Đồng ý, tạo bản đề xuất mới" : "Đồng ý, tạo bản phát triển"}</button>
          <button type="button" className="secondary" onClick={() => {
            setReviewedKey(null); document.getElementById("clarification-complete")?.focus();
          }}>Chưa, tôi muốn sửa tiếp</button>
        </div>
      </section>}
    </div>}
    </fieldset>
  </div>;
}

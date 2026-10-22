import type { StoryDraft } from "./projectsApi";
import { sectionLabels } from "./storyLabels";

const narrativeTitles = ["Beginning", "Middle", "Ending"];

export function StoryPlanReading({ draft, dirty }: { draft: StoryDraft; dirty: boolean }) {
  const narrative = draft.sections.filter(section => narrativeTitles.includes(section.title));
  const otherSections = draft.sections.filter(section => !narrativeTitles.includes(section.title));

  return <section className="story-reading" aria-label="Bản đọc story plan">
    <p className="eyebrow">Đọc câu chuyện</p>
    <p className="storage-note">{dirty ? "Bản đang làm việc · Có thay đổi chưa lưu" : "Bản đang làm việc · Đã lưu"}</p>
    <p>Đây là bản phác thảo câu chuyện (story plan), chưa phải kịch bản theo cảnh.
      Bạn hình dung điều gì diễn ra và muốn giữ chi tiết nào?</p>
    <h3 className="preserve-lines">{draft.title.trim() ? draft.title : "Chưa có tên phim."}</h3>
    <p className="story-kicker">Tóm tắt một câu</p>
    <p className="preserve-lines">{draft.logline.trim() ? draft.logline : "Chưa có tóm tắt."}</p>
    {narrative.map((section, index) => <div className="story-section" key={index}>
      <h4>{sectionLabels[section.title]}</h4>
      <p className="preserve-lines">{section.content.trim() ? section.content : "Chưa có nội dung."}</p>
    </div>)}
    {!narrative.length && <p>Chưa có phần mở đầu, diễn tiến hoặc kết thúc.</p>}
    {!!otherSections.length && <details>
      <summary>Các chi tiết khác ({otherSections.length})</summary>
      {otherSections.map((section, index) => <div className="story-section" key={index}>
        <h4>{sectionLabels[section.title] ?? section.title}</h4>
        <p className="preserve-lines">{section.content.trim() ? section.content : "Chưa có nội dung."}</p>
      </div>)}
    </details>}
    <button type="button" className="secondary" onClick={() => {
      const editor = document.getElementById("draft-logline");
      editor?.scrollIntoView({ block: "center" });
      editor?.focus({ preventScroll: true });
    }}>Chuyển tới phần chỉnh sửa</button>
  </section>;
}

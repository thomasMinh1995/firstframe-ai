"use client";

import type {PlanGeneration} from "./projectsApi";
import {StoryFeedback} from "./StoryResultCards";
import {sectionLabels} from "./storyLabels";

export type PlanReading = {
  projectId: string;
  generation: PlanGeneration;
  status: "pending" | "reviewed" | "failed" | "unknown";
};

export function PlanCheckpointReader({reading, onClose}: {reading: PlanReading; onClose: () => void}) {
  const {generation, status} = reading;
  const label = status === "pending" ? "Đang góp ý" : status === "reviewed" ? "Góp ý đã lưu"
    : status === "failed" ? "Chưa có góp ý hợp lệ" : "Chưa rõ kết quả góp ý";
  return <section className="panel form-stack plan-checkpoint-reader" aria-labelledby="plan-checkpoint-title">
    <h2 id="plan-checkpoint-title">{generation.applied_revision === null ? "Đề xuất Story plan đã lưu" : "Story plan đã lưu"}</h2>
    <p role="status" aria-live="polite">{label}</p>
    <button type="button" className="secondary" onClick={onClose}>Đóng bản đọc sớm · Xem bản đang viết và đề xuất đã lưu</button>
    <p className="storage-note">Bản đọc theo nguồn lúc tạo. Đọc không nhận đề xuất, lưu sửa hoặc chọn bản xuất PDF.</p>
    <h3>{generation.draft.title}</h3>
    <p className="preserve-lines">{generation.draft.logline}</p>
    {generation.draft.sections.map((section, i) => <div key={i}>
      <h3>{sectionLabels[section.title] ?? section.title}</h3>
      <p className="preserve-lines">{section.content}</p>
    </div>)}
    {status === "reviewed" && generation.feedback && generation.feedback_source &&
      <StoryFeedback evaluation={generation.feedback} uiLanguage="vi" source={generation.feedback_source} />}
    {(status === "failed" || status === "unknown") && <p className="form-message">
      Phần đã lưu vẫn đọc được. Giữ hoặc tải bản sao sửa đang có trước khi mở lại dự án để kiểm tra; không cần tạo lại Story plan.
    </p>}
  </section>;
}

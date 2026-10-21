import type { ProgressEvent } from "./projectsApi";
import type { UiLanguage } from "./language";

export type OperationStep = ProgressEvent & { occurrence: number };
export const progressCopy = {
  vi: {
    title: "Tiến trình xử lý", done: "Đã hoàn tất và lưu", failed: "Thao tác chưa hoàn tất",
    running: "Đã chạy", elapsed: "Hoàn tất sau", stopped: "Dừng sau",
    saved: "Kết quả đã được lưu. Xem phản hồi bên dưới để biết nội dung nào cần đối chiếu; hoàn tất xử lý không có nghĩa bản thảo đã đạt yêu cầu.",
    error: "Nội dung đã lưu trước khi gọi AI vẫn được giữ. Nếu mất kết nối, thao tác có thể tiếp tục trên máy chủ; hãy lưu hoặc tải bản sao các thay đổi mới trước khi mở lại dự án để kiểm tra.",
    unsavedError: "Bạn có thay đổi chưa lưu trên màn hình. Hãy lưu lại hoặc tải bản sao JSON trước khi tải lại trang hay mở lại dự án.",
    savedWithEdits: "Lần chạy trước đã hoàn tất và lưu. Các thay đổi mới trên màn hình chưa được lưu hoặc kiểm tra lại.",
    prepareError: "Chưa lưu được thay đổi. Bản đang sửa vẫn ở trên màn hình; hãy thử lưu lại hoặc tải bản sao JSON trước khi tải lại trang.",
    preparing: "Đang chuẩn bị yêu cầu…", active: "Đang thực hiện", completed: "Đã xong", failure: "Chưa hoàn tất",
    analyze: "Làm rõ ý tưởng", plan: "Tạo bản phát triển", review: "Nhận phản hồi",
    stages: { prepare: "Chuẩn bị và lưu nội dung hiện tại", reasoning: "Đọc ý tưởng và chuẩn bị câu hỏi",
      planning: "Phát triển câu chuyện từ lựa chọn của bạn", fidelity: "Đối chiếu bản thảo với ý đồ tác giả",
      evaluation: "Đọc bản thảo và đề xuất góp ý", fidelity_audit: "Kiểm tra căn cứ và hướng sửa của góp ý",
      saving: "Lưu kết quả và lịch sử phiên bản" } as Record<string, string>,
    other: "Xử lý yêu cầu", startError: "Không bắt đầu được thao tác. Bản đang sửa vẫn được giữ.",
    connectionError: "Kết nối bị gián đoạn. Bản đang sửa vẫn được giữ; hãy tải bản sao các thay đổi mới trước khi mở lại dự án.",
    invalid: "Kết quả trả về không hợp lệ. Bản đang sửa vẫn được giữ.",
  },
  en: {
    title: "Operation progress", done: "Completed and saved", failed: "Operation incomplete",
    running: "Working for", elapsed: "Completed in", stopped: "Stopped after",
    saved: "Results have been saved. Read the feedback below for items needing review; completion does not mean the draft meets all requirements.",
    error: "Content saved before the AI request is preserved. After a disconnection, processing may continue on the server; save or download any new edits before reopening the project to check results.",
    unsavedError: "You have unsaved edits on screen. Save or download a JSON backup before reloading or reopening the project.",
    savedWithEdits: "The previous run completed and was saved. New edits on screen have not been saved or reviewed again.",
    prepareError: "Changes could not be saved. Your edits remain on screen; retry saving or download a JSON backup before reloading.",
    preparing: "Preparing the request…", active: "In progress", completed: "Done", failure: "Incomplete",
    analyze: "Clarify the idea", plan: "Develop the story", review: "Review the draft",
    stages: { prepare: "Prepare and save current content", reasoning: "Read the idea and prepare questions",
      planning: "Develop the story from your choices", fidelity: "Compare the draft with author intent",
      evaluation: "Read the draft and propose feedback", fidelity_audit: "Check the evidence and proposed revision",
      saving: "Save results and version history" } as Record<string, string>,
    other: "Process the request", startError: "Could not start the operation. Your edits are preserved.",
    connectionError: "Connection interrupted. Your edits are preserved; download any new edits before reopening the project.",
    invalid: "Invalid response. Your edits are preserved.",
  },
};

// Steps appear only when the backend actually runs them, including repeated audits.
export function applyProgress(steps: OperationStep[], event: ProgressEvent): OperationStep[] {
  if (event.status === "active") return [...steps, { ...event,
    occurrence: steps.filter((step) => step.stage === event.stage).length + 1 }];
  const index = steps.findLastIndex((step) => step.stage === event.stage && step.status === "active");
  return steps.map((step, i) => i === index ? { ...step, status: event.status } : step);
}
export function progressLanguage(language: string): UiLanguage {
  // Auto selects the existing Vietnamese interface; it does not redetect or translate content.
  return language === "en" ? "en" : "vi";
}

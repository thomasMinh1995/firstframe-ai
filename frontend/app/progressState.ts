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
    waiting: "Chờ bước trước", notRun: "Chưa thực hiện", preparing: "Đang chuẩn bị yêu cầu…", active: "Đang thực hiện", completed: "Đã xong", failure: "Chưa hoàn tất",
    "screenplay-reviews": "Góp ý một cảnh", "screenplay-proposals": "Viết thử một cảnh", "scene-sketches": "Phác hình một cảnh", "scene-suggestions": "Gợi ý cảnh", analyze: "Làm rõ ý tưởng", plan: "Tạo bản phát triển", review: "Nhận phản hồi",
    stages: { reasoning_context: "Tập hợp ý tưởng và lựa chọn đã lưu", reasoning_validation: "Kiểm tra và sắp xếp câu hỏi", sketch_save: "Lưu kết quả phác hình", screenplay_review_source:"Giữ snapshot cảnh và nguồn dẫn chứng",screenplay_review_checkpoint:"Lưu ID trước khi nhận góp ý",screenplay_review:"Đọc cảnh để góp ý",screenplay_review_validation:"Kiểm tra ID/quote, chưa xác nhận lập luận đúng",screenplay_review_save:"Lưu góp ý riêng để tác giả cân nhắc",screenplay_source:"Giữ nguồn kịch bản và cảnh đích",screenplay_checkpoint:"Lưu ID tác vụ trước khi viết thử",screenplay_generation:"Viết thử đúng một cảnh",screenplay_validation:"Kiểm tra cấu trúc, chưa xác nhận đúng ý đồ",screenplay_proposal_save:"Lưu phương án riêng chờ tác giả chọn",sketch_checkpoint: "Giữ nguồn và ID trước khi phác", sketch_generation: "Đang tạo một ảnh local", sketch_validation: "Kiểm tra tệp PNG, chưa xác nhận đúng ý đồ", staging_generation: "Đưa phương án dàn cảnh có căn cứ", staging_validation: "Đối chiếu ID/quote với nguồn, chưa xác nhận lý do hay chất lượng", scene_source: "Giữ nguồn story plan và dàn cảnh", scene_checkpoint: "Lưu ID tác vụ trước khi gọi AI",
      scene_generation: "Đề xuất cảnh từ nguồn đã chọn", scene_validation: "Kiểm tra cấu trúc kết quả, chưa xác nhận chất lượng sáng tác",
      scene_proposal_save: "Lưu đề xuất riêng để tác giả đối chiếu", plan_choices: "Đọc các lựa chọn đã xác nhận và kiểm tra câu trả lời",
      planning_context: "Tập hợp ý tưởng, lựa chọn và điều muốn giữ",
      planning_structure: "Kiểm tra cấu trúc và sắp xếp các phần câu chuyện",
      plan_checkpoint: "Giữ bản phác thảo trước khi đọc góp ý",
      plan_save: "Lưu kết quả và lịch sử của lượt này", prepare: "Chuẩn bị và lưu nội dung hiện tại", reasoning: "Đọc ý tưởng và chuẩn bị câu hỏi",
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
    waiting: "Waiting for previous step", notRun: "Not performed", preparing: "Preparing the request…", active: "In progress", completed: "Done", failure: "Incomplete",
    "screenplay-reviews": "Review one screenplay scene", "screenplay-proposals": "Draft one screenplay scene", "scene-sketches": "Sketch one scene", "scene-suggestions": "Suggest scenes", analyze: "Clarify the idea", plan: "Develop the story", review: "Review the draft",
    stages: { reasoning_context: "Assemble the idea and saved choices", reasoning_validation: "Validate and arrange questions", sketch_save: "Save sketch result", screenplay_review_source:"Capture scene and evidence sources",screenplay_review_checkpoint:"Save review request ID",screenplay_review:"Read scene for feedback",screenplay_review_validation:"Check IDs/quotes, not reasoning quality",screenplay_review_save:"Save feedback for author review",screenplay_source:"Capture screenplay and target scene",screenplay_checkpoint:"Save request ID",screenplay_generation:"Draft exactly one scene",screenplay_validation:"Check structure, not creative quality",screenplay_proposal_save:"Save separate proposal for author review",sketch_checkpoint: "Save source and request ID", sketch_generation: "Generate one local image", sketch_validation: "Validate PNG, not creative accuracy", staging_generation: "Suggest staging options with sources", staging_validation: "Check source IDs/quotes, not reasoning or creative quality", scene_source: "Capture story plan and scene source", scene_checkpoint: "Save request ID before calling AI",
      scene_generation: "Suggest scenes from the chosen source", scene_validation: "Check result structure, not creative quality",
      scene_proposal_save: "Save proposal for author review", plan_choices: "Check confirmed choices and answers",
      planning_context: "Assemble the idea, choices and constraints",
      planning_structure: "Validate and arrange the story sections",
      plan_checkpoint: "Keep the draft before reviewing it",
      plan_save: "Save results and history for this run", prepare: "Prepare and save current content", reasoning: "Read the idea and prepare questions",
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


export type OperationKind = "analyze" | "plan" | "review" | "scene-suggestions" | "scene-sketches" | "screenplay-proposals" | "screenplay-reviews";
export type ProcessStatus = OperationStep["status"] | "pending" | "interrupted";
export type ProcessStep = Omit<OperationStep, "status"> & { status: ProcessStatus };

const processStages: Record<OperationKind, [string[], string[], string[]]> = {
  analyze: [["prepare", "reasoning_context"], ["reasoning", "reasoning_validation"], ["saving"]],
  plan: [["prepare", "plan_choices", "planning_context"], ["planning", "planning_structure"], ["plan_checkpoint", "evaluation", "plan_save"]],
  // Critic/audit calls are conditional: show them only when reported by the server.
  review: [["prepare"], [], ["saving"]],
  "scene-suggestions": [["prepare", "scene_source", "scene_checkpoint"], [], ["scene_proposal_save"]],
  "scene-sketches": [["prepare", "sketch_checkpoint"], ["sketch_generation", "sketch_validation"], ["sketch_save"]],
  "screenplay-proposals": [["prepare", "screenplay_source", "screenplay_checkpoint"], ["screenplay_generation", "screenplay_validation"], ["screenplay_proposal_save"]],
  "screenplay-reviews": [["prepare", "screenplay_review_source", "screenplay_review_checkpoint"], ["screenplay_review", "screenplay_review_validation"], ["screenplay_review_save"]],
};
export const processTitles = {
  vi: {
    analyze: ["Chuẩn bị nội dung", "Làm rõ ý tưởng", "Lưu câu hỏi và lựa chọn"],
    plan: ["Chuẩn bị từ lựa chọn của bạn", "Phát triển Story plan", "Đối chiếu và giữ kết quả"],
    review: ["Chuẩn bị bản thảo", "Đọc và đối chiếu bản thảo", "Lưu góp ý"],
    "scene-suggestions": ["Chuẩn bị nguồn câu chuyện", "Phát triển dàn cảnh", "Lưu phương án để bạn chọn"],
    "scene-sketches": ["Chuẩn bị cảnh và yêu cầu", "Tạo và kiểm tra hình ảnh", "Giữ kết quả phác hình"],
    "screenplay-proposals": ["Chuẩn bị nguồn và cảnh đích", "Viết thử và kiểm tra cảnh", "Lưu phương án để bạn chọn"],
    "screenplay-reviews": ["Chuẩn bị cảnh và dẫn chứng", "Đọc và kiểm tra góp ý", "Lưu góp ý để bạn xem"],
  },
  en: {
    analyze: ["Prepare the content", "Clarify the idea", "Save questions and choices"],
    plan: ["Prepare from your choices", "Develop the story plan", "Review and keep the result"],
    review: ["Prepare the draft", "Read and compare the draft", "Save feedback"],
    "scene-suggestions": ["Prepare story sources", "Develop the scene outline", "Save options for your review"],
    "scene-sketches": ["Prepare the scene and request", "Generate and validate the image", "Keep the sketch result"],
    "screenplay-proposals": ["Prepare sources and target scene", "Draft and validate the scene", "Save options for your review"],
    "screenplay-reviews": ["Prepare scene and evidence", "Read and validate feedback", "Save feedback for your review"],
  },
};

export function operationProgressGroups(kind: OperationKind, steps: OperationStep[], outcome: "running" | "completed" | "failed" = "running") {
  const definitions = processStages[kind];
  // Optional and unknown events remain in their actual order in the processing group.
  const owner = (stage: string) => definitions[0].includes(stage) ? 0
    : definitions[2].includes(stage) || (kind === "plan" && !definitions[1].includes(stage)) ? 2 : 1;
  return definitions.map((expected, index) => {
    const children: ProcessStep[] = steps.filter(step => owner(step.stage) === index).map(step => ({
      ...step, status: outcome === "failed" && step.status === "active" ? "interrupted" : step.status,
    }));
    if (outcome !== "completed") expected.forEach((stage, position) => {
      if (children.some(step => step.stage === stage)) return;
      const next = children.findIndex(step => expected.slice(position + 1).includes(step.stage));
      children.splice(next < 0 ? children.length : next, 0, { stage, occurrence: 1, status: "pending" });
    });
    const status: ProcessStatus = children.some(step => step.status === "failed") ? "failed"
      : children.some(step => step.status === "interrupted") ? "interrupted"
        : children.some(step => step.status === "active") ? "active"
          : children.length && children.every(step => step.status === "completed") ? "completed" : "pending";
    return { id: ["prepare", "develop", "review"][index], children, status };
  }).filter(group => group.children.length || outcome !== "completed");
}

export function planProgressGroups(steps: OperationStep[]) {
  return operationProgressGroups("plan", steps);
}

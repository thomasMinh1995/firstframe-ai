"use client";

const labels: Record<string, string> = {
  summary: "Tóm tắt", notes: "Ghi nhận", label: "Nhãn", content: "Nội dung", missing_information: "Câu hỏi làm rõ",
  story_plan: "Bản phát triển", working_title: "Tên tác phẩm", title: "Tên", logline: "Logline", text: "Nội dung",
  characters: "Nhân vật", protagonist: "Nhân vật chính", supporting_characters: "Nhân vật phụ",
  antagonist_or_obstacle: "Đối lực / trở ngại", conflict: "Xung đột", external: "Bên ngoài", internal: "Nội tâm", stakes: "Điều có thể mất",
  beginning: "Mở đầu", setup: "Bối cảnh", key_event: "Sự kiện chính", middle: "Phát triển", escalation: "Leo thang",
  turning_point: "Bước ngoặt", ending: "Kết", resolution: "Giải quyết", final_image: "Hình ảnh cuối",
  theme: "Chủ đề", statement: "Thông điệp", visual_style: "Hình ảnh", description: "Mô tả", visual_motifs: "Mô-típ hình ảnh",
  tone: "Sắc thái", production_notes: "Ghi chú sản xuất", locations: "Bối cảnh quay", cast_size: "Quy mô diễn viên",
  passed: "Đạt yêu cầu", rubric_scores: "Điểm tiêu chí (1–5)", strengths: "Điểm mạnh", weaknesses: "Điểm chưa tốt",
  suggestions: "Góp ý", story_clarity: "Độ rõ câu chuyện", character: "Nhân vật", emotional_impact: "Tác động cảm xúc",
  production_feasibility: "Khả thi sản xuất",
};

export default function OutputFields({value, onChange, name = "Output"}: {
  value: unknown; onChange: (value: unknown) => void; name?: string;
}) {
  if (Array.isArray(value)) return <div className="form-stack output-fields"><strong>{labels[name] ?? name}</strong>
    {value.map((item, index) => <div className="form-stack" key={index}>
      <OutputFields value={item} name={`${labels[name] ?? name} ${index + 1}`}
        onChange={(next) => onChange(value.map((old, i) => i === index ? next : old))} />
      <button type="button" className="secondary" onClick={() => onChange(value.filter((_, i) => i !== index))}>Xóa mục {index + 1}</button>
    </div>)}
    <button type="button" className="secondary" onClick={() => onChange([...value, name === "notes" ? {label: "", content: ""} : ""])}>Thêm mục</button>
  </div>;
  if (typeof value === "object" && value !== null) return <div className="form-stack output-fields">
    <strong>{labels[name] ?? name}</strong>
    {Object.entries(value).map(([key, item]) => <OutputFields key={key} name={key} value={item}
      onChange={(next) => onChange({...value, [key]: next})} />)}
  </div>;
  if (typeof value === "boolean") return <label className="review-choice"><input type="checkbox" checked={value}
    onChange={(event) => onChange(event.target.checked)} />{labels[name] ?? name}</label>;
  if (typeof value === "number") return <label>{labels[name] ?? name}<input type="number" min={1} max={5} step={1}
    value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
  return <label>{labels[name] ?? name}<textarea rows={2} value={typeof value === "string" ? value : ""}
    onChange={(event) => onChange(value === null && !event.target.value ? null : event.target.value)} /></label>;
}

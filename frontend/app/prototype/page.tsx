"use client";

import { useRef, useState } from "react";
import styles from "./prototype.module.css";

type Beat = { id: string; label: string; title: string; text: string; source: string; reason: string; added?: boolean };
type Scene = { id: string; heading: string; text: string };

const originalIdea = "Mẹ nhắc muốn ăn vải đầu mùa. Huy đạp xe đi mua, nhưng mua nhiều quá. Hai túi vải cứ nghiêng sang hai bên. Cậu dừng lại, buộc lại, rồi kiên nhẫn đưa món quà về nhà.";
const initialBeats: Beat[] = [
  { id: "wish", label: "LỜI GỢI MỞ", title: "Một lời nhắc rất khẽ", text: "Mẹ nhắc muốn ăn vải đầu mùa. Huy nghe thấy, lặng lẽ lấy xe đi chợ.", source: "“Mẹ nhắc muốn ăn vải đầu mùa.”", reason: "Giữ lời nhắc của mẹ làm điểm bắt đầu. Sự quan tâm của Huy hiện ra qua việc cậu đi mua." },
  { id: "market", label: "MỘT QUYẾT ĐỊNH", title: "Thêm một chùm nữa", text: "Ở chợ, Huy chọn đầy hai túi vải. Nhiều hơn cậu nghĩ mình sẽ mua.", source: "“Huy đạp xe đi mua, nhưng mua nhiều quá.”", reason: "Để việc mua quá nhiều xuất phát từ một lựa chọn nhỏ của Huy, chuẩn bị cho hành trình về nhà." },
  { id: "imbalance", label: "ĐƯỜNG VỀ", title: "Chiếc xe chao đảo", text: "Hai túi vải kéo ghi đông nghiêng qua nghiêng lại. Huy phải dừng xe.", source: "“Hai túi vải cứ nghiêng sang hai bên.”", reason: "Giữ trở ngại đúng với tình huống bạn kể: hai túi vải và chiếc xe đạp." },
  { id: "retry", label: "THỬ LẠI", title: "Buộc lại, rồi đi tiếp", text: "Huy đổi bên, buộc túi chắc hơn. Đi được một đoạn, cậu lại phải dừng.", source: "“Cậu dừng lại, buộc lại.”", reason: "Đề xuất thêm một lần dừng để sự kiên nhẫn có nhịp điệu và được nhìn thấy qua hành động.", added: true },
  { id: "walk", label: "MỘT CÁCH KHÁC", title: "Chậm một chút cũng được", text: "Huy xuống yên, chọn dắt xe. Hai túi vải đung đưa đều theo bước chân.", source: "“Kiên nhẫn đưa món quà về nhà.”", reason: "Đề xuất dắt xe thay vì cố đạp tiếp. Cách giải quyết nhỏ này vẫn giữ hành trình xe đạp làm trung tâm.", added: true },
  { id: "home", label: "VỀ ĐẾN NHÀ", title: "Cả một quãng quan tâm", text: "Huy đặt vải lên bàn. Mẹ bật cười, kéo ghế cho cậu. Tay Huy còn hằn vết quai túi.", source: "“Đưa món quà về nhà.”", reason: "Đề xuất phản ứng của mẹ và vết quai túi để khép lại bằng hình ảnh. Bạn có thể đổi sang một kết thúc lặng hơn.", added: true },
];
const initialScenes: Scene[] = [
  { id: "scene-1", heading: "01 · NHÀ · SÁNG", text: "Mẹ nhắc đến vải đầu mùa. Huy nghe thấy và lấy xe đi chợ." },
  { id: "scene-2", heading: "02 · CHỢ · SÁNG", text: "Huy lựa vải, ngập ngừng rồi lấy thêm. Hai túi đầy treo hai bên ghi đông." },
  { id: "scene-3", heading: "03 · ĐƯỜNG VỀ · TRƯA", text: "Xe chao đảo. Huy dừng, buộc lại túi, thử đi rồi quyết định dắt xe." },
  { id: "scene-4", heading: "04 · NHÀ · TRƯA", text: "Huy đặt vải lên bàn. Mẹ bật cười, kéo ghế cho cậu ngồi." },
];
const initialScript: Scene[] = [
  { id: "script-1", heading: "1. NỘI. BẾP NHÀ HUY — SÁNG", text: "Mẹ rửa chiếc rổ dưới vòi nước. Huy ngồi ở bàn, xỏ lại dây giày.\n\nMẸ\nĐến mùa vải rồi nhỉ.\n\nHuy ngẩng lên. Mẹ vẫn cúi rửa rổ.\n\nCậu lấy chiếc nón treo ở cửa. Ngoài sân, chân chống xe đạp bật lên một tiếng khô." },
  { id: "script-2", heading: "2. NGOẠI. SẠP HOA QUẢ — SÁNG", text: "Huy nhấc một chùm vải lên, xoay trong tay. Người bán mở túi.\n\nNGƯỜI BÁN\nThế này nhé?\n\nHuy nhìn chiếc túi, rồi nhìn đống vải. Cậu chỉ thêm một chùm.\n\nHai túi vải nặng trĩu được móc lên hai bên ghi đông. Huy giữ xe thẳng, cẩn thận leo lên yên." },
  { id: "script-3", heading: "3. NGOẠI. ĐƯỜNG VỀ NHÀ — TRƯA", text: "Bánh trước lượn sang trái. Một túi vải đập nhẹ vào khung xe.\n\nHuy bóp phanh. Cậu xuống xe, tháo túi bên phải rồi buộc cao hơn. Kéo thử. Chưa chắc. Cậu buộc thêm một vòng.\n\nHuy đạp được vài mét. Chiếc xe lại nghiêng.\n\nCậu đứng yên một lúc, lau mồ hôi bằng vai áo. Rồi nắm cả hai tay lái, chậm rãi dắt xe đi.\n\nHai túi vải đung đưa đều theo bước chân." },
  { id: "script-4", heading: "4. NỘI. BẾP NHÀ HUY — TRƯA", text: "Hai túi vải được đặt xuống bàn.\n\nMẹ quay lại. Bà nhìn túi thứ nhất, rồi túi thứ hai. Một tiếng cười bật ra.\n\nBà kéo chiếc ghế bên cạnh. Huy ngồi xuống. Hai vết quai túi đỏ hằn trong lòng bàn tay.\n\nMẹ đặt chiếc rổ trước mặt cậu. Huy bứt một quả vải khỏi chùm.\n\nHẾT." },
];
const stages = ["Ý tưởng", "Làm rõ", "Story plan", "Dàn cảnh", "Kịch bản"];
const endings = [
  { value: "home", title: "Món quà về đến nhà", detail: "Thấy phản ứng của mẹ ở cuối." },
  { value: "road", title: "Dừng ở hành trình", detail: "Huy vẫn đang đưa món quà về." },
  { value: "later", title: "Để quyết định sau", detail: "Xem một đề xuất kết thúc tạm." },
] as const;

function Icon({ name, size = 18 }: { name: "spark" | "edit" | "arrow" | "check" | "download" | "leaf" | "undo"; size?: number }) {
  const paths = {
    spark: "m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4L12 3Z",
    edit: "m15 5 4 4M4 20l4-1L20 7a2.8 2.8 0 0 0-4-4L4 15l-1 6Z",
    arrow: "M4 12h16m-6-6 6 6-6 6",
    check: "m5 12 4 4L19 6",
    download: "M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5",
    leaf: "M20 4C8 2 2 8 5 16c8 5 16-1 15-12ZM5 19l10-10",
    undo: "M8 4 3 9l5 5M3 9h11a6 6 0 0 1 0 12",
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}

function EditableText({ label, text, onSave, large = false }: { label: string; text: string; onSave: (value: string) => void; large?: boolean }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(text);
  const editButton = useRef<HTMLButtonElement>(null);
  function close() { setEditing(false); requestAnimationFrame(() => editButton.current?.focus()); }
  return <>
    {editing ? <div className={styles.editor}>
      <label>{label}<textarea autoFocus value={value} rows={large ? 10 : 4} maxLength={12000} onChange={event => setValue(event.target.value)} onKeyDown={event => { if (event.key === "Escape") close(); }} /></label>
      <div className={styles.editorActions}><button className={styles.primarySmall} disabled={!value.trim()} onClick={() => { onSave(value.trim()); close(); }}>Giữ thay đổi</button><button className={styles.textButton} onClick={close}>Hủy</button></div>
    </div> : <p className={large ? styles.screenplayText : styles.cardText}>{text}</p>}
    <button ref={editButton} className={styles.textButton} hidden={editing} onClick={() => { setValue(text); setEditing(true); }} aria-label={`Sửa ${label.toLowerCase()}`}><Icon name="edit" size={14} /> Sửa</button>
  </>;
}

export default function Prototype() {
  const [idea, setIdea] = useState("");
  const [submittedIdea, setSubmittedIdea] = useState("");
  const [clarifying, setClarifying] = useState(false);
  const [ending, setEnding] = useState<"home" | "road" | "later" | "">("");
  const [beats, setBeats] = useState(initialBeats);
  const [scenes, setScenes] = useState(initialScenes);
  const [script, setScript] = useState(initialScript);
  const [stage, setStage] = useState(0);
  const [openReason, setOpenReason] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [undo, setUndo] = useState<(() => void) | null>(null);
  const changedIdea = stage > 0 && idea !== submittedIdea;
  const [edited, setEdited] = useState(false);
  const step = stage === 0 ? (clarifying ? 2 : 1) : stage + 2;
  const sceneCount = ending === "road" ? 3 : 4;

  function focusSection(id: string) {
    requestAnimationFrame(() => {
      const heading = document.getElementById(id);
      heading?.scrollIntoView({ behavior: "smooth", block: "start" });
      heading?.focus({ preventScroll: true });
    });
  }
  function clarifyIdea() {
    if (!idea.trim()) return;
    setClarifying(true);
    setNotice("Đã giữ ý tưởng trong phiên thử. Tiếp theo: chọn phần kết cho ví dụ mẫu.");
    focusSection("prototype-clarification");
  }
  function showPlan() {
    if (!idea.trim() || !ending) return;
    setSubmittedIdea(idea);
    setBeats(initialBeats.map(beat => beat.id !== "home" ? beat : ending === "road" ? {
      ...beat, label: "KẾT MỞ", title: "Con đường vẫn phía trước",
      text: "Huy nhìn con đường còn dài, rồi tiếp tục bước. Hai túi vải vẫn ở bên cậu.",
      source: "Bạn chọn: dừng ở hành trình.",
      reason: "Giữ lựa chọn kết mở của bạn: chưa cho thấy phản ứng của mẹ, khép lại bằng việc Huy tiếp tục đi.",
    } : {
      ...beat, source: ending === "home" ? "Bạn chọn: món quà về đến nhà." : "Bạn để phần kết mở cho một đề xuất tạm.",
      reason: ending === "home" ? "Giữ lựa chọn về đến nhà của bạn. Phản ứng của mẹ và vết quai túi là những chi tiết gợi ý để kết bằng hình ảnh." : "Bạn chưa chốt phần kết. Đây là một phương án tạm để đọc thử; bạn có thể sửa hoặc bỏ qua.",
    }));
    setScenes(ending === "road" ? initialScenes.slice(0, 3) : initialScenes);
    setScript(ending === "road" ? initialScript.slice(0, 3).map((scene, index) => index === 2 ? {
      ...scene, text: `${scene.text}\n\nHuy nhìn con đường phía trước. Cậu tiếp tục bước.\n\nHẾT.`,
    } : scene) : initialScript);
    setStage(1);
    setNotice("Phác thảo mẫu đã mở theo lựa chọn phần kết của bạn.");
    focusSection("prototype-stage-1");
  }

  function announceEdit(restore: () => void) {
    const previousEdited = edited;
    setUndo(() => () => { restore(); setEdited(previousEdited); setNotice("Đã hoàn tác lần sửa gần nhất."); setUndo(null); });
    setEdited(true);
    setNotice("Đã giữ thay đổi trong phiên thử này.");
  }
  function goTo(index: number) {
    if (index >= step) return;
    const id = index === 0 ? "prototype-stage-0" : index === 1
      ? (stage === 0 ? "prototype-clarification" : "prototype-choice-summary") : `prototype-stage-${index - 1}`;
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function revealNext() {
    const next = stage + 1;
    setStage(next);
    setNotice(next === 2 ? "Đã mở dàn cảnh mẫu. Nội dung không được AI tạo lại." : "Đã mở kịch bản mẫu. Bạn có thể sửa từng cảnh.");
    requestAnimationFrame(() => {
      const heading = document.getElementById(`prototype-stage-${next}`);
      heading?.scrollIntoView({ behavior: "smooth", block: "start" });
      heading?.focus({ preventScroll: true });
    });
  }
  function exportScript() {
    const content = `VẢI ĐẦU MÙA\nBản thử Firstframe — nội dung mẫu, có thể đã chỉnh sửa\n\n${script.map(scene => `${scene.heading}\n\n${scene.text}`).join("\n\n--------------------\n\n")}`;
    const url = URL.createObjectURL(new Blob([content], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = "vai-dau-mua-ban-thu.txt"; link.click(); URL.revokeObjectURL(url);
    setNotice("Đã tải kịch bản dạng văn bản.");
  }

  return <div className={styles.app}>
    <header className={styles.header}>
      <a className={styles.brand} href="/" aria-label="Firstframe — về ứng dụng chính"><span className={styles.brandMark}>f<span>f</span></span>firstframe<span className={styles.brandDot}>.</span></a>
      <div className={styles.headerProject}><span className={styles.projectDot} /> {stage === 0 ? "Câu chuyện mới" : "Vải đầu mùa"} <span className={styles.separator}>/</span><span>Phim ngắn</span></div>
      <span className={styles.prototypeBadge}>PROTOTYPE <span>· Dữ liệu mẫu</span></span>
    </header>

    <div className={styles.layout}>
      <aside className={styles.sidebar} aria-label="Hành trình câu chuyện">
        <div><p className={styles.railLabel}>CÂU CHUYỆN CỦA BẠN</p><nav className={styles.stageNav}>
          {stages.map((label, index) => <button key={label} disabled={index >= step} className={`${styles.stageLink} ${index === step - 1 ? styles.currentStage : ""}`} onClick={() => goTo(index)} aria-label={`Tới ${label}${index >= step ? " — chưa mở" : ""}`}>
            <span className={styles.stageNumber}>{index < step - 1 ? <Icon name="check" size={14} /> : `0${index + 1}`}</span><span>{label}<small>{index < step - 1 ? "Đã qua bước này" : index === step - 1 ? "Đang làm việc" : "Bước tiếp theo"}</small></span>
          </button>)}
        </nav></div>
        <div className={styles.sidebarBottom}><Icon name="leaf" size={23} /><p>Một câu chuyện nhỏ.<br />Một cách kể của riêng bạn.</p><div className={styles.prototypeNote}>Bản thử tương tác · Không gọi AI.<br />Thay đổi chỉ giữ đến khi tải lại trang.</div></div>
      </aside>

      <main className={styles.canvas}>
        <div className={styles.topline}><span><span className={styles.liveDot} /> KHÔNG GIAN VIẾT</span><span>Mẫu · Chỉ giữ trong phiên</span></div>
        <div className={styles.titleRow}><div><p className={styles.overline}>BƯỚC {String(step).padStart(2, "0")} / 05 · {stage === 0 ? "BẮT ĐẦU TỪ MỘT KHOẢNH KHẮC" : "TỪ Ý TƯỞNG ĐẾN KỊCH BẢN"}</p><h1>{stage === 0 ? "Bạn muốn kể điều gì?" : "Vải đầu mùa"}</h1><p className={styles.subtitle}>{stage === 0 ? "Một điều bạn thấy, nghe hoặc nhớ. Chưa cần có cả câu chuyện." : "Có những lời quan tâm được nói bằng cả một quãng đường."}</p></div>{stage > 0 && <span className={styles.filmTag}>PHIM NGẮN<br /><strong>{sceneCount} cảnh</strong></span>}</div>

        <section className={styles.ideaCard} aria-labelledby="prototype-stage-0">
          <div className={styles.ideaLabel}><span className={styles.smallMark}>↳</span><h2 id="prototype-stage-0" tabIndex={-1}>Khoảnh khắc của bạn</h2><span className={styles.authorTag}>BẠN VIẾT</span></div>
          {stage === 0 ? <div className={styles.ideaInput}>
            <label className={styles.srOnly} htmlFor="prototype-idea">Ý tưởng của bạn</label>
            <textarea id="prototype-idea" placeholder="Ví dụ: Mẹ nhắc muốn ăn vải đầu mùa. Tôi đạp xe đi mua, nhưng mua nhiều quá…" value={idea} maxLength={5000} rows={5} onChange={event => { setIdea(event.target.value); setClarifying(false); setEnding(""); }} />
            <div className={styles.inputMeta}><button className={styles.textButton} onClick={() => { setIdea(originalIdea); setClarifying(false); setEnding(""); document.getElementById("prototype-idea")?.focus(); }}>Điền ý tưởng mẫu <span>↗</span></button><span>{idea.length} / 5.000</span></div>
          </div> : <>
            <EditableText label="Ý tưởng" text={idea} onSave={value => { const old = idea; setIdea(value); announceEdit(() => setIdea(old)); }} />
            <div className={styles.intent} id="prototype-choice-summary"><span>Lựa chọn của bạn</span> {endings.find(option => option.value === ending)?.title} <span className={styles.intentCheck}><Icon name="check" size={12} /> Đã giữ</span></div>
          </>}
        </section>
        {changedIdea && <p className={styles.warning} role="status">Bạn đã đổi ý tưởng. Các card bên dưới vẫn là mẫu “Vải đầu mùa”, chưa được tạo lại theo ý tưởng mới.</p>}

        {clarifying && stage === 0 && <section className={`${styles.clarification} ${styles.reveal}`} aria-labelledby="prototype-clarification">
          <div className={styles.sectionHeading}><div><span className={styles.overline}>02 · MỘT LỰA CHỌN TRƯỚC KHI VIẾT</span><h2 id="prototype-clarification" tabIndex={-1}>Bạn muốn khép lại ở đâu?</h2></div><Icon name="spark" size={21} /></div>
          <p className={styles.clarificationNote}>{idea.trim() === originalIdea ? "Giữ hành trình xe đạp làm trung tâm. Phần kết sẽ đi theo lựa chọn của bạn." : "Bản thử giữ nguyên ý tưởng bạn nhập, rồi minh họa các bước tiếp bằng câu chuyện mẫu “Vải đầu mùa”."}</p>
          <fieldset className={styles.endingOptions}><legend className={styles.srOnly}>Chọn phần kết cho câu chuyện mẫu Vải đầu mùa</legend>{endings.map(option => <label key={option.value} className={ending === option.value ? styles.selectedEnding : ""}>
            <input type="radio" name="prototype-ending" value={option.value} checked={ending === option.value} onChange={() => setEnding(option.value)} /><span><strong>{option.title}</strong><small>{option.detail}</small></span>{ending === option.value && <Icon name="check" size={16} />}
          </label>)}</fieldset>
          <details className={styles.whyQuestion}><summary>Vì sao hỏi điều này?</summary><p>Điểm dừng quyết định hình ảnh cuối câu chuyện. Chọn trước giúp bạn giữ quyền quyết định; nếu chưa chắc, bạn có thể để mở.</p></details>
        </section>}

        {stage === 0 && !clarifying && <div className={styles.upcoming}><span className={styles.overline}>TIẾP THEO</span><p>Làm rõ một lựa chọn <span>→</span> Phác thảo chữ S <span>→</span> Dàn cảnh <span>→</span> Kịch bản</p><small>Bản thử dùng câu chuyện “Vải đầu mùa” để minh họa, không gọi AI.</small></div>}

        {stage > 0 && <section className={`${styles.storySection} ${styles.reveal}`} aria-labelledby="prototype-stage-1">
          <div className={styles.sectionHeading}><div><span className={styles.overline}>03 · PHÁC THẢO CÂU CHUYỆN</span><h2 id="prototype-stage-1" tabIndex={-1}>Một mạch kể, từ đầu đến cuối.</h2></div><span className={styles.count}>{beats.length} nhịp · theo đường nối</span></div>
          {submittedIdea.trim() !== originalIdea && <p className={styles.warning}>Phác thảo minh họa của “Vải đầu mùa”, chưa phải kết quả AI cho ý tưởng bạn nhập.</p>}
          {ending === "later" && <p className={styles.clarificationNote}>Phần kết là một đề xuất tạm. Bạn chưa chốt lựa chọn này.</p>}
          <ol className={styles.timeline} aria-label="Phác thảo chữ S, đọc theo số thứ tự từ 1 đến 6">
            {beats.map((beat, index) => {
              const row = Math.floor(index / 2);
              const column = row % 2 === 0 ? index % 2 + 1 : 2 - index % 2;
              return <li key={beat.id} className={styles.beat} style={{ gridRow: row + 1, gridColumn: column }}>
              <span className={styles.beatNumber}>{index + 1}</span>
              <article className={styles.storyCard}>
                <div className={styles.cardEyebrow}><span>{beat.label}</span><span className={beat.added ? styles.aiTag : styles.sourceTag}>{beat.added ? "Có chi tiết AI đề xuất" : submittedIdea.trim() === originalIdea ? "Từ ý tưởng của bạn" : "Từ ý tưởng mẫu"}</span></div>
                <h3>{beat.title}</h3>
                <EditableText label={beat.title} text={beat.text} onSave={value => { const old = beats; setBeats(beats.map(item => item.id === beat.id ? { ...item, text: value } : item)); announceEdit(() => setBeats(old)); }} />
                <button className={`${styles.textButton} ${styles.reasonButton}`} aria-label={`Vì sao đề xuất: ${beat.title}`} aria-expanded={openReason === beat.id} aria-controls={`reason-${beat.id}`} onClick={() => setOpenReason(openReason === beat.id ? null : beat.id)}><Icon name="spark" size={14} /> Vì sao? <span>{openReason === beat.id ? "−" : "+"}</span></button>
                {openReason === beat.id && <div className={styles.reason} id={`reason-${beat.id}`}><span className={styles.overline}>CƠ SỞ CỦA ĐỀ XUẤT</span><blockquote>{beat.source}</blockquote><p>{beat.reason}</p><small>Giải thích mẫu cho bản gốc. Bạn quyết định giữ hay sửa.</small></div>}
              </article>
            </li>;
            })}
          </ol>
          <div className={styles.endNote}><Icon name="leaf" size={16} /><span>Câu chuyện có thể nhỏ. Điều bạn muốn kể thì không.</span></div>
        </section>}

        {stage >= 2 && <section className={styles.storySection} aria-labelledby="prototype-stage-2">
          <div className={styles.sectionHeading}><div><span className={styles.overline}>04 · DÀN CẢNH MẪU</span><h2 id="prototype-stage-2" tabIndex={-1}>Câu chuyện thành từng cảnh.</h2></div><span className={styles.count}>{scenes.length} cảnh</span></div>
          {edited && <p className={styles.warning}>Dàn cảnh và kịch bản mẫu không tự cập nhật theo các chỉnh sửa ở bước trước.</p>}
          <div className={styles.scenes}>{scenes.map(scene => <article key={scene.id} className={styles.sceneCard}><h3>{scene.heading}</h3><EditableText label={scene.heading} text={scene.text} onSave={value => { const old = scenes; setScenes(scenes.map(item => item.id === scene.id ? { ...item, text: value } : item)); announceEdit(() => setScenes(old)); }} /></article>)}</div>
        </section>}

        {stage >= 3 && <section className={styles.storySection} aria-labelledby="prototype-stage-3">
          <div className={styles.sectionHeading}><div><span className={styles.overline}>05 · KỊCH BẢN MẪU</span><h2 id="prototype-stage-3" tabIndex={-1}>Những gì ta thấy và nghe.</h2></div><span className={styles.count}>Bản nháp 01</span></div>
          <div className={styles.scriptPaper}><div className={styles.scriptTitle}>VẢI ĐẦU MÙA<small>KỊCH BẢN PHIM NGẮN · BẢN THỬ</small></div>{script.map(scene => <article className={styles.scriptScene} key={scene.id}><h3>{scene.heading}</h3><EditableText large label={scene.heading} text={scene.text} onSave={value => { const old = script; setScript(script.map(item => item.id === scene.id ? { ...item, text: value } : item)); announceEdit(() => setScript(old)); }} /></article>)}</div>
        </section>}

        <div className={styles.bottomSpace} />
      </main>
    </div>

    <footer className={styles.actionBar}>
      <div className={styles.actionInner}><div className={styles.actionContext}><span className={styles.statusIcon}>{stage === 0 ? `0${step}` : <Icon name="check" size={16} />}</span><div><strong>{stage === 0 ? (clarifying ? "Một lựa chọn của bạn" : "Bắt đầu từ ý tưởng") : stage === 1 ? "Phác thảo đã sẵn sàng" : stage === 2 ? "Đã có dàn cảnh mẫu" : "Bản nháp nằm ngay ở đây"}</strong><span>{stage === 0 ? (clarifying ? "Chọn phần kết hoặc để quyết định sau." : "Viết vài dòng hoặc thử ý tưởng mẫu.") : stage === 1 ? "Đọc, sửa, rồi tiếp tục câu chuyện." : "Các bước trước vẫn ở phía trên."}</span></div></div>
        <div className={styles.actionButtons}>{undo && <button className={styles.undoButton} onClick={undo} aria-label="Hoàn tác lần sửa gần nhất"><Icon name="undo" size={17} /><span>Hoàn tác</span></button>}{stage === 0 ? <button className={styles.primary} disabled={!idea.trim() || (clarifying && !ending)} onClick={clarifying ? showPlan : clarifyIdea}>{clarifying ? "Xem phác thảo mẫu" : "Làm rõ ý tưởng"}<Icon name="arrow" size={18} /></button> : stage < 3 ? <button className={styles.primary} onClick={revealNext}>{stage === 1 ? "Xem dàn cảnh mẫu" : "Xem kịch bản mẫu"}<Icon name="arrow" size={18} /></button> : <button className={styles.primary} onClick={exportScript}><Icon name="download" size={18} /> Tải kịch bản .txt</button>}</div>
      </div>
    </footer>
    <div className={styles.toast} role="status" aria-live="polite" key={notice}>{notice}</div>
  </div>;
}

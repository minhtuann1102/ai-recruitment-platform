// Man danh gia cho ung vien: bao cao /api/finalize, chi so trinh bay giong noi (voice-service) va ghi chu cua AI.
// Chi hien thong tin cho nguoi dung cuoi (khong JSON tho, khong ten truong noi bo).
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (x, d = 1) => (x == null ? "–" : Number(x).toLocaleString("vi-VN", { maximumFractionDigits: d }));
const PHASE_LABEL = { intro: "Giới thiệu", technical: "Kiến thức chuyên môn", scenario: "Tình huống" };
const VERDICT = { exceeds: "Vượt kỳ vọng", meets: "Đạt kỳ vọng", near: "Gần đạt", below: "Chưa đạt" };
const CRITERIA = { technical_accuracy: "Độ chính xác kỹ thuật", completeness: "Độ đầy đủ",
                   extensibility: "Khả năng mở rộng vấn đề", relevance: "Bám sát câu hỏi" };
const PRIORITY = { high: "Ưu tiên cao", medium: "Nên ôn" };
const NOTE_KIND = { hypothesis: "Giả thuyết", to_verify: "Cần kiểm chứng", strength: "Điểm mạnh", risk: "Rủi ro" };
const NOTE_STATUS = { open: "Còn mở", confirmed: "Đã xác nhận", rejected: "Đã bác bỏ" };
const STAT_LABEL = { thinking_time_s: ["Thời gian suy nghĩ", "giây"], answer_duration_s: ["Độ dài câu trả lời", "giây"],
                     speech_rate_spm: ["Tốc độ nói", "âm tiết/phút"], filler_ratio: ["Tỉ lệ từ đệm", "%"] };

// Link tai lieu chi nhan http(s) (chan "javascript:" ...); khac thi hien ten khong co link
const safeUrl = (u) => { try { return ["http:", "https:"].includes(new URL(u).protocol) ? u : ""; } catch { return ""; } };
const bar = (score) => `<span class="bar"><i style="width:${Math.max(0, Math.min(10, score ?? 0)) * 10}%"></i></span>`;
const scoreRow = (label, score) => `<div class="score-row"><span>${esc(label)}</span>${bar(score)}<b>${num(score)}</b></div>`;
const list = (items, line) => `<ul class="clean">${items.map((x) => `<li>${line(x)}</li>`).join("")}</ul>`;
const block = (title, html) => (html ? `<h2>${esc(title)}</h2>${html}` : "");

function renderReport(r, root) {
  const o = r.overall;
  let html = `<div class="overall">
    <div class="overall-score">${o.score == null ? "–" : num(o.score)}<small>/10</small></div>
    <div><span class="chip">${esc(VERDICT[o.verdict] || "Chưa đủ dữ liệu")}</span><p>${esc(o.summary)}</p>
    ${r.level_signal ? `<p class="muted">Bạn có thể thử sức ở level ${esc(r.level_signal.suggested_level)}.</p>` : ""}</div></div>`;
  if (r.status === "partial") html += `<p class="muted">Một phần nhận xét chưa tạo được, kết quả có thể chưa đầy đủ.</p>`;
  html += block("Điểm theo phần", r.sections?.map((s) => scoreRow(PHASE_LABEL[s.phase] || s.phase, s.score)).join(""));
  html += block("Theo tiêu chí", Object.entries(r.criteria || {}).filter(([, v]) => v != null)
    .map(([k, v]) => scoreRow(CRITERIA[k] || k, v)).join(""));
  html += block("Điểm mạnh", r.strengths?.length && list(r.strengths, (x) => esc(x.point)));
  html += block("Cần cải thiện", r.improvements?.length &&
    list(r.improvements, (x) => `<b>${esc(x.point.replace(/[.:;]\s*$/, ""))}</b>${x.why ? `: ${esc(x.why)}` : ""}`));
  html += block("Lộ trình ôn tập", r.study_plan?.length && list(r.study_plan, (x) =>
    `<b>${esc(x.topic)}</b> <span class="chip chip-soft">${esc(PRIORITY[x.priority] || x.priority)}</span>
     ${x.actions?.length ? list(x.actions, esc) : ""}
     ${x.resources?.length ? `<p class="muted">Tài liệu: ${x.resources.map((s) => safeUrl(s.url)
        ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>` : esc(s.title)).join(" · ")}</p>` : ""}`));
  if (r.requirements?.items?.length) {
    html += block("Mức đáp ứng yêu cầu công việc", `<p class="muted">${esc(r.requirements.summary)}</p>` + list(
      r.requirements.items, (x) => `${esc(x.text)} <span class="chip chip-soft">${x.status === "assessed"
        ? esc(VERDICT[x.band] || "") + " · " + num(x.score) : "Chưa được hỏi"}</span>`));
  }
  html += turnDetails(r.turns || []);
  if (r.meta?.disclaimer) html += `<p class="muted disclaimer">${esc(r.meta.disclaimer)}</p>`;
  root.innerHTML = html;
  root.classList.remove("hidden");
}

// Chi tiet tung cau: cau hoi, cau tra loi cua ung vien (lay tu S.turns), diem va nhan xet
function turnDetails(turns) {
  if (!turns.length) return "";
  const mine = Object.fromEntries(S.turns.map((t) => [t.turn_number, t]));
  return `<details class="turns"><summary>Chi tiết từng câu hỏi (${turns.length})</summary>${turns.map((t) => {
    const m = mine[t.turn_number];
    return `<div class="turn"><p class="turn-q">${esc(t.question)}</p>
      ${m ? `<p class="turn-a">${esc(m.answer)}</p>` : ""}
      <p><span class="chip chip-soft">${num(m?.evaluation?.turn_score_10)}/10</span> ${esc(t.comment)}</p></div>`;
  }).join("")}</details>`;
}

function renderVoiceSummary(r, root) {
  let html = `<h2>Cách trình bày khi nói</h2>`;
  if (!r.voice_turns) {
    html += `<p class="muted">Bạn chưa trả lời câu nào bằng giọng nói.</p>`;
  } else {
    html += `<div class="stats">${Object.entries(r.stats).map(([k, s]) => {
      const [label, unit] = STAT_LABEL[k] || [k, ""], f = unit === "%" ? (x) => num(x * 100, 0) : (x) => num(x);
      return `<div class="stat"><span>${esc(label)}</span><b>${f(s.median)} <small>${esc(unit)}</small></b>
        <small class="muted">từ ${f(s.min)} đến ${f(s.max)} · ${esc(s.n)} câu</small></div>`;
    }).join("")}</div>`;
    if (r.notes.length) html += list(r.notes, esc);
    html += `<p class="muted">Các chỉ số này chỉ để bạn tự luyện cách nói, không tính vào điểm kiến thức.</p>`;
  }
  root.innerHTML = html;
  root.classList.remove("hidden");
}

// Ghi chu xuyen chu de cua AI (state.notes): khong dung de tinh diem
function renderNotes(notes, root) {
  if (!notes?.length) { root.classList.add("hidden"); return; }
  root.innerHTML = `<h2>AI đã lưu ý gì trong buổi</h2>` + list(notes, (n) =>
    `<span class="chip chip-soft">${esc(NOTE_KIND[n.kind] || n.kind)}</span> ${esc(n.text)}
     <span class="muted">· câu ${esc(n.turn)} · ${esc(NOTE_STATUS[n.status] || n.status)}</span>`);
  root.classList.remove("hidden");
}

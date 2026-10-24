// Render bao cao /api/finalize cho trang dev /dev/play (chi hien sau khi buoi ket thuc).
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const turnsOf = (list) => (list?.length ? ` <span class="muted">(lượt ${list.join(", ")})</span>` : "");

function listBlock(title, items, line) {
  if (!items?.length) return "";
  return `<h2>${esc(title)}</h2><ul>${items.map((x) => `<li>${line(x)}</li>`).join("")}</ul>`;
}

function renderReport(r, root) {
  const o = r.overall, s = r.session;
  const partial = r.status === "partial" ? ' <span class="warn">· partial (Reporter lỗi, nhận xét là bản mẫu)</span>' : "";
  let html = `<h2>Báo cáo${partial}</h2>
    <div><span class="score">${esc(o.score)}/10</span> · ${esc(o.verdict)} · độ tin cậy ${esc(s.confidence)}
      <span class="muted">· ${esc(s.evaluated_turns)} lượt được chấm · kết thúc: ${esc(s.end_reason)}</span></div>
    <p>${esc(o.summary)}</p>`;
  html += `<h2>Theo phần</h2><table><tr><th>Phần</th><th>Điểm</th><th>Trọng số</th></tr>${r.sections
    .map((x) => `<tr><td>${esc(x.phase)}</td><td>${esc(x.score)}</td><td>${esc(x.weight)}</td></tr>`).join("")}</table>`;
  html += `<h2>Theo tiêu chí</h2><table>${Object.entries(r.criteria)
    .map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("")}</table>`;
  html += listBlock("Điểm mạnh", r.strengths, (x) => esc(x.point) + turnsOf(x.evidence_turns));
  html += listBlock("Cần cải thiện", r.improvements, (x) => `<b>${esc(x.point)}</b>: ${esc(x.why)}` + turnsOf(x.evidence_turns));
  html += listBlock("Lộ trình ôn tập", r.study_plan,
    (x) => `[${esc(x.priority)}] <b>${esc(x.topic)}</b>: ${x.actions.map(esc).join("; ")}`);
  if (r.requirements) {
    html += `<h2>Yêu cầu của JD</h2><p class="muted">${esc(r.requirements.summary)}</p><table>
      <tr><th>Yêu cầu</th><th>Loại</th><th>Trạng thái</th><th>Điểm</th></tr>${r.requirements.items
      .map((x) => `<tr><td>${esc(x.text)}</td><td>${esc(x.kind)}</td><td>${esc(x.status)}</td><td>${esc(x.score ?? "–")}</td></tr>`)
      .join("")}</table>`;
  }
  html += `<h2>Từng lượt</h2><table><tr><th>#</th><th>Câu hỏi</th><th>Điểm</th><th>Nhận xét</th></tr>${r.turns
    .map((t) => `<tr><td>${esc(t.turn_number)}</td><td>${esc(t.question)}</td>
      <td class="muted">${Object.entries(t.scores).map(([k, v]) => `${esc(k)} ${esc(v)}`).join("<br>")}</td>
      <td>${esc(t.comment)}</td></tr>`).join("")}</table>`;
  html += `<p class="muted">${esc(r.meta?.disclaimer)}</p>
    <details><summary>JSON đầy đủ</summary><pre>${esc(JSON.stringify(r, null, 1))}</pre></details>`;
  root.innerHTML = html;
  root.classList.remove("hidden");
  root.scrollIntoView({ block: "start" });
}

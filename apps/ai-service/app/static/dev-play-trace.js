// Bang "Luong he thong" cua trang dev /dev/play: moi request la mot khoi, ghi tung moc theo thoi gian thuc
// (gui request, event meta, token dau, done) va so lieu tung agent lay tu `metadata` ma ai-service tra ve.
const STEPS = {
  "/api/cv/parse": "CV Parser: trích text, redact PII, bỏ dòng nghi injection → LLM ra cv_profile → code hậu kiểm",
  "/api/jd/parse": "JD Parser: làm sạch JD → LLM gán topic trong catalog → code bỏ topic ngoài catalog",
  "/api/start": "Planner lập kế hoạch (LLM, tối đa 2 lần, hạn 22 s) → RAG gắn đoạn tham khảo từ ai_db (nếu bật, hạn 5 s) → Interviewer stream câu hỏi đầu",
  "/api/next-turn": "Evaluator chấm (LLM, hoặc code nếu “không biết”/thao túng) → luật thời gian + 11 luật policy chọn hành động (code) → Interviewer stream câu tiếp",
  "/api/finalize": "Code tính điểm (topic, phase, tiêu chí) → Reporter viết nhận xét (LLM, lỗi thì status=partial)",
};
const AGENT_NAME = { planner: "Planner", evaluator: "Evaluator", interviewer: "Interviewer", reporter: "Reporter",
  query_rewriter: "Query rewriter (RAG)", embedding: "Embedding (RAG)", cv_parser: "CV Parser", jd_parser: "JD Parser" };

function traceStart(path) {
  const box = document.createElement("div");
  box.className = "trace-block";
  box.innerHTML = `<div class="trace-head"><b>POST ${path}</b> <span class="muted">${new Date().toLocaleTimeString()}</span></div>
    <div class="muted trace-plan"></div><ol class="trace-lines"></ol>`;
  box.querySelector(".trace-plan").textContent = STEPS[path] || "";
  $("trace").prepend(box);
  return { box, t0: performance.now() };
}

function traceLine(tr, text, cls) {
  const li = document.createElement("li");
  li.className = cls || "";
  li.textContent = `+${((performance.now() - tr.t0) / 1000).toFixed(2)} s · ${text}`;
  tr.box.querySelector(".trace-lines").appendChild(li);
}

// usage/latency theo agent (metadata cua start, next-turn) hoac metadata 1 lan goi (cv/jd parse)
function traceAgents(tr, m) {
  if (!m) return;
  if (m.latency_ms && typeof m.latency_ms === "object") {
    for (const [agent, ms] of Object.entries(m.latency_ms)) {
      if (agent === "total") continue;
      const u = m.usage?.[agent] || {};
      traceLine(tr, `${AGENT_NAME[agent] || agent}: ${ms} ms` + (u.input_tokens ? ` · ${u.input_tokens}→${u.output_tokens} token` : ""), "agent");
    }
  } else if (m.model) {
    traceLine(tr, `${m.model} · ${m.latency_ms} ms · ${m.input_tokens}→${m.output_tokens} token · prompt ${m.prompt_version}`, "agent");
  }
  for (const f of m.fallbacks || []) traceLine(tr, `fallback: ${f}`, "warn");
}

function tracePlan(tr, plan) {
  for (const ph of plan.phases) {
    const topics = ph.topics.map((t) => `${t.title}${t.reference_snippets?.length ? ` [${t.reference_snippets.length} đoạn RAG]` : ""}`);
    traceLine(tr, `${ph.phase} (${ph.time_budget_min} phút): ${topics.join("; ")}`);
  }
}

function traceTurn(tr, done, showScores) {
  const ev = done.evaluation, turn = done.turn, st = done.state;
  if (ev) traceLine(tr, showScores ? `Evaluator: ${ev.answer_type} · ${ev.turn_score_10}/10${ev.degraded ? " · degraded (không tính điểm)" : ""}`
                                   : `Evaluator: ${ev.answer_type}${ev.degraded ? " · degraded" : ""} (điểm ẩn, bật debug để xem)`);
  if (turn?.reasoning) traceLine(tr, `Policy: ${turn.reasoning} · độ khó ${turn.difficulty}`);
  if (turn) traceLine(tr, `Interviewer: câu ${turn.turn_number} (${turn.turn_kind}), nguồn ${turn.question_source}`);
  if (st) traceLine(tr, `State: phase ${st.phase} · lượt ${st.turn_count} · follow-up ${st.counters?.follow_ups ?? 0}, hint ${st.counters?.hints ?? 0}`);
  if (done.session_end) traceLine(tr, `Kết thúc phiên: ${st?.end_reason || "plan_complete"}`, "warn");
}

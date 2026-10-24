// Trang dev /dev/play: dong vai interview-service (giu plan/state/turns giua cac luot) va goi API that cua ai-service.
// Luong: [cv/parse] [jd/parse] -> start (SSE) -> next-turn (SSE) ... -> finalize. Bao cao render o dev-play-report.js,
// bang "Luong he thong" o dev-play-trace.js, goi HTTP/SSE o dev-play-api.js.
const $ = (id) => document.getElementById(id);
const ACTION_TAG = { hint: "gợi ý", clarify: "hỏi lại", follow_up: "hỏi sâu", wrap_up: "kết thúc", ask_main: "câu chính" };
let S = null; // phien hien tai

function bubble(cls, text) {
  const div = document.createElement("div");
  div.className = `msg ${cls}`;
  div.innerHTML = '<span class="tag"></span><span class="body"></span><span class="debug hidden"></span>';
  div.querySelector(".body").textContent = text || "";
  $("log").appendChild(div);
  div.scrollIntoView({ block: "end" });
  return div;
}

function setDebug(div, text) {
  if (!$("showEval").checked || !text) return;
  const d = div.querySelector(".debug");
  d.textContent = text;
  d.classList.remove("hidden");
}

function topicTitle(topicId) {
  for (const ph of (S.plan?.phases || [])) for (const t of ph.topics) if (t.id === topicId) return t.title;
  return "";
}

function elapsedSeconds(answer) {
  if ($("clock").value === "real") return Math.round((Date.now() - S.startedAt) / 1000);
  S.simElapsed += Math.round(30 + 0.4 * answer.trim().split(/\s+/).length);
  return S.simElapsed;
}

// Stream mot cau hoi cua AI vao bubble moi; tra event done.
async function streamQuestion(path, body) {
  const div = bubble("ai");
  const tr = traceStart(path);
  traceLine(tr, "đã gửi request, đang chờ event đầu tiên…");
  S.liveBubble = div;
  const text = div.querySelector(".body");
  const started = performance.now();
  let ttft = null;
  let done;
  try {
    done = await postSse(path, body, (name, d) => {
      if (name === "meta") {
        div.querySelector(".tag").textContent = `${d.phase} · topic ${d.topic_index}/${d.topic_total} · ${ACTION_TAG[d.action] || d.action}`;
        traceLine(tr, `meta: ${path === "/api/start" ? "Planner + RAG xong" : "Evaluator + policy xong"} → ${d.action}, ${d.phase}, topic ${d.topic_index}/${d.topic_total}; Interviewer bắt đầu viết`);
      }
      if (name === "token") {
        if (ttft === null) { ttft = performance.now() - started; traceLine(tr, "token đầu tiên từ Interviewer"); }
        text.textContent += d.t;
      }
      if (name === "replace") {
        ttft ??= performance.now() - started;
        traceLine(tr, "replace: câu hỏi bị thay (lỗi stream, vi phạm kiểm tra, hoặc bỏ markdown)", "warn");
        text.textContent = d.question;
      }
      if (name === "done") traceLine(tr, "done");
      div.scrollIntoView({ block: "end" });
    });
  } catch (err) {
    traceLine(tr, err.message, "error");
    throw err;
  }
  traceAgents(tr, done.metadata);
  if (done.plan) tracePlan(tr, done.plan);
  traceTurn(tr, done, $("showEval").checked);
  S.liveBubble = null;
  if (!done.turn) { div.remove(); return done; } // phien ket thuc, khong co cau hoi
  text.textContent = done.question;
  if (done.plan) S.plan = done.plan; // /api/start: plan chi co trong done
  const title = topicTitle(done.turn.topic_id);
  if (title) div.querySelector(".tag").textContent += ` · ${title}`;
  const m = done.metadata || {};
  setDebug(div, `nguồn: ${done.turn.question_source} · độ khó ${done.turn.difficulty} · token đầu ${Math.round(ttft || 0)} ms` +
    ` · tổng ${m.latency_ms?.total ?? "?"} ms` + (m.fallbacks?.length ? ` · fallback: ${m.fallbacks.join(", ")}` : "") +
    (done.turn.reasoning ? `\n${done.turn.reasoning}` : ""));
  S.calls.push({ path, metadata: m });
  return done;
}

function setBusy(busy, status) {
  for (const id of ["sendBtn", "endBtn", "answer"]) $(id).disabled = busy;
  $("chatStatus").textContent = status || "";
  $("chatStatus").className = "status";
}

function showError(where, err) {
  $(where).textContent = err.message;
  $(where).className = "status error";
}

async function startSession() {
  $("startBtn").disabled = true;
  const track = $("track").value, level = $("level").value;
  S = { sid: `dev-${Date.now()}`, track, level, duration: Number($("duration").value), turns: [], history: {},
        calls: [], simElapsed: 0, cv: null, jd: null };
  try {
    if ($("cv").files[0]) {
      $("setupStatus").textContent = "Đang phân tích CV…";
      const form = new FormData();
      form.append("file", $("cv").files[0]);
      form.append("track", track);
      S.cv = (await postJson("/api/cv/parse", form, true)).cv_profile;
    }
    if ($("jd").value.trim()) {
      $("setupStatus").textContent = "Đang phân tích JD…";
      S.jd = (await postJson("/api/jd/parse", { track, jd_text: $("jd").value.trim() })).jd_profile;
    }
    $("setupStatus").textContent = "Đang lập kế hoạch phỏng vấn…";
    $("setup").classList.add("hidden");
    $("chat").classList.remove("hidden");
    setBusy(true, "AI đang chuẩn bị câu hỏi…");
    S.startedAt = Date.now();
    const done = await streamQuestion("/api/start", { session_id: S.sid, track, level, duration_minutes: S.duration,
                                                      cv_profile: S.cv, jd_profile: S.jd });
    Object.assign(S, { plan: done.plan, state: done.state, question: done.question, turn: done.turn });
    $("progress").textContent = `${track} · ${level} · ${S.duration} phút` + (S.cv ? " · có CV" : "") + (S.jd ? " · có JD" : "");
    setBusy(false);
    $("answer").focus();
  } catch (err) {
    S.liveBubble?.remove();
    $("setup").classList.remove("hidden");
    $("chat").classList.add("hidden");
    $("startBtn").disabled = false;
    showError("setupStatus", err);
  }
}

async function sendAnswer() {
  const answer = $("answer").value.trim();
  if (!answer) return;
  const turn = S.turn;
  S.pending = { answer, me: bubble("me", answer), body: {
    session_id: S.sid, level: S.level, track: S.track, plan: S.plan, state: S.state, turn_number: turn.turn_number,
    question: S.question, turn_kind: turn.turn_kind, answer, elapsed_seconds: elapsedSeconds(answer),
    topic_turns: (S.history[turn.topic_id] || []).slice(-5) } };
  $("answer").value = "";
  await runNextTurn();
}

async function runNextTurn() {
  const { answer, me, body } = S.pending, turn = S.turn;
  $("retryBtn").classList.add("hidden");
  setBusy(true, "AI đang chấm và chọn câu tiếp theo…");
  try {
    const done = await streamQuestion("/api/next-turn", body);
    const ev = done.evaluation;
    S.turns.push({ turn_number: turn.turn_number, phase: turn.phase, topic_id: turn.topic_id, turn_kind: turn.turn_kind,
                   difficulty: turn.difficulty, question: S.question, answer, evaluation: ev });
    (S.history[turn.topic_id] ||= []).push({ q: S.question, a: answer });
    if (ev) setDebug(me, `điểm lượt ${ev.turn_score_10}/10 · ${ev.answer_type}${ev.degraded ? " · degraded" : ""}` +
      (ev.covered_points.length ? `\nđã nêu: ${ev.covered_points.join("; ")}` : "") +
      (ev.missing_points.length ? `\nthiếu: ${ev.missing_points.join("; ")}` : ""));
    S.state = done.state;
    S.pending = null;
    if (done.session_end) return finalizeSession();
    Object.assign(S, { question: done.question, turn: done.turn });
    setBusy(false);
    $("answer").focus();
  } catch (err) {
    S.liveBubble?.remove();
    setBusy(false);
    $("sendBtn").disabled = true;
    $("retryBtn").classList.remove("hidden");
    showError("chatStatus", err);
  }
}

async function finalizeSession(byCandidate) {
  setBusy(true, "Đang viết báo cáo…");
  $("retryBtn").classList.add("hidden");
  if (byCandidate) S.state.end_reason = "candidate_ended";
  if (!S.turns.length) {
    setBusy(true, "Đã kết thúc trước khi trả lời câu nào, không có báo cáo.");
    return showEnd();
  }
  try {
    const durationS = $("clock").value === "real" ? Math.round((Date.now() - S.startedAt) / 1000) : S.simElapsed;
    S.report = await postJson("/api/finalize", { session_id: S.sid, track: S.track, level: S.level, plan: S.plan,
      state: S.state, end_reason: S.state.end_reason || "plan_complete", duration_s: durationS, turns: S.turns,
      jd_profile: S.jd });
    $("answerBox").classList.add("hidden");
    renderReport(S.report, $("report"));
    showEnd();
  } catch (err) {
    showError("chatStatus", err);
    $("endBtn").disabled = false;
  }
}

function showEnd() {
  $("downloadBtn").classList.remove("hidden");
  $("resetBtn").classList.remove("hidden");
}

function download() {
  const data = { session_id: S.sid, track: S.track, level: S.level, plan: S.plan, turns: S.turns, report: S.report || null, calls: S.calls };
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 1)], { type: "application/json" }));
  a.download = `${S.sid}.json`;
  a.click();
}

for (const t of window.TRACKS) $("track").add(new Option(t, t));
$("startBtn").onclick = startSession;
$("sendBtn").onclick = sendAnswer;
$("retryBtn").onclick = runNextTurn;
$("endBtn").onclick = () => finalizeSession(true);
$("downloadBtn").onclick = download;
$("resetBtn").onclick = () => location.reload();
$("answer").addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) sendAnswer(); });

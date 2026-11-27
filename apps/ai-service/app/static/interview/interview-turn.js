// Vong hoi dap cua man phong van (khung chat): stream cau hoi tu /api/start, /api/next-turn (SSE) vao bong chat AI,
// thanh tien do theo chu de, dong ho dem nguoc, gui cau tra loi, gui lai khi loi, nhan y muon dung cua ung vien.
const ACTION_LABEL = { hint: "Gợi ý", clarify: "Hỏi lại", follow_up: "Hỏi thêm", wrap_up: "Kết thúc" };
let clockTimer = null;

const elapsedSeconds = () => Math.round((Date.now() - S.startedAt) / 1000);
const RETRYABLE = new Set(["turn_in_progress", "session_store_unavailable"]);
// Gui lai dung body co ich khi: loi mang / stream, 5xx, hoac ma tam thoi; con lai (4xx) thi khong
const canRetry = (err) => err instanceof TypeError || err.stream || RETRYABLE.has(err.code) || (err.status ?? 500) >= 500;

// Y muon dung cua ung vien (noi hoac go): Evaluator cua ai-service chua co loai "muon dung" (chi 6 loai cau tra loi)
// nen trang nhan cau NGAN va hoi xac nhan; chon "khong" thi gui nhu cau tra loi binh thuong. Chi nhan khi:
// - co doi tuong la buoi phong van ("dung phong van", "khong muon tra loi nua"), hoac
// - ca cau chi la loi dung ("Dung lai", "Em xin dung o day"): "timer dung ngay", "cho dung container" khong tinh.
// Khong dung \b: JS coi chu co dau (vd "ề") la ranh gioi tu.
const STOP_SESSION = /(dừng|ngừng|kết thúc|nghỉ|bỏ)( lại)?( cuộc| buổi)? phỏng vấn|không (muốn )?(phỏng vấn|trả lời|tiếp tục phỏng vấn|tiếp tục buổi này) nữa/;
const STOP_ALONE = /^(((em|tôi|mình|cho (em|tôi|mình)) )?(xin |muốn )?)?(thôi )?(dừng|ngừng|nghỉ|kết thúc)( lại| ở đây| tại đây| luôn| đi| nhé| ạ| thôi| ngay| buổi này)*$/;
const normSpeech = (t) => t.toLowerCase().normalize("NFC").replace(/[.,!?;:…"“”'()-]/g, " ").replace(/\s+/g, " ").trim();
const wantsToStop = (text) => {
  const t = normSpeech(text);
  return t.length <= 160 && (STOP_SESSION.test(t) || STOP_ALONE.test(t));
};

// Thanh tien do theo CHU DE, khong phai so cau: moi chu de co the co cau hoi them / goi y / hoi lai.
// Tran so luot = max(8, round(24 * phut / 30)) theo app/time_budget.py (15 phut -> 12 luot)
function renderProgress(index, total, turnNumber) {
  const bars = $("progressBars");
  bars.innerHTML = "";
  for (let i = 1; i <= total; i += 1) bars.appendChild(Object.assign(document.createElement("i"), { className: i <= index ? "done" : "" }));
  const cap = Math.max(8, Math.round((24 * S.duration) / 30));
  $("progressCount").textContent = `Chủ đề ${index}/${total}` + (turnNumber ? ` · câu ${turnNumber}/${cap}` : "");
  S.progress = { index, total };
}

function topicTitle(topicId, plan) {
  for (const ph of (plan || S.plan)?.phases || []) for (const t of ph.topics) if (t.id === topicId) return t.title;
  return "";
}

function startClock() {
  const tick = () => { $("timerText").textContent = fmtClock(Math.max(0, S.duration * 60 - elapsedSeconds())); };
  tick();
  clockTimer = setInterval(tick, 1000);
}

function stopClock() { clearInterval(clockTimer); }

// Nut "Ket thuc" luon bam duoc (dung cung): ket qua dang ve sau khi ket thuc bi bo qua nho co S.ended
function setBusy(busy, text) {
  for (const id of ["sendBtn", "micBtn", "answer", "typeBtn", "replayBtn"]) $(id).disabled = busy;
  setStatus("chatStatus", text);
}

// Stream mot cau hoi vao bong chat AI moi; tra event done (khong co turn khi buoi ket thuc thi bo bong)
async function streamQuestion(path, body) {
  const bubble = addBubble("ai", ""), text = bubbleBody(bubble), log = $("chatLog");
  let done, meta = null;
  log.setAttribute("aria-busy", "true"); // trinh doc man hinh doc ca cau khi xong, khong doc tung manh dang stream
  try {
    done = await postSse(path, body, (name, d) => {
      if (S.ended) return;
      if (name === "meta") { meta = d; renderProgress(d.topic_index, d.topic_total); }
      if (name === "token") { text.textContent += d.t; scrollChatEnd(false); }
      if (name === "replace") text.textContent = d.question;
    });
  } catch (err) {
    bubble.remove(); // cau hoi dang viet do: bo, gui lai se viet lai
    throw err;
  } finally {
    log.removeAttribute("aria-busy");
  }
  if (!done.turn || S.ended) { bubble.remove(); return done; }
  const parts = [AI_TAG, PHASE_LABEL[meta?.phase || done.turn.phase], topicTitle(done.turn.topic_id, done.plan),
                 ACTION_LABEL[meta?.action]];
  setBubble(bubble, done.question, parts.filter(Boolean).join(" · "));
  return done;
}

const voiceReady = () => Boolean(V.stream && V.svcOk);

// Che do go chu: hien o go + nut Gui; mac dinh tra loi bang giong noi, dung ghi la tu gui.
// Nut doi che do chi hien khi giong noi dung duoc; lua chon cua ung vien giu qua cac cau (S.preferTyping)
function setTyping(on) {
  $("answer").classList.toggle("hidden", !on);
  $("sendBtn").classList.toggle("hidden", !on);
  $("typeBtn").textContent = on ? "Trả lời bằng giọng nói" : "Gõ thay vì nói";
  $("typeBtn").classList.toggle("hidden", on && !voiceReady());
  if (on) { stopSpeaking(); $("answer").focus(); }
}

function toggleTyping() {
  S.preferTyping = $("answer").classList.contains("hidden");
  setTyping(S.preferTyping);
  setRecStatus(S.preferTyping ? "" : "Bấm micro để trả lời");
}

// Cau hoi moi da ve (bong AI da co): reset o go, doc bang TTS
function showQuestion(done) {
  if (S.ended) return;
  Object.assign(S, { question: done.question, turn: done.turn });
  if (S.progress) renderProgress(S.progress.index, S.progress.total, done.turn.turn_number);
  $("answer").value = "";
  const typing = S.preferTyping || !voiceReady(); // khong co micro / dich vu giong noi: mo san o go chu
  setTyping(typing);
  setBusy(false);
  setRecorderState("idle");
  setRecStatus(typing ? "" : "Bấm micro để trả lời");
  speakQuestion(done.question);
  scrollChatEnd(); // trang thai thanh micro doi chieu cao sau khi co cau hoi
}

async function startInterview() {
  showScreen("screenQuestion");
  $("chatLog").innerHTML = "";
  setBusy(true, "AI đang chuẩn bị buổi phỏng vấn cho bạn…");
  S.startedAt = Date.now();
  startClock();
  try {
    const done = await streamQuestion("/api/start", { session_id: S.sid, track: S.track, level: S.level,
      duration_minutes: S.duration, cv_profile: S.cv, jd_profile: S.jd });
    S.plan = done.plan;
    S.state = done.state;
    showQuestion(done);
  } catch (err) {
    if (S.ended) return;
    stopClock();
    showScreen("screenSetup");
    setStatus("setupStatus", `Chưa bắt đầu được buổi phỏng vấn. ${friendlyError(err)}`, "error");
  }
}

// Nut Gui / Ctrl+Enter o che do go chu: cau go thanh bong chat chi doc, o go xoa
async function sendAnswer() {
  if ($("sendBtn").disabled || $("sendBtn").classList.contains("hidden")) return; // dang ghi / dang cho / gui lai
  const answer = $("answer").value.trim();
  if (!answer) return setStatus("chatStatus", "Bạn chưa nhập câu trả lời.", "warn");
  $("answer").value = "";
  await submitTurn(answer, "text", null, addBubble("me", answer, "Bạn · gõ chữ"));
}

// Gui mot luot: tu ban ghi giong noi (interview-voice.js goi ngay sau STT) hoac tu o go chu. bubble = bong cua luot
async function submitTurn(answer, source, metrics, bubble) {
  if (S.ended) return;
  if (wantsToStop(answer)) {
    setBusy(true);
    const stop = await askConfirm({ title: "Bạn muốn dừng buổi phỏng vấn?",
      text: "Mình nghe như bạn muốn kết thúc. Bạn có thể dừng ngay và xem đánh giá cho các câu đã trả lời.",
      ok: "Kết thúc & xem đánh giá", cancel: "Không, đây là câu trả lời của tôi" });
    if (S.ended) return; // da bam "Ket thuc" o noi khac trong luc hop mo
    if (stop) {
      addBubbleNote(bubble, "Bạn đã dừng buổi phỏng vấn.");
      return finalizeSession(true);
    }
  }
  stopSpeaking();
  // Tu phase 04 (PR #117) ai-service giu plan / state / cau hoi / topic_turns trong checkpoint phien: request chi gom
  // phan moi cua luot (khoa thua bi 422). voice: khong gui stt_confidence (Blaze khong co)
  const voice = { answer_source: source };
  S.pending = { answer, voice, metrics, bubble, body: {
    session_id: S.sid, turn_number: S.turn.turn_number, answer, elapsed_seconds: elapsedSeconds(), ...voice } };
  await runNextTurn();
}

async function runNextTurn() {
  const { answer, voice, metrics, bubble, body } = S.pending, turn = S.turn;
  $("retryBtn").classList.add("hidden");
  setBusy(true, "AI đang nghe câu trả lời của bạn…");
  try {
    const done = await streamQuestion("/api/next-turn", body);
    if (S.ended) return; // da ket thuc trong luc AI xu ly: bao cao da chay voi cac luot truoc, bo luot nay
    S.turns.push({ turn_number: turn.turn_number, phase: turn.phase, topic_id: turn.topic_id, turn_kind: turn.turn_kind,
                   difficulty: turn.difficulty, question: S.question, answer, evaluation: done.evaluation });
    if (voice.answer_source === "voice" && metrics) S.voiceMetrics.push(metrics);
    S.state = done.state;
    S.pending = null;
    if (done.session_end) return finalizeSession(false);
    showQuestion(done);
  } catch (err) {
    if (S.ended) return;
    setBusy(false);
    setRecorderState("idle");
    if (err.code?.startsWith("voice_")) { // ai-service khong tinh luot (vd chi co tu dem): noi lai
      S.pending = null;
      markRejected(bubble, "Câu này chưa được ghi nhận, bạn trả lời lại nhé.");
      setStatus("chatStatus", "");
      return voiceRejected(err);
    }
    if (!canRetry(err)) { // gui lai cung noi dung se loi y het: noi / go lai hoac ket thuc
      S.pending = null;
      markRejected(bubble, "Câu này chưa gửi được.");
      if (voice.answer_source === "text") { $("answer").value = answer; setTyping(true); }
      return setStatus("chatStatus", friendlyError(err), "error");
    }
    $("sendBtn").disabled = $("micBtn").disabled = true; // cho gui lai dung noi dung cu (ai-service tra lai neu da xong)
    $("retryBtn").classList.remove("hidden");
    setStatus("chatStatus", friendlyError(err), "error");
  }
}

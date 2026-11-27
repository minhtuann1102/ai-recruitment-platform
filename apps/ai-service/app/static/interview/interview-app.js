// Man phong van bang giong noi (ai-service + voice-service that). Trang giu plan/state/turns giua cac luot
// (dong vai interview-service). Thu tu man: setup -> permission -> question (chat) -> result (danh gia).
// API o interview-api.js, giong noi interview-voice.js, khung chat interview-chat.js, vong hoi dap interview-turn.js,
// man danh gia interview-report.js + interview-result.js.
let S = null; // buoi phong van hien tai
const LEVELS = { fresher: "Fresher", junior: "Junior", middle: "Middle", senior: "Senior" };

function showScreen(id) {
  for (const s of document.querySelectorAll(".screen")) s.classList.toggle("hidden", s.id !== id);
  $("timer").classList.toggle("hidden", id !== "screenQuestion");
  window.scrollTo(0, 0);
}

function setStatus(id, text, cls) {
  $(id).textContent = text || "";
  $(id).className = `status ${cls || ""} ${$(id).classList.contains("center") ? "center" : ""}`;
}

function setToggle(id, on) { $(id).setAttribute("aria-checked", String(on)); }

// Thuat ngu goi y cho STT theo track; loi thi van chay (STT nhan kem thuat ngu hon, khong hong luong)
async function loadPhrases(track) {
  try {
    return (await getJson(`/api/stt/phrases?track=${encodeURIComponent(track)}`)).phrases || [];
  } catch {
    return [];
  }
}

async function submitSetup() {
  const track = $("track").value, level = $("level").value;
  if (!track) return setStatus("setupStatus", "Bạn chọn vị trí muốn luyện phỏng vấn trước nhé.", "warn");
  $("setupNext").disabled = true;
  S = { sid: `web-${crypto.randomUUID()}`, track, level, duration: Number($("duration").value), turns: [],
        cv: null, jd: null, voiceMetrics: [], phrases: [], summary: null, report: null };
  try {
    if ($("cv").files[0]) {
      setStatus("setupStatus", "Đang đọc CV của bạn…");
      const form = new FormData();
      form.append("file", $("cv").files[0]);
      form.append("track", track);
      S.cv = (await postJson("/api/cv/parse", form, true)).cv_profile;
    }
    if ($("jd").value.trim()) {
      setStatus("setupStatus", "Đang đọc mô tả công việc…");
      S.jd = (await postJson("/api/jd/parse", { track, jd_text: $("jd").value.trim() })).jd_profile;
    }
    S.phrases = await loadPhrases(track);
    setStatus("setupStatus", "");
    showScreen("screenPermission");
    checkVoiceService();
  } catch (err) {
    setStatus("setupStatus", friendlyError(err), "error");
  } finally {
    $("setupNext").disabled = false;
  }
}

async function enableMic() {
  if (V.stream) return;
  try {
    await micEnable();
    setToggle("micToggle", true);
    setStatus("permStatus", "");
  } catch {
    setStatus("permStatus", "Trình duyệt chưa cho dùng micro. Bấm biểu tượng ổ khoá trên thanh địa chỉ để cho phép, "
              + "hoặc bắt đầu và trả lời bằng cách gõ.", "warn");
  }
  updateStartLabel();
}

async function checkVoiceService() {
  $("svcText").textContent = "Đang kiểm tra…";
  await voiceHealth();
  setToggle("svcToggle", V.svcOk);
  $("svcText").textContent = V.svcOk ? "Sẵn sàng" : "Chưa sẵn sàng. Bấm công tắc để kiểm tra lại.";
  updateStartLabel();
}

// Khong co micro / dich vu giong noi van bat dau duoc: tra loi bang cach go
function updateStartLabel() {
  $("permNext").textContent = V.stream && V.svcOk ? "Bắt đầu phỏng vấn" : "Bắt đầu (trả lời bằng chữ)";
}

async function endByButton() {
  const ok = await askConfirm({ title: "Kết thúc buổi phỏng vấn?",
    text: S.turns.length ? "AI sẽ tổng hợp đánh giá cho các câu bạn đã trả lời." : "Bạn chưa trả lời câu nào nên sẽ chưa có đánh giá.",
    ok: "Kết thúc & xem đánh giá", cancel: "Tiếp tục phỏng vấn" });
  if (ok) finalizeSession(true);
}

for (const t of window.TRACKS) $("track").add(new Option(t.title, t.id));
for (const [v, label] of Object.entries(LEVELS)) $("level").add(new Option(label, v, false, v === "junior"));
$("cv").onchange = () => { $("cvName").textContent = $("cv").files[0]?.name || "Chưa chọn tệp"; };
$("setupNext").onclick = submitSetup;
$("micToggle").onclick = enableMic;
$("svcToggle").onclick = checkVoiceService;
$("permBack").onclick = () => showScreen("screenSetup");
$("permNext").onclick = startInterview;
$("micBtn").onclick = toggleRecording;
$("sendBtn").onclick = sendAnswer;
$("retryBtn").onclick = runNextTurn;
$("endBtn").onclick = endByButton;
$("replayBtn").onclick = () => speakQuestion(S.question);
$("typeBtn").onclick = toggleTyping;
$("finalizeRetryBtn").onclick = () => finalizeSession(false);
$("resetBtn").onclick = () => location.reload();
$("answer").addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) sendAnswer(); });

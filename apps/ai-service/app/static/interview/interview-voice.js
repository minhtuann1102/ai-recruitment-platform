// Giong noi cho man phong van: TTS + STT that qua proxy /dev/voice/* (ai-service -> voice-service -> Blaze).
// Ghi am bang MediaRecorder (webm/opus); bam dung -> STT ca file (contract 015) -> TU GUI ban ghi lam cau tra loi
// (khong cho sua: ung vien tra loi bang giong noi nhu phong van that; muon go chu thi bam "Go thay vi noi").
// Blaze khong tra do tin cay nen luot voice gui answer_source=voice, khong kem stt_confidence (cong confidence bo qua).
const MAX_REC_S = 180; // Blaze tinh phi ca file: tu dung o 3 phut, ngan hon VOICE_MAX_AUDIO_S (300 s)
const V = { stream: null, recorder: null, chunks: [], recStartedAt: null, questionEndedAt: null, audio: new Audio(),
            speakSeq: 0, svcOk: false, recTimer: null };

function setRecStatus(text, cls) {
  $("recStatus").textContent = text || "";
  $("recStatus").className = `status center ${cls || ""}`;
}

const fmtClock = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

// Bat micro (sau thao tac cua nguoi dung) va chay thanh muc am o goc man hinh
async function micEnable() {
  V.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  const ctx = new AudioContext(), an = ctx.createAnalyser();
  an.fftSize = 512;
  ctx.createMediaStreamSource(V.stream).connect(an);
  const buf = new Uint8Array(an.fftSize), bars = document.querySelectorAll("#micBars i");
  setInterval(() => {
    an.getByteTimeDomainData(buf);
    let peak = 0;
    for (const v of buf) peak = Math.max(peak, Math.abs(v - 128));
    const level = Math.min(4, Math.ceil(peak / 12));
    bars.forEach((b, i) => b.classList.toggle("on", i < level));
  }, 120);
}

async function voiceHealth() {
  let h;
  try {
    const resp = await fetch("/dev/voice/health", { headers: headers(false) });
    h = await resp.json();
    if (!resp.ok) h = { status: "error", provider: null, message: h.message || `${resp.status}` };
  } catch (err) {
    h = { status: "error", provider: null, message: err.message };
  }
  V.svcOk = h.status === "ok" && h.provider === "blaze";
  document.querySelectorAll("#svcBars i").forEach((b) => b.classList.toggle("on", V.svcOk));
  return h;
}

// Doc cau hoi bang TTS. Khong doc duoc thi coi nhu cau hoi "doc xong" luc hien chu (moc tinh thoi gian suy nghi)
async function speakQuestion(text) {
  if (V.recorder || S?.ended) return; // dang ghi am: khong doc chen vao ban ghi; buoi da ket thuc: im lang
  stopSpeaking();
  V.questionEndedAt = null;
  const seq = ++V.speakSeq;
  if (!V.svcOk || !text || text.length > 1000) {
    V.questionEndedAt = Date.now();
    if (!V.svcOk) setRecStatus("Chưa dùng được giọng nói lúc này. Bạn đọc câu hỏi ở trên và gõ câu trả lời bên dưới.", "warn");
    return;
  }
  try {
    setRecStatus("AI đang đọc câu hỏi…");
    const resp = await fetch("/dev/voice/speak", { method: "POST", headers: headers(true), body: JSON.stringify({ text }) });
    if (!resp.ok) throw await apiError(resp);
    const blob = await resp.blob();
    if (seq !== V.speakSeq) return; // da bam ghi am / sang cau khac trong luc tai: bo, khong doc chen
    if (V.audio.src) URL.revokeObjectURL(V.audio.src);
    V.audio.src = URL.createObjectURL(blob);
    V.audio.onended = () => { V.questionEndedAt = Date.now(); setRecStatus("Bấm micro để trả lời"); };
    await V.audio.play();
  } catch {
    if (seq !== V.speakSeq) return;
    V.questionEndedAt = Date.now();
    setRecStatus("Chưa phát được tiếng câu hỏi. Bạn đọc câu hỏi ở trên rồi bấm micro để trả lời.", "warn");
  }
}

// Dung doc (bam ghi am, gui, ket thuc): moc "doc xong" = luc dung neu chua co
function stopSpeaking() {
  V.speakSeq += 1;
  if (!V.audio.paused) V.audio.pause();
  V.questionEndedAt ??= Date.now();
}

function setRecorderState(state) {
  $("micBtn").classList.toggle("recording", state === "recording");
  $("micBtn").classList.toggle("busy", state === "busy");
  $("micBtn").disabled = state === "busy";
  // dang ghi / dang chuyen chu: khong gui, khong doc lai cau hoi (doc lai se lot vao ban ghi va lech moc thoi gian)
  for (const id of ["sendBtn", "replayBtn", "typeBtn"]) $(id).disabled = state !== "idle";
}

function toggleRecording() {
  if (V.recorder) return V.recorder.stop();
  if (!V.stream) {
    setTyping(true);
    return setRecStatus("Micro chưa được bật, bạn gõ câu trả lời bên dưới nhé.", "warn");
  }
  stopSpeaking();
  setStatus("chatStatus", ""); // xoa canh bao cu (vd bam Gui khi chua co cau tra loi)
  const mime = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm"].find((t) => MediaRecorder.isTypeSupported(t));
  const rec = new MediaRecorder(V.stream, mime ? { mimeType: mime } : {});
  V.chunks = [];
  rec.ondataavailable = (e) => { if (e.data.size) V.chunks.push(e.data); };
  rec.onstop = () => onRecorded(rec.mimeType);
  V.recStartedAt = Date.now();
  V.recTurn = S.turn?.turn_number; // ket qua STT ve muon (luot da doi) thi bo, khong ghi vao cau hoi moi
  rec.start();
  V.recorder = rec;
  setRecorderState("recording");
  setRecStatus("Đang ghi 00:00 · bấm micro lần nữa để dừng và gửi");
  V.recTimer = setInterval(() => {
    const s = Math.round((Date.now() - V.recStartedAt) / 1000);
    setRecStatus(`Đang ghi ${fmtClock(s)} · bấm micro lần nữa để dừng và gửi`);
    if (s >= MAX_REC_S) V.recorder?.stop();
  }, 500);
}

// Huy lan ghi dang do (gui / ket thuc buoi): khong chuyen thanh chu
function abortRecording() {
  if (!V.recorder) return;
  V.recorder.onstop = null;
  V.recorder.stop();
  clearInterval(V.recTimer);
  V.recorder = null;
  setRecorderState("idle");
}

async function onRecorded(mime) {
  clearInterval(V.recTimer);
  V.recorder = null;
  const blob = new Blob(V.chunks, { type: mime || "audio/webm" });
  setRecorderState("busy");
  setRecStatus("Đang chuyển giọng nói thành chữ…");
  // stale: buoi da ket thuc / luot da doi / dang gui luot khac -> bo ket qua STT, khong gui them luot
  const turn = V.recTurn, stale = () => S.ended || turn !== S.turn?.turn_number || S.pending;
  const bubble = addBubble("me", "Đang chuyển giọng nói thành chữ…", "Bạn · giọng nói");
  bubble.classList.add("pending");
  try {
    const r = await transcribe(blob);
    if (stale()) return bubble.remove(); // ban ghi cua luot cu: khong hien vao luot moi
    if (r.no_speech) {
      bubble.remove();
      return setRecStatus("Không nghe thấy tiếng nói. Kiểm tra micro rồi ghi lại, hoặc gõ câu trả lời.", "warn");
    }
    bubble.classList.remove("pending");
    setBubble(bubble, r.transcript, "Bạn · giọng nói");
    addBubbleNote(bubble, deliveryLine(r.metrics));
    setRecStatus("");
    // ban ghi gui nguyen van, khong cho sua. Khong await: S.pending dat dong bo -> finally thay stale, bo qua
    submitTurn(r.transcript, "voice", r.metrics, bubble);
  } catch (err) {
    bubble.remove();
    if (stale()) return;
    if (err instanceof TypeError || (err.status ?? 0) >= 502) { // dich vu giong noi sap giua buoi: chuyen sang go chu
      V.svcOk = false;
      document.querySelectorAll("#svcBars i").forEach((b) => b.classList.remove("on"));
      setTyping(true);
      setRecStatus("Dịch vụ giọng nói đang gặp sự cố, bạn gõ câu trả lời bên dưới nhé.", "warn");
    } else {
      setRecStatus(friendlyError(err), "error");
    }
  } finally {
    if (!stale()) setRecorderState("idle"); // luot da doi / dang gui: trang thai nut do luong hoi dap quyet
  }
}

async function transcribe(blob) {
  const form = new FormData();
  form.append("audio", blob, blob.type.includes("ogg") ? "answer.ogg" : "answer.webm");
  form.append("consent_confirmed", "true"); // dong y o buoc cap quyen (bat micro = dong y xu ly giong noi)
  for (const k of S.phrases) form.append("keywords", k);
  if (V.questionEndedAt) form.append("question_audio_ended_at", String(V.questionEndedAt));
  form.append("recording_started_at", String(V.recStartedAt));
  if (S.turn?.topic_id) form.append("topic_id", S.turn.topic_id.slice(0, 64));
  form.append("language", "vi");
  return postJson("/dev/voice/transcribe", form, true);
}

// Chi so trinh bay cua luot (FR-006 spec 015) hien duoi bong; chi so rong thi bo qua
function deliveryLine(m) {
  if (!m) return "";
  const parts = [];
  if (m.thinking_time_s != null) parts.push(`Suy nghĩ ${num(m.thinking_time_s)} giây`);
  if (m.answer_duration_s != null) parts.push(`nói ${num(m.answer_duration_s)} giây`);
  if (m.speech_rate_spm != null) parts.push(`${num(m.speech_rate_spm, 0)} âm tiết/phút`);
  if (m.long_pause_count) parts.push(`${m.long_pause_count} lần ngập ngừng`);
  if (m.filler_ratio) parts.push(`từ đệm ${num(m.filler_ratio * 100, 0)}%`);
  return parts.join(" · ");
}

// 422 voice_no_speech tu ai-service (ban ghi chi co tu dem): luot khong luu, ghi lai tu dau
function voiceRejected(err) {
  setRecStatus(err.serverMessage || err.message, "warn");
}

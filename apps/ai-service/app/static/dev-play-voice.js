// Voice cho trang dev /dev/play (tuy chon A, docs 11): TTS doc cau hoi, STT bam-de-noi, deu bang Web Speech API cua
// trinh duyet (khong can key). Chi de thu luong: Chrome gui am thanh len may chu Google, khong nhan thuat ngu goi y,
// confidence thieu on dinh. San pham that goi nha cung cap STT/TTS qua interview-service (NFR-AI-QUAL16).
const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const V = { rec: null, base: "", heard: null }; // heard: {text, confidence} cua lan ghi gan nhat, null = chua ghi
const tts = window.speechSynthesis; // khong co thi bo qua TTS, khong lam hong trang

function voiceOn() { return $("voice").checked; }

function voiceSpeak(text) {
  if (!voiceOn() || !tts || !text) return;
  tts.cancel(); // cau moi thay cau dang doc
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "vi-VN";
  u.voice = tts.getVoices().find((v) => v.lang.replace("_", "-").startsWith("vi")) || null;
  tts.speak(u);
}

function micStatus(text, cls) {
  $("chatStatus").textContent = text;
  $("chatStatus").className = `status ${cls || ""}`;
}

// Ghep ket qua cua ca lan ghi. confidence = trung binh cac doan da chot (Chrome doi khi tra 0: coi nhu khong biet);
// con doan chua chot (gui giua chung) thi khong gui confidence de doan do khong lot cong STT_MIN_CONFIDENCE
function onResult(e) {
  let text = "", sum = 0, n = 0, allFinal = true;
  for (const r of e.results) {
    text += r[0].transcript;
    allFinal &&= r.isFinal;
    if (r.isFinal && r[0].confidence > 0) { sum += r[0].confidence; n += 1; }
  }
  $("answer").value = (V.base ? `${V.base} ` : "") + text.trim();
  V.heard = { text: $("answer").value.trim(),
              confidence: !V.base && allFinal && n ? Number((sum / n).toFixed(3)) : null };
}

function micIdle() {
  V.rec = null;
  $("answer").readOnly = false;
  $("micBtn").textContent = "🎤 Nói";
  $("micBtn").classList.remove("primary");
}

// Huy han lan ghi: go handler truoc de ket qua den muon (sau khi gui / tat voice) khong ghi lai vao o tra loi
function abortMic() {
  const rec = V.rec;
  if (!rec) return;
  rec.onresult = rec.onerror = rec.onend = null;
  rec.abort();
  micIdle();
}

const MIC_ERRORS = { "not-allowed": "Trình duyệt chặn micro: cho phép micro cho trang này.",
                     "audio-capture": "Không tìm thấy micro.",
                     "no-speech": "Chưa nghe thấy tiếng. Nói lại, hoặc bấm Gửi để thử phản hồi voice_no_speech." };

function toggleMic() {
  if (V.rec) return V.rec.stop(); // Dung: Chrome con tra ket qua cuoi roi moi onend
  tts?.cancel(); // dang doc cau hoi thi dung de khong thu lai tieng loa
  const rec = new Recognition();
  Object.assign(rec, { lang: "vi-VN", continuous: true, interimResults: true, maxAlternatives: 1 });
  V.base = $("answer").value.trim(); // da go san: van tinh la voice nhung khong gui confidence
  V.heard = { text: V.base, confidence: null };
  rec.onresult = onResult;
  rec.onerror = (e) => {
    if (e.error !== "no-speech") V.heard = null; // micro hong / bi chan: cau go tay sau do la text
    micStatus(MIC_ERRORS[e.error] || `Lỗi nhận dạng: ${e.error}`, "warn");
  };
  rec.onend = micIdle; // Chrome tu dung sau mot luc im lang
  try {
    rec.start();
  } catch (err) {
    V.heard = null;
    return micStatus(`Không bật được micro: ${err.message}`, "warn");
  }
  V.rec = rec;
  $("answer").readOnly = true; // dang ghi: ket qua moi se ghi de o tra loi
  $("micBtn").textContent = "■ Dừng";
  $("micBtn").classList.add("primary");
  micStatus("Đang nghe… bấm Dừng khi nói xong (có thể sửa transcript trước khi gửi).");
}

// Truong voice cho /api/next-turn (docs 06 §7.4): sua transcript sau khi ghi thi gui voice khong kem confidence
function voiceFields(answer) {
  if (!V.heard || !voiceOn()) return { answer_source: "text" };
  const edited = answer !== V.heard.text;
  return { answer_source: "voice", stt_confidence: edited ? null : V.heard.confidence };
}

// Gui cau tra loi / ket thuc buoi / tat voice: bo lan ghi dang do, dung doc
function voiceReset() {
  abortMic();
  tts?.cancel();
  V.heard = null;
}

// 422 voice_no_speech / voice_unclear: luot khong duoc luu, transcript tra lai o tra loi de noi lai hoac sua.
// Gui lai transcript do (sua hay khong) la voice khong kem confidence, nhu ung vien sua transcript (06 §7.4)
function voiceRejected(err, answer) {
  if (!err.code?.startsWith("voice_")) return false;
  const noSpeech = err.code === "voice_no_speech"; // chi co am dem: xoa de ghi lai tu dau, confidence tinh lai
  if (noSpeech) $("answer").value = "";
  V.heard = answer && !noSpeech ? { text: answer, confidence: null } : null;
  micStatus(err.serverMessage, "warn");
  voiceSpeak(err.serverMessage);
  if (err.code === "voice_unclear") $("answer").focus();
  return true;
}

function voiceSetup() {
  if (!Recognition) {
    $("voiceNote").textContent = "Trình duyệt này không có Web Speech API (STT): dùng Chrome hoặc Edge. TTS vẫn chạy.";
  }
  $("micBtn").onclick = toggleMic;
  $("voice").onchange = () => {
    $("micBtn").classList.toggle("hidden", !voiceOn() || !Recognition);
    if (!voiceOn()) voiceReset();
  };
  $("voice").onchange();
}

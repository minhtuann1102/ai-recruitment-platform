// Ket thuc buoi va man danh gia: /api/finalize (bao cao) va /dev/voice/session-summary (chi so trinh bay giong noi)
// chay song song; hien bang interview-report.js. Viet lai bao cao duoc khi loi (giu thoi luong luc ket thuc).

async function finalizeSession(byCandidate) {
  S.ended = true; // ket qua STT / next-turn ve muon sau moc nay bi bo qua (khong them luot, khong doc cau moi)
  stopClock();
  stopSpeaking();
  abortRecording();
  V.stream?.getTracks().forEach((t) => t.stop()); // tat micro (den bao ghi am cua trinh duyet)
  S.durationS ??= elapsedSeconds(); // viet lai bao cao: giu thoi luong luc ket thuc, khong cong thoi gian o man ket qua
  if (byCandidate && S.state) S.state.end_reason = "candidate_ended";
  showScreen("screenResult");
  $("finalizeRetryBtn").classList.add("hidden");
  if (!S.turns.length) {
    return setResult("Bạn kết thúc trước khi trả lời câu nào nên chưa có đánh giá. Bấm “Buổi mới” để thử lại nhé.");
  }
  setResult("AI đang tổng hợp đánh giá cho bạn…");
  renderNotes(S.state?.notes, $("agentNotes"));
  const [report, summary] = await Promise.allSettled([
    // phase 04: plan / state / turns / jd_profile lay tu checkpoint phien; phien da done thi end_reason da luu thang
    postJson("/api/finalize", { session_id: S.sid, end_reason: S.state.end_reason || "plan_complete",
      duration_s: S.durationS }),
    S.summary ? Promise.resolve(S.summary) : postJson("/dev/voice/session-summary", { turns: S.voiceMetrics }),
  ]);
  if (summary.status === "fulfilled") {
    S.summary = summary.value;
    renderVoiceSummary(S.summary, $("voiceSummary"));
  }
  if (report.status === "rejected") {
    $("finalizeRetryBtn").classList.remove("hidden");
    return setResult(`Chưa tạo được đánh giá. ${friendlyError(report.reason)}`, "error");
  }
  S.report = report.value;
  try {
    renderReport(S.report, $("report"));
  } catch {
    $("finalizeRetryBtn").classList.remove("hidden");
    return setResult("Chưa hiển thị được đánh giá. Bạn bấm “Thử lại” nhé.", "error");
  }
  setResult(`Buổi phỏng vấn dài ${Math.max(1, Math.round(S.durationS / 60))} phút, ${S.turns.length} câu trả lời. `
            + "Đánh giá chi tiết ở bên dưới.");
}

function setResult(text, cls) {
  $("resultStatus").textContent = text;
  $("resultStatus").classList.toggle("error-text", cls === "error");
}

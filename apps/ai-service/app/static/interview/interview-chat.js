// Khung chat cua man phong van: moi luot noi (AI hoi, ung vien tra loi) la mot bong chat CHI DOC.
// Noi dung gan bang textContent, khong co o sua: cau hoi / ban ghi giong noi da hien la co dinh. Kem hop xac nhan.
const AI_TAG = "AI phỏng vấn";

// Thanh micro dinh o cuoi man (sticky) che bong moi nhat: scrollIntoView "nearest" coi bong la da hien nen khong cuon.
// Cuon ca trang xuong day de bong cuoi nam ngay tren thanh micro (goi moi khi them bong / doi chu / co token moi).
// force=false (token dang stream): chi cuon khi nguoi dung dang o gan cuoi, khong keo nguoi dang doc cau cu xuong
function scrollChatEnd(force = true) {
  const el = document.documentElement;
  if (force || window.innerHeight + window.scrollY >= el.scrollHeight - 160) window.scrollTo({ top: el.scrollHeight });
}

function addBubble(who, text, tag) {
  const div = document.createElement("div");
  div.className = `msg msg-${who}`;
  div.innerHTML = '<span class="msg-tag"></span><span class="msg-body"></span>';
  div.querySelector(".msg-tag").textContent = tag || (who === "ai" ? AI_TAG : "Bạn");
  div.querySelector(".msg-body").textContent = text || "";
  $("chatLog").appendChild(div);
  scrollChatEnd();
  return div;
}

const bubbleBody = (b) => b.querySelector(".msg-body");

// Doi chu / nhan cua bong (chi code goi; nguoi dung khong sua duoc)
function setBubble(b, text, tag) {
  if (text !== undefined) bubbleBody(b).textContent = text;
  if (tag) b.querySelector(".msg-tag").textContent = tag;
  scrollChatEnd();
}

// Luot khong duoc tinh (micro khong thu duoc tieng, loi gui): giu bong, lam mo, ghi ly do
function markRejected(b, note) {
  b.classList.add("rejected");
  addBubbleNote(b, note);
}

// Dong phu duoi bong (ly do khong tinh, chi so trinh bay cua luot)
function addBubbleNote(b, note) {
  if (!note) return;
  const n = document.createElement("span");
  n.className = "msg-note";
  n.textContent = note;
  b.appendChild(n);
  scrollChatEnd();
}

// Hop xac nhan cua trang (thay window.confirm): <dialog> showModal -> phan duoi bi khoa (khong Tab / bam toi duoc).
// Tra Promise<boolean>; Esc / bam ra ngoai = huy. Mac dinh focus nut huy (an toan khi vua bam Enter de gui).
// Dang co hop mo thi hop moi tra false ngay (khong chong hai hop, khong de lai handler cu).
function askConfirm({ title, text, ok, cancel }) {
  const dlg = $("confirmDialog");
  if (dlg.open) return Promise.resolve(false);
  const opener = document.activeElement;
  $("confirmTitle").textContent = title;
  $("confirmText").textContent = text;
  $("confirmOk").textContent = ok;
  $("confirmCancel").textContent = cancel;
  dlg.showModal();
  $("confirmCancel").focus();
  return new Promise((resolve) => {
    const close = (value) => {
      $("confirmOk").onclick = $("confirmCancel").onclick = dlg.onclick = dlg.oncancel = null;
      dlg.close();
      if (opener?.isConnected && !opener.disabled) opener.focus();
      resolve(value);
    };
    dlg.oncancel = (e) => { e.preventDefault(); close(false); };
    $("confirmOk").onclick = () => close(true);
    $("confirmCancel").onclick = () => close(false);
    dlg.onclick = (e) => { // bam vao nen mo (ngoai khung hop)
      const r = dlg.getBoundingClientRect();
      if (e.target === dlg && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) close(false);
    };
  });
}

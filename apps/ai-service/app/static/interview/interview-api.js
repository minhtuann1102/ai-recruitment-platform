// Goi API cho man phong van (ai-service + proxy voice): JSON, SSE (POST) va loi than thien cho nguoi dung cuoi.
// Khong phu thuoc trang dev /dev/play (khong bang "Luong he thong", khong o token tren man hinh).
const $ = (id) => document.getElementById(id);

// Token noi bo chi dung khi may dev dat AI_SERVICE_INTERNAL_TOKEN: truyen qua ?token=... tren URL, khong hien len man
const INTERNAL_TOKEN = new URLSearchParams(location.search).get("token") || "";

function headers(json) {
  const h = json ? { "Content-Type": "application/json" } : {};
  if (INTERNAL_TOKEN) h["X-Internal-Token"] = INTERNAL_TOKEN;
  return h;
}

// Loi API thanh Error co code / status / serverMessage (message cua API da la tieng Viet)
async function apiError(resp) {
  const body = await resp.text();
  let j = {};
  try { j = JSON.parse(body); } catch { /* body khong phai JSON */ }
  return Object.assign(new Error(j.message || `HTTP ${resp.status}`),
                       { code: j.error, status: resp.status, serverMessage: j.message });
}

async function getJson(path) {
  const resp = await fetch(path, { headers: headers(false) });
  if (!resp.ok) throw await apiError(resp);
  return resp.json();
}

async function postJson(path, body, isForm) {
  const resp = await fetch(path, { method: "POST", headers: headers(!isForm), body: isForm ? body : JSON.stringify(body) });
  if (!resp.ok) throw await apiError(resp);
  return resp.json();
}

// POST + doc SSE (EventSource khong ho tro POST). Tra data cua event `done`; event `error` nem loi.
async function postSse(path, body, onEvent) {
  const resp = await fetch(path, { method: "POST", headers: headers(true), body: JSON.stringify(body) });
  if (!resp.ok) throw await apiError(resp);
  const reader = resp.body.getReader(), decoder = new TextDecoder();
  let buf = "", done = null;
  for (;;) {
    const { value, done: end } = await reader.read();
    if (end) break;
    buf += decoder.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, i);
      buf = buf.slice(i + 2);
      let name = "", data = "{}";
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) name = line.slice(7);
        else if (line.startsWith("data: ")) data = line.slice(6);
      }
      const payload = JSON.parse(data);
      if (name === "error") throw Object.assign(new Error(payload.message), { code: payload.errorCode, stream: true });
      if (name === "done") done = payload;
      onEvent(name, payload);
    }
  }
  if (!done) throw Object.assign(new Error("stream_cut"), { stream: true });
  return done;
}

const VOICE_DOWN = "Dịch vụ giọng nói đang gặp sự cố. Bạn thử lại, hoặc bấm “Gõ thay vì nói”.";
const FRIENDLY = {
  voice_service_unreachable: VOICE_DOWN, voice_service_timeout: VOICE_DOWN, provider_error: VOICE_DOWN,
  provider_timeout: VOICE_DOWN, provider_unconfigured: VOICE_DOWN, provider_rate_limited: VOICE_DOWN,
  quota_exceeded: VOICE_DOWN,
  session_not_found: "Buổi phỏng vấn đã hết hạn trên máy chủ. Bạn tải lại trang để bắt đầu buổi mới nhé.",
  audio_too_long: "Câu trả lời quá dài. Hãy trả lời gọn hơn (dưới 3 phút).",
  invalid_audio: "Không đọc được bản ghi âm. Bạn thử ghi lại nhé.",
  unauthorized: "Phiên làm việc không hợp lệ. Hãy tải lại trang.", misconfigured: "Hệ thống chưa sẵn sàng. Vui lòng thử lại sau.",
};

// Loi -> cau cho nguoi dung: ma da biet -> cau soan san; 4xx co message tieng Viet cua API -> dung; con lai -> chung
function friendlyError(err) {
  if (FRIENDLY[err.code]) return FRIENDLY[err.code];
  if (err instanceof TypeError) return "Mất kết nối. Kiểm tra mạng rồi thử lại.";
  if (err.stream) return "AI chưa phản hồi xong. Bấm “Gửi lại” để thử lại.";
  if (err.status && err.status < 500 && err.serverMessage) return err.serverMessage;
  return "Hệ thống đang bận. Vui lòng thử lại sau ít phút.";
}

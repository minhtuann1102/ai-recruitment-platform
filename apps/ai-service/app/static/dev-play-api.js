// Goi API ai-service cho trang dev /dev/play: JSON va SSE (POST), kem X-Internal-Token neu nhap tren trang.
// Moi request ghi vao bang "Luong he thong" (dev-play-trace.js).
function headers(json) {
  const h = json ? { "Content-Type": "application/json" } : {};
  const token = $("token").value.trim();
  if (token) h["X-Internal-Token"] = token;
  return h;
}

async function errorText(resp) {
  const body = await resp.text();
  try { const j = JSON.parse(body); return `${resp.status} ${j.error}: ${j.message}`; } catch { return `${resp.status}: ${body.slice(0, 200)}`; }
}

async function postJson(path, body, isForm) {
  const tr = traceStart(path);
  try {
    const resp = await fetch(path, { method: "POST", headers: headers(!isForm), body: isForm ? body : JSON.stringify(body) });
    if (!resp.ok) throw new Error(await errorText(resp));
    const data = await resp.json();
    traceLine(tr, `200 OK`);
    traceAgents(tr, data.metadata?.model ? data.metadata : null);
    if (path === "/api/finalize") traceFinalize(tr, data);
    return data;
  } catch (err) {
    traceLine(tr, err.message, "error");
    throw err;
  }
}

function traceFinalize(tr, r) {
  for (const [agent, ms] of Object.entries(r.metadata?.latency_ms_by_agent || {})) {
    if (agent !== "total") traceLine(tr, `${AGENT_NAME[agent] || agent}: ${ms} ms`, "agent");
  }
  for (const f of r.meta?.fallbacks || []) traceLine(tr, `fallback: ${f}`, "warn");
  traceLine(tr, `Báo cáo ${r.status}: ${r.session.evaluated_turns} lượt được chấm, độ tin cậy ${r.session.confidence}`);
}

// POST + doc SSE (EventSource khong ho tro POST). Tra data cua event `done`; event `error` nem loi.
async function postSse(path, body, onEvent) {
  const resp = await fetch(path, { method: "POST", headers: headers(true), body: JSON.stringify(body) });
  if (!resp.ok) throw new Error(await errorText(resp));
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
      if (name === "error") throw new Error(`${payload.errorCode}: ${payload.message}`);
      if (name === "done") done = payload;
      onEvent(name, payload);
    }
  }
  if (!done) throw new Error("Stream kết thúc mà không có event done");
  return done;
}

# Review phase 02 (graph LangGraph mỗi lượt) + cách xử lý

Plan: [261127-1517-langgraph-orchestrator-session-memory](../261127-1517-langgraph-orchestrator-session-memory/plan.md),
phase 02. Reviewer: agent `code-reviewer` (opus), đọc diff + chạy probe, không sửa code. Người sửa: AIE (session chính).

## Kết luận reviewer
Phần chuyển code nguyên văn đúng hành vi. 1 lỗi major (M1) + test dương tính giả (M2), 5 minor.

| # | Mức | Vấn đề | Xử lý |
|---|---|---|---|
| M1 | major | Client ngắt giữa câu hỏi: Starlette huỷ generator bằng cancel scope anyio, `astream` bị ngắt nhưng LangGraph không kịp huỷ task node `ask` → Interviewer chạy tiếp trong nền tới hết câu (tốn token, span / usage ghi sau `request_done`) | **Đã sửa.** `GraphTurnRun` chạy graph trong task asyncio riêng (pump → `asyncio.Queue`); `aclose()` huỷ task đó, LangGraph dọn dẹp bình thường. `prime()` lỗi / bị huỷ cũng `aclose()` |
| M2 | major | Test ngắt client assert sau `asyncio.run`, lúc vòng sự kiện đã tự huỷ task còn sót → luôn xanh | **Đã sửa.** `post_and_disconnect` assert ngay khi app trả về và sau 0,3 s trong cùng vòng; 5 biến thể (ngắt sau 1–4 message, có / không nhường lượt trong `send`). Trước khi sửa M1: 4/4 đỏ; sau: xanh |
| m1 | minor | `"end"` vừa là route kết thúc phiên vừa có thể là tên hành động; hành động lạ làm graph `KeyError` | **Đã sửa.** Route `SESSION_END = "session_end"`; test mọi nguồn hành động (hybrid `ACTIONS`, forced, low_performance) ⊆ `DECIDE_ACTIONS` |
| m2 | minor | `get_evaluator()` / `get_interviewer()` gọi sớm cho mọi request: cấu hình agent sai biến 409 thành 500; `/start` gọi ngoài `_logged_failure` | **Đã sửa.** Evaluator lấy lúc chấm (`turn_steps._default_evaluator`, vẫn patch ở `app.turn_engine.get_evaluator`); Interviewer truyền dạng hàm, gọi trong `turn_question_events` khi còn hỏi. Test: agent lỗi vẫn ra 409 |
| m3 | minor | Lỗi trong `ask` ra SSE `error` nhờ chi tiết nội bộ LangGraph, chưa có test HTTP | **Đã sửa** (pump bỏ phụ thuộc đó) + test: Interviewer lỗi → `meta`, `error` (retryable) |
| m4 | minor | `LANGSMITH_TRACING` bật thì input graph (câu trả lời, plan) lên LangSmith | Ghi cảnh báo ở `context/environment.md` |
| m5 | minor | Graph compile ở request đầu; cảnh báo deprecation; hai đường điều phối (tuần tự cho test / evals, graph cho HTTP) | Compile trong `lifespan`. Cảnh báo: vô hại, ghi ở `context/environment.md`. Hai đường: giữ tới phase 04 |

## Kiểm sau khi sửa
- `pytest -q`: 1439 passed, 8 skipped (thêm 7 test so với lúc review).
- Mô phỏng `evals.simulate --matrix quick` in-process: graph sau sửa == code cũ (10 phiên / 125 lượt / báo cáo, bỏ
  timing). Qua HTTP (uvicorn mock): 10 phiên / 125 lượt chạy hết.

## Câu hỏi mở
1. interview-service có retry nhanh sau khi SSE đứt không? Với M1 đã sửa thì không chồng stream, nhưng cần biết để thiết kế khoá phiên ở phase 03 (G3).
2. Phase 04 / 05: `/start` có đi qua graph không (node `plan`)? Nếu có thì dùng lại `GraphTurnRun`.

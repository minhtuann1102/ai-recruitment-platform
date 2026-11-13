"""Ra soat pham vi cau hoi (spec 005 FR-030, T067): tach dap an thanh y va kiem tra khoi code ```."""
from pipeline.qa_scope_check_points import BULLET, check_fences, segment_answer, split_points


def texts(answer):
    return [p["text"] for p in segment_answer(answer)]


def test_bullets_and_numbered_are_one_point_each_with_ids():
    points = segment_answer("- a\n* b\n1. c\n2) d")
    assert [p["id"] for p in points] == ["p1", "p2", "p3", "p4"]
    assert [p["text"] for p in points] == ["a", "b", "1. c", "2) d"]


def test_bold_only_and_colon_headings_prefix_following_points():
    answer = "**Schema**\n- a\n- b\n\n**Báo lỗi:**\n- c\n\nCách sửa:\n1. d\n\n**Kết**:\n- e"
    assert texts(answer) == ["[Schema] a", "[Schema] b", "[Báo lỗi] c", "[Cách sửa] 1. d", "[Kết] e"]


def test_long_colon_line_and_bullet_ending_colon_are_points_not_headings():
    long_line = "Chia audio theo các khoảng im lặng, với OpenAI Realtime API có ba tham số chính:"
    assert len(long_line) > 60
    assert texts(f"{long_line}\n- a\n- Các bước:\n  - x") == [long_line, "a", "Các bước:\n  - x"]


def test_bold_label_line_with_text_is_a_point_not_a_heading():
    assert texts("**Khởi điểm**: chọn giải pháp đơn giản.\n**Kết luận**: xong.") == [
        "**Khởi điểm**: chọn giải pháp đơn giản.\n**Kết luận**: xong."]
    assert texts("**Khởi điểm**: a\n\n**Kết luận**: b") == ["**Khởi điểm**: a", "**Kết luận**: b"]


def test_paragraph_is_one_point_and_blank_line_splits_paragraphs():
    assert texts("dòng một\ndòng hai\n\nđoạn hai\n- bullet") == ["dòng một\ndòng hai", "đoạn hai", "bullet"]


def test_heading_scope_ends_at_blank_then_paragraph_but_not_at_blank_then_bullet():
    assert texts("**H**\n\n- a\n\n- b\n\nKết luận chung.\n- c") == ["[H] a", "[H] b", "Kết luận chung.", "c"]


def test_indented_lines_continue_previous_bullet_even_nested_or_after_blank():
    answer = "- cha:\n  - con 1\n  - con 2\n    tiếp\n\n  đoạn thụt sau dòng trống\n- bullet sau"
    assert texts(answer) == ["cha:\n  - con 1\n  - con 2\n    tiếp\n  đoạn thụt sau dòng trống", "bullet sau"]


def test_code_fence_stays_with_previous_point_and_its_content_is_not_classified():
    answer = "- Ví dụ\n\n```py\n- không phải bullet\n\n**Không phải heading**\nx:\n```\nđoạn sau\n\n```\ncode thứ hai\n```"
    assert texts(answer) == ["Ví dụ\n```py\n- không phải bullet\n\n**Không phải heading**\nx:\n```",
                             "đoạn sau\n```\ncode thứ hai\n```"]
    assert texts("```\ncode mồ côi\n```\n- a") == ["```\ncode mồ côi\n```", "a"]  # chua co y nao truoc: tu thanh mot y


def test_fence_after_heading_is_its_own_point_with_heading_prefix():
    assert texts("Ví dụ:\n```js\nfoo()\n```") == ["[Ví dụ] ```js\nfoo()\n```"]


def test_adjacent_headings_stack_and_trailing_heading_becomes_a_point():
    assert texts("**A**\nBước sau đây:\n- x") == ["[A > Bước sau đây] x"]
    assert texts("- x\n**Kết luận**") == ["x", "**Kết luận**"]
    assert texts("") == []


def test_every_non_heading_line_lands_in_exactly_one_point_in_order():
    answer = ("**Schema**\n- `inputSchema` chặt.\n  - con\n\n**Lỗi:**\nĐoạn mở đầu\ntiếp dòng.\n1. bước một\n```\nx = 1\n\n```\n"
              "Cách làm:\n- a\n\nĐoạn cuối.")
    expected = ["`inputSchema` chặt.", "- con", "Đoạn mở đầu", "tiếp dòng.", "1. bước một", "```", "x = 1", "", "```",
                "a", "Đoạn cuối."]

    def core(line):  # bo dau bullet: phan bo dau marker khong tinh la noi dung
        match = BULLET.match(line)
        return match.group(1) if match else line

    body = [core(line.strip()) for _, lines in split_points(answer) for line in lines]
    assert body == [core(line) for line in expected]


def test_check_fences_accepts_balanced_start_of_line_fences_and_rejects_the_rest():
    assert check_fences("- a\n```py\nx = 1\n```\nb") is None
    assert check_fences("- a\n  ```py\n  x\n  ```") is None  # thut le van la dau dong
    assert check_fences("khong co fence") is None
    assert "le" in check_fences("- a\n```py\nx = 1")  # khoi khong dong
    assert "dau dong" in check_fences("- Ví dụ: ```py\nx\n```")  # ``` giua dong

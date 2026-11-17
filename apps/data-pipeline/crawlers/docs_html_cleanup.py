"""Tien xu ly DOM cho parse_html_page (textbook 012): bo phan tu an va giu xuong dong trong khoi code.

Chi parse_html_page goi cac ham nay; parse_sections / react_docs_crawler (005) khong dung nen hanh vi cu giu nguyen.
"""
from bs4 import Tag

# Phan tu an khoi nguoi doc: thuoc tinh hidden, aria-hidden="true", devsite-actions (the hoac class; web.dev that la
# <devsite-actions hidden> trong h1 chua tooltip "Stay organized with collections..." nen lot vao title va moi chunk)
HIDDEN_SELECTOR = "[hidden], [aria-hidden='true' i], devsite-actions, .devsite-actions"
# Mot dong code la mot the khoi (react.dev: <div class="cm-line">...<br/></div> trong <pre><code>)
CODE_LINE_TAGS = ("div", "p", "li")


def remove_hidden(root: Tag) -> None:
    """Xoa phan tu an nam trong root (khong xoa chinh root)."""
    for element in root.select(HIDDEN_SELECTOR):
        if not element.decomposed:  # phan tu an long nhau: cha da bi xoa keo theo con
            element.decompose()


def preserve_code_line_breaks(root: Tag) -> None:
    """Moi <br> trong <pre> thanh "\\n"; moi dong-the-khoi chua ket thuc bang xuong dong thi them "\\n".

    Token <span> (to mau cu phap) khong bi dong vao: chi the khoi va <br> moi sinh xuong dong, nen code da co "\\n"
    san trong text (MDN, web.dev) khong bi nhan doi dong trong.
    """
    for pre in root.find_all("pre"):
        for br in pre.find_all("br"):
            br.replace_with("\n")
        # Duyet nguoc: the trong xu ly truoc, de the ngoai thay "\n" cuoi cua the trong va khong them lan nua
        for line in reversed(pre.find_all(CODE_LINE_TAGS)):
            after = line.next_sibling
            if line.get_text().endswith("\n") or (isinstance(after, str) and after.startswith("\n")):
                continue
            line.append("\n")

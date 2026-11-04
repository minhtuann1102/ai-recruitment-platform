"""Doi thuat ngu Anh bi STT phien am ve dang viet dung truoc khi Evaluator cham (NFR-AI-QUAL17, voice tuy chon A).

Bang tra co dinh, khong goi LLM: "đốc cơ" -> Docker, "thờ rét" -> thread. Nguon tu: thuat ngu trong topic catalog
(app/catalog/*.yaml) va tu vung lap trinh chung (cau truc du lieu, CRUD, HTTP, dong thoi); khong lay tu bo nhieu
golden (evals/evaluator_golden_stt.jsonl) de so do khong lac quan.

Moi dang phien am phai >= 2 am tiet: am tiet don ("cát", "sét", "nốt", "ghét") trung tu tieng Viet thuong gap nen
khong doi; cum 2 am tiet trung tieng Viet ("con bách thú", "gia va" = "gia vị" go khong dau)
cung bi bo. ai-service khong biet cau tra loi den tu chat hay giong noi, nen bang ap cho moi luot; test kiem cau
go tay trong golden khong bi doi chu nao.
"""
import re
import unicodedata
from typing import Dict, Tuple

STT_TERMS: Dict[str, Tuple[str, ...]] = {
    # dong thoi, Java
    "thread": ("thờ rét", "thờ rẹt", "thơ rét"),
    "thread pool": ("thờ rét pun", "thờ rét pul"),
    "thread-safe": ("thờ rét sếp", "thờ rét xếp", "thờ rét xêu"),
    "HashMap": ("hát mắp", "hách mắp", "hát máp"),
    "ConcurrentHashMap": ("con ca rừn hát mắp", "con ca rần hát mắp", "con cơ rần hát mắp"),
    "synchronized": ("xin cờ rô nai", "sin cờ rô nai", "xin cờ rô nai dờ"),
    "atomic": ("a tô mích", "ờ tôm mích"),
    "bucket": ("bắc kết", "bắc kít"),
    "garbage collector": ("ga bịch cô léc tơ", "ga bít cô lếch tơ"),
    "Spring Boot": ("xờ pring bút", "sờ pring bút", "spring bút"),
    "transaction": ("tran sắc sần", "tờ ran sắc sần", "trăn sắc sần"),
    "dependency injection": ("đi pen đần si in giếch sần", "đi pen đền xi in déc sần"),
    "dependency": ("đi pen đần si", "đi pen đền xi", "đi pen đen si"),
    "interface": ("in tơ phây", "in tơ phết"),
        # Node.js, JavaScript
    "Node.js": ("nốt gia ét", "nốt dê ét", "nốt giây ét"),
    "event loop": ("i ven lúp", "i vần lúp", "ê ven lúp"),
    "callback": ("côn bách",),  # "con bách thú", "cô Bách" la tieng Viet
    "Promise": ("prô mít", "pờ rô mít"),
    "async": ("ây sinh", "ây xinh"),
    "await": ("a quết", "ờ quết"),
    "asyncio": ("ây sinh ai ô", "ây xinh ai ô"),
    "I/O": ("ai ô",),
    "libuv": ("li bu vê", "lip iu vi"),
    "middleware": ("mít đồ que", "mít đồ ve", "mít đô que"),
    "Express": ("ích xpréc", "ếch xờ prét"),
    "NestJS": ("nét gia ét", "nét dê ét"),
    "TypeScript": ("thai xờ críp", "tai xcríp", "thai sờ cờ ríp"),
    "JavaScript": ("gia va xờ críp", "gia va xcríp"),
    "stream": ("xờ trim", "sờ trim"),
    "buffer": ("bắp phơ", "bấp phơ"),
    "worker": ("uốc cơ", "guốc cơ"),
    "cluster": ("cờ lớt tơ", "cờ lắt xtơ"),
    "backoff": ("bách óp", "béc óp"),
    # React, frontend
    "React": ("ri ác", "ri ắc", "ri éc"),
    "Next.js": ("nếch gia ét", "néc xờ gia ét"),
    "useEffect": ("diu ép phéc", "giu ép phéc", "iu ép phéc"),
    "useState": ("diu xờ tết", "diu sờ tết", "diu xtết"),
    "useMemo": ("diu mem mô", "diu me mô"),
    "useCallback": ("diu côn bách", "diu con bách"),
    "effect": ("ép phéc",),
    "component": ("com pô nần", "com pô nừn", "cờm pô nần"),
    "re-render": ("ri ren đờ", "ri ren đơ"),
    "render": ("ren đờ", "ren đơ", "ren dơ"),
    "props": ("pờ róp", "pờ rốp"),
    "state": ("sờ tết", "xờ tết"),
    "cleanup": ("cờ lin ấp", "cơ lin ấp", "clin ấp"),
    "unmount": ("ăn mao",),  # "ăn mau" la tieng Viet thuong
    "return": ("ri tơn", "ri tớn"),
    "WebSocket": ("guép xóc kịt", "uếp sóc kít", "web xóc kết"),
    "realtime": ("rêu thai", "riêu tai"),
    # du lieu, cache
    "database": ("đa ta bết", "đa ta bêt", "đây ta bết", "đa ta bây"),
    "DB": ("đê bê",),  # "đi bi" trung "đi bi-a"
    "index": ("in đếch", "in đéc"),
    "query": ("quy ri", "quơ ri"),
    "SQL": ("ét kiu eo", "ét quy eo"),
    "PostgreSQL": ("pốt grét", "pốt gờ rét", "pốt grê ét kiu eo"),
    "MySQL": ("mai ét kiu eo", "mai xi quồ"),
    "MongoDB": ("mon gô đi bi", "mông gô đê bê"),
    "Redis": ("rê đít", "re đít", "ri đít"),
    "cache-aside": ("cát ơ sai", "cát ờ sai"),
    "cache miss": ("cát mít",),
    "cache hit": ("cát hít",),
    "stampede": ("xtem pít", "xờ tem pít", "x tam pít"),
    "TTL": ("ti ti eo", "ti ti en"),
    "ORM": ("ô a em", "ô rờ em"),
    "migration": ("mai grây sần", "mai gờ rây sần"),
    "isolation": ("ai xô lây sần", "ai sô lây sần"),
    "update": ("ấp đết", "ấp đây"),
    "insert": ("in sớt", "in xớt"),
    "delete": ("đi lít", "đi lét"),
    "select": ("xi léc", "sờ léc"),
    "refresh": ("ri phét", "ri phrét"),
    "JSON": ("giây sơn",),
    # API, bao mat
    "API": ("ây pi ai", "ê pi ai"),
    "FastAPI": ("phát ây pi ai", "phát xờ ây pi ai"),
    "request": ("ri quét", "rì quét", "ri quest"),
    "response": ("ri pón", "ri xpón", "rì pon"),
    "endpoint": ("en poi", "en point"),
    "HTTP": ("hát tê tê pê", "ếch tê tê pê"),
    "JWT": ("giây đắp bờ liu ti", "gi đắp liu ti"),
    "token": ("tô cần", "tô kần", "thâu cần"),
    "OAuth": ("ô ót", "ô ọt"),
    "session": ("xét sần", "sét sần"),
    "cookie": ("cúc ki",),
    "rate limit": ("rết lim mít", "rây lim mít"),
    "retry": ("ri trai", "ri chai"),
    "timeout": ("thai mao", "tai mao"),
    "idempotent": ("ai đem pô tần",),
    "idempotency": ("ai đem pô tần xi",),
    "server": ("xơ vơ", "sơ vơ"),
    "client": ("cờ lai ần", "clai ần"),
    "backend": ("bách en", "béc en"),
    "frontend": ("phờ ron en", "phron en"),
    "framework": ("phờ rêm uốc", "phrêm guốc"),
    "unit test": ("iu nít tét", "diu nít tét"),
    "memory leak": ("me mơ ri líc", "mem mơ ri lích"),
    "profiling": ("prô phai linh", "pờ rô phai linh"),
    "stack": ("xờ tách", "x tách"),
    "proxy": ("prốc xi", "pờ rốc xi"),
    "load balancer": ("lốt ba lăn xơ", "lốt ba lan sơ"),
    "microservice": ("mai crô xơ vít", "mai cờ rô sơ vịt"),
    # DevOps
    "Docker Compose": ("đốc cơ com pâu", "đốc cơ cầm pốt"),
    "Dockerfile": ("đốc cơ phai",),
    "Docker": ("đốc cơ", "đốc kơ", "đóc cơ"),
    "Kubernetes": ("cu bơ nét", "cu bơ nê tít", "ku bơ nét tít"),
    "container": ("con tê nơ", "con tây nơ", "cơn tây nơ"),
    "deploy": ("đi ploi", "đi plôi"),
    "CI/CD": ("xi ai xi đi", "si ai si đi"),
    "pipeline": ("pai pờ lai",),
    "Kafka": ("ca phờ ca", "káp ca", "kháp ca"),
    "RabbitMQ": ("ráp bít em kiu", "ra bít em kiu"),
    "Nginx": ("en gin ích",),
    "Linux": ("li nắc", "lai nắc"),
    "canary": ("ca na ri", "cơ ne ri"),
    "rollback": ("rôn bách", "rô bách"),
    # Python, AI
    "Python": ("pai thon", "pai thơn", "bai thon"),
    "Django": ("giang gô", "đi giang gô"),
    "Celery": ("xe lơ ri", "sê lơ ri"),
    "Pydantic": ("pai đan tích",),
    "decorator": ("đê cô rây tơ", "đếc cơ rây tơ"),
    "generator": ("gien nơ rây tơ", "gie nơ rây tơ"),
    "LLM": ("eo eo em", "en en em"),
    "prompt": ("pờ rom", "prôm pờ"),
    "embedding": ("im bét đinh", "em bét đinh"),  # "em bé" la tu thuong
    "chunking": ("chăn king",),  # "chân kinh" la tu Han Viet
    "retrieval": ("ri tri vồ", "ri tri vần"),
    "hallucination": ("ha lu xi nây sần",),
    "fine-tune": ("phai tiun", "phai chun"),
    "agent": ("ây gien", "ây giần"),
}


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower()


# dang dai truoc ("con ca rừn hát mắp" truoc "hát mắp"); bien la khong phai chu/so de khong cat giua tu
_LOOKUP = {_nfc(v): term for term, variants in STT_TERMS.items() for v in variants}
_PATTERN = re.compile(r"(?<!\w)(" + "|".join(re.escape(v).replace(r"\ ", r"\s+")
                                             for v in sorted(_LOOKUP, key=len, reverse=True)) + r")(?!\w)",
                      re.IGNORECASE)


def normalize_stt_terms(text: str) -> str:
    """Thay dang phien am bang thuat ngu; van ban khong co dang nao trong bang giu nguyen tung ky tu."""
    nfc = unicodedata.normalize("NFC", text)
    if not _PATTERN.search(nfc):
        return text
    # IGNORECASE khop rong hon lower() ("ſ" ~ "s", "İ" ~ "i"): khoa khong co trong bang thi giu nguyen doan do
    return _PATTERN.sub(lambda m: _LOOKUP.get(" ".join(_nfc(m.group(0)).split()), m.group(0)), nfc)

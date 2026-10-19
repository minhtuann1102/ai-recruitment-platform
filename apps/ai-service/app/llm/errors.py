class ConfigError(RuntimeError):
    """Cau hinh moi truong thieu hoac sai."""


class LlmError(RuntimeError):
    """Loi khi goi LLM sau khi het retry/repair."""


class LlmOutputError(LlmError):
    """Dau ra LLM khong dung dinh dang (cat cut hoac sai schema sau repair)."""

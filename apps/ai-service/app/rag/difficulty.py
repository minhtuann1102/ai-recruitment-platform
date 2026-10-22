"""Map do kho noi bo 1-5 sang cot knowledge_chunks.difficulty (docs/ai-service/01 muc 2.1)."""


def difficulty_bucket(level: int) -> str:
    """1-2 -> easy, 3 -> medium, 4-5 -> hard."""
    if not 1 <= level <= 5:
        raise ValueError(f"do kho phai trong 1-5, nhan {level}")
    if level <= 2:
        return "easy"
    return "medium" if level == 3 else "hard"

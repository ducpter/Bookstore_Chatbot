import re
from typing import Optional, Set

# Affirmative responses in Vietnamese
AFFIRMATIVE_RESPONSES: Set[str] = {
    "có", "ok", "ừ", "oke", "được", "yes", "đúng", "đồng ý", "mua", 
    "có chứ", "được chứ", "ok luôn", "mua luôn", "lấy luôn", "đúng rồi",
    "chốt", "chốt đơn", "lấy", "đặt"
}

def is_affirmative(text: str) -> bool:
    """Check if the text is an affirmative response in Vietnamese"""
    text = text.lower().strip()
    return any(text == resp or text.startswith(f"{resp} ") or text.endswith(f" {resp}") 
              for resp in AFFIRMATIVE_RESPONSES)

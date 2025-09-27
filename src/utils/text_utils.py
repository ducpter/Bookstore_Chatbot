import re
from typing import Optional

ORDER_KW = ["mua", "đặt", "ship", "giao", "lấy", "order"]
LOOKUP_KW = ["giá", "còn không", "tác giả", "thể loại", "tồn kho", "bao nhiêu", "tìm", "tra cứu", "có sách", "stock"]
NOISE_WORDS = ["cuốn", "quyển", "bản", "copies", "copy", "books", "book", "mình", "cho", "xin", "tôi", "của", "cái", "với", "và", "là", "có"]

re_qty = re.compile(r"(\d+)\s*(cuốn|quyển|bản|copies?|books?)", re.IGNORECASE)
re_phone = re.compile(r"(\+?\d{9,12})")

def classify_intent_heuristic(text: str) -> str:
    """Phân loại ý định dựa trên từ khóa"""
    t = text.lower()
    # Ưu tiên ORDER trước LOOKUP
    if any(k in t for k in ORDER_KW): 
        return "ORDER"
    if any(k in t for k in LOOKUP_KW):
        return "LOOKUP"
    # Có từ "muốn" -> có thể là ORDER
    if "muốn" in t:
        return "ORDER"
    return "LOOKUP"

def guess_quantity(text: str) -> Optional[int]:
    """Tìm số lượng sách trong câu"""
    # Tìm theo pattern cụ thể trước
    m = re_qty.search(text)
    if m: 
        try: return int(m.group(1))
        except: return None
        
    # Sau đó mới tìm số đứng một mình
    nums = re.findall(r"\b(\d{1,3})\b", text)
    return int(nums[0]) if nums else None

def guess_phone(text: str) -> Optional[str]:
    """Tìm số điện thoại trong câu"""
    m = re_phone.search(text)
    return m.group(1) if m else None

def clean_title(text: str) -> str:
    """Làm sạch và chuẩn hóa tên sách"""
    # Chuyển về chữ thường
    text = text.lower()
    
    # Loại bỏ dấu câu và ký tự đặc biệt
    text = re.sub(r'[,.!?;:"\']', ' ', text)
    
    # Thay thế nhiều khoảng trắng bằng một khoảng trắng
    text = re.sub(r'\s+', ' ', text)
    
    # Viết hoa chữ cái đầu mỗi từ
    text = text.title()
    
    return text.strip()

def guess_title(text: str) -> Optional[str]:
    """Tìm tên sách trong câu"""
    if not text:
        return None
        
    # Chuẩn hóa text
    text = text.lower().strip()
    
    # Các pattern để tách tên sách
    patterns = [
        # Pattern 1: "sách/cuốn/quyển X"
        r"(?:sách|cuốn|quyển|tập|truyện)\s+(.+?)(?:\s+của|\s*$)",
        
        # Pattern 2: "mua/đặt/tìm X"
        r"(?:mua|đặt|tìm|order)\s+(.+?)(?:\s+của|\s*$)",
        
        # Pattern 3: "muốn X"
        r"muốn\s+(?:mua\s+)?(.+?)(?:\s+của|\s*$)",
        
        # Pattern 4: lấy text sau các từ chỉ thị
        r"(?:về|là|tên|nhan đề)\s+(.+?)(?:\s+của|\s*$)",
        
        # Pattern 5: lấy toàn bộ text (fallback)
        r"^(.+?)(?:\s+của|\s*$)"
    ]
    
    # Thử từng pattern
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            title = match.group(1).strip()
            # Loại bỏ các từ nhiễu
            for word in NOISE_WORDS:
                title = re.sub(fr'\b{word}\b', '', title, flags=re.IGNORECASE)
            # Chuẩn hóa khoảng trắng
            title = re.sub(r'\s+', ' ', title).strip()
            if title and len(title) >= 2:
                return title
                
    return None

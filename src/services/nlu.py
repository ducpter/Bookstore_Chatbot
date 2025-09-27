import os
import json
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# ============================================================
# 1️⃣ Load environment variables (.env ở gốc dự án)
# ============================================================
env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".env"
)
load_dotenv(env_path)

api_key = os.getenv("GOOGLE_API_KEY", "").strip()
print(f"[DEBUG] API key length: {len(api_key)}")
if api_key:
    print(f"[DEBUG] API key starts with: {api_key[:10]}...")

# ============================================================
# 2️⃣ Configure Gemini (2.0 flash)
# ============================================================
USE_LLM = False
MODEL_NAME = "gemini-2.0-flash"

try:
    import google.generativeai as genai
    print("[DEBUG] Imported google.generativeai successfully")

    if not api_key:
        print("[ERROR] No GOOGLE_API_KEY found in .env")
    else:
        genai.configure(api_key=api_key)
        try:
            # Test connection
            model = genai.GenerativeModel(MODEL_NAME)
            test_resp = model.generate_content("Xin chào, Gemini!")
            print(f"[DEBUG] Gemini test response: {test_resp.text[:50]}...")
            print(f"[DEBUG] Connected to Gemini using model: {MODEL_NAME}")
            USE_LLM = True
        except Exception as e:
            print(f"[ERROR] Gemini API test failed: {e}")

except ImportError:
    print("[ERROR] google-generativeai not installed. Run:")
    print("       pip install google-generativeai python-dotenv pydantic")

# ============================================================
# 3️⃣ Define schema for extraction
# ============================================================
class LlmExtraction(BaseModel):
    intent: Literal["ORDER", "LOOKUP", "UNKNOWN"]
    title: Optional[str] = None
    quantity: Optional[int] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    customer_name: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    missing_fields: List[str] = Field(default_factory=list)

# ============================================================
# 4️⃣ Prompt few-shot setup
# ============================================================
SYSTEM_INSTRUCTION = """Bạn là NLU (Natural Language Understanding) cho chatbot bán sách.
Phân tích câu nhập của người dùng và trả về JSON theo schema:
{
  "intent": "ORDER|LOOKUP|UNKNOWN",
  "title": str|null,
  "quantity": int|null,
  "address": str|null,
  "phone": str|null,
  "customer_name": str|null,
  "author": str|null,
  "category": str|null,
  "missing_fields": [str]
}
Quy tắc:
- Nếu người dùng có ý định mua/đặt/giao sách → intent=ORDER.
- Nếu người dùng hỏi thông tin (giá, tồn kho, tác giả, thể loại) → intent=LOOKUP.
- Với ORDER, liệt kê các trường còn thiếu vào missing_fields.
- Chuẩn hóa tên sách (bỏ 'cuốn', 'quyển', 'mình muốn', 'cho mình', ...).
- Chỉ trả JSON hợp lệ, không thêm văn bản khác.
"""

FEWSHOTS = [
    ("Mình mua 2 cuốn Đắc Nhân Tâm ship về 10 Trần Hưng Đạo, Hoàn Kiếm, Hà Nội. 0912345678",
     {"intent": "ORDER", "title": "Đắc Nhân Tâm", "quantity": 2,
      "address": "10 Trần Hưng Đạo, Hoàn Kiếm, Hà Nội", "phone": "0912345678",
      "customer_name": None, "author": None, "category": None, "missing_fields": []}),
    ("Cho mình 1 quyển Dế Mèn Phiêu Lưu Ký",
     {"intent": "ORDER", "title": "Dế Mèn Phiêu Lưu Ký", "quantity": 1,
      "address": None, "phone": None, "customer_name": None,
      "author": None, "category": None, "missing_fields": ["address", "phone"]}),
    ("Sách Sapiens giá bao nhiêu, còn hàng không?",
     {"intent": "LOOKUP", "title": "Sapiens", "quantity": None,
      "address": None, "phone": None, "customer_name": None,
      "author": "Yuval Noah Harari", "category": None, "missing_fields": []}),
    ("Có sách kỹ năng sống nào hay không?",
     {"intent": "LOOKUP", "title": None, "quantity": None,
      "address": None, "phone": None, "customer_name": None,
      "author": None, "category": "Kỹ năng sống", "missing_fields": []}),
    ("mình muốn đắc nhân tâm",
     {"intent": "ORDER", "title": "Đắc Nhân Tâm", "quantity": None,
      "address": None, "phone": None, "customer_name": None,
      "author": None, "category": None, "missing_fields": ["quantity", "address", "phone"]})
]



# ============================================================
# 5️⃣ Extraction function
# ============================================================
def llm_extract(user_text: str) -> LlmExtraction:
    """Use Gemini 2.0 Flash to extract structured intent and entities."""
    if not USE_LLM:
        print("[WARN] Gemini not available; fallback to UNKNOWN intent.")
        return LlmExtraction(intent="UNKNOWN", missing_fields=["title", "quantity", "address", "phone"])

    try:
        model = genai.GenerativeModel(
            MODEL_NAME,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.9,
                "max_output_tokens": 512,
                "response_mime_type": "application/json"
            },
        )

        # Build messages with few-shot examples
        msgs = [{"role": "user", "parts": [SYSTEM_INSTRUCTION]}]
        for inp, outp in FEWSHOTS:
            msgs.append({"role": "user", "parts": [inp]})
            msgs.append({"role": "model", "parts": [json.dumps(outp, ensure_ascii=False)]})

        msgs.append({"role": "user", "parts": [f"Phân tích câu: {user_text}"]})

        response = model.generate_content(msgs)
        raw = response.text
        if not raw:
            raise ValueError("Empty LLM response")

        data = json.loads(raw)
        return LlmExtraction(**data)

    except Exception as e:
        print(f"[ERROR] LLM extraction failed: {e}")
        return LlmExtraction(intent="UNKNOWN", missing_fields=["title", "quantity", "address", "phone"])

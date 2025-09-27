from typing import Optional, Tuple
import re
from src.models.types import Ctx, Draft
from src.database.db import book_pick_one_by_title, book_search, create_order_tx
from src.utils.text_utils import guess_quantity, guess_phone, guess_title
from src.utils.vietnamese import is_affirmative

def handle_lookup(draft: Draft, title=None, author=None, category=None) -> Tuple[str, Optional[dict]]:
    """Returns (message, book_info if found and unique)"""
    rows = book_search(keyword=title, author=author, category=category)
    if not rows:
        return "Không tìm thấy sách phù hợp. Bạn có thể cho mình tên sách/tác giả/thể loại rõ hơn?", None
    if len(rows) == 1:
        b = rows[0]
        book_info = dict(rows[0])  # Convert to regular dict
        msg = f"Sách: {b['title']} — Tác giả: {b['author']} — Giá: {int(b['price']):,}đ — Tồn kho: {b['stock']} — Thể loại: {b['category']}. Mua không?"
        return msg, book_info
    s = ["Mình thấy vài lựa chọn, chọn số nhé:"]
    for i, r in enumerate(rows, 1):
        s.append(f"{i}) {r['title']} ({r['author']}) — {int(r['price']):,}đ — còn {r['stock']}")
    return "\n".join(s), None

def resolve_book_id(draft: Draft):
    if draft.title and not draft.book_id:
        b = book_pick_one_by_title(draft.title)
        if b:
            draft.book_id = b["book_id"]
            draft.title = b["title"]

def handle_order(ctx: Ctx, user_text: str) -> str:
    d = ctx.draft
    
    # Check for affirmative response to previous book suggestion
    if ctx.next_state == "ASK_QUANTITY" and is_affirmative(user_text):
        return f"Bạn muốn mua mấy cuốn '{d.title}'?"
        
    # naive fill
    qty = guess_quantity(user_text)
    phone = guess_phone(user_text)
    title_key = guess_title(user_text)
    
    if qty: d.quantity = qty
    if phone: d.phone = phone
    if title_key and not d.title: d.title = title_key
    resolve_book_id(d)

    if not d.title or not d.book_id:
        ctx.next_state = "ASK_TITLE"
        return "Bạn muốn mua sách nào ạ?"
    if not d.quantity or d.quantity <= 0:
        ctx.next_state = "ASK_QUANTITY"
        return f"Bạn muốn mua mấy cuốn '{d.title}'?"
    if not d.address or len(d.address) < 6:
        if ctx.next_state == "ASK_ADDRESS" and not phone and not qty:
            d.address = user_text
        if not d.address or len(d.address) < 6:
            ctx.next_state = "ASK_ADDRESS"
            return "Cho mình xin địa chỉ nhận hàng nhé."
    if not d.phone or len(re.sub(r"\D","", d.phone)) < 9:
        ctx.next_state = "ASK_PHONE"
        return "Bạn cho mình xin số điện thoại liên hệ khi giao nhé."

    ok, msg, order_id, remaining = create_order_tx(d.book_id, d.quantity, d.customer_name, d.phone, d.address)
    if ok:
        ctx.intent, ctx.next_state, ctx.draft = None, None, Draft()
        return f"Xác nhận đơn: '{d.title}' x {d.quantity}, giao {d.address}, SĐT {d.phone}.\nĐã tạo đơn #{order_id}. Trạng thái: CONFIRMED. Cảm ơn bạn!"
    else:
        if remaining is not None and remaining >= 0:
            ctx.next_state = "ASK_QUANTITY"
            return f"{msg} Bạn muốn điều chỉnh số lượng còn {remaining} không?"
        return f"Tạo đơn không thành công: {msg}"

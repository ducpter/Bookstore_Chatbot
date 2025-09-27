import os
import re
import sqlite3
import threading
from typing import List, Any, Optional
from sqlite3 import Row

DB_PATH = os.getenv("DB_PATH", "bookstore.db")
_db_lock = threading.Lock()

SEED_BOOKS = [
    (1, "Đắc Nhân Tâm", "Dale Carnegie", 85000, 14, "Kỹ năng sống"),
    (2, "Dế Mèn Phiêu Lưu Ký", "Tô Hoài", 52000, 30, "Thiếu nhi"),
    (3, "Sapiens", "Yuval Noah Harari", 189000, 7, "Lịch sử"),
    (4, "Harry Potter và Hòn Đá Phù Thủy", "J.K. Rowling", 120000, 18, "Fantasy"),
    (5, "Tuổi Thơ Dữ Dội", "Phùng Quán", 98000, 4, "Văn học"),
]

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(seed=False):
    conn = get_conn()
    with conn:
        conn.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS Books (
          book_id     INTEGER PRIMARY KEY,
          title       TEXT NOT NULL,
          author      TEXT,
          price       REAL NOT NULL,
          stock       INTEGER NOT NULL DEFAULT 0,
          category    TEXT
        );
        CREATE TABLE IF NOT EXISTS Orders (
          order_id       INTEGER PRIMARY KEY AUTOINCREMENT,
          customer_name  TEXT,
          phone          TEXT,
          address        TEXT,
          book_id        INTEGER NOT NULL,
          quantity       INTEGER NOT NULL,
          status         TEXT NOT NULL DEFAULT 'PENDING',
          created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(book_id) REFERENCES Books(book_id)
        );
        """)
        if seed:
            conn.execute("DELETE FROM Orders")
            conn.execute("DELETE FROM Books")
            conn.executemany(
                "INSERT INTO Books(book_id, title, author, price, stock, category) VALUES (?,?,?,?,?,?)",
                SEED_BOOKS
            )
    conn.close()

def normalize_text(text: str) -> str:
    """Chuẩn hóa text để so sánh"""
    if not text:
        return ""
    # Bỏ dấu câu và khoảng trắng
    text = re.sub(r'[,.!?;:"\']', '', text)
    # Chuyển về lowercase và bỏ khoảng trắng dư
    return re.sub(r'\s+', ' ', text.lower().strip())

def book_search(keyword: Optional[str]=None, author: Optional[str]=None, category: Optional[str]=None) -> List[Row]:
    """Tìm sách theo từ khóa, tác giả hoặc thể loại"""
    conn = get_conn()
    try:
        sql = ["SELECT * FROM Books WHERE 1=1"]
        params: List[Any] = []
        
        if keyword:
            # Chuẩn hóa keyword
            norm_keyword = normalize_text(keyword)
            # Tìm kiếm theo nhiều pattern khác nhau
            sql.append("""AND (
                LOWER(title) LIKE LOWER(?) OR 
                ? LIKE '%' || LOWER(title) || '%' OR
                LOWER(REPLACE(title, ' ', '')) LIKE LOWER(REPLACE(?, ' ', ''))
            )""")
            params.extend([f"%{norm_keyword}%", norm_keyword, norm_keyword])
            
        if author:
            sql.append("AND LOWER(author) LIKE LOWER(?)")
            params.append(f"%{author}%")
            
        if category:
            sql.append("AND LOWER(category) = LOWER(?)")
            params.append(category)
            
        # Sort by relevance (title match), then stock
        sql.append("ORDER BY CASE WHEN LOWER(title) = LOWER(?) THEN 1 ELSE 2 END, stock DESC, title ASC LIMIT 10")
        params.append(keyword or "")
        
        cur = conn.execute(" ".join(sql), params)
        return cur.fetchall()
    finally:
        conn.close()

def book_pick_one_by_title(title_key: str) -> Optional[Row]:
    rows = book_search(keyword=title_key)
    if not rows:
        return None
    def norm(s: str): 
        return re.sub(r"\s+"," ", s.strip()).lower()
    for r in rows:
        if norm(r["title"]) == norm(title_key):
            return r
    return rows[0]

def create_order_tx(book_id: int, quantity: int, customer_name: Optional[str], phone: str, address: str):
    """Return (ok, message, order_id, remaining_stock_if_fail)"""
    conn = get_conn()
    with _db_lock:
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute("SELECT stock FROM Books WHERE book_id = ?", (book_id,))
            row = cur.fetchone()
            if not row:
                conn.execute("ROLLBACK")
                return False, "Không tìm thấy sách.", None, None
            stock = row["stock"]
            if stock < quantity:
                conn.execute("ROLLBACK")
                return False, f"Hiện chỉ còn {stock} cuốn.", None, stock
            conn.execute("UPDATE Books SET stock = stock - ? WHERE book_id = ?", (quantity, book_id))
            cur = conn.execute(
                """INSERT INTO Orders(customer_name, phone, address, book_id, quantity, status)
                   VALUES(?,?,?,?,?,'CONFIRMED')""",
                (customer_name, phone, address, book_id, quantity)
            )
            order_id = cur.lastrowid
            conn.execute("COMMIT")
            return True, "Đã tạo đơn hàng thành công.", order_id, None
        except Exception as e:
            conn.execute("ROLLBACK")
            return False, f"Lỗi: {e}", None, None
        finally:
            conn.close()

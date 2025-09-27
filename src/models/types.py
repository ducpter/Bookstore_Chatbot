from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Draft:
    title: Optional[str] = None
    quantity: Optional[int] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    customer_name: Optional[str] = None
    book_id: Optional[int] = None

@dataclass
class Ctx:
    intent: Optional[str] = None
    draft: Draft = field(default_factory=Draft)
    next_state: Optional[str] = None  # ASK_TITLE / ASK_QUANTITY / ASK_ADDRESS / ASK_PHONE

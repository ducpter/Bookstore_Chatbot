from src.models.types import Ctx, Draft
from src.database.db import init_db
from src.services.nlu import USE_LLM, llm_extract
from src.services.chat import handle_lookup, handle_order
from src.utils.text_utils import classify_intent_heuristic, guess_title

def step(ctx: Ctx, user_text: str) -> str:
    # 1) NLU
    if USE_LLM:
        try:
            llm = llm_extract(user_text)
            if not ctx.intent or ctx.intent == "UNKNOWN":
                ctx.intent = "ORDER" if llm.intent == "ORDER" else ("LOOKUP" if llm.intent == "LOOKUP" else None)
            d = ctx.draft
            if llm.title: d.title = llm.title
            if llm.quantity: d.quantity = llm.quantity
            if llm.address: d.address = llm.address
            if llm.phone: d.phone = llm.phone
            if llm.customer_name: d.customer_name = llm.customer_name
            # LOOKUP path using llm fields
            if ctx.intent == "LOOKUP":
                return handle_lookup(d, title=llm.title, author=llm.author, category=llm.category)
        except Exception as e:
            # fallback if LLM fails
            ctx.intent = ctx.intent or classify_intent_heuristic(user_text)

    # Heuristic path
    if not ctx.intent:
        ctx.intent = classify_intent_heuristic(user_text)

    if ctx.intent == "LOOKUP":
        title_key = guess_title(user_text)
        return handle_lookup(ctx.draft, title=title_key)

    # ORDER
    return handle_order(ctx, user_text)

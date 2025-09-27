#!/usr/bin/env python3
import os
import re
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables before anything else
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

# Add the parent directory to sys.path so Python can find our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.types import Ctx, Draft
from src.database.db import init_db
from src.services.nlu import USE_LLM, llm_extract
from src.services.chat import handle_lookup, handle_order
from src.utils.text_utils import classify_intent_heuristic, guess_title
from src.utils.vietnamese import is_affirmative

def step(ctx: Ctx, user_text: str) -> str:
    # Check for affirmative response first
    if ctx.draft.title and is_affirmative(user_text):
        ctx.intent = "ORDER"
        ctx.next_state = "ASK_QUANTITY"
        return f"Bạn muốn mua mấy cuốn '{ctx.draft.title}'?"

    # Always try LLM first if available
    if USE_LLM:
        try:
            print("[Debug] Calling LLM for analysis...")  # Debug log
            llm = llm_extract(user_text)
            print(f"[Debug] LLM result: {llm}")  # Debug log
            
            # Set intent if not already set or if current intent is UNKNOWN
            if not ctx.intent or ctx.intent == "UNKNOWN":
                ctx.intent = llm.intent
            
            # Update draft with LLM extracted info
            d = ctx.draft
            if llm.title: 
                d.title = llm.title
                print(f"[Debug] Setting title to: {d.title}")  # Debug log
            if llm.quantity and llm.quantity > 0: 
                d.quantity = llm.quantity
            if llm.address: 
                d.address = llm.address
            if llm.phone: 
                d.phone = llm.phone
            if llm.customer_name: 
                d.customer_name = llm.customer_name
            
            # If it's a LOOKUP, use extracted fields
            if ctx.intent == "LOOKUP":
                msg, book_info = handle_lookup(d, title=llm.title, author=llm.author, category=llm.category)
                if book_info:  # If we found a specific book
                    d.title = book_info['title']
                    d.book_id = book_info['book_id']
                return msg
                
        except Exception as e:
            print(f"[Debug] LLM error: {e}")  # Debug log
            ctx.intent = ctx.intent or classify_intent_heuristic(user_text)
    else:
        # Fallback to heuristic path
        ctx.intent = ctx.intent or classify_intent_heuristic(user_text)

    if ctx.intent == "LOOKUP":
        title_key = guess_title(user_text)
        msg, book_info = handle_lookup(ctx.draft, title=title_key)
        if book_info:  # If we found a specific book
            ctx.draft.title = book_info['title']
            ctx.draft.book_id = book_info['book_id']
        return msg

    # ORDER path
    return handle_order(ctx, user_text)

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Debug information
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[DEBUG] No GOOGLE_API_KEY found in environment variables")
    else:
        print(f"[DEBUG] GOOGLE_API_KEY found: {api_key[:5]}...")
    
    parser = argparse.ArgumentParser(description="BookStore Chatbot (Terminal)")
    parser.add_argument("--seed", action="store_true", help="Seed sample data")
    args = parser.parse_args()

    init_db(seed=args.seed)
    ctx = Ctx()

    print("\n== BookStore Chatbot (CLI) ==")
    print("Gõ câu hỏi/đặt hàng. Gõ 'exit' để thoát. (LLM: {} )".format("ON" if USE_LLM else "OFF"))
    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not user:
            continue
        if user.lower() in ("exit","quit","q"):
            print("Bye!")
            break
        reply = step(ctx, user)
        print("Bot:", reply)

if __name__ == "__main__":
    main()

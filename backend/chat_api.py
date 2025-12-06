import os, re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.tools import tool
from db import db

from banking_tools import (
    get_balance, deposit_money, withdraw_money,
    get_transactions, transfer_money
)

# Load DB
load_dotenv()

users_collection = db["users"]
print("DB in use:", db.name)
print("User test:", users_collection.find_one({"account_number": "ABC1234"}))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    account_number: str | None = None
    pin: str | None = None


class ChatResponse(BaseModel):
    reply: str | None = None
    error: str | None = None



# ============= Intent Detection Helpers ============= #

def parse_number(msg: str):
    nums = re.findall(r"\d+", msg)
    return int(nums[0]) if nums else None

def parse_account(msg: str):
    match = re.search(r"[A-Z]{3}[0-9]{4}", msg, re.IGNORECASE)
    return match.group(0).upper() if match else None



# ---------------- CHAT API ---------------- #

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    msg = req.message.lower()
    acc = req.account_number
    pin = req.pin

    # Phase 1: Login
    if msg == "login_auth":
        user = users_collection.find_one({"account_number": acc})

        if not user:
            return ChatResponse(error="Account not found.")

        if pin != user["pin"]:
            return ChatResponse(reply="Incorrect PIN. Try again.")

        return ChatResponse(reply=f"PIN verified. Hello {user['customer_name']}! How may I assist you today?")

    # 🚀 Phase 2: FAST command routing (instant)
    amount = parse_number(msg)

    if "balance" in msg:
        result = get_balance(acc)
        return ChatResponse(reply=f"Your current balance is ₹{result['balance']:,}")

    if "withdraw" in msg or "debit" in msg:
        if not amount:
            return ChatResponse(reply="Please specify an amount to withdraw.")
        result = withdraw_money(acc, amount)
        if "error" in result:
            return ChatResponse(error=result["error"])
        return ChatResponse(reply=f"₹{amount:,} withdrawn successfully! New balance: ₹{result['balance']:,}")

    if "deposit" in msg or "credit" in msg:
        if not amount:
            return ChatResponse(reply="Please specify an amount to deposit.")
        result = deposit_money(acc, amount)
        return ChatResponse(reply=f"₹{amount:,} deposited successfully! New balance: ₹{result['balance']:,}")

    if "transfer" in msg or "send" in msg or "pay" in msg:
        receiver = parse_account(msg)
        if not receiver:
            return ChatResponse(reply="Please specify a correct receiver account.")
        if not amount:
            return ChatResponse(reply="Specify amount to transfer.")
        result = transfer_money(acc, receiver, amount)
        if "error" in result:
            return ChatResponse(error=result["error"])
        return ChatResponse(reply=f"₹{amount:,} sent to {receiver} successfully ✔")

    if "statement" in msg or "history" in msg:
        result = get_transactions(acc)
        if result["transactions"]:
            return ChatResponse(reply="\n".join(result["transactions"]))
        return ChatResponse(reply="No recent transactions.")


    # 🧠 If unclear → fallback to LLM
    return ChatResponse(
        reply="Kindly select a valid service option: Balance | Deposit | Withdrawal | Transfer | Statement"
    )


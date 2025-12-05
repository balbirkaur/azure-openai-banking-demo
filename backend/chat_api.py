import os, re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv

from tools.banking_tools import (
    get_balance, deposit_money, withdraw_money,
    get_transactions, transfer_money,
)

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["banking_ai"]
users_collection = db["users"]

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


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    msg = req.message.strip()
    lower = msg.lower()

    if not req.account_number:  # ⬅ Phase 1
        if lower in ["hi", "hello", "hey"]:
            return ChatResponse(reply="Welcome to ABC Bank. Please enter your account number.")
        user = users_collection.find_one({"account_number": msg.upper()})
        if not user:
            return ChatResponse(reply="Account not found. Please enter a valid account number.")
        return ChatResponse(reply="Account found. Now please enter your PIN.")

    user = users_collection.find_one({"account_number": req.account_number.upper()})
    if not user:
        return ChatResponse(reply="Invalid account. Try again.")

    if not req.pin:  # ⬅ Phase 2
        if msg != user["pin"]:
            return ChatResponse(reply="Incorrect PIN. Please try again.")
        return ChatResponse(reply=f"PIN verified. Hello {user['customer_name']}, how may I assist you today?")

    account_number = req.account_number.upper()

    # ---------------- Banking Commands ---------------- #

    if "balance" in lower:
        res = get_balance(account_number)
        return ChatResponse(reply=f"Your balance is ₹{res['balance']}")

    if "deposit" in lower:
        nums = [int(n) for n in msg.split() if n.isdigit()]
        if not nums:
            return ChatResponse(reply="Specify amount: deposit 200")
        amount = nums[0]
        res = deposit_money(account_number, amount)
        return ChatResponse(reply=f"Deposited ₹{amount}. New balance ₹{res['balance']}")

    if "withdraw" in lower:
        nums = [int(n) for n in msg.split() if n.isdigit()]
        if not nums:
            return ChatResponse(reply="Specify amount: withdraw 200")
        amount = nums[0]
        res = withdraw_money(account_number, amount)
        if "error" in res:
            return ChatResponse(reply=res["error"])
        return ChatResponse(reply=f"Withdrawn ₹{amount}. New balance ₹{res['balance']}")

    # 🔥 FIXED receiver account extraction
    if any(x in lower for x in ["transfer", "send", "pay"]):
        nums = [int(n) for n in msg.split() if n.isdigit()]
        if not nums:
            return ChatResponse(reply="Specify amount: transfer 200 to ABC5678")
        amount = nums[0]

        receiver_ac = None
        match = re.search(r"\bto\s+([A-Za-z0-9]+)\b", msg, re.IGNORECASE)
        if match:
            receiver_ac = match.group(1).upper()
        else:
            parts = re.findall(r"[A-Za-z0-9]+", msg)
            if len(parts) >= 2:
                receiver_ac = parts[-1].upper()

        print("Receiver extracted:", receiver_ac)

        if not receiver_ac:
            return ChatResponse(reply="Provide receiver account number.")

        res = transfer_money(account_number, receiver_ac, amount)
        if "error" in res:
            return ChatResponse(reply=res["error"])
        return ChatResponse(reply=f"Sent ₹{amount} to {receiver_ac}")

    if "statement" in lower or "history" in lower:
        res = get_transactions(account_number)
        tx = res["transactions"]
        if not tx:
            return ChatResponse(reply="No recent transactions.")
        return ChatResponse(reply="\n".join(tx))

    return ChatResponse(reply="I can help with balance, withdraw, deposit, transfer, or statement.")

import os
import json
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from dotenv import load_dotenv

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# ========== ENV + DB SETUP ========== #
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI not set in .env")

client = MongoClient(MONGO_URI)
db = client["banking_ai"]
users_collection = db["users"]
print("DB in use:", db.name)
print("User test:", users_collection.find_one({"account_number": "ABC1234"}))


# ========== FASTAPI APP ========== #
app = FastAPI(title="Secure Banking with AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== SCHEMAS ========== #
class ChatRequest(BaseModel):
    message: str
    account_number: Optional[str] = None
    pin: Optional[str] = None


class ChatResponse(BaseModel):
    reply: Optional[str] = None
    error: Optional[str] = None


# ================================================ #
# ========== BANKING HELPERS (TOOLS) ============= #
# ================================================ #
def get_balance(acc: str) -> dict:
    user = users_collection.find_one({"account_number": acc})
    if not user:
        return {"error": "Account not found"}
    return {"balance": user.get("balance", 0)}


def deposit_money(acc: str, amount: int) -> dict:
    if amount <= 0:
        return {"error": "Invalid amount"}

    users_collection.update_one(
        {"account_number": acc},
        {
            "$inc": {"balance": amount},
            "$push": {"transactions": f"➕ Deposit ₹{amount}"}
        }
    )
    return get_balance(acc)


def withdraw_money(acc: str, amount: int) -> dict:
    user = users_collection.find_one({"account_number": acc})
    if not user:
        return {"error": "Account not found"}

    if user.get("balance", 0) < amount:
        return {"error": "Insufficient balance"}

    users_collection.update_one(
        {"account_number": acc},
        {
            "$inc": {"balance": -amount},
            "$push": {"transactions": f"➖ Withdraw ₹{amount}"}
        }
    )
    return get_balance(acc)


def transfer_money(acc: str, receiver: str, amount: int) -> dict:
    sender = users_collection.find_one({"account_number": acc})
    rec = users_collection.find_one({"account_number": receiver})

    if not sender:
        return {"error": "Sender account not found"}
    if not rec:
        return {"error": "Receiver account not found"}
    if sender.get("balance", 0) < amount:
        return {"error": "Insufficient balance"}

    users_collection.update_one(
        {"account_number": acc},
        {
            "$inc": {"balance": -amount},
            "$push": {"transactions": f"🔁 Sent ₹{amount} to {receiver}"}
        }
    )

    users_collection.update_one(
        {"account_number": receiver},
        {
            "$inc": {"balance": amount},
            "$push": {"transactions": f"📥 Received ₹{amount} from {acc}"}
        }
    )

    return get_balance(acc)


def get_transactions(acc: str) -> dict:
    user = users_collection.find_one({"account_number": acc})
    if not user:
        return {"error": "Account not found"}
    return {"transactions": user.get("transactions", [])[-5:]}


# ================================================ #
# ==========  LLM SETUP (WORKING CONFIG) ========= #
# ================================================ #
llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    temperature=0,
)


# ================================================ #
# ==========  MAIN CHAT ENDPOINT ================= #
# ================================================ #
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    msg_raw = req.message or ""
    msg = msg_raw.strip()
    lower = msg.lower()
    acc = req.account_number
    pin = req.pin

    # -------- PHASE 1: LOGIN -------- #
    if lower == "login_auth":
        if not acc or not pin:
            return ChatResponse(error="Account number and PIN required.")

        user = users_collection.find_one({"account_number": acc})
        if not user:
            return ChatResponse(error="Account not found")

        if pin != str(user.get("pin")):
            return ChatResponse(reply="Incorrect PIN ❌ Try again")

        return ChatResponse(
            reply=f"PIN verified. Hello {user['customer_name']}! 😊"
        )

    # -------- PHASE 2: AUTH CHECK -------- #
    if not acc or not pin:
        return ChatResponse(error="Please login first")

    user = users_collection.find_one({"account_number": acc})
    if not user or str(user.get("pin")) != pin:
        return ChatResponse(error="Invalid login credentials")


    # -------- PHASE 3: LLM INTENT PARSING -------- #
    system_prompt = (
        "You are a secure banking assistant for an authenticated user.\n"
        "Supported services: balance, deposit, withdraw, transfer, statement.\n\n"
        "Respond ONLY using JSON:\n"
        "{\n"
        '  "intent": "balance|deposit|withdraw|transfer|statement|greeting|farewell|unsupported",\n'
        '  "amount": <integer or null>,\n'
        '  "receiver": "ABC1234 or null"\n'
        "}\n\n"
        "- If unclear → intent = \"unsupported\"\n"
        "- Hi/Hello = greeting\n"
        "- Thanks/Bye = farewell\n"
        "NO explanation. ONLY JSON!"
    )


    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=msg_raw),
    ]

    try:
        ai_resp = llm.invoke(messages)
        print("LLM RAW RESPONSE:", ai_resp.content)
        decision = json.loads(ai_resp.content)
    except Exception as e:
        print("LLM JSON ERROR:", e)
        return ChatResponse(
            reply="❌ I'm sorry, I didn't understand that. Try again."
        )

    intent = decision.get("intent")
    amount = decision.get("amount")
    receiver = decision.get("receiver")


    # -------- PHASE 4: ACTION ROUTING -------- #

    if intent == "balance":
        res = get_balance(acc)
        return ChatResponse(reply=f"💰 Your balance: ₹{res['balance']:,}")

    if intent == "deposit":
        if amount is None:
            return ChatResponse(reply="Please specify amount")
        res = deposit_money(acc, int(amount))
        if "error" in res:
            return ChatResponse(error=res["error"])
        return ChatResponse(reply=f"➕ ₹{amount:,} deposited ✔")

    if intent == "withdraw":
        if amount is None:
            return ChatResponse(reply="How much to withdraw?")
        res = withdraw_money(acc, int(amount))
        if "error" in res:
            return ChatResponse(error=res["error"])
        return ChatResponse(reply=f"➖ ₹{amount:,} withdrawn ✔")

    if intent == "transfer":
        if not receiver:
            return ChatResponse(reply="Receiver account missing")
        if amount is None:
            return ChatResponse(reply="Amount missing")
        res = transfer_money(acc, receiver, int(amount))
        if "error" in res:
            return ChatResponse(error=res["error"])
        return ChatResponse(
            reply=f"🔁 ₹{amount:,} sent to **{receiver}** successfully"
        )

    if intent == "statement":
        res = get_transactions(acc)
        txns = res.get("transactions", [])

        if not txns:
            return ChatResponse(reply="📭 No transactions found")

        # newest first
        formatted = "\n".join(reversed(txns))

        return ChatResponse(reply=f"📄 Last 5 transactions:\n{formatted}")


    if intent == "greeting":
        return ChatResponse(reply="👋 Hello! How can I help with banking today?")

    if intent == "farewell":
        return ChatResponse(reply="😊 Thank you for banking with us! Bye 👋")

    return ChatResponse(
        reply="🙇 I'm sorry, I can only help with banking-related services."
    )


@app.get("/")
def root():
    return {"status": "ok"}

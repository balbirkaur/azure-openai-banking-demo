import os
import json
from getpass import getpass
from pymongo import MongoClient
from dotenv import load_dotenv

from langchain_core.messages import SystemMessage, HumanMessage
from langchain.tools import tool
from langchain_openai import AzureChatOpenAI

from tools.banking_tools import (
    get_balance, deposit_money, withdraw_money,
    get_transactions, transfer_money
)

# ----------------- SETUP -----------------
load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["banking_ai"]
users_collection = db["users"]

# ----------------- TOOLS -----------------
@tool("check_balance")
def tool_check_balance(account_number: str):
    """Check the current account balance for the specified account number."""
    return get_balance(account_number)

@tool("deposit")
def tool_deposit(account_number: str, amount: int):
    """Deposit a specified amount into the account."""
    return deposit_money(account_number, amount)

@tool("withdraw")
def tool_withdraw(account_number: str, amount: int):
    """Withdraw a specified amount from the account if sufficient balance exists."""
    return withdraw_money(account_number, amount)

@tool("mini_statement")
def tool_statement(account_number: str):
    """Retrieve the last 5 transactions (mini statement) for the account."""
    return get_transactions(account_number)

@tool("fund_transfer")
def tool_fund_transfer(sender_ac: str, receiver_ac: str, amount: int):
    """Transfer funds from sender account to receiver account."""
    return transfer_money(sender_ac, receiver_ac, amount)

tool_list = [
    tool_check_balance,
    tool_deposit,
    tool_withdraw,
    tool_statement,
    tool_fund_transfer,
]
tool_dict = {t.name: t for t in tool_list}

# ----------------- LLM (NO RAG) -----------------
llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0,
).bind_tools(tool_list, tool_choice="auto")

# ----------------- LOGIN FLOW -----------------
print("\n🤖 Banking AI - ABC Bank")

account_number = input("🔢 Account Number: ").strip()
user = users_collection.find_one({"account_number": account_number})

while not user:
    print("❌ Invalid account number!")
    account_number = input("🔢 Account Number: ").strip()
    user = users_collection.find_one({"account_number": account_number})

customer_name = user["customer_name"]
correct_pin = user["pin"]  # plain text PIN

print(f"👋 Hi {customer_name}! Enter your PIN:")
attempts = 3
while attempts > 0:
    pin = getpass("🔐 PIN: ").strip()
    if pin == correct_pin:
        print(f"🔓 Welcome {customer_name}! 😊")
        break
    attempts -= 1
    print(f"❌ Wrong PIN! Attempts left: {attempts}")

if attempts == 0:
    exit("⛔ Account Locked!")

# ----------------- SYSTEM CONTEXT -----------------
system_context = SystemMessage(content=f"""
CRITICAL BANKING INSTRUCTIONS:

AUTHENTICATED USER:
- Customer: {customer_name}
- Account: {account_number}

RULES:
- NEVER ask again for account number or PIN.
- For anything about balance, deposits, withdrawals, statement, or transfers, ALWAYS use the tools.

TOOL ROUTING EXAMPLES:
- "Check my balance" → check_balance("{account_number}")
- "Deposit 1000" → deposit("{account_number}", 1000)
- "Withdraw 500" → withdraw("{account_number}", 500)
- "Show my statement" → mini_statement("{account_number}")
- "Transfer 100 ABC5678" → fund_transfer("{account_number}", "ABC5678", 100)

Be brief, friendly, and secure.
""")

print("💡 Try: 'Check my balance', 'deposit 1000', 'statement', 'transfer 100 ABC5678'")

# ----------------- CHAT LOOP -----------------
while True:
    user_input = input("You: ").strip()
    if user_input.lower() == "exit":
        print(f"👋 Bye {customer_name}, thanks for banking with us!")
        break

    text = user_input.lower()

    # ---------- 1. TRANSFER (must be FIRST) ----------
    if "transfer" in text:
        parts = user_input.split()

        nums = [int(s) for s in parts if s.isdigit()]
        if not nums:
            print("💸 Please specify amount, e.g. 'transfer 100 ABC5678'")
            continue
        amount = nums[0]

        receiver_ac = None
        for token in reversed(parts):
            if not token.isdigit() and token.lower() not in ["to", "transfer"]:
                receiver_ac = token
                break

        if not receiver_ac:
            print("💸 Please specify receiver account, e.g. 'transfer 100 ABC5678'")
            continue

        result = transfer_money(account_number, receiver_ac, amount)
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"✔ Transferred ₹{amount} to {receiver_ac}")
        continue

    # ---------- 2. BALANCE ----------
    if any(word in text for word in ["balance", "bal", "check balance"]):
        result = get_balance(account_number)
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"💰 Your balance: ₹{result['balance']}")
        continue

    # ---------- 3. MINI STATEMENT (no 'transfer') ----------
    if any(word in text for word in ["statement", " history", " transactions"]) and "transfer" not in text:
        result = get_transactions(account_number)
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print("📄 Mini Statement:")
            for t in result["transactions"]:
                print(f"  • {t}")
        continue

    # ---------- 4. DEPOSIT ----------
    if "deposit" in text:
        nums = [int(s) for s in user_input.split() if s.isdigit()]
        if not nums:
            print("💰 Please specify amount, e.g. 'deposit 1000'")
            continue
        amount = nums[0]
        result = deposit_money(account_number, amount)
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"✔ Deposited ₹{amount}. New balance: ₹{result['balance']}")
        continue

    # ---------- 5. WITHDRAW ----------
    if "withdraw" in text:
        nums = [int(s) for s in user_input.split() if s.isdigit()]
        if not nums:
            print("💸 Please specify amount, e.g. 'withdraw 500'")
            continue
        amount = nums[0]
        result = withdraw_money(account_number, amount)
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"✔ Withdrawn ₹{amount}. New balance: ₹{result['balance']}")
        continue

    # ---------- 6. LLM TOOL CALLING (fallback) ----------
    response = llm.invoke([system_context, HumanMessage(content=user_input)])

    tool_calls = []
    if hasattr(response, "message") and hasattr(response.message, "additional_kwargs"):
        tool_calls = response.message.additional_kwargs.get("tool_calls", [])
    elif hasattr(response, "additional_kwargs"):
        tool_calls = response.additional_kwargs.get("tool_calls", [])

    if tool_calls:
        call = tool_calls[0]
        tool_name = call["function"]["name"]
        tool_args = json.loads(call["function"]["arguments"])

        tool_args.setdefault("account_number", account_number)
        if tool_name == "fund_transfer":
            tool_args["sender_ac"] = account_number

        try:
            result = tool_dict[tool_name].invoke(tool_args)
            print(f"✅ {result}")
        except Exception as e:
            print(f"❌ Tool error: {str(e)}")
        continue

    # ---------- 7. DEFAULT HELP ----------
    print("🤖 I can help with: balance, deposit, withdraw, statement, transfer.")

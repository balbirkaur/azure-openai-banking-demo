import os
import json
import re
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

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["banking_ai"]
users_collection = db["users"]

# ========== TOOLS ==========
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

tool_list = [tool_check_balance, tool_deposit, tool_withdraw, tool_statement, tool_fund_transfer]
tool_dict = {t.name: t for t in tool_list}

# ========== LLM (NO RAG) ==========
llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0,
).bind_tools(tool_list, tool_choice="auto")

# ========== LOGIN ==========
print("\n🤖 Banking AI - ABC Bank")
account_number = input("🔢 Account Number: ").strip()
user = users_collection.find_one({"account_number": account_number})

while not user:
    print("❌ Invalid account number!")
    account_number = input("🔢 Account Number: ").strip()
    user = users_collection.find_one({"account_number": account_number})

customer_name = user["customer_name"]
correct_pin = user["pin"]

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

# ========== EXPLICIT SYSTEM CONTEXT ==========
system_context = SystemMessage(content=f"""
CRITICAL BANKING INSTRUCTIONS:

✅ AUTHENTICATED USER:
Customer: {customer_name}
Account: {account_number} ← USE THIS FOR ALL TOOLS

MANDATORY TOOL ROUTING:
"balance", "check balance", "how much money" → check_balance("{account_number}")
"deposit 1000", "add money" → deposit("{account_number}", 1000)  
"withdraw 500" → withdraw("{account_number}", 500)
"statement", "transactions" → mini_statement("{account_number}")
"transfer 1000 XYZ123" → fund_transfer("{account_number}", "XYZ123", 1000)

❌ NEVER ASK FOR ACCOUNT NUMBER OR PIN
✅ ONLY USE TOOLS FOR BANKING OPERATIONS

Be brief and use TOOLS FIRST.
""")

# ========== MAIN CHAT LOOP ==========
print(f"💡 Try: 'Check my balance', 'deposit 1000', 'statement'")
while True:
    user_input = input("You: ").strip()
    if user_input.lower() == "exit":
        print(f"👋 Bye {customer_name}, thanks for banking with us!")
        break

    text = user_input.lower()

    # ========== KEYWORD BACKUP ==========
    if any(word in text for word in ["balance", "bal"]):
        result = get_balance(account_number)
        print(f"💰 Your balance: ₹{result['balance']}")
        continue

    if any(word in text  for word in ["statement", " history", " transactions"]) and "transfer" not in text:
        result = get_transactions(account_number)
        print("📄 Mini Statement:")
        for t in result['transactions']:
            print(f"  • {t}")
        continue

    if "deposit" in text:
        nums = [int(s) for s in user_input.split() if s.isdigit()]
        if nums:
            result = deposit_money(account_number, nums[0])
            print(f"💰 {result}")
        else:
            print("💰 Please specify amount (e.g., 'deposit 1000')")
        continue

    if "withdraw" in text:
        nums = [int(s) for s in user_input.split() if s.isdigit()]
        if nums:
            result = withdraw_money(account_number, nums[0])
            print(f"💸 {result}")
        else:
            print("💸 Please specify amount (e.g., 'withdraw 500')")
        continue

    # ========== LLM TOOL CALLING ==========
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

    # ========== DEFAULT RESPONSE ==========
    print("🤖 How can I help? Try: balance, deposit, withdraw, statement, transfer")

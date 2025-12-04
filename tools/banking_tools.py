from pymongo import MongoClient, ReturnDocument
import os

client = MongoClient(os.getenv("MONGO_URI"))
db = client["banking_ai"]
users_collection = db["users"]

def create_user(name: str, account_number: str, pin: str, initial_balance: int = 0):
    users_collection.insert_one({
        "name": name,
        "account_number": account_number,
        "pin": pin,  # Plain PIN (NO encryption)
        "balance": initial_balance,
        "transactions": [],
    })

def verify_pin(account_number: str, pin: str) -> bool:
    user = users_collection.find_one({"account_number": account_number})
    if not user:
        return False
    return user["pin"] == pin  # Simple string comparison

def get_balance(account_number: str) -> dict:
    user = users_collection.find_one({"account_number": account_number})
    if not user:
        return {"error": "Account not found"}
    return {"balance": user["balance"]}

def deposit_money(account_number: str, amount: int) -> dict:
    if amount <= 0:
        return {"error": "Invalid amount"}
    result = users_collection.find_one_and_update(
        {"account_number": account_number},
        {"$inc": {"balance": amount}, "$push": {"transactions": f"Deposit: ₹{amount}"}},
        return_document=ReturnDocument.AFTER
    )
    if not result:
        return {"error": "Account not found"}
    return {"balance": result["balance"]}

def withdraw_money(account_number: str, amount: int) -> dict:
    if amount <= 0:
        return {"error": "Invalid amount"}
    result = users_collection.find_one_and_update(
        {"account_number": account_number, "balance": {"$gte": amount}},
        {"$inc": {"balance": -amount}, "$push": {"transactions": f"Withdraw: ₹{amount}"}},
        return_document=ReturnDocument.AFTER
    )
    if not result:
        return {"error": "Insufficient balance or account not found"}
    return {"balance": result["balance"]}

def get_transactions(account_number: str) -> dict:
    user = users_collection.find_one({"account_number": account_number})
    if not user:
        return {"error": "Account not found"}
    return {"transactions": user.get("transactions", [])[-5:]}

def transfer_money(sender_ac: str, receiver_ac: str, amount: int) -> dict:
    if amount <= 0:
        return {"error": "Invalid amount"}
    with client.start_session() as session:
        def txn(s):
            sender = users_collection.find_one({"account_number": sender_ac, "balance": {"$gte": amount}}, session=s)
            receiver = users_collection.find_one({"account_number": receiver_ac}, session=s)
            if not sender or not receiver:
                return {"error": "Account not found or insufficient balance"}
            users_collection.update_one({"account_number": sender_ac}, 
                {"$inc": {"balance": -amount}, "$push": {"transactions": f"Transfer Sent: ₹{amount} → {receiver_ac}"}}, session=s)
            users_collection.update_one({"account_number": receiver_ac}, 
                {"$inc": {"balance": amount}, "$push": {"transactions": f"Transfer Received: ₹{amount} ← {sender_ac}"}}, session=s)
            return {"status": "success"}
        return session.with_transaction(txn) or {"error": "Transfer failed"}

from pymongo import MongoClient, ReturnDocument
import os
from db import db

users_collection = db["users"]


def normalize_ac(ac: str) -> str:
    return ac.upper().strip()


def create_user(customer_name: str, account_number: str, pin: str, initial_balance: int = 0):
    account_number = normalize_ac(account_number)
    users_collection.insert_one({
        "customer_name": customer_name,
        "account_number": account_number,
        "pin": pin,
        "balance": initial_balance,
        "transactions": [],
    })


def get_balance(account_number: str) -> dict:
    account_number = normalize_ac(account_number)
    user = users_collection.find_one({"account_number": account_number})
    print(users_collection.find_one({"account_number": "ABC1234"}))

    if not user:
        return {"error": "Account not found"}
    return {"balance": user["balance"]}


def deposit_money(account_number: str, amount: int) -> dict:
    account_number = normalize_ac(account_number)
    if amount <= 0:
        return {"error": "Invalid amount"}

    result = users_collection.find_one_and_update(
        {"account_number": account_number},
        {"$inc": {"balance": amount},
         "$push": {"transactions": f"Deposit ₹{amount}"}},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        return {"error": "Account not found"}
    return {"balance": result["balance"]}


def withdraw_money(account_number: str, amount: int) -> dict:
    account_number = normalize_ac(account_number)
    if amount <= 0:
        return {"error": "Invalid amount"}

    result = users_collection.find_one_and_update(
        {"account_number": account_number, "balance": {"$gte": amount}},
        {"$inc": {"balance": -amount},
         "$push": {"transactions": f"Withdraw ₹{amount}"}},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        return {"error": "Insufficient balance or account not found"}
    return {"balance": result["balance"]}


def get_transactions(account_number: str) -> dict:
    account_number = normalize_ac(account_number)
    user = users_collection.find_one({"account_number": account_number})
    if not user:
        return {"error": "Account not found"}
    return {"transactions": user.get("transactions", [])[-5:]}


def transfer_money(sender_ac: str, receiver_ac: str, amount: int) -> dict:
    sender_ac = normalize_ac(sender_ac)
    receiver_ac = normalize_ac(receiver_ac)

    if amount <= 0:
        return {"error": "Invalid amount"}
    if sender_ac == receiver_ac:
        return {"error": "Cannot transfer to the same account"}

    sender = users_collection.find_one({"account_number": sender_ac})
    receiver = users_collection.find_one({"account_number": receiver_ac})
 
    if not sender:
        return {"error": "Sender account not found"}
    if not receiver:
        return {"error": "Receiver account not found"}
    if sender["balance"] < amount:
        return {"error": "Insufficient balance"}

    users_collection.update_one(
        {"account_number": sender_ac},
        {"$inc": {"balance": -amount},
         "$push": {"transactions": f"Sent ₹{amount} to {receiver_ac}"}}
    )

    users_collection.update_one(
        {"account_number": receiver_ac},
        {"$inc": {"balance": amount},
         "$push": {"transactions": f"Received ₹{amount} from {sender_ac}"}}
    )

    return {"status": "success", "amount": amount, "to": receiver_ac}

from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

uri = os.getenv("MONGO_URI")
if not uri:
    raise ValueError("❌ MONGO_URI not found in environment variables!")

client = MongoClient(uri)
db = client["banking_db"]

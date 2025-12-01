import os
import random
from dotenv import load_dotenv

# Clean console output
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Azure + LangChain imports
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

# Load environment variables
load_dotenv()

# Azure Chat LLM
llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0
)

# Azure Embeddings Model
embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
)

# Load RAG Documents
loader = DirectoryLoader("./docs", glob="*.txt", loader_cls=TextLoader)
docs = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# FAISS Vector DB (zero telemetry)
vectordb = FAISS.from_documents(chunks, embeddings)

# Conversation Memory
memory = ConversationBufferMemory(
    memory_key="chat_history", return_messages=True
)

# RAG Conversational Chain
qa_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=vectordb.as_retriever(search_kwargs={"k": 1}),
    memory=memory
)


# ------------------ Banking State -------------------
authenticated = False
correct_pin = "1234"
balance = 25500
transactions = []
last_intents = []

def add_txn(action, amount=0):
    transactions.append(f"{action}: ₹{amount}")
    if len(transactions) > 5:
        transactions.pop(0)

def reset_intent():
    last_intents.clear()


# ------------------ Chat Loop -----------------------
print("\n🤖 Banking AI Agent Ready (Azure RAG + FAISS)")
print("Please enter your PIN:\n")

while True:
    user_input = input("You: ").lower().strip()

    if user_input == "exit":
        print("👋 Thank you for banking with us!")
        break

    # Login
    if not authenticated:
        if user_input == correct_pin:
            authenticated = True
            print("🔓 Login successful! How can I assist you?")
        else:
            print("❌ Wrong PIN. Try again.")
        continue

    # Unblock Card
    if "unblock" in user_input and "card" in user_input:
        reset_intent()
        print("🔓 Your card has been unblocked successfully!")
        continue

    # Block Card
    if "block" in user_input and "card" in user_input:
        reset_intent()
        ticket = random.randint(100000, 999999)
        add_txn("Card Block")
        print(f"🔒 Card blocked successfully.\n📝 Ticket#: {ticket}")
        continue

    # Balance
    if "balance" in user_input:
        print(f"💰 Current balance: ₹{balance}")
        continue

    # Mini Statement
    if "transaction" in user_input or "statement" in user_input:
        if transactions:
            print("📄 Recent transactions:")
            for t in transactions:
                print("  •", t)
        else:
            print("📄 No recent transactions.")
        continue

    # Deposit
    if "deposit" in user_input or ("deposit" in last_intents):
        reset_intent()
        last_intents.append("deposit")
        nums = [int(s) for s in user_input.split() if s.isdigit()]
        if not nums:
            print("💰 Enter deposit amount:")
            continue
        amount = nums[0]
        balance += amount
        add_txn("Deposit", amount)
        print(f"✔ Deposited ₹{amount}. New Balance ₹{balance}")
        continue

    # Withdraw
    if "withdraw" in user_input or ("withdraw" in last_intents):
        reset_intent()
        last_intents.append("withdraw")
        nums = [int(s) for s in user_input.split() if s.isdigit()]
        if not nums:
            print("💸 Enter withdrawal amount:")
            continue
        amount = nums[0]
        if amount > balance:
            print("⚠ Insufficient balance!")
        else:
            balance -= amount
            add_txn("Withdraw", amount)
            print(f"✔ Withdrawn ₹{amount}. Remaining balance ₹{balance}")
        continue

    # RAG fallback (Banking FAQs)
    result = qa_chain.invoke({"question": user_input})
    print("🤖 Agent:", result["answer"])

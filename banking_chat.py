import os
import random
from dotenv import load_dotenv

# Disable token parallel warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Azure OpenAI + LangChain
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import DirectoryLoader, TextLoader

#  Updated LangChain RAG API
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.prompts import ChatPromptTemplate


# Load environment
load_dotenv()

# Azure Chat Model
llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0
)

# Embedding Model
embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
)

# Load RAG Docs
loader = DirectoryLoader("./docs", glob="*.txt", loader_cls=TextLoader)
docs = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# FAISS Vector Store
vectorstore = FAISS.from_documents(chunks, embeddings)

# ---------------- RAG Prompt ----------------
prompt = ChatPromptTemplate.from_template(
    """
    You are a helpful banking support assistant.
    Use the context below to answer briefly and correctly:

    Context:
    {context}

    Question:
    {input}
    """
)

doc_chain = create_stuff_documents_chain(llm, prompt)
qa_chain = create_retrieval_chain(vectorstore.as_retriever(), doc_chain)

# ---------------- Banking System ----------------

def add_txn(type, amount=0):
    transactions.append(f"{type}: ₹{amount}")
    if len(transactions) > 5:
        transactions.pop(0)


# ---------------- Chat Loop ----------------
print("\n🤖 Banking AI Agent (Azure RAG + FAISS)")
print("Welcome to ABC Bank virtual assistant!")

stage = "ask_name"
customer_name = ""
account_number = ""
authenticated = False
correct_pin = "1234"
balance = 25500
transactions = []

while True:
    user_input = input("You: ").strip()

    if user_input.lower() == "exit":
        print(f"👋 Thank you for banking with us, {customer_name or 'customer'}!")
        break

    # Onboarding flow
    if stage == "ask_name":
        print("🤖 May I know your name?")
        stage = "get_name"
        continue

    if stage == "get_name":
        customer_name = user_input
        print(f"🤖 Nice to meet you, {customer_name}! Please enter your account number:")
        stage = "get_account"
        continue

    if stage == "get_account":
        account_number = user_input
        print(f"🤖 Thanks, {customer_name}. Please enter your 4‑digit PIN:")
        stage = "get_pin"
        continue

    if stage == "get_pin":
        if user_input == correct_pin:
            authenticated = True
            stage = "chat"
            print(f"🔓 Login successful for A/C {account_number}. How can I help you today?")
        else:
            print("❌ Incorrect PIN. Try again:")
        continue

    # After this point, user is authenticated and normal logic runs
    if not authenticated:
        print("⛔ Session error. Please restart.")
        break

    text = user_input.lower()

    # Commands
    if "balance" in text:
        print(f"💰 {customer_name}, your available balance is: ₹{balance}")
        continue

    if "withdraw" in text:
        nums = [int(s) for s in text.split() if s.isdigit()]
        if not nums:
            print("💸 Enter the amount to withdraw (for example: withdraw 1000):")
            continue
        amt = nums[0]
        if amt > balance:
            print("⚠ Insufficient balance!")
        else:
            balance -= amt
            add_txn("Withdraw", amt)
            print(f"✔ Withdrawn ₹{amt}. New balance: ₹{balance}")
        continue

    if "deposit" in text:
        nums = [int(s) for s in text.split() if s.isdigit()]
        if not nums:
            print("💰 Enter deposit amount (for example: deposit 2000):")
            continue
        amt = nums[0]
        balance += amt
        add_txn("Deposit", amt)
        print(f"✔ Deposited ₹{amt}. New balance: ₹{balance}")
        continue

    if "statement" in text or "transactions" in text:
        if not transactions:
            print("📄 No recent transactions")
        else:
            print("📄 Mini Statement:")
            for t in transactions:
                print(" -", t)
        continue

    if "block" in text and "card" in text:
        ticket = random.randint(100000, 999999)
        add_txn("Card Block")
        print(f"🔒 Card blocked.\n📝 Ticket#: {ticket}")
        continue

    # RAG fallback
    result = qa_chain.invoke({
        "input": user_input,
        "authenticated": authenticated,
        "balance": balance,
        "transactions": transactions,
        "customer_name": customer_name,
        "account_number": account_number,
    })
    print("🤖 Agent:", result["answer"])

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
authenticated = False
correct_pin = "1234"
balance = 25500
transactions = []


def add_txn(type, amount=0):
    transactions.append(f"{type}: ₹{amount}")
    if len(transactions) > 5:
        transactions.pop(0)


# ---------------- Chat Loop ----------------
print("\n🤖 Banking AI Agent (Azure RAG + FAISS)")
print("Please enter your PIN:\n")

while True:
    user_input = input("You: ").strip().lower()

    if user_input == "exit":
        print("👋 Thank you for banking with us!")
        break

    # Login Check
    if not authenticated:
        if user_input == correct_pin:
            authenticated = True
            print("🔓 Login successful! How can I help?")
        else:
            print("❌ Incorrect PIN. Try again.")
        continue

    # Commands
    if "balance" in user_input:
        print(f"💰 Available balance: ₹{balance}")
        continue

    if "withdraw" in user_input:
        nums = [int(s) for s in user_input.split() if s.isdigit()]
        if not nums:
            print("💸 Enter the amount to withdraw:")
            continue
        amt = nums[0]
        if amt > balance:
            print("⚠ Insufficient balance!")
        else:
            balance -= amt
            add_txn("Withdraw", amt)
            print(f"✔ Withdrawn {amt}. New balance: ₹{balance}")
        continue

    if "deposit" in user_input:
        nums = [int(s) for s in user_input.split() if s.isdigit()]
        if not nums:
            print("💰 Enter deposit amount:")
            continue
        amt = nums[0]
        balance += amt
        add_txn("Deposit", amt)
        print(f"✔ Deposited {amt}. New balance: ₹{balance}")
        continue

    if "statement" in user_input or "transactions" in user_input:
        if not transactions:
            print("📄 No recent transactions")
        else:
            print("📄 Mini Statement:")
            for t in transactions:
                print(" -", t)
        continue

    if "block" in user_input and "card" in user_input:
        ticket = random.randint(100000, 999999)
        add_txn("Card Block")
        print(f"🔒 Card blocked.\n📝 Ticket#: {ticket}")
        continue

    # -------------- RAG Fallback ----------------
    result = qa_chain.invoke({"input": user_input})
    print("🤖 Agent:", result["answer"])

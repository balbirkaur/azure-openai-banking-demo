# 🏦 Banking AI Agent — Azure OpenAI + LangChain + FAISS

A smart conversational **Banking AI Agent** powered by **Azure OpenAI**, **LangChain**, and **FAISS Vector DB**.  
Supports secure banking actions and RAG-based answers using custom banking documents — fully local execution for **low-cost demos**.

---

## 🚀 Features

| Capability                             | Status |
| -------------------------------------- | :----: |
| PIN Login Authentication               |   ✅   |
| Check Balance                          |   ✅   |
| Withdraw & Deposit                     |   ✅   |
| Block & Unblock Card                   |   ✅   |
| Mini Transaction Statement             |   ✅   |
| FAQ support via RAG (docs in `./docs`) |   ✅   |
| FAISS for Vector Search (No telemetry) |   ✅   |
| Azure Chat LLM Integration             |   ✅   |

---

## 🧠 Tech Stack

- Azure OpenAI Service (Chat + Embeddings)
- LangChain Conversational Retrieval Chain
- FAISS Local Vector DB
- Python 3.10/3.11
- Retrieval-Augmented Generation (RAG)

---

## 📂 Folder Structure

anking-ai-agent/
│
├── banking_chat.py # Main application
├── docs/ # Knowledge base for RAG
│ └── banking_faq.txt
├── .env # Azure credentials (not committed)
├── requirements.txt # Dependencies list
└── README.md # Project documentation

---

## 🔧 Setup & Installation

### Step 1️⃣ — Clone Repository

````bash
git clone <your-repo-url>
cd banking-ai-agent
```bash

Step 2️⃣ — Setup Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate
```bash
Step 4️⃣ — Environment Variables (.env)
```bash
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-chat-deployment-name
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=your-embedding-deployment-name
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```bash


You: 1234
🔓 Login successful!
You: balance
💰 Current balance: ₹25500
You: withdraw 500
✔ Withdrawn ₹500. Remaining: ₹25000
You: block my card
🔒 Card blocked. Ticket#: 123456
You: what is KYC?
🤖 Agent: KYC means Know Your Customer...

````

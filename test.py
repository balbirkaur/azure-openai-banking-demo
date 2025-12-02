import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

print("🔍 Testing Azure OpenAI Connection…")

try:
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        messages=[{"role": "user", "content": "Hello Azure!"}],
    )
    print("✔ SUCCESS! Azure Chat Response:")
    print(response.choices[0].message.content)

except Exception as e:
    print("❌ FAILED:", e)

import os

from groq import Groq

from  dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

print(f"Using Groq model: {GROQ_MODEL}")
print(f"Groq API key set: {GROQ_API_KEY }")

client = Groq(
    api_key=GROQ_API_KEY
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Explain the importance of fast language models",
        }
    ],
    model=GROQ_MODEL,
    temperature=0.3,
)

print(chat_completion.choices[0].message.content)
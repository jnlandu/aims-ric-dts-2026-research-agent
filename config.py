import os
from dotenv import load_dotenv

load_dotenv()

# GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_KEY="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"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# print(f"Using Groq model: {GROQ_MODEL}")
# print(f"Groq API key set: {'Yes' if GROQ_API_KEY else 'No'}")

# Search settings
MAX_SEARCH_QUERIES = 3
MAX_RESULTS_PER_QUERY = 5
MAX_CONTENT_LENGTH = 3000  # max chars to extract per page

# Agent settings
TEMPERATURE = 0.3

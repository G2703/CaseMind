import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key loaded: {api_key[:10]}..." if api_key else "No API key found")

genai.configure(api_key=api_key)

# Create model and test (using gemini-1.5-flash which has better quota)
model = genai.GenerativeModel("gemini-2.5-flash")

# Simple test
response = model.generate_content("Say 'Hello, Gemini API is working!' if you can read this.")

print("\n--- Gemini API Test Result ---")
print(response.text)
print("--- Test Complete ---\n")

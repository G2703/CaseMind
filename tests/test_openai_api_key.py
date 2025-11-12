from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize the OpenAI client with the API key from environment variable
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

try:
    # Make a simple API call to list models
    # This is a good way to verify authentication without incurring significant cost.
    models = client.models.list()
    print("API key is valid. Available models:")
    for model in models.data:
        print(f"- {model.id}")

    # Alternatively, you can try a chat completion:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Hello, world!"}
        ]
    )
    print("Chat completion successful:", response.choices[0].message.content)

except Exception as e:
    # Check for authentication errors
    if "Incorrect API key" in str(e) or "Invalid API key" in str(e):
        print("Invalid OpenAI API key. Please check your key.")
    elif "API key" in str(e):
        print(f"API key related error: {e}")
    else:
        print(f"An error occurred: {e}")
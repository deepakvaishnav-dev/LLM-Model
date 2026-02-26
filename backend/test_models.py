import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY"))

try:
    models = client.models.list()
    for m in models:
        for action in m.supported_actions:
            if "embedContent" in action or "embed" in action:
                print(f"Supported Embedding Model: {m.name}")
except Exception as e:
    print(e)

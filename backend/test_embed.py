import os
from dotenv import load_dotenv

from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")

try:
    print("Testing with: models/gemini-embedding-001")
    embed = GoogleGenAIEmbedding(api_key=google_api_key, model="models/gemini-embedding-001")
    print("Embedding test 1:")
    print(embed.get_text_embedding("Hello world")[:2])
except Exception as e:
    import traceback
    traceback.print_exc()

try:
    print("Testing with: gemini-embedding-001")
    embed2 = GoogleGenAIEmbedding(api_key=google_api_key, model="gemini-embedding-001")
    print("Embedding test 2:")
    print(embed2.get_text_embedding("Hello world")[:2])
except Exception as e:
    import traceback
    traceback.print_exc()

try:
    import google.genai
    client = google.genai.Client(api_key=google_api_key)
    res = client.models.embed_content(model="models/gemini-embedding-001", contents="Hello world")
    print("DIRECT API CALL test:")
    print(res.embeddings[0].values[:2])
except Exception as e:
    import traceback
    traceback.print_exc()

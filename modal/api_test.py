import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------
# Modal API URL is loaded from .env file
# Set MODAL_API_URL in your .env file
# It usually looks like: https://your-username--text-embeddings-inference-api-text-embed-7389a1.modal.run
# ---------------------------------------------------------
API_URL = os.getenv("MODAL_API_URL", "").strip()

if not API_URL:
    raise ValueError("MODAL_API_URL not found in .env file. Please set it to your Modal endpoint URL.") 

def test_embeddings():
    print(f"Testing API at: {API_URL}")
    
    # 1. Define the input text
    payload = {
        "inputs": [
            "Hello, this is a test sentence.",
            "Running text embeddings on Modal is fast."
        ]
    }

    try:
        # 2. Send POST request
        response = requests.post(API_URL, json=payload)
        
        # 3. Check for errors
        response.raise_for_status()
        
        # 4. Parse the result
        data = response.json()
        
        # 5. Display results
        model_name = data.get("model", "Unknown")
        embeddings = data.get("embeddings", [])
        dims = data.get("dimensions", 0)
        
        print("\n--- Success! ---")
        print(f"Model used: {model_name}")
        print(f"Vector dimensions: {dims}")
        print(f"Number of texts embedded: {len(embeddings)}")
        
        # Print the first few numbers of the first embedding to verify
        if embeddings:
            print(f"\nFirst 5 values of first embedding:\n{embeddings[0][:5]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"\nError calling API: {e}")
        if response is not None:
             print(f"Server response: {response.text}")

if __name__ == "__main__":
    test_embeddings()
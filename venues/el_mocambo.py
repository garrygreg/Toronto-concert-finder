import os
import json
import re
import sys
from google import genai
from google.genai import types

# 1. Setup API
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

VENUE_NAME = "El Mocambo"
LISTING_URL = "https://elmocambo.com/events-new/"

def get_data():
    # Force the model to be a JSON-only machine
    prompt = f"""
    Visit {LISTING_URL} and extract all upcoming concerts.
    
    Return the data as a JSON array of objects with these exact keys: 
    "date" (YYYY-MM-DD), "artist", "url", "venue", "price", "age".
    
    RULES:
    - If you find no concerts, return an empty array: []
    - Every 'url' must be the direct link to the event on elmocambo.com.
    - DO NOT include any introductory text or thinking. ONLY the JSON array.
    """
    
    try:
        # We're using a very simple config to avoid "Thinking" loops or timeouts
        response = client.models.generate_content(
            model="gemini-2.0-flash", # Using 2.0 Flash for maximum speed/stability in this test
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(url_context=types.UrlContext())],
                # Explicitly request JSON format to help the model stay in bounds
                response_mime_type="application/json"
            )
        )
        
        # 2. Extract and Print
        # Even with mime_type, we use regex as a safety net for main.py
        text = response.text.strip()
        
        # If the model didn't return brackets, we wrap it or provide an empty one
        if not text.startswith('['):
            # Sometimes models return a single object instead of a list
            if text.startswith('{'):
                print(f"[{text}]")
            else:
                print("[]")
        else:
            print(text)
            
    except Exception as e:
        # Log the error to stderr so it shows up in your 'Logs:' section in main.py
        print(f"ERROR: {str(e)}", file=sys.stderr)
        print("[]")

if __name__ == "__main__":
    get_data()

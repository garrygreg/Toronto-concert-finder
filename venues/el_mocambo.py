import os
import json
import datetime
from google import genai
from google.genai import types

# Setup
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

VENUE_NAME = "El Mocambo"
LISTING_URL = "https://elmocambo.com/events-new/"

def get_data():
    prompt = f"""
    Visit {LISTING_URL} and extract upcoming concerts.
    
    LITERAL EXTRACTION RULES:
    1. FIND DEEP LINKS: Copy the exact 'href' for the specific show page. 
    2. TARGET: Any concert from today onwards.
    3. VENUE: Use "{VENUE_NAME}".
    
    Return a raw JSON array: "date" (YYYY-MM-DD), "artist", "url", "venue", "price", "age".
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(url_context=types.UrlContext())]
            )
        )
        
        # Clean the response to ensure only JSON is printed
        import re
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            # We PRINT the JSON to stdout so main.py can capture it
            print(json_match.group(0))
        else:
            print("[]")
            
    except Exception as e:
        # If it fails, print an empty array so main.py doesn't crash
        print("[]")

if __name__ == "__main__":
    get_data()

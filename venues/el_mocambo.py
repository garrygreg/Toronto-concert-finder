import os
import json
import re
import sys
from google import genai
from google.genai import types

# Setup
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

VENUE_NAME = "El Mocambo"
LISTING_URL = "https://elmocambo.com/events-new/"

def get_data():
    # We give the model "Hints" about the current date and what to look for
    today = "2026-04-27" 
    
    prompt = f"""
    MANDATORY MISSION: Extract the concert calendar for {VENUE_NAME}.
    
    PRIMARY SOURCE: {LISTING_URL}
    BACKUP SOURCE: Use Google Search to find 'El Mocambo Toronto upcoming events April 2026' if the primary link is blocked.
    
    EXTRACTION RULES:
    1. DATE: Extract in YYYY-MM-DD. (Note: It is currently April 2026).
    2. DEEP LINKS: Find the unique event page URL (usually starts with 'https://elmocambo.com/event/'). 
    3. ARTIST: Extract the full headliner name.
    4. NO HALLUCINATIONS: If you see a 'Bo Steezy' or 'Everything 80s' event, capture it.

    Return ONLY a raw JSON array of objects: "date", "artist", "url", "venue", "price", "age".
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(url_context=types.UrlContext()),
                    types.Tool(google_search=types.GoogleSearch()) # Backup tool
                ]
            )
        )
        
        # Look for the JSON block
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        
        if json_match:
            # We print ONLY the JSON to satisfy the Master script
            print(json_match.group(0))
        else:
            # If it fails, print the model's text to stderr so you can see it in logs 
            # but it won't break the JSON parsing of the Master script.
            print(f"DEBUG: Model failed to find JSON. Response was: {response.text[:200]}", file=sys.stderr)
            print("[]")
            
    except Exception as e:
        print(f"DEBUG: Script Error: {str(e)}", file=sys.stderr)
        print("[]")

if __name__ == "__main__":
    get_data()

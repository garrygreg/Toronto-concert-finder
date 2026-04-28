import os
import json
import re
import sys
from google import genai
from google.genai import types

# Setup API
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

VENUE_NAME = "El Mocambo"
LISTING_URL = "https://elmocambo.com/events-new/"

def get_data():
    today = "2026-04-27"
    
    prompt = f"""
    Visit {LISTING_URL} and extract all upcoming concerts from {today} onwards.
    
    LITERAL EXTRACTION RULES:
    1. THE "HREF" RULE: Find the <a> tag for every concert. Copy the 'href' attribute EXACTLY.
    2. NO GUESSING: If a deep link on elmocambo.com is not visible in the HTML, skip the event.
    3. DOMAIN LOCKDOWN: Every URL must be on elmocambo.com.
    
    Return ONLY a JSON array: "date", "artist", "url", "venue", "price", "age", "youtube_sample".
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(url_context=types.UrlContext())],
                # Re-enabling Thinking mode for precision
                thinking_config={'include_thoughts': True}
            )
        )
        print(response.text)
            
    except Exception as e:
        print(f"DEBUG: {str(e)}", file=sys.stderr)
        print("[]")

if __name__ == "__main__":
    get_data()

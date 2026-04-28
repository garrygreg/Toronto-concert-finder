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
    today = "2026-04-27"
    
    prompt = f"""
    Visit {LISTING_URL} and extract all upcoming concerts from {today} onwards.
    
    LITERAL EXTRACTION RULES:
    1. THE "HREF" RULE: You must find the <a> tag for every concert listing. Copy the 'href' attribute EXACTLY.
    2. NO GUESSING: Only return links that exist on elmocambo.com.
    3. SEARCH VERIFICATION: Use your search tool to verify the 'El Mocambo' calendar if the page appears empty.
    
    Return a JSON array of objects: "date" (YYYY-MM-DD), "artist", "url", "venue", "price", "age", "youtube_sample".
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(url_context=types.UrlContext()),
                    types.Tool(google_search=types.GoogleSearch())
                ],
                # This 'Thinking' process is what allows it to parse the complex HTML
                thinking_config={'include_thoughts': True}
            )
        )
        
        # 2. Extract and Print
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            print(json_match.group(0))
        else:
            # Send the model's actual reasoning/response to stderr for debugging
            print(f"DEBUG: No JSON found. Model response: {response.text[:200]}", file=sys.stderr)
            print("[]")
            
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        print("[]")

if __name__ == "__main__":
    get_data()

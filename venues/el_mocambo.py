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
    Visit {LISTING_URL} and perform a forensic audit of EVERY concert container.
    
    TASK: There are approximately 16-20 concerts on this page. You are currently only finding 11. You must find ALL of them.
    
    AUDIT CHECKLIST:
    1. SCAN THE WHOLE PAGE: Do not stop until you hit the footer.
    2. IGNORE DESCRIPTIONS: Do not extract the 'Perk Check-in' or 'Bio' text. Only focus on the Date, Artist, and the 'href' link.
    3. LITERAL HREF: For every single event, find the link that points to '{VENUE_NAME.lower()}.com/event/'. 
       - Example: 'everything-80s-party'
       - Example: 'global-warming-2026-way-better-north-america-tour'
    4. NO SUMMARIZATION: Even if two shows look similar or happen in the same week, they must be separate entries.
    
    Return ONLY a JSON array: "date", "artist", "url", "venue", "price", "age".
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
                # 'Thinking' helps it navigate the long list without getting bored
                thinking_config={'include_thoughts': True}
            )
        )
        
        # Capture the JSON
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            
            # Python-side cleanup for URLs and Date sorting
            for entry in data:
                if entry['url'].startswith('/'):
                    entry['url'] = f"https://elmocambo.com{entry['url']}"
                entry['venue'] = VENUE_NAME
                
            print(json.dumps(data))
        else:
            print(f"DEBUG: No JSON found. Response: {response.text[:150]}", file=sys.stderr)
            print("[]")
            
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        print("[]")

if __name__ == "__main__":
    get_data()

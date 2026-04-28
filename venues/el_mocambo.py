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
    today = "2026-04-27"
    
    # We use the 'Forensic' instructions that finally cracked the links earlier
    prompt = f"""
    Visit this specific Toronto venue page: {LISTING_URL}
    
    TASK: Extract all upcoming concerts from {today} onwards.
    
    LITERAL EXTRACTION RULES:
    1. NO GUESSING: Do not construct URLs based on the artist name. 
    2. THE "HREF" RULE: You must look at the HTML 'href' attribute for the "More Info" button or the Artist Name. Copy that link EXACTLY as it is written in the code.
       - Example: If the link is '/event/global-warming-tour', copy it exactly.
    3. DOMAIN LOCKDOWN: Every 'url' MUST stay on the official domain: elmocambo.com.
    4. NO TICKETING: If a link goes to Ticketmaster or Eventbrite, ignore it. Find the link that stays on elmocambo.com.
    5. DATA COMPLETENESS: Find EVERY concert listing on the page. Do not stop at the first one.
    
    Return a raw JSON array of objects: "date" (YYYY-MM-DD), "artist", "url" (LITERAL HREF), "venue", "price", "age", "youtube_sample".
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(url_context=types.UrlContext())]
            )
        )
        
        # Capture JSON array
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group(0))
            
            # Ensure relative links become full URLs
            for entry in data:
                if entry['url'].startswith('/'):
                    entry['url'] = f"https://elmocambo.com{entry['url']}"
                entry['venue'] = VENUE_NAME
            
            # Print ONLY the final JSON for main.py to capture
            print(json.dumps(data))
        else:
            # For debugging in GitHub logs if it returns empty
            print(f"DEBUG: No JSON found. Model response: {response.text[:150]}", file=sys.stderr)
            print("[]")
            
    except Exception as e:
        print(f"DEBUG: API or Script Error: {str(e)}", file=sys.stderr)
        print("[]")

if __name__ == "__main__":
    get_data()

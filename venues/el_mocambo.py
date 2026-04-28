import os
import json
import re
import sys
import datetime
from google import genai
from google.genai import types

# 1. Setup API
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

VENUE_NAME = "El Mocambo"
LISTING_URL = "https://elmocambo.com/events-new/"

def get_data():
    # 2. Define Date Range (Today through +1 Year)
    # Since it is currently April 2026, this stays dynamic.
    today = datetime.date.today()
    one_year_later = today + datetime.timedelta(days=365)
    
    prompt = f"""
    Visit {LISTING_URL} and perform a forensic audit of EVERY concert container.
    
    TASK: Extract EVERY concert that occurs between {today} and {one_year_later}.
    
    AUDIT CHECKLIST:
    1. SCAN THE WHOLE PAGE: Do not stop until you hit the footer.
    2. IGNORE DESCRIPTIONS: Only focus on Date, Artist, and the 'href' link.
    3. LITERAL HREF: Find the link that points to 'elmocambo.com/event/'.
    
    Return ONLY a JSON array: "date" (YYYY-MM-DD), "artist", "url", "venue", "price", "age".
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
                thinking_config={'include_thoughts': True}
            )
        )
        
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            
            filtered_data = []
            for entry in data:
                try:
                    # 3. Apply Strict Date Filter in Python
                    event_date = datetime.datetime.strptime(entry['date'], "%Y-%m-%d").date()
                    
                    if today <= event_date <= one_year_later:
                        # Fix URLs and Venue Name as before
                        if entry['url'].startswith('/'):
                            entry['url'] = f"https://elmocambo.com{entry['url']}"
                        entry['venue'] = VENUE_NAME
                        filtered_data.append(entry)
                except (ValueError, KeyError):
                    # Skip any records with invalid dates or missing keys
                    continue
            
            # Print only the filtered list for main.py
            print(json.dumps(filtered_data))
        else:
            print(f"DEBUG: No JSON found. Response: {response.text[:150]}", file=sys.stderr)
            print("[]")
            
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        print("[]")

if __name__ == "__main__":
    get_data()

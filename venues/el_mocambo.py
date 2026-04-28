import os
import json
import re
import sys
import datetime
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

VENUE_NAME = "El Mocambo"
LISTING_URL = "https://elmocambo.com/events-new/"

def get_data():
    today = datetime.date.today()
    one_year_later = today + datetime.timedelta(days=365)
    
    prompt = f"""
    Visit {LISTING_URL} and audit every concert from {today} to {one_year_later}.
    
    CRITICAL INSTRUCTIONS:
    1. ARTIST NAME: Extract the main bold TITLE of the event (usually the largest text in the card). 
       - DO NOT use category tags (e.g., 'Live Music').
       - DO NOT include descriptions.
    2. DATE: YYYY-MM-DD.
    3. URL: The exact 'href' to the event page.
    
    Return a JSON array: "date", "artist", "url", "venue", "price", "age".
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(url_context=types.UrlContext()), types.Tool(google_search=types.GoogleSearch())],
                thinking_config={'include_thoughts': True}
            )
        )
        
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            filtered_data = []
            for entry in data:
                try:
                    event_date = datetime.datetime.strptime(entry['date'], "%Y-%m-%d").date()
                    if today <= event_date <= one_year_later:
                        if entry['url'].startswith('/'):
                            entry['url'] = f"https://elmocambo.com{entry['url']}"
                        entry['venue'] = VENUE_NAME
                        filtered_data.append(entry)
                except: continue
            print(json.dumps(filtered_data))
        else:
            print("[]")
    except:
        print("[]")

if __name__ == "__main__":
    get_data()

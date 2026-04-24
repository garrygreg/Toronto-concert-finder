import os
import json
import datetime
import re
import time
from google import genai
from google.genai import types

# 1. Setup API Client
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

today = datetime.date.today()
next_year = today + datetime.timedelta(days=364)

listing_pages = [
    "https://masseyhall.mhrth.com/tickets/",
    "https://www.historytoronto.com/events",
    "https://www.thedanforth.com/",
    "https://theoperahousetoronto.com/events/",
    "https://horseshoetavern.com/",
    "https://www.leespalace.com/",
    "http://www.garrisontoronto.com/",
    "https://elmocambo.com/events-new/",
    "https://thegreathall.ca/calendar/",
    "https://thephoenixconcerttheatre.com/events/"
]

def scrape_single_venue(url):
    """Deep-link extraction for a single venue using Gemini 3."""
    # We add a specific 'Context' instruction to stop it from using the main URL
    prompt = f"""
    Visit this specific Toronto venue page: {url}
    
    TASK: 
    1. Identify every individual concert listing on this page.
    2. For EACH listing, you MUST find the unique URL that leads to that specific artist's event detail page. 
    3. This is usually the link attached to the 'Tickets', 'More Info', 'Buy', or the Artist's Name itself.
    
    STRICT URL EXTRACTION RULES:
    - NEVER use the main listing URL ({url}) as the 'url' for an artist.
    - If the page uses a pop-up or doesn't have a deep link, use Google Search to find the official event page on the venue's domain.
    - Example of a GOOD link: 'https://masseyhall.mhrth.com/tickets/waxahatchee-mj-lenderman/'
    - Example of a BAD link: '{url}'
    
    Return a raw JSON array of objects with: 
    "date" (YYYY-MM-DD), "artist", "url" (the deep link), "venue", "price", "age", "youtube_sample".
    """
    
    response = client.models.generate_content(
        model="gemini-3-flash-preview", 
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(url_context=types.UrlContext()),
                types.Tool(google_search=types.GoogleSearch())
            ],
            # We add thinking_config back in for ONE venue at a time to ensure deep-link precision
            thinking_config={'include_thoughts': True}
        )
    )
    return response.text

# 2. Main Execution Loop (Unchanged from previous successful logic)
all_concerts = []

for url in listing_pages:
    success = False
    max_retries = 3
    attempt = 0
    
    while not success and attempt < max_retries:
        try:
            print(f"Deep-Scanning: {url}...")
            raw_output = scrape_single_venue(url)
            
            json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)
            if json_match:
                venue_data = json.loads(json_match.group(0))
                # Final check: filter out any entries that accidentally used the main URL
                for entry in venue_data:
                    if entry['url'].strip('/') == url.strip('/'):
                        # If it failed to find a deep link, we don't want it.
                        entry['url'] = "SEARCHING..." 
                
                all_concerts.extend(venue_data)
                success = True
                print(f"   Success! Extracted {len(venue_data)} deep links.")
            else:
                attempt += 1
                time.sleep(5)

        except Exception as e:
            if "503" in str(e):
                time.sleep(20)
                attempt += 1
            else:
                print(f"   Skipping {url}: {e}")
                break

# 3. Save Final Results
if all_concerts:
    # Sort and Clean
    unique_concerts = []
    seen = set()
    for c in all_concerts:
        key = f"{c.get('date')}-{c.get('artist')}"
        if key not in seen:
            unique_concerts.append(c)
            seen.add(key)
    
    unique_concerts.sort(key=lambda x: x.get('date', '9999-99-99'))

    with open("concerts.json", "w") as f:
        json.dump(unique_concerts, f, indent=4)
    print(f"\n--- DEEP SCRAPE COMPLETE: {len(unique_concerts)} Events ---")
else:
    exit(1)

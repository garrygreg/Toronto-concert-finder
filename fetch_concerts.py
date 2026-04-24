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

# THE SOURCE OF TRUTH: listing one per line makes it easy to add more later
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
    """Surgical extraction for a single venue using Gemini 3."""
    prompt = f"""
    Visit this specific Toronto venue page: {url}
    
    EXTRACT all upcoming concert data from {today} to {next_year}.
    
    Required Fields:
    - "date" (YYYY-MM-DD)
    - "artist" (Full name)
    - "url" (The EXACT 'More Info' or 'Ticket' link found on the page. NO guessing.)
    - "venue" (The name of the venue)
    - "price" (The price listed, or 'TBD')
    - "age" (e.g., '19+', 'All Ages')
    - "youtube_sample" (Search link: https://www.youtube.com/results?search_query=[Artist]+Live)

    STRICT RULES:
    1. EXTRACT REAL LINKS: Only provide URLs that actually exist as links on the page.
    2. NO PATTERN GUESSING: If you cannot find a deep link to an individual event, use the main URL: {url}
    3. Return ONLY a raw JSON array.
    """
    
    response = client.models.generate_content(
        model="gemini-3-flash-preview", 
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(url_context=types.UrlContext()),
                types.Tool(google_search=types.GoogleSearch())
            ]
        )
    )
    return response.text

# 2. Main Execution Loop
all_concerts = []

for url in listing_pages:
    success = False
    max_retries = 3
    attempt = 0
    
    while not success and attempt < max_retries:
        try:
            print(f"Processing: {url}...")
            raw_output = scrape_single_venue(url)
            
            # Extract JSON array
            json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)
            if json_match:
                venue_data = json.loads(json_match.group(0))
                all_concerts.extend(venue_data)
                success = True
                print(f"   Success! Found {len(venue_data)} events.")
            else:
                print(f"   Error: No JSON found for this venue. (Attempt {attempt+1})")
                attempt += 1
                time.sleep(5)

        except Exception as e:
            if "503" in str(e) or "high demand" in str(e).lower():
                wait_time = (attempt + 1) * 20
                print(f"   Server Busy (503). Waiting {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                attempt += 1
            else:
                print(f"   Skipping {url} due to error: {e}")
                break

# 3. Final Data Cleanup & Save
if all_concerts:
    # Deduplicate entries (just in case)
    seen = set()
    unique_concerts = []
    for c in all_concerts:
        # Create a unique key based on date, artist, and venue
        key = f"{c.get('date')}-{c.get('artist')}-{c.get('venue')}"
        if key not in seen:
            unique_concerts.append(c)
            seen.add(key)

    # Sort by date for the website
    unique_concerts.sort(key=lambda x: x.get('date', '9999-99-99'))

    with open("concerts.json", "w") as f:
        json.dump(unique_concerts, f, indent=4)
    
    print(f"\n--- SUCCESS ---")
    print(f"Total Unique Events Saved: {len(unique_concerts)}")
else:
    print("No data collected. Check Action logs for errors.")
    exit(1)

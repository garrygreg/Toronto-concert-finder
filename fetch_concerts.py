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

BANNED_DOMAINS = ["ticketmaster", "livenation", "eventbrite", "dice.fm", "showpass", "universe.com", "ticketweb", "admitone"]

listing_pages = [
    "https://masseyhall.mhrth.com/tickets/",
    "https://www.historytoronto.com/events",
    "https://www.thedanforth.com/shows",
    "https://www.theoperahousetoronto.com/shows/",
    "https://horseshoetavern.com/",
    "https://www.leespalace.com/",
    "http://www.garrisontoronto.com/",
    "https://elmocambo.com/events-new/",
    "https://thegreathall.ca/calendar/",
    "https://thephoenixconcerttheatre.com/events/"
]

def scrape_single_venue(url):
    """Forensic extraction for a single venue using Gemini 3."""
    
    # Static Overrides for venues that don't use deep links (Opera/Garrison/Danforth)
    if any(x in url for x in ["thedanforth.com", "theoperahousetoronto.com", "garrisontoronto.com"]):
        extraction_mode = "STATIC_LINK_MODE"
    else:
        extraction_mode = "DEEP_LINK_MODE"

    prompt = f"""
    Analyze the HTML of this Toronto venue page: {url}
    
    TASK: Extract EVERY upcoming concert from {today} to {next_year}. 
    
    CRITICAL INSTRUCTIONS:
    1. DON'T STOP AT ONE: You must find EVERY concert listing on the page. 
    2. DEEP LINK EXTRACTION: For each concert, find the <a> tag associated with the artist or "More Info." 
       - You MUST extract the literal 'href' value. 
       - NEVER use the current page URL ({url}) if a deeper event URL exists.
    3. SUB-VENUE (LEE'S PALACE): If scraping Lee's Palace, check if the show is in the 'Dance Cave'. 
       - If the URL contains 'dance-cave' or the text says 'Dance Cave', set the venue to "Lee's Palace (Dance Cave)".
    4. DOMAIN SHACKLE: All deep links must stay on the venue's official domain. Ignore Ticketmaster/Eventbrite.
    5. MODE: {extraction_mode} (If STATIC, use {url} for all links. If DEEP, find the individual show page).

    Return a raw JSON array: "date" (YYYY-MM-DD), "artist", "url", "venue", "price", "age", "youtube_sample".
    """
    
    response = client.models.generate_content(
        model="gemini-3-flash-preview", 
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(url_context=types.UrlContext()), types.Tool(google_search=types.GoogleSearch())],
            thinking_config={'include_thoughts': True}
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
            print(f"Auditing: {url}...")
            raw_output = scrape_single_venue(url)
            
            json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)
            if json_match:
                venue_data = json.loads(json_match.group(0))
                
                # Manual Lockdown & Cleaning
                for entry in venue_data:
                    # Fix Danforth/Opera/Garrison specifically
                    if "Danforth" in entry['venue']:
                        entry['url'] = "https://www.thedanforth.com/shows"
                    elif "Opera House" in entry['venue']:
                        entry['url'] = "https://www.theoperahousetoronto.com/shows/"
                    elif "Garrison" in entry['venue']:
                        entry['url'] = "http://www.garrisontoronto.com/"
                    
                    # Ensure Lee's Palace sub-venues are correct
                    if "Lees Palace" in entry['venue'] or "Lee's Palace" in entry['venue']:
                        if "dance-cave" in entry['url'].lower():
                            entry['venue'] = "Lee's Palace (Dance Cave)"

                    # Safety check for Ticketing leaks
                    if any(banned in entry['url'].lower() for banned in BANNED_DOMAINS):
                        entry['url'] = url 
                
                all_concerts.extend(venue_data)
                success = True
                print(f"   Success! Found {len(venue_data)} events.")
            else:
                attempt += 1
                time.sleep(10)

        except Exception as e:
            if "503" in str(e):
                time.sleep(30)
                attempt += 1
            else:
                print(f"   Error: {e}")
                break

# 3. Sort and Save
if all_concerts:
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
    print(f"\n--- SCRAPE COMPLETE: {len(unique_concerts)} Events ---")
else:
    exit(1)

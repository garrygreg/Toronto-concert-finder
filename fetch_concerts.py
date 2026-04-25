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
# Limit to 6 months to reduce token "weight" and prevent timeouts
end_date = today + datetime.timedelta(days=180)

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
    """Surgical extraction with explicit 'No Hallucination' instructions."""
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    official_domain = domain_match.group(1) if domain_match else ""

    # Static Overrides
    if any(x in url for x in ["thedanforth.com", "theoperahousetoronto.com", "garrisontoronto.com"]):
        instruction = f"STATIC MODE: Set 'url' for EVERY show to exactly: {url}"
    else:
        instruction = f"DEEP LINK MODE: Find the literal 'href' attribute for each show's page on {official_domain}."

    prompt = f"""
    Visit {url} and extract concert data from {today} to {end_date}.
    
    {instruction}
    
    EXTRACTION RULES:
    1. FIND EVERY SHOW: Scrape the entire list. If the page is empty, tell me 'EMPTY_PAGE'.
    2. LITERAL LINKS: Copy the exact 'href' from the artist link. 
       - LEE'S/HORSESHOE: Deep links start with '/event/'. 
       - MASSEY: Deep links start with '/tickets/'.
    3. SUB-VENUE: If 'Dance Cave' is mentioned in the link or text, set venue to "Lee's Palace (Dance Cave)".
    4. NO TICKETMASTER: If you only see Ticketmaster links, use {url} as the fallback URL.

    Return ONLY a JSON array: "date", "artist", "url", "venue", "price", "age", "youtube_sample".
    """
    
    # We use gemini-1.5-flash for the actual scrape if gemini-3 is timing out, 
    # but I'll keep gemini-3-flash-preview here as requested.
    response = client.models.generate_content(
        model="gemini-3-flash-preview", 
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(url_context=types.UrlContext())]
        )
    )
    return response.text

# 2. Main Execution Loop
all_concerts = []

for index, url in enumerate(listing_pages):
    print(f"[{index+1}/{len(listing_pages)}] Fetching: {url}...")
    success = False
    retries = 2
    
    while not success and retries >= 0:
        try:
            raw_output = scrape_single_venue(url)
            
            # Diagnostic: Search for JSON
            json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)
            
            if json_match:
                venue_data = json.loads(json_match.group(0))
                
                # Cleanup
                for entry in venue_data:
                    if any(banned in entry['url'].lower() for banned in BANNED_DOMAINS):
                        entry['url'] = url 
                
                all_concerts.extend(venue_data)
                success = True
                print(f"   Success! Found {len(venue_data)} events.")
            else:
                print(f"   Warning: No JSON found for {url}. Model said: {raw_output[:100]}...")
                retries -= 1
                time.sleep(10)

        except Exception as e:
            print(f"   Error on {url}: {e}")
            retries -= 1
            time.sleep(20)

# 3. Final Save
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
    print(f"\n--- DONE: {len(unique_concerts)} Total Events ---")
else:
    print("FATAL: No data collected from any venue.")
    exit(1)

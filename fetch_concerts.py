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

# Banned domains for ticketing redirects
BANNED_DOMAINS = ["ticketmaster", "livenation", "eventbrite", "dice.fm", "showpass", "universe.com", "ticketweb", "admitone"]

# The Sources of Truth
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
    """Fast, literal extraction for a single venue."""
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    official_domain = domain_match.group(1) if domain_match else ""

    # Define Static Overrides directly in the prompt
    if any(x in url for x in ["thedanforth.com", "theoperahousetoronto.com", "garrisontoronto.com"]):
        instruction = f"STATIC MODE: Set the 'url' for EVERY concert at this venue to exactly: {url}"
    else:
        instruction = f"DEEP LINK MODE: Find the literal 'href' attribute for the specific show page on {official_domain}. Do NOT guess slugs."

    prompt = f"""
    Visit {url} and extract the next 30 upcoming concerts from {today} onwards.
    
    {instruction}
    
    LITERAL EXTRACTION RULES:
    1. ARTIST: Extract the full name.
    2. URL: If in DEEP LINK MODE, copy the EXACT link from the HTML <a> tag. 
       - For Lee's Palace/Horseshoe, look for '/event/slug'. 
       - For Massey, look for '/tickets/slug/'.
    3. SUB-VENUE (LEE'S PALACE): If the link or text mentions 'Dance Cave', set the venue to "Lee's Palace (Dance Cave)".
    4. NO TICKETMASTER: Do not use links to ticketing sites. Stay on {official_domain}.
    
    Return a raw JSON array of objects: "date" (YYYY-MM-DD), "artist", "url", "venue", "price", "age", "youtube_sample".
    """
    
    # We remove thinking_config and google_search to prevent 50+ minute hangs
    response = client.models.generate_content(
        model="gemini-3-flash-preview", 
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(url_context=types.UrlContext())]
        )
    )
    return response.text

# 2. Execution Loop
all_concerts = []

for index, url in enumerate(listing_pages):
    success = False
    retries = 2 # Lower retries to prevent the script from running forever
    
    while not success and retries >= 0:
        try:
            print(f"[{index+1}/{len(listing_pages)}] Fetching: {url}...")
            raw_output = scrape_single_venue(url)
            
            json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)
            if json_match:
                venue_data = json.loads(json_match.group(0))
                
                # Double-Check: Filter out banned domains
                for entry in venue_data:
                    if any(banned in entry['url'].lower() for banned in BANNED_DOMAINS):
                        entry['url'] = url 
                
                all_concerts.extend(venue_data)
                success = True
                print(f"   Success! Found {len(venue_data)} events.")
            else:
                retries -= 1
                time.sleep(5)

        except Exception as e:
            print(f"   Error on {url}: {e}")
            retries -= 1
            time.sleep(10)

# 3. Final Sort & Save
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
    print(f"\n--- SCRAPE FINISHED: {len(unique_concerts)} Events Saved ---")
else:
    print("No data collected.")
    exit(1)

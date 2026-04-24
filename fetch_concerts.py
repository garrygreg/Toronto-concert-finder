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

# List of banned domains to ensure we never point to ticketing sites
BANNED_DOMAINS = ["ticketmaster", "livenation", "eventbrite", "dice.fm", "showpass", "universe.com", "ticketweb"]

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
    """Link-Auditor extraction for a single venue using Gemini 3."""
    # We define the 'Official Domain' for the specific venue to help the model stay on-track
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    official_domain = domain_match.group(1) if domain_match else ""

    prompt = f"""
    Visit this Toronto venue page: {url}
    
    TASK: Extract all upcoming concerts from {today} to {next_year}.
    
    LINK AUDIT RULES (CRITICAL):
    1. EVERY 'url' MUST BE ON THE DOMAIN: {official_domain}
    2. LOOK DEEPER: Do not just take the 'Buy Tickets' link. Look for the link attached to the Artist's Name or a 'More Info' / 'About' button.
    3. FORBIDDEN LINKS: If a link contains 'ticketmaster', 'livenation', 'eventbrite', 'dice.fm', or 'showpass', it is DISCARDED.
    4. FALLBACK LOGIC: If a deep link on {official_domain} is not found, use the main listing URL: {url}
    
    Required Fields:
    - "date" (YYYY-MM-DD)
    - "artist" (Full name)
    - "url" (The deep link on {official_domain} ONLY)
    - "venue", "price", "age", "youtube_sample"
    
    Return a raw JSON array.
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
            print(f"Auditing Links for: {url}...")
            raw_output = scrape_single_venue(url)
            
            json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)
            if json_match:
                venue_data = json.loads(json_match.group(0))
                
                # --- POST-EXTRACTION DOMAIN LOCKDOWN ---
                # This ensures we catch any hallucinations or leaks before they hit the site
                for entry in venue_data:
                    is_banned = any(banned in entry['url'].lower() for banned in BANNED_DOMAINS)
                    if is_banned:
                        # Replace the Ticketmaster link with the venue listing page
                        entry['url'] = url 
                
                all_concerts.extend(venue_data)
                success = True
                print(f"   Done. Found {len(venue_data)} events.")
            else:
                attempt += 1
                time.sleep(10)

        except Exception as e:
            if "503" in str(e):
                time.sleep(30)
                attempt += 1
            else:
                print(f"   Skipping {url}: {e}")
                break

# 3. Save Final Results
if all_concerts:
    # Sort and Deduplicate
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
    print(f"\n--- SCRAPE COMPLETE ---")
else:
    exit(1)

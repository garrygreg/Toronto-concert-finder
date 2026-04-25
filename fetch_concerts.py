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

# Banned domains to prevent redirects to third-party ticketing sites
BANNED_DOMAINS = ["ticketmaster", "livenation", "eventbrite", "dice.fm", "showpass", "universe.com", "ticketweb", "admitone"]

# The "Sources of Truth"
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
    """Literal extraction for a single venue using Gemini 3."""
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    official_domain = domain_match.group(1) if domain_match else ""

    # Specific static overrides for venues that do not have detail pages
    if "thedanforth.com" in url:
        static_url = "https://www.thedanforth.com/shows"
    elif "theoperahousetoronto.com" in url:
        static_url = "https://www.theoperahousetoronto.com/shows/"
    elif "garrisontoronto.com" in url:
        static_url = "http://www.garrisontoronto.com/"
    else:
        static_url = url

    prompt = f"""
    Visit this Toronto venue page: {url}
    
    TASK: Extract all upcoming concerts from {today} to {next_year}.
    
    LITERAL EXTRACTION RULES:
    1. NO GUESSING: Do not construct URLs based on the artist name. 
    2. THE "HREF" RULE: You must look at the HTML 'href' attribute for the "More Info" button or the Artist Name. Copy that link EXACTLY as it is written in the code.
       - Example (Lee's): If the code says '/event/blackout-dance-cave', do NOT change it to '/event/blackout'.
       - Example (Massey): If the code says '/tickets/cal-steely-dan-greatest-hits/', do NOT change it to '/tickets/classic-albums-live...'.
    3. DOMAIN LOCKDOWN: Every 'url' MUST stay on the official domain: {official_domain}.
    4. NO TICKETING: If a link goes to Ticketmaster or Eventbrite, ignore it. Find the link that stays on {official_domain}.
    5. STATIC OVERRIDE: For this specific venue, if you cannot find a deep link that stays on {official_domain}, use: {static_url}
    
    Required Fields: "date" (YYYY-MM-DD), "artist", "url" (LITERAL HREF), "venue", "price", "age", "youtube_sample".
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
            print(f"Extracting: {url}...")
            raw_output = scrape_single_venue(url)
            
            json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)
            if json_match:
                venue_data = json.loads(json_match.group(0))
                
                # Double-Check: Filter out banned domains and ensure static fallbacks
                for entry in venue_data:
                    # Fix for Danforth/Opera House based on user request
                    if "Danforth" in entry['venue'] or "thedanforth.com" in entry['url']:
                        entry['url'] = "https://www.thedanforth.com/shows"
                    elif "Opera House" in entry['venue'] or "theoperahousetoronto.com" in entry['url']:
                        entry['url'] = "https://www.theoperahousetoronto.com/shows/"
                    
                    # Prevent Ticketmaster leaks
                    if any(banned in entry['url'].lower() for banned in BANNED_DOMAINS):
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

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

# Banned domains to prevent redirects to ticketing sites
BANNED_DOMAINS = ["ticketmaster", "livenation", "eventbrite", "dice.fm", "showpass", "universe.com", "ticketweb", "admitone"]

# UPDATED LISTING PAGES (Correcting The Opera House URL)
listing_pages = [
    "https://masseyhall.mhrth.com/tickets/",
    "https://www.historytoronto.com/events",
    "https://www.thedanforth.com/",
    "https://www.theoperahousetoronto.com/shows/",
    "https://horseshoetavern.com/",
    "https://www.leespalace.com/",
    "http://www.garrisontoronto.com/",
    "https://elmocambo.com/events-new/",
    "https://thegreathall.ca/calendar/",
    "https://thephoenixconcerttheatre.com/events/"
]

def scrape_single_venue(url):
    """Deep-link audit for a single venue using Gemini 3."""
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    official_domain = domain_match.group(1) if domain_match else ""

    prompt = f"""
    Visit this Toronto venue page: {url}
    
    TASK: Extract all upcoming concerts from {today} to {next_year}.
    
    DEEP LINK BLUEPRINT:
    You MUST find the URL that leads to the specific artist page. Do not be lazy.
    - FOR LEE'S PALACE & HORSESHOE: Look for links starting with '{url}event/'. They are usually hidden behind the artist title or the 'About' button.
    - FOR EL MOCAMBO: Look for links starting with 'https://elmocambo.com/event/'.
    - FOR THE GREAT HALL: Look for links starting with 'https://thegreathall.ca/event/'.
    - FOR MASSEY HALL: Look for links starting with 'https://masseyhall.mhrth.com/tickets/'.
    - FOR OPERA HOUSE & GARRISON: Since deep links are often unavailable, you may use their main listing URL as the 'url'.
    
    STRICT RULES:
    1. DOMAIN LOCKDOWN: Every 'url' MUST be on the official domain: {official_domain}.
    2. NO TICKETING LINKS: If a link contains 'ticketmaster', 'livenation', or 'eventbrite', it is FORBIDDEN. Skip it and look for the 'More Info' link instead.
    3. If no artist-specific page exists on the official domain, use: {url}
    
    Required Fields: "date" (YYYY-MM-DD), "artist", "url", "venue", "price", "age", "youtube_sample".
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

# 2. Main Execution Loop (One at a time)
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
                
                # Manual Check: Ensure no Ticketmaster links snuck through
                for entry in venue_data:
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
    print(f"\n--- SCRAPE COMPLETE: {len(unique_concerts)} Events ---")
else:
    exit(1)

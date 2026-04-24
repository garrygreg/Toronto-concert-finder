import os
import json
import datetime
import re
from google import genai
from google.genai import types

# Use Environment Variable for GitHub, but allow local testing
api_key = os.environ.get("GEMINI_API_KEY", "YOUR_LOCAL_KEY_HERE")
client = genai.Client(api_key=api_key)

today = datetime.date.today()
next_year = today + datetime.timedelta(days=364)

venues = [
    "Massey Hall", "Horseshoe Tavern", "Lee's Palace", "History Toronto", 
    "Phoenix Concert Theatre", "The Danforth Music Hall", "The Opera House", 
    "El Mocambo", "The Garrison", "The Great Hall"
]

# Updated Venue Mapping
venue_map = """
- Massey Hall: https://masseyhall.mhrth.com/tickets/
- History Toronto: https://www.historytoronto.com/events/detail/
- The Danforth Music Hall: https://www.thedanforth.com/events/detail/
- The Opera House: https://www.theoperahousetoronto.com/events/
- Horseshoe Tavern: https://horseshoetavern.com/event/
- Lee's Palace: https://www.leespalace.com/event/
- The Garrison: http://www.garrisontoronto.com/
- El Mocambo: https://elmocambo.com/event/
- The Great Hall: https://thegreathall.ca/event/
- Phoenix Concert Theatre: https://thephoenixconcerttheatre.com/events/event/
"""

prompt = f"""
Using Google Search, find the specific unique event detail URLs for upcoming concerts at these Toronto venues:
{venue_map}

Return a JSON array of objects with: "date", "artist", "url", "venue", "price", "age", "youtube_sample".

STRICT ARTIST LINK RULES:
1. OFFICIAL DOMAINS ONLY: Every "url" MUST use the official domain from the map. Under no circumstances use ticketmaster.ca, livenation.com, or any other third-party ticketing site.
2. EL MOCAMBO FIX: Do not guess the slug for tours like 'Global Warming Tour'. Search 'site:elmocambo.com [artist name]' to find the exact long-form slug (e.g., /event/global-warming-tour-2026/).
3. HORSESHOE TAVERN FIX: Slugs for the Horseshoe often include the year or a trailing number (e.g., /event/steve-poltz-2026/ or /event/artist-name-2/). You MUST find the exact link currently active on their site.
4. DANFORTH / OPERA HOUSE FIX: Force the search to find the /[venue-domain]/events/detail/[slug] path. If no detail page exists on the official domain, use the venue's main /events or /shows page as the fallback. 
5. THE GARRISON FIX: Since this site is often a single-page list, if a specific /event/ page is not found on garrisontoronto.com, use 'http://www.garrisontoronto.com/' for every event at that venue.
6. NO 404s: Before finalizing a URL, ensure it follows the known patterns provided in the venue_map.
"""

try:
    response = client.models.generate_content(
        model="gemini-3-flash-preview", 
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )

    raw_text = response.text
    # Find everything between the first [ and the LAST ]
    json_match = re.search(r'(\[.*\])', raw_text, re.DOTALL)

    if json_match:
        clean_json = json_match.group(1)
        # Validate that it is actually valid JSON before saving
        parsed_data = json.loads(clean_json)
        
        with open("concerts.json", "w") as f:
            json.dump(parsed_data, f, indent=4)
        print(f"Success! {len(parsed_data)} concerts found.")
    else:
        print("ERROR: Gemini output did not contain a JSON list.")
        print("Raw output sample:", raw_text[:500])
        exit(1) # Forces GitHub to show the error

except Exception as e:
    print(f"CRITICAL ERROR: {str(e)}")
    exit(1)

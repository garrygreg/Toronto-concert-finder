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

# Updated Venue Mapping - Grounding the model in actual 2026 paths
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
Using Google Search, find the unique event detail URLs for upcoming concerts at these Toronto venues:
{venue_map}

Return a JSON array of objects with: "date", "artist", "url", "venue", "price", "age", "youtube_sample".

STRICT DEEP-LINKING RULES (APRIL 2026):
1. DOMAIN ENFORCEMENT: Every "url" MUST use the domain from the map (e.g., leespalace.com). NO ticketmaster.ca or livenation.com links.
2. SLUG PRECISION: Do not guess slugs. Search the venue's site for the exact permalink.
   - Example (Lee's Palace): 'https://www.leespalace.com/event/uada-mortiis-lees' (not just /uada/)
   - Example (El Mocambo): 'https://elmocambo.com/event/global-warming-2026-way-better-north-america-tour/'
   - Example (Great Hall): 'https://thegreathall.ca/event/archive-joycut/'
3. THE GARRISON: Since this venue uses a single-page list, use 'http://www.garrisontoronto.com/' for all their events.
4. THE OPERA HOUSE: Use 'https://www.theoperahousetoronto.com/events/' for all their events.
5. DANFORTH: Attempt to find the /events/detail/[slug] link. If it cannot be found on thedanforth.com, use 'https://www.thedanforth.com/shows'.
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

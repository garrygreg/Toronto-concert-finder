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

# Updated Venue Mapping - Strict Official Domains Only
venue_map = """
- Massey Hall: https://masseyhall.mhrth.com/tickets/
- History Toronto: https://www.historytoronto.com/events/detail/
- The Danforth Music Hall: https://www.thedanforth.com/events/detail/
- The Opera House: https://www.theoperahousetoronto.com/events/detail/
- Horseshoe Tavern: https://horseshoetavern.com/event/
- Lee's Palace: https://www.leespalace.com/event/
- The Garrison: https://www.garrisontoronto.com/event/
- El Mocambo: https://elmocambo.com/event/
- The Great Hall: https://thegreathall.ca/event/
- Phoenix Concert Theatre: https://thephoenixconcerttheatre.com/events/event/
"""

prompt = f"""
Find upcoming concerts for these Toronto venues from {today} to {next_year}:
{venue_map}

Return a JSON array of objects with: "date", "artist", "url", "venue", "price", "age", "youtube_sample".

STRICT URL & DOMAIN RULES:
1. FORBIDDEN DOMAINS: Never use ticketmaster.ca, livenation.com, eventbrite.ca, or dice.fm.
2. MANDATORY DOMAINS: The "url" MUST use the official domain from the map (e.g., historytoronto.com, leespalace.com).
3. DEEP LINK PATTERNS:
   - History / Danforth / Opera House: Use [domain]/events/detail/[artist-slug]
   - Horseshoe / Lee's / Garrison / El Mocambo: Use [domain]/event/[artist-slug]
4. SLUG PRECISION: For "Global Warming Tour" and other tours, search the venue's site specifically for the correct slug.
5. FALLBACK: If a deep link is not found, use the venue's main listings page on their OWN domain (e.g., https://www.historytoronto.com/events).
6. YOUTUBE: Use https://www.youtube.com/results?search_query=Artist+Name+Live (replace spaces with +).
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

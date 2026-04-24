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

# Updated Venue Mapping - Preservation + Targeted Fixes
venue_map = """
- Massey Hall: https://masseyhall.mhrth.com/tickets/
- History Toronto: https://www.historytoronto.com/events/detail/
- The Danforth Music Hall: https://www.thedanforth.com/events/detail/
- The Opera House: https://theoperahousetoronto.com/events/detail/
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

STRICT ARTIST LINK RULES (APRIL 2026):
1. PRESERVE SUCCESS: Do not change the logic for El Mocambo, History, Massey Hall, The Garrison, The Great Hall, or The Opera House.
2. HORSESHOE & LEE'S FIX: These venues MUST NOT link to the main calendar. 
   - The URL must follow: [domain]/event/[artist-slug]
   - You MUST find the exact slug by searching specifically on their sites. For example, Lee's Palace often uses slugs like 'master-boot-record' or 'outer-space-2026'.
3. PHOENIX CONCERT THEATRE: The URL pattern MUST be exactly: https://thephoenixconcerttheatre.com/events/event/[artist-slug]/
   - IMPORTANT: The trailing slash at the very end is required for the link to resolve.
4. DANFORTH MUSIC HALL: Follow the same pattern as History Toronto: https://www.thedanforth.com/events/detail/[artist-slug]
   - Search specifically for the 'More Info' link on thedanforth.com to ensure the slug is correct.
5. NO TICKETMASTER: Every link MUST stay on the official venue domain provided in the map. If a deep link is absolutely not found on the venue's domain, use the venue's main listings page on their OWN domain.
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

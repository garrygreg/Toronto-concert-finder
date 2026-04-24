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

# Updated Venue Mapping - Preservation + Final 3 Fixes
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
1. PRESERVE SUCCESS: Do not change the logic for El Mocambo, History, Massey Hall, The Garrison, The Great Hall, The Opera House, or Phoenix.
2. HORSESHOE TAVERN (FIX): Slugs almost always require a year suffix. 
   - You MUST find the exact slug (e.g., /event/steve-poltz26/ or /event/black-flag26/). 
   - If a specific show link is not found, use 'https://horseshoetavern.com/events' as the fallback.
3. LEE'S PALACE (FIX): Slugs for this venue are long and often include the tour name or year.
   - Example: 'https://www.leespalace.com/event/uada-mortiis-lees' or 'https://www.leespalace.com/event/outer-space-2026'.
   - You MUST search for the exact "More Info" link on their homepage.
4. DANFORTH MUSIC HALL (FIX): The URL MUST follow the pattern: https://www.thedanforth.com/events/detail/[slug]
   - Under no circumstances use ticketmaster.ca or livenation.com. 
   - Search specifically on thedanforth.com for the informational "Detail" page.
5. NO REDIRECTS: If you are unsure of a deep link slug, use the venue's main listings page (e.g., /events or /shows) from the venue_map above instead of guessing a broken slug.
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

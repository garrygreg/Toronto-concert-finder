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

# Updated Venue Mapping - Optimized for the final 4 broken venues
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
1. PRESERVE WORKING BEHAVIOR: Do not change the logic for Massey Hall, History, Lee's Palace, Phoenix, The Great Hall, or The Garrison.
2. DANFORTH & OPERA HOUSE FIX: These are Live Nation venues. The URL MUST follow the pattern: [domain]/events/detail/[artist-slug]. Search for the 'More Info' link on the official venue site.
3. HORSESHOE TAVERN FIX: Slugs for the Horseshoe often include a year suffix. 
   - Example: 'https://horseshoetavern.com/event/steve-poltz26' (the '26' is crucial). 
   - You MUST find the exact link active on their site, not a guessed artist name.
4. EL MOCAMBO FIX: El Mocambo uses long-form, descriptive slugs. 
   - Example: 'https://elmocambo.com/event/bo-steezy-presents-bo-with-a-side-of-steez-album-release/' 
   - Search specifically for the event title to get the full slug.
5. NO TICKETMASTER: Every link MUST be on the official venue domain provided in the map. If a deep link is absolutely missing, use the venue's general /events or /shows page on their OWN domain.
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

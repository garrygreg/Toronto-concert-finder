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

# Updated Venue Mapping with specific 2026 "Deep Link" paths
venue_map = """
- Massey Hall: https://masseyhall.mhrth.com/tickets/
- Horseshoe Tavern: https://horseshoetavern.com/event/
- Lee's Palace: https://www.leespalace.com/event/
- History Toronto: https://www.ticketmaster.ca/ (History uses Ticketmaster for deep links)
- Phoenix Concert Theatre: https://thephoenixconcerttheatre.com/events/event/
- The Danforth Music Hall: https://www.ticketmaster.ca/ (Danforth uses Ticketmaster for deep links)
- The Opera House: https://www.ticketmaster.ca/ (Opera House uses Ticketmaster for deep links)
- El Mocambo: https://elmocambo.com/
- The Garrison: http://www.garrisontoronto.com/event/
- The Great Hall: https://thegreathall.ca/event/
"""

prompt = f"""
Using Google Search, find the specific "Deep Link" for every individual concert at these venues:
{venue_map}

Return a JSON array with: "date", "artist", "url", "venue", "price", "age", "youtube_sample".

STRICT URL RULES FOR 2026:
1. MASSEY HALL: Links MUST follow the pattern https://masseyhall.mhrth.com/tickets/[artist-slug]
2. PHOENIX: Links MUST follow the pattern https://thephoenixconcerttheatre.com/events/event/[artist-slug]
3. HORSESHOE/LEE'S/GARRISON: Use the singular /event/ path (e.g., /event/artist-name).
4. THE "BIG THREE" (History, Danforth, Opera House): These venues use Ticketmaster for individual show pages. For these three venues ONLY, you MUST provide the direct Ticketmaster.ca event link.
5. NO REDIRECTS: Avoid linking to /events or /calendar. Search specifically for the "Ticket" or "Show" page for the artist.
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

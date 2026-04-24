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

# Create a mapping string to "ground" the model
venue_map = """
- Massey Hall: https://masseyhall.mhrth.com/
- Horseshoe Tavern: https://horseshoetavern.com/events
- Lee's Palace: https://www.leespalace.com/events
- History Toronto: https://www.historytoronto.com/
- Phoenix Concert Theatre: https://thephoenixconcerttheatre.com/events/
- The Danforth Music Hall: https://www.thedanforth.com/shows
- The Opera House: https://theoperahousetoronto.com/
- El Mocambo: https://elmocambo.com/
- The Garrison: http://www.garrisontoronto.com/
- The Great Hall: https://thegreathall.ca/calendar/
"""

prompt = f"""
Using Google Search, find the specific, unique event detail page for every upcoming concert at these Toronto venues from {today.isoformat()} to {next_year.isoformat()}:
{venue_map}

Return a JSON array of objects with keys: "date", "artist", "url", "venue", "price", "age", "youtube_sample".

STRICT URL REQUIREMENTS:
1. The "url" MUST be the direct 'deep link' to the individual event page (e.g., https://www.historytoronto.com/events/detail/william-black-1).
2. DO NOT simply return the venue's general calendar or home page.
3. If a direct event page cannot be found after searching, use the most specific listing page available (like the specific month's calendar), but prioritize the individual show link.
4. If multiple ticket platforms exist (Ticketmaster, Dice, etc.), prioritize the link that lives on the official venue domain first.
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

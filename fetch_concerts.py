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

# Updated Venue Mapping with specific sub-paths for April 2026
venue_map = """
- Massey Hall: https://masseyhall.mhrth.com/performances/
- Horseshoe Tavern: https://horseshoetavern.com/event/
- Lee's Palace: https://www.leespalace.com/events/detail/
- History Toronto: https://www.historytoronto.com/events/detail/
- Phoenix Concert Theatre: https://thephoenixconcerttheatre.com/events/
- The Danforth Music Hall: https://www.thedanforth.com/events/detail/
- The Opera House: https://www.theoperahousetoronto.com/events/detail/
- El Mocambo: https://elmocambo.com/
- The Garrison: http://www.garrisontoronto.com/event/
- The Great Hall: https://thegreathall.ca/event/
"""

prompt = f"""
Using Google Search, find the unique event detail URLs for upcoming concerts at these venues:
{venue_map}

Return a JSON array of objects with: "date", "artist", "url", "venue", "price", "age", "youtube_sample".

STRICT DEEP-LINKING RULES (April 2026):
1. USE THESE EXACT PATHS:
   - For History, Danforth, Opera House, and Lee's Palace: The URL MUST follow the pattern [domain]/events/detail/[slug]
   - For Horseshoe, Garrison, and Great Hall: The URL MUST follow the pattern [domain]/event/[slug]/
   - For Massey Hall: The URL MUST follow the pattern [domain]/performances/[slug]
2. DO NOT return general listing pages (like /shows or /events). Every link must lead to a page about ONE specific artist.
3. Validate each slug: Slugs usually look like 'artist-name-yyyy-mm-dd'. 
4. If a deep link is absolutely not found, use the closest 'event/' path from the venue_map above, NEVER just the homepage.
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

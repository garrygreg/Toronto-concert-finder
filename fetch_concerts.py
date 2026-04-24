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

# Updated Venue Mapping - Specific sub-pages to fix "No Records"
venue_map = """
- Massey Hall: https://masseyhall.mhrth.com/tickets/
- History Toronto: https://www.historytoronto.com/events/detail/
- The Danforth Music Hall: https://www.thedanforth.com/events/detail/
- The Opera House: https://theoperahousetoronto.com/events/
- Horseshoe Tavern: https://horseshoetavern.com/event/
- Lee's Palace: https://www.leespalace.com/event/
- The Garrison: http://www.garrisontoronto.com/
- El Mocambo: https://elmocambo.com/events-new/
- The Great Hall: https://thegreathall.ca/event/
- Phoenix Concert Theatre: https://thephoenixconcerttheatre.com/events/event/
"""

prompt = f"""
Using Google Search, find ALL upcoming concerts from {today} to {next_year} at these exact URLs:
{venue_map}

Return a JSON array of objects with: "date", "artist", "url", "venue", "price", "age", "youtube_sample".

STRICT RULES TO FIX "NO RECORDS":
1. EL MOCAMBO: Scrape https://elmocambo.com/events-new/ directly. There are many shows like 'Bo Steezy' (Apr 25) and 'KEiiNO' (May 1).
2. THE GREAT HALL: Scrape the 'event/' subpages. Look for 'Archive + JoyCut' (Apr 24) and 'Flyte' (May 13).
3. THE OPERA HOUSE: Scrape https://theoperahousetoronto.com/events/. Look for 'Drug Church' (Apr 28) and 'Unprocessed' (Apr 30).

STRICT RULES TO FIX "BROKEN URLS":
1. HORSESHOE TAVERN: Deep links almost always require the '26' suffix (e.g., /event/steve-poltz26/). Search for the 'More Info' link to get it right.
2. LEE'S PALACE: Use the singular /event/[artist-slug] pattern. Search specifically for shows like 'Master Boot Record' (Apr 26) to find the correct slug.
3. DANFORTH: The pattern MUST be https://www.thedanforth.com/events/detail/[slug]. Find the informational page on thedanforth.com, NOT ticketmaster.
4. NO TICKETMASTER: Do not use ticketmaster.ca or livenation.com for any "url". If a deep link isn't found, use the venue's Base URL from the map.
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

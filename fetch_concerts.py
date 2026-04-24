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

# Updated Venue Mapping - Forcing Official Venue Domains
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

STRICT URL RULES (APRIL 2026):
1. NO TICKETING SITES: You are STRICTLY FORBIDDEN from using URLs from ticketmaster.ca, livenation.com, dice.fm, or eventbrite.ca. 
2. DOMAIN MATCHING: Every "url" MUST exist on the venue's own domain provided in the map (e.g., historytoronto.com, thedanforth.com, etc.).
3. DEEP LINKS: You must find the specific detail page for each show. 
   - Pattern for History/Danforth/Opera House: [domain]/events/detail/[artist-slug]
   - Pattern for Horseshoe/Lee's/Garrison/Great Hall: [domain]/event/[artist-slug]/
4. EL MOCAMBO: Be extremely precise with the slug. Search for the exact event title on elmocambo.com to ensure the link works.
5. FALLBACK: If a deep link is not found, use the venue's main listings page on their OWN domain (e.g., https://www.historytoronto.com/events). NEVER use a third-party site.
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

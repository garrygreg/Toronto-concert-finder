import os
import json
import datetime
import re
from google import genai
from google.genai import types

# Initialize Client
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

today = datetime.date.today()
next_year = today + datetime.timedelta(days=364)

# These are the DIRECT listing pages where the links live
listing_pages = [
    "https://masseyhall.mhrth.com/tickets/",
    "https://www.historytoronto.com/events",
    "https://www.thedanforth.com/",
    "https://theoperahousetoronto.com/events/",
    "https://horseshoetavern.com/",
    "https://www.leespalace.com/",
    "http://www.garrisontoronto.com/",
    "https://elmocambo.com/events-new/",
    "https://thegreathall.ca/calendar/",
    "https://thephoenixconcerttheatre.com/events/"
]

prompt = f"""
Visit each of the following Toronto venue listing pages:
{', '.join(listing_pages)}

Your mission is to EXTRACT (not guess) the upcoming concert data from {today} to {next_year}.

STRICT EXTRACTION RULES:
1. URL EXTRACTION: For every concert, you MUST find the 'More Info' or 'Tickets' link on the page and extract the EXACT destination URL.
2. NO PATTERNS: Do not invent URLs. If you cannot find a direct link to an individual event page on the venue's own domain, use the venue's main listing URL as a fallback.
3. PRICE & AGE: Pull the specific price and age restriction listed next to the artist.
4. YOUTUBE: Construct the YouTube link: https://www.youtube.com/results?search_query=[Artist+Name]+Live

Return the data as a raw JSON array of objects with these keys: 
"date" (YYYY-MM-DD), "artist", "url", "venue", "price", "age", "youtube_sample".
"""

try:
    response = client.models.generate_content(
        model="gemini-2.5-flash", # Or gemini-1.5-pro for higher reasoning
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(url_context=types.UrlContext()), # This is the magic tool
                types.Tool(google_search=types.GoogleSearch())
            ]
        )
    )

    json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
    if json_match:
        data = json.loads(json_match.group(0))
        with open("concerts.json", "w") as f:
            json.dump(data, f, indent=4)
        print(f"Extraction successful! Found {len(data)} events.")
    else:
        print("Error: Could not extract JSON.")
        exit(1)

except Exception as e:
    print(f"Scraper failed: {e}")
    exit(1)

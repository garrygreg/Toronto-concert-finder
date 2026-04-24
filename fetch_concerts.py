import os
import json
import datetime
import re
from google import genai
from google.genai import types

# 1. Setup API Client
# Ensure GEMINI_API_KEY is set in your GitHub Repository Secrets
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# 2. Define Timeframe
today = datetime.date.today()
next_year = today + datetime.timedelta(days=364)

# 3. Define "Source of Truth" Listing Pages
# We point directly to the pages where the 'More Info' or 'Ticket' links live.
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

# 4. Construct the Precision Extraction Prompt
prompt = f"""
Act as a professional data scraper. Visit the following Toronto venue listing pages:
{', '.join(listing_pages)}

Your mission is to EXTRACT (not guess) all upcoming concert data from {today} to {next_year}.

STRICT EXTRACTION PROTOCOL:
1. REAL LINKS ONLY: For every concert, you MUST find the 'More Info', 'Tickets', or 'Event Detail' button in the HTML and extract the EXACT 'href' destination URL.
2. NO HALLUCINATIONS: Do not construct or guess URLs. If a specific event page link is not found on the venue's own domain, use the venue's main listing URL as a fallback.
3. DOMAIN RESTRICTION: The "url" field MUST stay on the official venue domains (e.g., thedanforth.com, historytoronto.com). NEVER provide links to ticketmaster.ca or livenation.com.
4. YOUTUBE SAMPLES: Construct a search link for each artist: https://www.youtube.com/results?search_query=[Artist+Name]+Live (replace spaces with '+').
5. DATA FIELDS: For each event, pull the "date" (YYYY-MM-DD), "artist", "url", "venue", "price", and "age" (e.g., '19+', 'All Ages', or 'TBD').

Return the result as a raw JSON array of objects.
"""

# 5. Execute with Gemini 3 Flash & URL Context
try:
    print("Starting precision extraction...")
    response = client.models.generate_content(
        model="gemini-3-flash-preview", 
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[
                # This tool allows Gemini to 'read' the listing_pages URLs
                types.Tool(url_context=types.UrlContext()),
                types.Tool(google_search=types.GoogleSearch())
            ],
            # Enables the model to 'reason' through complex HTML structures
            thinking_config={'include_thoughts': True}
        )
    )

    # 6. Parse and Clean the Output
    # We use Regex to ensure we grab only the JSON array even if Gemini adds text.
    json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
    
    if json_match:
        concert_data = json.loads(json_match.group(0))
        
        # Save to concerts.json for the website to read
        with open("concerts.json", "w") as f:
            json.dump(concert_data, f, indent=4)
            
        print(f"Successfully extracted {len(concert_data)} events.")
        
    else:
        print("Error: The model did not return a valid JSON array.")
        # Print the response text for debugging in GitHub Actions logs
        print("Model Response:", response.text)
        exit(1)

except Exception as e:
    print(f"Scraper encountered a fatal error: {e}")
    exit(1)

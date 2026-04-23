import os
import json
import datetime
from google import genai
from google.genai import types

# 1. Initialize Gemini Client
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# 2. Calculate Date Range
today = datetime.date.today()
next_year = today + datetime.timedelta(days=364)

# 3. Define the Venues
venues = [
    "Massey Hall", "Horseshoe Tavern", "Lee's Palace", "History Toronto", 
    "Phoenix Concert Theatre", "The Danforth Music Hall", "The Opera House", 
    "El Mocambo", "The Garrison", "The Great Hall"
]

# 4. Construct the Prompt
prompt = f"""
Thoroughly scour the official websites for these Toronto venues: {', '.join(venues)}.
Exhaustively list ALL upcoming events from {today.isoformat()} through {next_year.isoformat()}.

Return a JSON array of objects with these keys: 
"date" (YYYY-MM-DD), "time", "artist", "price", "venue", "age", "youtube_sample".

Rules:
1. Each set or show must be its own record. 
2. Replace any internal pipes (|) with forward slashes (/).
3. Use "TBD" for any missing details (time, price, age).
4. The "youtube_sample" value MUST be: https://www.youtube.com/results?search_query=[artist+name]+playing+live
5. Only include venues with a capacity of 5,000 or less.
"""

# 5. Call Gemini with Search Grounding
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        response_mime_type="application/json"
    )
)

# 6. Save directly to concerts.json
with open("concerts.json", "w") as f:
    f.write(response.text)

print(f"Update complete: {today.isoformat()}")

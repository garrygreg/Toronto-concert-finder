import os
import json
import re
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def get_data():
    prompt = """
    Visit https://elmocambo.com/events-new/ and extract upcoming concerts.
    Return a raw JSON array: "date" (YYYY-MM-DD), "artist", "url", "venue", "price", "age".
    """
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(url_context=types.UrlContext())]
            )
        )
        # Find the JSON block and print ONLY that
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            print(json_match.group(0))
        else:
            # If no JSON, print an empty array so Master doesn't crash
            print("[]")
    except:
        print("[]")

if __name__ == "__main__":
    get_data()

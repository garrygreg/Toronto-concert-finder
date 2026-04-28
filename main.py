import os
import json
import subprocess
import datetime
import re
import urllib.parse

CONCERTS_FILE = "concerts.json"
VENUES_DIR = "venues"
BANNED_DOMAINS = ["ticketmaster", "livenation", "eventbrite", "dice.fm", "showpass", "universe.com", "ticketweb"]

def clean_price(price_str):
    if not price_str or "Check Venue" in str(price_str):
        return "Check Venue"
    prices = re.findall(r'\d+(?:\.\d{2})?', str(price_str))
    if not prices: return "Check Venue"
    price_floats = sorted(list(set([float(p) for p in prices])))
    if len(price_floats) > 1:
        return f"${price_floats[0]:,.2f}+"
    return f"${price_floats[0]:,.2f}"

def main():
    print(f"--- Starting Scrape: {datetime.datetime.now()} ---")
    
    # 1. Calculate the '2 Years Ago' date for YouTube filtering
    two_years_ago = (datetime.date.today() - datetime.timedelta(days=730)).isoformat()
    
    all_data = []
    venue_scripts = [f for f in os.listdir(VENUES_DIR) if f.endswith(".py") and f != "__init__.py"]
    
    for script in venue_scripts:
        script_path = os.path.join(VENUES_DIR, script)
        print(f"Executing: {script}...")
        try:
            result = subprocess.run(["python", script_path], capture_output=True, text=True, env=os.environ)
            raw_output = result.stdout.strip()
            json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)

            if json_match:
                venue_data = json.loads(json_match.group(0))
                for concert in venue_data:
                    is_banned = any(banned in concert.get('url', '').lower() for banned in BANNED_DOMAINS)
                    if not is_banned:
                        # Price Logic (Locked)
                        concert['price'] = clean_price(concert.get('price'))
                        
                        # 2. YOUTUBE RESTORATION + 2-YEAR FILTER
                        # We add 'after:YYYY-MM-DD' to the search query
                        query_text = f"{concert.get('artist')} playing live after:{two_years_ago}"
                        artist_query = urllib.parse.quote_plus(query_text)
                        concert['youtube_sample'] = f"https://www.youtube.com/results?search_query={artist_query}"
                        
                        all_data.append(concert)
        except Exception as e:
            print(f"   FAILED {script}: {e}")

    # Deduplicate
    unique_list = []
    seen = set()
    for c in all_data:
        key = f"{c.get('date')}-{c.get('artist')}-{c.get('url')}"
        if key not in seen:
            unique_list.append(c)
            seen.add(key)
            
    # Sort and Transform for Display (Locked)
    unique_list.sort(key=lambda x: x.get('date', '9999-12-31'))
    for entry in unique_list:
        try:
            raw_date = entry.get('date')
            date_obj = datetime.datetime.strptime(raw_date, "%Y-%m-%d")
            pretty_date = date_obj.strftime("%A, %B %d, %Y")
            entry['date'] = f'<span style="display:none">{raw_date}</span>{pretty_date}'
        except: continue

    with open(CONCERTS_FILE, "w") as f:
        json.dump(unique_list, f, indent=4)
    
    print(f"--- Scrape Complete: {len(unique_list)} Total Events Saved ---")

if __name__ == "__main__":
    main()

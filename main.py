import os
import json
import subprocess
import datetime
import re

CONCERTS_FILE = "concerts.json"
VENUES_DIR = "venues"
BANNED_DOMAINS = ["ticketmaster", "livenation", "eventbrite", "dice.fm", "showpass", "universe.com", "ticketweb"]

def main():
    print(f"--- Starting Scrape: {datetime.datetime.now()} ---")
    
    if not os.path.exists(VENUES_DIR):
        print(f"ERROR: Folder '{VENUES_DIR}' not found!")
        return

    all_data = []
    venue_scripts = [f for f in os.listdir(VENUES_DIR) if f.endswith(".py") and f != "__init__.py"]
    
    for script in venue_scripts:
        script_path = os.path.join(VENUES_DIR, script)
        print(f"Executing: {script}...")
        
        try:
            result = subprocess.run(
                ["python", script_path], 
                capture_output=True, 
                text=True,
                env=os.environ 
            )
            
            raw_output = result.stdout.strip()
            json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)

            if json_match:
                venue_data = json.loads(json_match.group(0))
                
                count = 0
                for concert in venue_data:
                    is_banned = any(banned in concert.get('url', '').lower() for banned in BANNED_DOMAINS)
                    if not is_banned:
                        all_data.append(concert)
                        count += 1
                print(f"   Success: Added {count} events.")
            else:
                print(f"   ERROR: {script} returned no JSON.")
                if result.stderr:
                    print(f"   Logs: {result.stderr.strip()}")

        except Exception as e:
            print(f"   FAILED to execute {script}: {e}")

    # 1. Deduplicate
    unique_list = []
    seen = set()
    for c in all_data:
        key = f"{c.get('date')}-{c.get('artist')}"
        if key not in seen:
            unique_list.append(c)
            seen.add(key)
            
    # 2. Sort by raw ISO date (YYYY-MM-DD)
    unique_list.sort(key=lambda x: x.get('date', '9999-12-31'))

    # 3. TRANSFORMATION: Add Day of the Week
    # We do this AFTER sorting so alphabetical 'Monday' doesn't ruin the order
    for entry in unique_list:
        try:
            raw_date = entry.get('date')
            date_obj = datetime.datetime.strptime(raw_date, "%Y-%m-%d")
            # This turns '2026-04-27' into 'Monday, April 27, 2026'
            entry['date'] = date_obj.strftime("%A, %B %d, %Y")
        except (ValueError, TypeError):
            continue

    # 4. Save to file
    with open(CONCERTS_FILE, "w") as f:
        json.dump(unique_list, f, indent=4)
    
    print(f"--- Scrape Complete: {len(unique_list)} Total Events Saved ---")

if __name__ == "__main__":
    main()

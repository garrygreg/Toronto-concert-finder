import os
import json
import subprocess
import datetime

# Configuration
CONCERTS_FILE = "concerts.json"
VENUES_DIR = "venues"  # Folder containing your venue-specific scripts
BANNED_DOMAINS = ["ticketmaster", "livenation", "eventbrite", "dice.fm", "showpass"]

def main():
    print(f"--- Starting Scrape: {datetime.datetime.now()} ---")
    
    # 1. Reset/Empty the concerts.json file
    with open(CONCERTS_FILE, "w") as f:
        json.dump([], f)
    
    all_data = []

    # 2. Get all venue scripts (ending in .py)
    venue_scripts = [f for f in os.listdir(VENUES_DIR) if f.endswith(".py")]
    
    for script in venue_scripts:
        script_path = os.path.join(VENUES_DIR, script)
        print(f"Executing: {script}...")
        
        try:
            # Run the sub-script and capture its output
            result = subprocess.run(
                ["python", script_path], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # The sub-script should print its JSON array to the console
            venue_concerts = json.loads(result.stdout)
            
            # 3. Apply Banned Domain Filter
            filtered_concerts = []
            for concert in venue_concerts:
                if not any(banned in concert.get('url', '').lower() for banned in BANNED_DOMAINS):
                    filtered_concerts.append(concert)
                else:
                    # Fallback to venue homepage if deep link was banned
                    # This logic assumes the sub-script passes back the venue_url too
                    pass 
            
            all_data.extend(filtered_concerts)
            print(f"   Success: Found {len(filtered_concerts)} events.")

        except Exception as e:
            print(f"   FAILED {script}: {e}")
            if result.stderr:
                print(f"   Error details: {result.stderr}")

    # 4. Save final consolidated data
    # Deduplicate and sort by date
    unique_data = []
    seen = set()
    for c in all_data:
        key = f"{c.get('date')}-{c.get('artist')}"
        if key not in seen:
            unique_concerts.append(c)
            seen.add(key)
            
    all_data.sort(key=lambda x: x.get('date', '9999-12-31'))

    with open(CONCERTS_FILE, "w") as f:
        json.dump(all_data, f, indent=4)
    
    print(f"--- Scrape Complete: {len(all_data)} Total Events Saved ---")

if __name__ == "__main__":
    main()

import os
import json
import subprocess
import datetime

CONCERTS_FILE = "concerts.json"
VENUES_DIR = "venues"
BANNED_DOMAINS = ["ticketmaster", "livenation", "eventbrite", "dice.fm", "showpass"]

def main():
    print(f"--- Starting Scrape: {datetime.datetime.now()} ---")
    
    # Ensure the venues directory exists
    if not os.path.exists(VENUES_DIR):
        print(f"ERROR: Folder '{VENUES_DIR}' not found!")
        return

    all_data = []
    venue_scripts = [f for f in os.listdir(VENUES_DIR) if f.endswith(".py")]
    
    for script in venue_scripts:
        script_path = os.path.join(VENUES_DIR, script)
        print(f"Executing: {script}...")
        
        try:
            # Capture output
            result = subprocess.run(
                ["python", script_path], 
                capture_output=True, 
                text=True
            )
            
            # DEBUG: Print what the sub-script actually said
            # This will show up in your GitHub Action logs
            raw_output = result.stdout.strip()
            print(f"   Raw output from {script}: {raw_output[:100]}...") 

            if not raw_output:
                print(f"   WARNING: {script} returned absolutely nothing.")
                continue

            venue_concerts = json.loads(raw_output)
            
            # Filter and Add
            count = 0
            for concert in venue_concerts:
                is_banned = any(banned in concert.get('url', '').lower() for banned in BANNED_DOMAINS)
                if not is_banned:
                    all_data.append(concert)
                    count += 1
            
            print(f"   Success: Added {count} events.")

        except Exception as e:
            print(f"   FAILED to parse {script}: {e}")
            print(f"   Sub-script Error Log: {result.stderr}")

    # Deduplicate and Save
    final_list = []
    seen = set()
    for c in all_data:
        key = f"{c.get('date')}-{c.get('artist')}"
        if key not in seen:
            final_list.append(c)
            seen.add(key)
            
    final_list.sort(key=lambda x: x.get('date', '9999-12-31'))

    with open(CONCERTS_FILE, "w") as f:
        json.dump(final_list, f, indent=4)
    
    print(f"--- Scrape Complete: {len(final_list)} Total Events Saved ---")

if __name__ == "__main__":
    main()

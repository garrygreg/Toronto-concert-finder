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
    # Ignore __init__.py and non-python files
    venue_scripts = [f for f in os.listdir(VENUES_DIR) if f.endswith(".py") and f != "__init__.py"]
    
    for script in venue_scripts:
        script_path = os.path.join(VENUES_DIR, script)
        print(f"Executing: {script}...")
        
        try:
            # Explicitly pass environment variables (API Key) to the sub-process
            result = subprocess.run(
                ["python", script_path], 
                capture_output=True, 
                text=True,
                env=os.environ 
            )
            
            raw_output = result.stdout.strip()
            # Look for the JSON array in the output
            json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)

            if json_match:
                venue_data = json.loads(json_match.group(0))
                
                if not venue_data:
                    print(f"   Warning: {script} returned an empty list [].")
                    if result.stderr:
                        print(f"   Diagnostic Logs (stderr): {result.stderr.strip()}")
                
                count = 0
                for concert in venue_data:
                    # Filter out banned ticketing domains
                    is_banned = any(banned in concert.get('url', '').lower() for banned in BANNED_DOMAINS)
                    if not is_banned:
                        all_data.append(concert)
                        count += 1
                print(f"   Success: Added {count} events.")
            else:
                print(f"   ERROR: {script} returned no JSON array.")
                if result.stderr:
                    print(f"   Diagnostic Logs (stderr): {result.stderr.strip()}")
                elif raw_output:
                    print(f"   Raw Output (first 100 chars): {raw_output[:100]}")

        except Exception as e:
            print(f"   FAILED to execute {script}: {e}")

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

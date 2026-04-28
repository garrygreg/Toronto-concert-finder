import os
import json
import subprocess
import datetime
import re

CONCERTS_FILE = "concerts.json"
VENUES_DIR = "venues"
BANNED_DOMAINS = ["ticketmaster", "livenation", "eventbrite", "dice.fm", "showpass", "universe.com", "ticketweb"]

def clean_price(price_str):
    """
    Applies logic: [Price] if singular, [Lowest]+ if multiple, 
    'Check Venue' if missing.
    """
    if not price_str or "Check Venue" in str(price_str):
        return "Check Venue"
    
    # Extract all numbers/prices from the string (e.g., "$25.00", "30")
    # Matches decimals and whole numbers
    prices = re.findall(r'\d+(?:\.\d{2})?', str(price_str))
    
    if not prices:
        return "Check Venue"
    
    # Convert to floats for comparison
    price_floats = [float(p) for p in prices]
    
    if len(price_floats) > 1:
        lowest = min(price_floats)
        # Format back to currency string
        return f"${lowest:,.2f}+"
    else:
        # Singular price
        return f"${price_floats[0]:,.2f}"

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
                        # --- PRICE REFINEMENT ---
                        concert['price'] = clean_price(concert.get('price'))
                        
                        all_data.append(concert)
                        count += 1
                print(f"   Success: Added {count} events.")
            else:
                print(f"   ERROR: {script} returned no JSON.")

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
    for entry in unique_list:
        try:
            raw_date = entry.get('date')
            date_obj = datetime.datetime.strptime(raw_date, "%Y-%m-%d")
            entry['date'] = date_obj.strftime("%A, %B %d, %Y")
        except:
            continue

    with open(CONCERTS_FILE, "w") as f:
        json.dump(unique_list, f, indent=4)
    
    print(f"--- Scrape Complete: {len(unique_list)} Total Events Saved ---")

if __name__ == "__main__":
    main()

import os
import json
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIGURATION ---
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
SERVICE_ACCOUNT_JSON = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))

# Target niches to search in Doha
NICHES = ["clinics", "beauty salons", "gyms", "landscaping company", "nursery","cafeteria","super market","grocery store"]
DOHA_COORDS = "25.2854,51.5310"
RADIUS = "15000" # 15km search radius

def get_automated_leads():
    # 1. Access Google Sheet
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_JSON, scope)
    client = gspread.authorize(creds)
    
    try:
        sheet = client.open("Doha Leads").sheet1
    except Exception as e:
        print(f"CRITICAL ERROR: Could not open sheet: {e}")
        return 0

    # Get existing Place IDs from Column H to avoid duplicates
    existing_ids = sheet.col_values(8) 
    new_leads_to_add = []

    for niche in NICHES:
        print(f"--- Searching for: {niche} ---")
        search_url = (
            f"https://maps.googleapis.com/maps/api/place/textsearch/json?"
            f"query={niche}+in+Doha&location={DOHA_COORDS}&radius={RADIUS}&key={GOOGLE_API_KEY}"
        )
        
        response = requests.get(search_url).json()
        status = response.get("status")
        results = response.get('results', [])
        
        print(f"Google Status: {status} | Found {len(results)} total results.")

        if status == "REQUEST_DENIED":
            print(f"Error Message: {response.get('error_message')}")
            continue

        for place in results:
            pid = place['place_id']
            
            # Skip if already in our database
            if pid in existing_ids:
                continue
            
            # Check business details
            details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={pid}&fields=name,formatted_phone_number,website,user_ratings_total,rating&key={GOOGLE_API_KEY}"
            details = requests.get(details_url).json().get('result', {})

            # LEAD FILTER: No Website + Must have a Phone Number
            website = details.get('website')
            phone = details.get('formatted_phone_number')

            if not website and phone:
                reviews = details.get('user_ratings_total', 0)
                rating = details.get('rating', 0)
                address = details.get('formatted_address', 'No Address') # Added this

                # Order must match: Name, Phone, Address, Reviews, Rating, Niche, Date
                lead_data = [
                    details.get('name'),          # 1. Name
                    phone,                         # 2. Phone
                    address,                       # 3. Address
                    reviews,                       # 4. Reviews
                    rating,                        # 5. Rating
                    niche,                         # 6. Niche
                    datetime.now().strftime("%Y-%m-%d"), # 7. Date Found
                    pid                            # 8. Place ID (for deduplication check)
                ]
                new_leads_to_add.append(lead_data)                
                print(f"Added: {details.get('name')} ({reviews} reviews)")
    # 3. Save to Sheet
    if new_leads_to_add:
        sheet.append_rows(new_leads_to_add)
        return len(new_leads_to_add)
    
    return 0

if __name__ == "__main__":
    count = get_automated_leads()
    print(f"\nFinal Result: {count} new leads added to the sheet.")

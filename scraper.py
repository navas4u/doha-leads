import os
import json
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Setup
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
SERVICE_ACCOUNT_JSON = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))

def get_automated_leads():
    # 1. Access Google Sheet
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_JSON, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Doha Leads").sheet1
    
    # 2. Get existing Place IDs to avoid duplicates
    # We assume Column H (index 8) stores the unique Place ID
    existing_ids = sheet.col_values(8) 

    new_leads_to_add = []
    niches = ["clinics", "beauty salons", "gyms", "landscaping"]
    
    for niche in niches:
        search_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={niche}+in+Doha&key={GOOGLE_API_KEY}"
        results = requests.get(search_url).json().get('results', [])

        for place in results:
            pid = place['place_id']
            
            # CHECK: Skip if we already have this business
            if pid in existing_ids:
                continue
            
            # Get details to check for website
            details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={pid}&fields=name,formatted_phone_number,website,user_ratings_total&key={GOOGLE_API_KEY}"
            details = requests.get(details_url).json().get('result', {})

            if not details.get('website'):
                reviews = details.get('user_ratings_total', 0)
                lead_data = [
                    details.get('name'),
                    details.get('formatted_phone_number', 'N/A'),
                    niche,
                    reviews,
                    "Hot Lead" if reviews > 20 else "Cold Lead",
                    datetime.now().strftime("%Y-%m-%d"),
                    f"https://www.google.com/maps/place/?q=place_id:{pid}",
                    pid # This is our unique key for deduplication
                ]
                new_leads_to_add.append(lead_data)

    # 3. Batch append only the truly NEW leads
    if new_leads_to_add:
        sheet.append_rows(new_leads_to_add)
        return len(new_leads_to_add)
    return 0

if __name__ == "__main__":
    count = get_automated_leads()
    print(f"Workflow finished. Added {count} new unique leads.")

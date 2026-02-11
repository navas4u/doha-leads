import os
import json
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# 1. Setup APIs
GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
SERVICE_ACCOUNT_JSON = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))

# 2. Define Niches in Doha
NICHES = ["clinics", "beauty salons", "restaurants", "car repair", "cleaning services"]
LOCATION = "25.2854,51.5310" # Doha Coordinates

def get_no_website_leads():
    leads = []
    for niche in NICHES:
        # Search for the niche in Doha
        search_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={niche}+in+Doha&key={GOOGLE_API_KEY}"
        results = requests.get(search_url).json().get('results', [])
        
        for place in results:
            place_id = place['place_id']
            # Get Details (Specifically checking for website)
            details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=name,formatted_phone_number,formatted_address,website,rating,user_ratings_total&key={GOOGLE_API_KEY}"
            details = requests.get(details_url).json().get('result', {})
            
            # FILTER: If NO website exists, it's a lead
            if not details.get('website'):
                leads.append([
                    details.get('name'),
                    details.get('formatted_phone_number', 'N/A'),
                    details.get('formatted_address', 'N/A'),
                    details.get('user_ratings_total', 0),
                    details.get('rating', 0),
                    niche,
                    datetime.now().strftime("%Y-%m-%d")
                ])
    return leads

def save_to_sheets(data):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_JSON, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Doha Leads").sheet1
    sheet.append_rows(data)

if __name__ == "__main__":
    new_leads = get_no_website_leads()
    if new_leads:
        save_to_sheets(new_leads)
        print(f"Added {len(new_leads)} leads to Google Sheets.")

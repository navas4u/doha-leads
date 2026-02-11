import os
import json
import gspread
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIG ---
# Replace this with your actual Google Sheet URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/126toOJXk07Lq_RIN_lTpo5YyoeqPx5RZdQbKEJYiOTw"

def send_email_notification(count):
    sender = os.getenv("SENDER_EMAIL")
    password = os.getenv("SENDER_PASSWORD")
    if not sender or not password or count == 0: return

    subject = f"🚀 Doha Leads: {count} New Prospects Found!"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2 style="color: #2e7d32;">Lead Generation Report</h2>
        <p>Your Doha Lead Machine just finished a run.</p>
        <div style="background: #f1f8e9; padding: 15px; border-radius: 8px; border-left: 5px solid #4caf50;">
            <b>Results:</b> {count} new leads added to your list.
        </div>
        <p><a href="{SHEET_URL}" style="display: inline-block; background-color: #4CAF50; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin-top: 15px;">Open Google Sheet</a></p>
        <p style="font-size: 12px; color: #888;">Note: This scan used your personal API credentials.</p>
      </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = f"Doha Lead Bot <{sender}>"
    msg['To'] = sender
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        print("✅ Success: Email notification sent.")
    except Exception as e:
        print(f"❌ Email Error: {e}")

def get_automated_leads():
    # 1. AUTHENTICATION
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    SERVICE_ACCOUNT_JSON = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_JSON, scope)
    client = gspread.authorize(creds)
    
    try:
        full_sheet = client.open("Doha Leads")
        # 2. READ SETTINGS FROM SHEET
        settings_tab = full_sheet.worksheet("Settings")
        NICHES = [n.strip() for n in settings_tab.acell('B1').value.split(',')]
        COORDS = settings_tab.acell('B2').value
        RADIUS = settings_tab.acell('B3').value
        
        main_sheet = full_sheet.sheet1
    except Exception as e:
        print(f"Sheet Error: {e}"); return 0

    existing_ids = main_sheet.col_values(8) 
    new_leads = []
    google_key = os.getenv("GOOGLE_MAPS_API_KEY")

    # 3. SCRAPING LOOP
    for niche in NICHES:
        search_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={niche}&location={COORDS}&radius={RADIUS}&key={google_key}"
        results = requests.get(search_url).json().get('results', [])

        for place in results:
            pid = place['place_id']
            if pid in existing_ids: continue
            
            details_url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={pid}&fields=name,formatted_phone_number,formatted_address,website,user_ratings_total,rating&key={google_key}"
            details = requests.get(details_url).json().get('result', {})

            # Your filter: No website, has phone
            if not details.get('website') and details.get('formatted_phone_number'):
                new_leads.append([
                    details.get('name'),
                    details.get('formatted_phone_number'),
                    details.get('formatted_address', 'N/A'),
                    details.get('user_ratings_total', 0),
                    details.get('rating', 0),
                    niche,
                    datetime.now().strftime("%Y-%m-%d"),
                    pid
                ])

    if new_leads:
        main_sheet.append_rows(new_leads)
        return len(new_leads)
    return 0

if __name__ == "__main__":
    count = get_automated_leads()
    if count > 0:
        send_email_notification(count)
    else:
        print("No new leads found today.")

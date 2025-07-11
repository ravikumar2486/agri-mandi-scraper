import os
import json
import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# ✅ Get today's date in required format (e.g. 07-Jul-2025)
today_str = datetime.now().strftime("%d-%b-%Y")

# ✅ Write credentials from environment variable to a temp file
firebase_json_str = os.environ.get("FIREBASE_CREDENTIALS_JSON")

if not firebase_json_str:
    with open("authenticationapp-c3711-firebase-adminsdk-fbsvc-f96d0b7bf3.json") as f:
        firebase_json_str = f.read()
    with open("temp_firebase.json", "w") as f:
        f.write(firebase_json_str)

# ✅ Initialize Firebase
cred = credentials.Certificate("temp_firebase.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ✅ Define scraping function
def scrape_agmarknet():
    # 🔗 Insert today's date dynamically in the URL
    url = f"https://agmarknet.gov.in/SearchCmmMkt.aspx?Tx_Commodity=78&Tx_State=RJ&Tx_District=0&Tx_Market=0&DateFrom={today_str}&DateTo={today_str}&Fr_Date={today_str}&To_Date={today_str}&Tx_Trend=0&Tx_CommodityHead=Tomato&Tx_StateHead=Rajasthan&Tx_DistrictHead=--Select--&Tx_MarketHead=--Select--"

    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table", {"id": "cphBody_GridPriceData"})
        mandi_prices = []
        
        if table:
            rows = table.find_all("tr")[1:]
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 10:
                    mandi = {
                        "market": cols[1].text.strip(),
                        "district": cols[2].text.strip(),
                        "commodity": cols[3].text.strip(),
                        "variety": cols[4].text.strip(),
                        "grade": cols[5].text.strip(),
                        "min_price": cols[6].text.strip(),
                        "max_price": cols[7].text.strip(),
                        "modal_price": cols[8].text.strip(),
                        "date": cols[9].text.strip()
                    }
                    mandi_prices.append(mandi)
            
            for item in mandi_prices:
                doc_ref = db.collection("mandi_prices").document()
                doc_ref.set(item)
            
            print("✅ Mandi prices scraped and uploaded successfully.")
        else:
            print("❌ Data table not found on Agmarknet page.")
    else:
        print(f"❌ Failed to fetch page. Status code: {response.status_code}")

# ✅ Run scraper
if __name__ == "__main__":
    try:
        scrape_agmarknet()
    finally:
        os.remove("temp_firebase.json")

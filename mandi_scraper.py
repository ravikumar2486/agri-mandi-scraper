import os
import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta

# ✅ Write credentials from environment variable to a temp file OR read local file
firebase_json_str = os.environ.get("FIREBASE_CREDENTIALS_JSON")

if firebase_json_str:
    with open("temp_firebase.json", "w") as f:
        f.write(firebase_json_str)
    cred_file = "temp_firebase.json"
else:
    cred_file = "authenticationapp-c3711-firebase-adminsdk-fbsvc-f96d0b7bf3.json.json"

# ✅ Initialize Firebase
cred = credentials.Certificate(cred_file)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ✅ Define commodities with their Agmarknet codes
commodity_codes = {
    "Tomato": "78",
    "Potato": "80",
    "Onion": "79",
    "Wheat": "15",
    "Maize": "17",
    "Gram": "68",
    # ➕ Add more commodities with their correct codes here
}

# ✅ Date fallback logic: today, yesterday, day before yesterday
dates_to_try = []
for i in range(3):
    date_str = (datetime.today() - timedelta(days=i)).strftime('%d-%b-%Y')
    dates_to_try.append(date_str)

# ✅ Define scraping function with fallback dates
def scrape_agmarknet():
    for date in dates_to_try:
        data_found = False
        print(f"🔎 Trying date: {date}")

        for commodity_name, code in commodity_codes.items():
            url = f"https://agmarknet.gov.in/SearchCmmMkt.aspx?Tx_Commodity={code}&Tx_State=RJ&Tx_District=0&Tx_Market=0&DateFrom={date}&DateTo={date}&Fr_Date={date}&To_Date={date}&Tx_Trend=0&Tx_CommodityHead={commodity_name}&Tx_StateHead=Rajasthan&Tx_DistrictHead=--Select--&Tx_MarketHead=--Select--"
            
            response = requests.get(url)
            print(f"Fetching {commodity_name} prices for {date}...")

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                table = soup.find("table", {"id": "cphBody_GridPriceData"})
                mandi_prices = []

                if table:
                    rows = table.find_all("tr")[1:]  # Skip header
                    for row in rows:
                        cols = row.find_all("td")
                        if len(cols) >= 10:
                            mandi = {
                                "market": cols[1].text.strip(),
                                "district": cols[2].text.strip(),
                                "commodity": commodity_name,
                                "variety": cols[4].text.strip(),
                                "grade": cols[5].text.strip(),
                                "min_price": cols[6].text.strip(),
                                "max_price": cols[7].text.strip(),
                                "modal_price": cols[8].text.strip(),
                                "date": cols[9].text.strip()
                            }
                            mandi_prices.append(mandi)
                        else:
                            print("Skipping row with insufficient columns")

                    # ✅ Upload to Firestore
                    for item in mandi_prices:
                        doc_ref = db.collection("mandi_prices").document()
                        doc_ref.set(item)

                    print(f"✅ {commodity_name} prices for {date} scraped and uploaded successfully.")
                    data_found = True  # Data was found for this date
                else:
                    print(f"❌ Data table not found for {commodity_name} on {date}.")
            else:
                print(f"❌ Failed to fetch page for {commodity_name} on {date}. Status code: {response.status_code}")

        if data_found:
            print(f"✅ Data found for {date}, skipping older dates.")
            break  # Exit loop if data found for any commodity on this date

# ✅ Run scraper
if __name__ == "__main__":
    try:
        scrape_agmarknet()
    finally:
        if firebase_json_str:
            os.remove("temp_firebase.json")
